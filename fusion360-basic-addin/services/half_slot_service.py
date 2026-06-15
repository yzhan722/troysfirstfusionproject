import adsk.core
import adsk.fusion

from core.models import BodyModel
from config import ATTRIBUTE_GROUP


class HalfSlotService:
    """
    Step-1 minimal version:
    Only create a rectangle sketch on the vertical board side face.
    No tongue/groove extrusion yet.
    """

    def __init__(self, fusion_adapter):
        self.fusion = fusion_adapter

    def create(self):
        return self._create_slot_variant(full_depth=False)

    def create_full_slot(self):
        return self._create_slot_variant(full_depth=True)

    def _create_slot_variant(self, full_depth):
        self._clear_debug_log()
        selected = self.fusion.selected_bodies()
        if len(selected) < 2:
            return ["Select at least 2 bodies first."]
        selected_models = [BodyModel.from_brep_body(owner, body) for owner, body in selected]
        selected_tokens = [model.token for model in selected_models]
        variant_label = "Full Slot" if full_depth else "Half Slot"
        pair_count = 0
        detail_lines = []

        for i in range(len(selected_models)):
            for j in range(i + 1, len(selected_models)):
                current_models = self._current_models_by_tokens(selected_tokens)
                if len(current_models) <= max(i, j):
                    continue
                pair = self._detect_pair_faces(current_models[i], current_models[j])
                if not pair:
                    continue
                ok, lines = self._apply_slot_pair(pair, full_depth, variant_label)
                if ok:
                    pair_count += 1
                    detail_lines.extend(lines)
                else:
                    detail_lines.extend(lines)

        app, _ = self.fusion.get_app_ui()
        if app and app.activeViewport:
            app.activeViewport.refresh()

        if pair_count == 0:
            return ["No valid horizontal/vertical contact pair found."] + detail_lines

        return [
            f"{variant_label} completed.",
            f"Pairs processed: {pair_count}",
            "",
        ] + detail_lines

    def _current_models_by_tokens(self, ordered_tokens):
        # Fast path: refresh only the currently selected bodies. This is much
        # cheaper than rescanning the entire design for every pair we process.
        by_token = {}
        current_pairs = self.fusion.selected_bodies()
        for owner, body in current_pairs:
            token = getattr(body, "entityToken", None)
            if token:
                by_token[token] = BodyModel.from_brep_body(owner, body)

        missing = [token for token in ordered_tokens if token not in by_token]
        if missing:
            # Fallback only when selection context changed and we can no longer
            # refresh every chosen body from the active selection.
            design = self.fusion.get_active_design()
            if not design:
                return [by_token[token] for token in ordered_tokens if token in by_token]
            current_pairs = self.fusion.all_project_bodies(design)
            for owner, body in current_pairs:
                token = getattr(body, "entityToken", None)
                if token and token in missing:
                    by_token[token] = BodyModel.from_brep_body(owner, body)
        return [by_token[token] for token in ordered_tokens if token in by_token]

    def _apply_slot_pair(self, pair, full_depth, variant_label):
        horizontal_model, horizontal_face, vertical_model, vertical_face, contact = pair
        horizontal = horizontal_model.source_body
        vertical = vertical_model.source_body
        center = self._contact_center_mm(contact)
        slot_length_mm = 160.0
        short_edge_mm = min(contact["ov1"], contact["ov2"])
        slot_width_mm = short_edge_mm + 1.0
        axis = contact["axis"]
        plane_coord = contact["plane_coord"]

        horizontal_face = self._nearest_planar_face(horizontal, axis, plane_coord)
        vertical_face = self._nearest_planar_face(vertical, axis, plane_coord)
        if not horizontal_face or not vertical_face:
            return False, [f"{horizontal.name} <-> {vertical.name} | face refresh failed"]

        slot_sketch = self._draw_rect_sketch(
            body=horizontal,
            face=horizontal_face,
            center_mm=center,
            length_mm=slot_length_mm,
            width_mm=slot_width_mm,
            sketch_name="TroyPlugin_SlotSketch_{}_{}".format("Full" if full_depth else "Half", horizontal.name),
        )
        if slot_sketch is None:
            return False, [f"{horizontal.name} <-> {vertical.name} | slot sketch failed"]

        extrude_mm = horizontal_model.thickness_mm if full_depth else (horizontal_model.thickness_mm * 0.5)
        if extrude_mm < 0.1:
            extrude_mm = 0.1

        slot_ok = self._extrude_on_face(
            body=horizontal,
            face=horizontal_face,
            sketch=slot_sketch,
            distance_mm=extrude_mm,
            expected_area_mm2=(slot_length_mm * slot_width_mm),
            feature_name="TroyPlugin_SlotCut_{}".format("Full" if full_depth else "Half"),
            operation=adsk.fusion.FeatureOperations.CutFeatureOperation,
            participant_body=horizontal,
            outward_only=True,
            debug_label="slot",
            forced_sign=self._slot_cut_sign(horizontal_face, horizontal),
        )
        if not slot_ok:
            return False, [f"{horizontal.name} <-> {vertical.name} | slot cut failed"] + self._consume_debug_log()

        tongue_length_mm = 150.0
        tongue_width_mm = short_edge_mm
        tongue_height_mm = horizontal_model.thickness_mm if full_depth else ((horizontal_model.thickness_mm * 0.5) - 0.5)
        if tongue_height_mm < 0.1:
            tongue_height_mm = 0.1

        vertical_face = self._nearest_planar_face(vertical, axis, plane_coord)
        if not vertical_face:
            return False, [f"{horizontal.name} <-> {vertical.name} | tongue face refresh failed"]

        tongue_sketch = self._draw_rect_sketch(
            body=vertical,
            face=vertical_face,
            center_mm=center,
            length_mm=tongue_length_mm,
            width_mm=tongue_width_mm,
            sketch_name="TroyPlugin_TongueSketch_{}_{}".format("Full" if full_depth else "Half", vertical.name),
        )
        if tongue_sketch is None:
            return False, [f"{horizontal.name} <-> {vertical.name} | tongue sketch failed"]

        tongue_ok = self._create_joined_tongue(
            body=vertical,
            face=vertical_face,
            sketch=tongue_sketch,
            distance_mm=tongue_height_mm,
            expected_area_mm2=(tongue_length_mm * tongue_width_mm),
            feature_name="TroyPlugin_Tongue_{}".format("Full" if full_depth else "Half"),
            forced_sign=self._tongue_sign(vertical_face, horizontal, axis, plane_coord),
        )
        if not tongue_ok:
            return False, [f"{horizontal.name} <-> {vertical.name} | tongue extrude failed"] + self._consume_debug_log()

        self._write_joinery_metadata(
            horizontal=horizontal,
            vertical=vertical,
            variant="full" if full_depth else "half",
            axis=contact["axis"],
            center_mm=center,
            tongue_length_mm=tongue_length_mm,
            tongue_width_mm=tongue_width_mm,
            tongue_height_mm=tongue_height_mm,
        )

        return True, [
            "{} | {} -> {}".format(variant_label, horizontal.name, vertical.name),
            f"Slot size: {slot_width_mm:.2f} x {slot_length_mm:.2f} mm",
            f"Tongue size: {tongue_width_mm:.2f} x {tongue_length_mm:.2f} mm",
            f"Contact center: ({center[0]:.2f}, {center[1]:.2f}, {center[2]:.2f}) mm",
            f"Slot depth: {extrude_mm:.2f} mm",
            f"Tongue height: {tongue_height_mm:.2f} mm",
            "",
        ]

    def _create_joined_tongue(self, body, face, sketch, distance_mm, expected_area_mm2, feature_name, forced_sign):
        if not hasattr(self, "_debug_lines"):
            self._debug_lines = []
        native_body = getattr(body, "nativeObject", None) or body
        native_face = getattr(face, "nativeObject", None) or face
        comp = native_body.parentComponent
        if not comp:
            self._debug_lines.append("debug[tongue] comp:none")
            return False

        try:
            prof_count = sketch.profiles.count if sketch and sketch.profiles else 0
        except:
            prof_count = 0
        self._debug_lines.append(f"debug[tongue] profiles:{prof_count}")
        profile = self._best_profile(sketch, expected_area_mm2=expected_area_mm2)
        if not profile:
            self._debug_lines.append("debug[tongue] profile:none")
            return False
        try:
            area_cm2 = profile.areaProperties(adsk.fusion.CalculationAccuracy.LowCalculationAccuracy).area
            self._debug_lines.append(f"debug[tongue] profile_area_mm2:{area_cm2 * 100.0:.2f}")
        except:
            self._debug_lines.append("debug[tongue] profile_area_mm2:unknown")

        sign = 1.0 if forced_sign >= 0 else -1.0
        distance_cm = (abs(distance_mm) / 10.0) * sign
        self._debug_lines.append(f"debug[tongue] dir_ref:forced_sign sign:{sign:+.0f}")
        self._debug_lines.append(f"debug[tongue] dist_mm:{abs(distance_mm):.3f} dist_cm:{distance_cm:.4f}")

        extrudes = comp.features.extrudeFeatures
        combines = comp.features.combineFeatures
        tool_feat = None
        try:
            tool_inp = extrudes.createInput(profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            tool_inp.setDistanceExtent(False, adsk.core.ValueInput.createByReal(distance_cm))
            tool_feat = extrudes.add(tool_inp)
            tool_feat.name = feature_name + "_Tool"
            self._debug_lines.append(f"debug[tongue] success tool:{tool_feat.name}")
        except Exception as ex:
            self._debug_lines.append(f"debug[tongue] fail tool err:{ex}")
            return False

        try:
            if not tool_feat.bodies or tool_feat.bodies.count == 0:
                self._debug_lines.append("debug[tongue] tool_body:none")
                return False
            tools = adsk.core.ObjectCollection.create()
            tools.add(tool_feat.bodies.item(0))
            combine_inp = combines.createInput(native_body, tools)
            combine_inp.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
            combine_inp.isKeepToolBodies = False
            feat = combines.add(combine_inp)
            feat.name = feature_name
            self._debug_lines.append(f"debug[tongue] success combine:{feat.name}")
            return True
        except Exception as ex:
            self._debug_lines.append(f"debug[tongue] fail combine err:{ex}")
            return False

    def _write_joinery_metadata(
        self, horizontal, vertical, variant, axis, center_mm, tongue_length_mm, tongue_width_mm, tongue_height_mm
    ):
        for body, role, mate in ((horizontal, "horizontal", vertical), (vertical, "vertical", horizontal)):
            attrs = body.attributes
            attrs.add(ATTRIBUTE_GROUP, "joinery_variant", variant)
            attrs.add(ATTRIBUTE_GROUP, "joinery_role", role)
            attrs.add(ATTRIBUTE_GROUP, "joinery_axis", str(axis))
            attrs.add(ATTRIBUTE_GROUP, "joinery_center_x_mm", "{:.3f}".format(center_mm[0]))
            attrs.add(ATTRIBUTE_GROUP, "joinery_center_y_mm", "{:.3f}".format(center_mm[1]))
            attrs.add(ATTRIBUTE_GROUP, "joinery_center_z_mm", "{:.3f}".format(center_mm[2]))
            attrs.add(ATTRIBUTE_GROUP, "joinery_tongue_length_mm", "{:.3f}".format(tongue_length_mm))
            attrs.add(ATTRIBUTE_GROUP, "joinery_tongue_width_mm", "{:.3f}".format(tongue_width_mm))
            attrs.add(ATTRIBUTE_GROUP, "joinery_tongue_height_mm", "{:.3f}".format(tongue_height_mm))
            attrs.add(ATTRIBUTE_GROUP, "joinery_mate_token", mate.entityToken)

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
        normal = self._face_normal(native_face)
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

    def _face_normal(self, face):
        try:
            point = face.pointOnFace
            ok, normal = face.evaluator.getNormalAtPoint(point)
            if ok and normal and normal.length > 1e-6:
                normal.normalize()
                return normal
        except:
            pass
        plane = adsk.core.Plane.cast(face.geometry)
        if plane and plane.normal and plane.normal.length > 1e-6:
            normal = plane.normal.copy()
            normal.normalize()
            return normal
        return adsk.core.Vector3D.create(0, 0, 1)

    def _tongue_sign(self, vertical_face, horizontal_body, axis, plane_coord_mm):
        face_normal = self._face_normal(vertical_face)
        normal_axis_sign = 1.0 if [face_normal.x, face_normal.y, face_normal.z][axis] >= 0 else -1.0
        h_bbox = horizontal_body.boundingBox
        h_center_axis_mm = [
            (h_bbox.minPoint.x + h_bbox.maxPoint.x) * 5.0,
            (h_bbox.minPoint.y + h_bbox.maxPoint.y) * 5.0,
            (h_bbox.minPoint.z + h_bbox.maxPoint.z) * 5.0,
        ][axis]
        desired_axis_sign = 1.0 if h_center_axis_mm >= plane_coord_mm else -1.0
        return 1.0 if normal_axis_sign == desired_axis_sign else -1.0

    def _slot_cut_sign(self, horizontal_face, horizontal_body):
        face_normal = self._face_normal(horizontal_face)
        bbox = horizontal_body.boundingBox
        center = adsk.core.Point3D.create(
            (bbox.minPoint.x + bbox.maxPoint.x) * 0.5,
            (bbox.minPoint.y + bbox.maxPoint.y) * 0.5,
            (bbox.minPoint.z + bbox.maxPoint.z) * 0.5,
        )
        plane = adsk.core.Plane.cast(horizontal_face.geometry)
        if not plane:
            return 1.0
        to_center = adsk.core.Vector3D.create(
            center.x - plane.origin.x, center.y - plane.origin.y, center.z - plane.origin.z
        )
        return 1.0 if to_center.dotProduct(face_normal) >= 0 else -1.0

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
        toward_body=None,
        forced_sign=None,
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
        face_normal = self._face_normal(native_face)

        if forced_sign is not None:
            outward_sign = 1.0 if forced_sign >= 0 else -1.0
            self._debug_lines.append(f"debug[{debug_label}] dir_ref:forced_sign sign:{outward_sign:+.0f}")
        elif toward_body is not None:
            ref_body = getattr(toward_body, "nativeObject", None) or toward_body
            ref_bbox = ref_body.boundingBox
            ref_center = adsk.core.Point3D.create(
                (ref_bbox.minPoint.x + ref_bbox.maxPoint.x) * 0.5,
                (ref_bbox.minPoint.y + ref_bbox.maxPoint.y) * 0.5,
                (ref_bbox.minPoint.z + ref_bbox.maxPoint.z) * 0.5,
            )
            to_ref = adsk.core.Vector3D.create(
                ref_center.x - plane.origin.x, ref_center.y - plane.origin.y, ref_center.z - plane.origin.z
            )
            dot = to_ref.dotProduct(face_normal)
            # Move toward the reference body center.
            outward_sign = 1.0 if dot > 0 else -1.0
            self._debug_lines.append(f"debug[{debug_label}] dir_ref:toward_body dot:{dot:.6f}")
        elif away_from_body is not None:
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
            dot = to_ref.dotProduct(face_normal)
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
            dot = to_center.dotProduct(face_normal)
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

    def _clear_debug_log(self):
        self._debug_lines = []

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
