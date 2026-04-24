import adsk.core
import adsk.fusion
import math

from core.models import BodyModel
from config import ATTRIBUTE_GROUP


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
        candidates.sort(key=lambda c: (c["gap"], -c["ov1"] * c["ov2"]))
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

                contact_face = self._face_toward_body(horizontal, vertical, axis)
                if not contact_face:
                    continue

                target_face = self._opposite_face(horizontal, axis, contact_face)
                if not target_face:
                    continue

                face_plane = adsk.core.Plane.cast(target_face.geometry)
                if not face_plane:
                    continue
                target_plane_coord = [face_plane.origin.x * 10.0, face_plane.origin.y * 10.0, face_plane.origin.z * 10.0][axis]

                pts = self._hole_points(c, target_plane_coord)
                if not pts:
                    continue

                depth_mm = horizontal_model.thickness_mm
                inward_sign = self._inward_sign(horizontal, target_face)
                safe_pts = [p for p in pts if not self._hits_recorded_full_tongue(p, vertical, horizontal_model, axis)]
                if not safe_pts:
                    continue

                n = self._create_holes(
                    horizontal,
                    target_face,
                    safe_pts,
                    diameter_mm=3.0,
                    depth_mm=depth_mm,
                )
                if n > 0:
                    skipped = len(pts) - len(safe_pts)
                    return n, "{} <- {} | holes:{} | skipped:{} | gap:{:.3f}mm | profile:back-face".format(
                        horizontal_model.name,
                        vertical_model.name,
                        n,
                        skipped,
                        c["gap"],
                    )
        return 0, ""

    def _create_holes(self, target_body, target_face, points_mm, diameter_mm, depth_mm):
        body = getattr(target_body, "nativeObject", None) or target_body
        face = getattr(target_face, "nativeObject", None) or target_face
        comp = body.parentComponent
        if not comp:
            return 0

        depth_cm = depth_mm / 10.0
        radius_cm = (diameter_mm * 0.5) / 10.0

        sketch = comp.sketches.add(face)
        sketch.name = "TroyPlugin_HoleSketch"
        circles = sketch.sketchCurves.sketchCircles
        for p in points_mm:
            world = adsk.core.Point3D.create(p[0] / 10.0, p[1] / 10.0, p[2] / 10.0)
            sp = sketch.modelToSketchSpace(world)
            circles.addByCenterRadius(sp, radius_cm)

        expected_area_cm2 = math.pi * (radius_cm**2)
        circle_profiles = self._circle_profiles(sketch, expected_area_cm2)
        if not circle_profiles:
            return 0

        inward_sign = self._inward_sign(body, face)
        if inward_sign is None:
            return 0

        extrudes = comp.features.extrudeFeatures
        combines = comp.features.combineFeatures
        created = 0
        try:
            for idx, profile in enumerate(circle_profiles):
                tool_inp = extrudes.createInput(profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
                tool_inp.setDistanceExtent(False, adsk.core.ValueInput.createByReal(depth_cm * inward_sign))
                tool_feat = extrudes.add(tool_inp)
                tool_feat.name = "TroyPlugin_HoleToolFeature_{}".format(idx + 1)

                if not tool_feat.bodies or tool_feat.bodies.count == 0:
                    continue

                tool_bodies = adsk.core.ObjectCollection.create()
                tool_bodies.add(tool_feat.bodies.item(0))
                combine_inp = combines.createInput(body, tool_bodies)
                combine_inp.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
                combine_inp.isKeepToolBodies = False
                feat = combines.add(combine_inp)
                feat.name = "TroyPlugin_HoleFeature_{}".format(idx + 1)
                created += 1
            return created
        except:
            return 0

    def _circle_profiles(self, sketch, expected_area_cm2):
        matches = []
        tolerance = max(expected_area_cm2 * 0.25, 0.001)
        for i in range(sketch.profiles.count):
            profile = sketch.profiles.item(i)
            try:
                area = profile.areaProperties(adsk.fusion.CalculationAccuracy.LowCalculationAccuracy).area
            except:
                continue
            if abs(area - expected_area_cm2) <= tolerance:
                matches.append((abs(area - expected_area_cm2), profile))
        matches.sort(key=lambda item: item[0])
        return [profile for _, profile in matches]

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

    def _hole_points(self, c, plane_coord_mm):
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
            coords[c["axis"]] = plane_coord_mm
            coords[long_axis] = long_min + long_len * t
            coords[short_axis] = short_mid
            pts.append(coords)
        return pts

    def _face_toward_body(self, source_body, target_body, axis):
        source_bbox = source_body.boundingBox
        target_bbox = target_body.boundingBox
        source_center = [
            (source_bbox.minPoint.x + source_bbox.maxPoint.x) * 5.0,
            (source_bbox.minPoint.y + source_bbox.maxPoint.y) * 5.0,
            (source_bbox.minPoint.z + source_bbox.maxPoint.z) * 5.0,
        ]
        target_center = [
            (target_bbox.minPoint.x + target_bbox.maxPoint.x) * 5.0,
            (target_bbox.minPoint.y + target_bbox.maxPoint.y) * 5.0,
            (target_bbox.minPoint.z + target_bbox.maxPoint.z) * 5.0,
        ]
        prefer_negative = target_center[axis] < source_center[axis]

        best = None
        best_score = None
        for i in range(source_body.faces.count):
            face = source_body.faces.item(i)
            plane = adsk.core.Plane.cast(face.geometry)
            if not plane:
                continue
            normal = [abs(plane.normal.x), abs(plane.normal.y), abs(plane.normal.z)]
            n_axis = normal.index(max(normal))
            if n_axis != axis:
                continue
            coord = [plane.origin.x * 10.0, plane.origin.y * 10.0, plane.origin.z * 10.0][axis]
            outward_sign = 1 if [plane.normal.x, plane.normal.y, plane.normal.z][axis] >= 0 else -1
            score = (
                0 if ((prefer_negative and outward_sign < 0) or ((not prefer_negative) and outward_sign > 0)) else 1,
                abs(coord - target_center[axis]),
            )
            if best_score is None or score < best_score:
                best_score = score
                best = face
        return best

    def _inward_sign(self, body, face):
        plane = adsk.core.Plane.cast(face.geometry)
        if not plane:
            return None
        body_bbox = body.boundingBox
        body_center = adsk.core.Point3D.create(
            (body_bbox.minPoint.x + body_bbox.maxPoint.x) * 0.5,
            (body_bbox.minPoint.y + body_bbox.maxPoint.y) * 0.5,
            (body_bbox.minPoint.z + body_bbox.maxPoint.z) * 0.5,
        )
        to_center = adsk.core.Vector3D.create(
            body_center.x - plane.origin.x, body_center.y - plane.origin.y, body_center.z - plane.origin.z
        )
        return 1.0 if to_center.dotProduct(plane.normal) >= 0 else -1.0

    def _hits_recorded_full_tongue(self, point_mm, vertical_body, mate_model, axis):
        attrs = vertical_body.attributes
        variant = attrs.itemByName(ATTRIBUTE_GROUP, "joinery_variant")
        role = attrs.itemByName(ATTRIBUTE_GROUP, "joinery_role")
        mate = attrs.itemByName(ATTRIBUTE_GROUP, "joinery_mate_token")
        stored_axis = attrs.itemByName(ATTRIBUTE_GROUP, "joinery_axis")
        if not variant or variant.value != "full":
            return False
        if not role or role.value != "vertical":
            return False
        mate_token = getattr(mate_model, "token", None)
        if not mate_token and getattr(mate_model, "source_body", None):
            mate_token = mate_model.source_body.entityToken
        if not mate or mate.value != mate_token:
            return False
        if not stored_axis or stored_axis.value != str(axis):
            return False

        try:
            center_mm = [
                float(attrs.itemByName(ATTRIBUTE_GROUP, "joinery_center_x_mm").value),
                float(attrs.itemByName(ATTRIBUTE_GROUP, "joinery_center_y_mm").value),
                float(attrs.itemByName(ATTRIBUTE_GROUP, "joinery_center_z_mm").value),
            ]
            tongue_length_mm = float(attrs.itemByName(ATTRIBUTE_GROUP, "joinery_tongue_length_mm").value)
            tongue_width_mm = float(attrs.itemByName(ATTRIBUTE_GROUP, "joinery_tongue_width_mm").value)
        except:
            return False

        contact_face = self._face_toward_body(vertical_body, mate_model.source_body, axis)
        if not contact_face:
            return False
        plane = adsk.core.Plane.cast(contact_face.geometry)
        if not plane:
            return False

        x_axis, y_axis = self._plane_basis(plane.normal)
        delta = adsk.core.Vector3D.create(
            (point_mm[0] - center_mm[0]) / 10.0,
            (point_mm[1] - center_mm[1]) / 10.0,
            (point_mm[2] - center_mm[2]) / 10.0,
        )
        local_x_mm = delta.dotProduct(x_axis) * 10.0
        local_y_mm = delta.dotProduct(y_axis) * 10.0
        return (abs(local_x_mm) <= (tongue_width_mm * 0.5 + 1.5)) and (
            abs(local_y_mm) <= (tongue_length_mm * 0.5 + 1.5)
        )

    def _plane_basis(self, normal):
        z_axis = adsk.core.Vector3D.create(0, 0, 1)
        x_axis = z_axis.crossProduct(normal)
        if x_axis.length < 1e-6:
            y_seed = adsk.core.Vector3D.create(0, 1, 0)
            x_axis = y_seed.crossProduct(normal)
        x_axis.normalize()
        y_axis = normal.crossProduct(x_axis)
        y_axis.normalize()
        return x_axis, y_axis

    def _opposite_face(self, body, axis, reference_face):
        ref_plane = adsk.core.Plane.cast(reference_face.geometry)
        if not ref_plane:
            return None
        ref_coord = [ref_plane.origin.x * 10.0, ref_plane.origin.y * 10.0, ref_plane.origin.z * 10.0][axis]

        best = None
        best_dist = -1.0
        for i in range(body.faces.count):
            face = body.faces.item(i)
            if face == reference_face:
                continue
            plane = adsk.core.Plane.cast(face.geometry)
            if not plane:
                continue
            normal = [abs(plane.normal.x), abs(plane.normal.y), abs(plane.normal.z)]
            n_axis = normal.index(max(normal))
            if n_axis != axis:
                continue
            coord = [plane.origin.x * 10.0, plane.origin.y * 10.0, plane.origin.z * 10.0][axis]
            dist = abs(coord - ref_coord)
            if dist > best_dist:
                best_dist = dist
                best = face
        return best

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

