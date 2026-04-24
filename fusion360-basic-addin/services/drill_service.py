import adsk.core
import adsk.fusion

from core.models import BodyModel


class DrillService:
    def __init__(self, fusion_adapter):
        self.fusion = fusion_adapter

    def drill(self):
        design = self.fusion.get_active_design()
        if not design:
            return ["No active Fusion design."]

        selected = self.fusion.selected_bodies()
        if len(selected) < 2:
            return ["Select at least 2 bodies first."]
        bodies = [BodyModel.from_brep_body(owner, body) for owner, body in selected]

        pairs = 0
        holes_total = 0
        lines = []
        for i in range(len(bodies)):
            for j in range(i + 1, len(bodies)):
                a = bodies[i]
                b = bodies[j]
                created, detail = self._drill_pair(a, b)
                if detail:
                    pairs += 1
                    holes_total += created
                    lines.append(detail)

        app, _ = self.fusion.get_app_ui()
        if app and app.activeViewport:
            app.activeViewport.refresh()

        if not lines:
            lines = ["No valid side-to-front/back contact pair found."]
        return [
            f"Pairs matched: {pairs}",
            f"Holes created: {holes_total}",
            "",
        ] + lines

    def _drill_pair(self, model_a, model_b):
        body_a = model_a.source_body
        body_b = model_b.source_body
        candidates = self._contact_candidates(body_a, body_b)
        for c in candidates:
            if c["gap"] > 0.5:
                continue
            axis = c["axis"]
            for horizontal_model, vertical_model in ((model_a, model_b), (model_b, model_a)):
                horizontal = horizontal_model.source_body
                vertical = vertical_model.source_body
                h_axis = horizontal_model.thickness_axis
                v_axis = vertical_model.thickness_axis
                if h_axis != axis or v_axis == axis:
                    continue

                target_face = self._nearest_planar_face(horizontal, axis, c["plane_coord"])
                if not target_face:
                    continue

                pts = self._hole_points(c)
                if not pts:
                    continue

                n = self._create_holes(horizontal, target_face, pts, diameter_mm=3.0)
                if n > 0:
                    return n, "{} <- {} | holes:{} | gap:{:.3f}mm".format(
                        horizontal_model.name, vertical_model.name, n, c["gap"]
                    )
        return 0, ""

    def _create_holes(self, target_body, target_face, points_mm, diameter_mm):
        body = getattr(target_body, "nativeObject", None) or target_body
        face = getattr(target_face, "nativeObject", None) or target_face
        comp = body.parentComponent
        if not comp:
            return 0

        l, w, h = self.fusion.dims_mm(body)
        depth_cm = (min(l, w, h)) / 10.0
        dia_cm = diameter_mm / 10.0

        sketch = comp.sketches.add(face)
        sketch.name = "TroyPlugin_HoleSketch"
        points = adsk.core.ObjectCollection.create()
        for p in points_mm:
            world = adsk.core.Point3D.create(p[0] / 10.0, p[1] / 10.0, p[2] / 10.0)
            sp = sketch.modelToSketchSpace(world)
            points.add(sketch.sketchPoints.add(sp))

        if points.count == 0:
            return 0

        holes = comp.features.holeFeatures
        try:
            inp = holes.createSimpleInput(adsk.core.ValueInput.createByReal(dia_cm))
            inp.setPositionBySketchPoints(points)
            inp.setDistanceExtent(adsk.core.ValueInput.createByReal(depth_cm))
            feat = holes.add(inp)
            feat.name = "TroyPlugin_HoleFeature"
            return points.count
        except:
            return 0

    def _contact_candidates(self, a_body, b_body):
        a = a_body.boundingBox
        b = b_body.boundingBox
        a_min = [a.minPoint.x * 10.0, a.minPoint.y * 10.0, a.minPoint.z * 10.0]
        a_max = [a.maxPoint.x * 10.0, a.maxPoint.y * 10.0, a.maxPoint.z * 10.0]
        b_min = [b.minPoint.x * 10.0, b.minPoint.y * 10.0, b.minPoint.z * 10.0]
        b_max = [b.maxPoint.x * 10.0, b.maxPoint.y * 10.0, b.maxPoint.z * 10.0]
        out = []
        for axis in range(3):
            if a_max[axis] < b_min[axis]:
                gap = b_min[axis] - a_max[axis]
                plane_coord = (a_max[axis] + b_min[axis]) * 0.5
            elif b_max[axis] < a_min[axis]:
                gap = a_min[axis] - b_max[axis]
                plane_coord = (a_min[axis] + b_max[axis]) * 0.5
            else:
                gap = 0.0
                plane_coord = (max(a_min[axis], b_min[axis]) + min(a_max[axis], b_max[axis])) * 0.5

            plane_axes = [idx for idx in (0, 1, 2) if idx != axis]
            ov1_min = max(a_min[plane_axes[0]], b_min[plane_axes[0]])
            ov1_max = min(a_max[plane_axes[0]], b_max[plane_axes[0]])
            ov2_min = max(a_min[plane_axes[1]], b_min[plane_axes[1]])
            ov2_max = min(a_max[plane_axes[1]], b_max[plane_axes[1]])
            ov1 = ov1_max - ov1_min
            ov2 = ov2_max - ov2_min
            if ov1 <= 0 or ov2 <= 0:
                continue
            out.append(
                {
                    "axis": axis,
                    "gap": gap,
                    "plane_coord": plane_coord,
                    "plane_axes": plane_axes,
                    "ov1_min": ov1_min,
                    "ov1_max": ov1_max,
                    "ov2_min": ov2_min,
                    "ov2_max": ov2_max,
                    "ov1": ov1,
                    "ov2": ov2,
                }
            )
        return out

    def _hole_points(self, c):
        p1, p2 = c["plane_axes"][0], c["plane_axes"][1]
        len1, len2 = c["ov1"], c["ov2"]
        if len1 >= len2:
            long_axis = p1
            short_axis = p2
            long_min, long_max = c["ov1_min"], c["ov1_max"]
            short_mid = (c["ov2_min"] + c["ov2_max"]) * 0.5
        else:
            long_axis = p2
            short_axis = p1
            long_min, long_max = c["ov2_min"], c["ov2_max"]
            short_mid = (c["ov1_min"] + c["ov1_max"]) * 0.5

        long_len = long_max - long_min
        if long_len <= 0.1:
            return []

        pts = []
        for t in (1.0 / 6.0, 3.0 / 6.0, 5.0 / 6.0):
            coords = [0.0, 0.0, 0.0]
            coords[c["axis"]] = c["plane_coord"]
            coords[long_axis] = long_min + long_len * t
            coords[short_axis] = short_mid
            pts.append(coords)
        return pts

    def _nearest_planar_face(self, body, axis, plane_coord_mm):
        best = None
        best_dist = 1e9
        for i in range(body.faces.count):
            face = body.faces.item(i)
            plane = adsk.core.Plane.cast(face.geometry)
            if not plane:
                continue
            normal = [abs(plane.normal.x), abs(plane.normal.y), abs(plane.normal.z)]
            n_axis = normal.index(max(normal))
            if n_axis != axis:
                continue
            coord = [plane.origin.x * 10.0, plane.origin.y * 10.0, plane.origin.z * 10.0][axis]
            dist = abs(coord - plane_coord_mm)
            if dist < best_dist:
                best_dist = dist
                best = face
        return best

