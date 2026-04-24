import adsk.core
import adsk.fusion

from core.models import BodyModel


class HalfSlotService:
    """
    Step-1 minimal version:
    Only create a rectangle sketch on the vertical board side face.
    No tongue/groove extrusion yet.
    """

    def __init__(self, fusion_adapter):
        self.fusion = fusion_adapter

    def create(self):
        selected = self.fusion.selected_bodies()
        if len(selected) < 2:
            return ["Select at least 2 bodies first."]
        selected_models = [BodyModel.from_brep_body(owner, body) for owner, body in selected]

        pair = self._detect_pair_faces(selected_models[0], selected_models[1])
        if not pair:
            return ["No valid horizontal/vertical contact pair found."]

        horizontal_model, horizontal_face, vertical_model, vertical_face, contact = pair
        horizontal = horizontal_model.source_body
        vertical = vertical_model.source_body
        center = self._contact_center_mm(contact)
        slot_length_mm = 160.0
        short_edge_mm = min(contact["ov1"], contact["ov2"])
        slot_width_mm = short_edge_mm + 1.0

        # Slot only: sketch on horizontal contact face, then cut in.
        slot_sketch = self._draw_rect_sketch(
            body=horizontal,
            face=horizontal_face,
            center_mm=center,
            length_mm=slot_length_mm,
            width_mm=slot_width_mm,
            sketch_name="TroyPlugin_SlotSketch_{}".format(horizontal.name),
        )
        if slot_sketch is None:
            return ["Failed to create slot sketch."]

        extrude_mm = horizontal_model.thickness_mm * 0.5
        if extrude_mm < 0.1:
            extrude_mm = 0.1

        slot_ok = self._extrude_on_face(
            body=horizontal,
            face=horizontal_face,
            sketch=slot_sketch,
            distance_mm=extrude_mm,
            expected_area_mm2=(slot_length_mm * slot_width_mm),
            feature_name="TroyPlugin_SlotCut",
            operation=adsk.fusion.FeatureOperations.CutFeatureOperation,
            participant_body=horizontal,
        )
        if not slot_ok:
            return ["Slot sketch created, but slot cut failed."]

        # Tongue: sketch on vertical contact face, then extrude out.
        tongue_length_mm = 150.0
        tongue_width_mm = short_edge_mm
        tongue_height_mm = (horizontal_model.thickness_mm * 0.5) - 0.5
        if tongue_height_mm < 0.1:
            tongue_height_mm = 0.1

        tongue_sketch = self._draw_rect_sketch(
            body=vertical,
            face=vertical_face,
            center_mm=center,
            length_mm=tongue_length_mm,
            width_mm=tongue_width_mm,
            sketch_name="TroyPlugin_TongueSketch_{}".format(vertical.name),
        )
        if tongue_sketch is None:
            return ["Slot created, but tongue sketch failed."]

        tongue_ok = self._extrude_on_face(
            body=vertical,
            face=vertical_face,
            sketch=tongue_sketch,
            distance_mm=tongue_height_mm,
            expected_area_mm2=(tongue_length_mm * tongue_width_mm),
            feature_name="TroyPlugin_Tongue",
            operation=adsk.fusion.FeatureOperations.JoinFeatureOperation,
            participant_body=vertical,
            outward_only=True,
            fallback_new_body=True,
            debug_label="tongue",
            away_from_body=horizontal,
        )
        if not tongue_ok:
            return ["Slot created, but tongue extrude failed."] + self._consume_debug_log()

        app, _ = self.fusion.get_app_ui()
        if app and app.activeViewport:
            app.activeViewport.refresh()

        return [
            "Half Slot completed.",
            "Action: slot(cut) on horizontal + tongue(join) on vertical.",
            f"Horizontal body: {horizontal.name}",
            f"Vertical body: {vertical_model.name}",
            f"Slot size: {slot_width_mm:.2f} x {slot_length_mm:.2f} mm",
            f"Tongue size: {tongue_width_mm:.2f} x {tongue_length_mm:.2f} mm",
            f"Contact center: ({center[0]:.2f}, {center[1]:.2f}, {center[2]:.2f}) mm",
            f"Slot depth: {extrude_mm:.2f} mm",
            f"Tongue height: {tongue_height_mm:.2f} mm",
            f"Slot sketch owner: {horizontal.name}",
            f"Tongue sketch owner: {vertical.name}",
        ] + self._consume_debug_log()

    def _detect_pair_faces(self, model_a, model_b):
        body_a = model_a.source_body
        body_b = model_b.source_body
        candidates = self._contact_candidates(body_a, body_b)
        candidates.sort(key=lambda x: (0 if x["gap"] <= 0.5 else 1, x["gap"], -x["area"]))
        for c in candidates:
            if c["gap"] > 0.5:
                continue
            axis = c["axis"]
            orientation_scores = []
            for horizontal_model, vertical_model in ((model_a, model_b), (model_b, model_a)):
                horizontal = horizontal_model.source_body
                vertical = vertical_model.source_body
                h_axis = horizontal_model.thickness_axis
                v_axis = vertical_model.thickness_axis
                if h_axis != axis or v_axis == axis:
                    continue
                h_face = self._nearest_planar_face(horizontal, axis, c["plane_coord"])
                v_face = self._nearest_planar_face(vertical, axis, c["plane_coord"])
                if not h_face or not v_face:
                    continue
                try:
                    h_area = h_face.area
                    v_area = v_face.area
                except:
                    h_area, v_area = 0.0, 0.0
                orientation_scores.append((h_area - v_area, horizontal_model, h_face, vertical_model, v_face, c))
            if orientation_scores:
                orientation_scores.sort(key=lambda x: x[0], reverse=True)
                _, h_model, h_face, v_model, v_face, contact = orientation_scores[0]
                return h_model, h_face, v_model, v_face, contact
        return None

    def _thickness_mm(self, body):
        l, w, h = self.fusion.dims_mm(body)
        return min(l, w, h)

    def _thickness_axis(self, body):
        bbox = body.boundingBox
        min_pt = bbox.minPoint
        max_pt = bbox.maxPoint
        lens = [
            abs(max_pt.x - min_pt.x) * 10.0,
            abs(max_pt.y - min_pt.y) * 10.0,
            abs(max_pt.z - min_pt.z) * 10.0,
        ]
        return lens.index(min(lens))

    def _pick_side_face(self, body, thickness_axis):
        # Pick the largest planar face whose normal is NOT thickness axis.
        best = None
        best_area = -1.0
        for i in range(body.faces.count):
            face = body.faces.item(i)
            plane = adsk.core.Plane.cast(face.geometry)
            if not plane:
                continue
            normal = [abs(plane.normal.x), abs(plane.normal.y), abs(plane.normal.z)]
            normal_axis = normal.index(max(normal))
            if normal_axis == thickness_axis:
                continue
            try:
                area = face.area
            except:
                area = 0.0
            if area > best_area:
                best_area = area
                best = face
        return best

    def _contact_center_mm(self, contact):
        axis = contact["axis"]
        p_axes = contact["plane_axes"]
        c = [0.0, 0.0, 0.0]
        c[axis] = contact["plane_coord"]
        c[p_axes[0]] = (contact["ov1_min"] + contact["ov1_max"]) * 0.5
        c[p_axes[1]] = (contact["ov2_min"] + contact["ov2_max"]) * 0.5
        return c

    def _draw_rect_sketch(self, body, face, center_mm, length_mm, width_mm, sketch_name):
        native_body = getattr(body, "nativeObject", None) or body
        native_face = getattr(face, "nativeObject", None) or face
        comp = native_body.parentComponent
        if not comp:
            return False

        sketch = comp.sketches.add(native_face)
        sketch.name = sketch_name

        plane = adsk.core.Plane.cast(native_face.geometry)
        if not plane:
            return False

        # Build in-plane axes from face normal.
        normal = plane.normal
        z_axis = adsk.core.Vector3D.create(0, 0, 1)
        x_axis = z_axis.crossProduct(normal)
        if x_axis.length < 1e-6:
            y_axis = adsk.core.Vector3D.create(0, 1, 0)
            x_axis = y_axis.crossProduct(normal)
        x_axis.normalize()
        y_axis = normal.crossProduct(x_axis)
        y_axis.normalize()

        half_l = length_mm * 0.5
        half_w = width_mm * 0.5

        c = adsk.core.Point3D.create(center_mm[0] / 10.0, center_mm[1] / 10.0, center_mm[2] / 10.0)

        def offset_point(base, vx, dx, vy, dy):
            p = adsk.core.Point3D.create(base.x, base.y, base.z)
            p.translateBy(adsk.core.Vector3D.create(vx.x * dx + vy.x * dy, vx.y * dx + vy.y * dy, vx.z * dx + vy.z * dy))
            return p

        # Rotate rectangle orientation by 90 degrees:
        # length follows in-plane y axis, width follows in-plane x axis.
        # dx/dy are in cm (Fusion internal unit)
        p1w = offset_point(c, x_axis, -half_w / 10.0, y_axis, -half_l / 10.0)
        p2w = offset_point(c, x_axis, +half_w / 10.0, y_axis, -half_l / 10.0)
        p3w = offset_point(c, x_axis, +half_w / 10.0, y_axis, +half_l / 10.0)
        p4w = offset_point(c, x_axis, -half_w / 10.0, y_axis, +half_l / 10.0)

        p1 = sketch.modelToSketchSpace(p1w)
        p2 = sketch.modelToSketchSpace(p2w)
        p3 = sketch.modelToSketchSpace(p3w)
        p4 = sketch.modelToSketchSpace(p4w)

        lines = sketch.sketchCurves.sketchLines
        lines.addByTwoPoints(p1, p2)
        lines.addByTwoPoints(p2, p3)
        lines.addByTwoPoints(p3, p4)
        lines.addByTwoPoints(p4, p1)
        return sketch

    def _best_profile(self, sketch, expected_area_mm2=None):
        if not sketch or not sketch.profiles or sketch.profiles.count == 0:
            return None
        best = None
        if expected_area_mm2 is not None:
            best_err = float("inf")
            for i in range(sketch.profiles.count):
                prof = sketch.profiles.item(i)
                try:
                    area_cm2 = prof.areaProperties(adsk.fusion.CalculationAccuracy.LowCalculationAccuracy).area
                    area_mm2 = area_cm2 * 100.0
                except:
                    area_mm2 = 0.0
                err = abs(area_mm2 - expected_area_mm2)
                if err < best_err:
                    best_err = err
                    best = prof
            return best

        best_area = -1.0
        for i in range(sketch.profiles.count):
            prof = sketch.profiles.item(i)
            try:
                area = prof.areaProperties(adsk.fusion.CalculationAccuracy.LowCalculationAccuracy).area
            except:
                area = 0.0
            if area > best_area:
                best_area = area
                best = prof
        return best

    def _extrude_on_face(
        self,
        body,
        face,
        sketch,
        distance_mm,
        expected_area_mm2,
        feature_name,
        operation,
        participant_body,
        outward_only=False,
        fallback_new_body=False,
        debug_label="extrude",
        away_from_body=None,
    ):
        if not hasattr(self, "_debug_lines"):
            self._debug_lines = []
        native_body = getattr(body, "nativeObject", None) or body
        native_face = getattr(face, "nativeObject", None) or face
        comp = native_body.parentComponent
        if not comp:
            self._debug_lines.append(f"debug[{debug_label}] comp:none")
            return False

        try:
            prof_count = sketch.profiles.count if sketch and sketch.profiles else 0
        except:
            prof_count = 0
        self._debug_lines.append(f"debug[{debug_label}] profiles:{prof_count}")
        profile = self._best_profile(sketch, expected_area_mm2=expected_area_mm2)
        if not profile:
            self._debug_lines.append(f"debug[{debug_label}] profile:none")
            return False
        try:
            area_cm2 = profile.areaProperties(adsk.fusion.CalculationAccuracy.LowCalculationAccuracy).area
            area_mm2 = area_cm2 * 100.0
            self._debug_lines.append(f"debug[{debug_label}] profile_area_mm2:{area_mm2:.2f}")
        except:
            self._debug_lines.append(f"debug[{debug_label}] profile_area_mm2:unknown")

        extrudes = comp.features.extrudeFeatures
        plane = adsk.core.Plane.cast(native_face.geometry)
        if not plane:
            self._debug_lines.append(f"debug[{debug_label}] face_plane:none")
            return False

        if away_from_body is not None:
            ref_body = getattr(away_from_body, "nativeObject", None) or away_from_body
            ref_bbox = ref_body.boundingBox
            ref_center = adsk.core.Point3D.create(
                (ref_bbox.minPoint.x + ref_bbox.maxPoint.x) * 0.5,
                (ref_bbox.minPoint.y + ref_bbox.maxPoint.y) * 0.5,
                (ref_bbox.minPoint.z + ref_bbox.maxPoint.z) * 0.5,
            )
            to_ref = adsk.core.Vector3D.create(
                ref_center.x - plane.origin.x, ref_center.y - plane.origin.y, ref_center.z - plane.origin.z
            )
            dot = to_ref.dotProduct(plane.normal)
            # Move away from reference body center.
            outward_sign = -1.0 if dot > 0 else 1.0
            self._debug_lines.append(f"debug[{debug_label}] outward_ref:other_body dot:{dot:.6f}")
        else:
            bbox = native_body.boundingBox
            center = adsk.core.Point3D.create(
                (bbox.minPoint.x + bbox.maxPoint.x) * 0.5,
                (bbox.minPoint.y + bbox.maxPoint.y) * 0.5,
                (bbox.minPoint.z + bbox.maxPoint.z) * 0.5,
            )
            to_center = adsk.core.Vector3D.create(
                center.x - plane.origin.x, center.y - plane.origin.y, center.z - plane.origin.z
            )
            dot = to_center.dotProduct(plane.normal)
            outward_sign = 1.0 if dot < 0 else -1.0
            self._debug_lines.append(f"debug[{debug_label}] outward_ref:self_body dot:{dot:.6f}")

        signs = (outward_sign,) if outward_only else (outward_sign, -outward_sign)
        distance_cm_abs = abs(distance_mm) / 10.0
        self._debug_lines.append(
            f"debug[{debug_label}] dist_mm:{abs(distance_mm):.3f} dist_cm:{distance_cm_abs:.4f} outward_sign:{outward_sign:+.0f}"
        )
        for sign in signs:
            try:
                dist_cm = distance_cm_abs * sign
                self._debug_lines.append(
                    f"debug[{debug_label}] try op:{operation} sign:{sign:+.0f} dist_cm:{dist_cm:.4f}"
                )
                ext_inp = extrudes.createInput(profile, operation)
                ext_inp.setDistanceExtent(False, adsk.core.ValueInput.createByReal(dist_cm))
                try:
                    native_participant = getattr(participant_body, "nativeObject", None) or participant_body
                    participants = adsk.core.ObjectCollection.create()
                    participants.add(native_participant)
                    ext_inp.participantBodies = participants
                except:
                    pass
                feat = extrudes.add(ext_inp)
                feat.name = feature_name
                self._debug_lines.append(f"debug[{debug_label}] success op:{operation} name:{feat.name}")
                return True
            except Exception as ex:
                self._debug_lines.append(f"debug[{debug_label}] fail op:{operation} sign:{sign:+.0f} err:{ex}")
                continue
        # Fallback for tongue visibility: if Join fails, create as NewBody.
        if fallback_new_body:
            for sign in signs:
                try:
                    dist_cm = distance_cm_abs * sign
                    self._debug_lines.append(
                        "debug[{}] try fallback:NewBody sign:{:+.0f} dist_cm:{:.4f}".format(
                            debug_label, sign, dist_cm
                        )
                    )
                    ext_inp = extrudes.createInput(profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
                    ext_inp.setDistanceExtent(False, adsk.core.ValueInput.createByReal(dist_cm))
                    feat = extrudes.add(ext_inp)
                    feat.name = feature_name + "_NewBody"
                    self._debug_lines.append(f"debug[{debug_label}] success fallback name:{feat.name}")
                    return True
                except Exception as ex:
                    self._debug_lines.append(
                        "debug[{}] fail fallback sign:{:+.0f} err:{}".format(debug_label, sign, ex)
                    )
                    continue
        return False

    def _consume_debug_log(self):
        logs = getattr(self, "_debug_lines", [])
        self._debug_lines = []
        if not logs:
            return []
        return ["", "Debug:"] + logs

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
            ov1 = min(a_max[plane_axes[0]], b_max[plane_axes[0]]) - max(a_min[plane_axes[0]], b_min[plane_axes[0]])
            ov2 = min(a_max[plane_axes[1]], b_max[plane_axes[1]]) - max(a_min[plane_axes[1]], b_min[plane_axes[1]])
            if ov1 <= 0 or ov2 <= 0:
                continue
            out.append(
                {
                    "axis": axis,
                    "gap": gap,
                    "plane_coord": plane_coord,
                    "plane_axes": plane_axes,
                    "ov1_min": max(a_min[plane_axes[0]], b_min[plane_axes[0]]),
                    "ov1_max": min(a_max[plane_axes[0]], b_max[plane_axes[0]]),
                    "ov2_min": max(a_min[plane_axes[1]], b_min[plane_axes[1]]),
                    "ov2_max": min(a_max[plane_axes[1]], b_max[plane_axes[1]]),
                    "ov1": ov1,
                    "ov2": ov2,
                    "area": ov1 * ov2,
                }
            )
        return out

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
