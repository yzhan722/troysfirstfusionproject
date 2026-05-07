import adsk.core
import adsk.fusion

from core.overhead_geometry import (
    BOTTOM_THICKNESS_MM,
    DEFAULT_ROUTER_DIAMETER_MM,
    DIVIDER_THICKNESS_MM,
    FEATURE_GROOVE_WIDTH_MM,
    FRONT_TOP_NOTCH_Y_OFFSET_MM,
    T1_HEIGHT_MM,
    T3_THICKNESS_MM,
    T4_THICKNESS_MM,
    T4_HEIGHT_MM,
    calculate_overhead_geometry_from_internal_xds,
)


ATTRIBUTE_GROUP = "CabinetGenerator"
T1_THICKNESS_MM = 16.0
T2_THICKNESS_MM = 15.0
T1_T2_Y_ADJUST_MM = 39.0
T1_T2_Z_ADJUST_MM = 15.0
T3_Y_ADJUST_MM = -80.0
T3_Z_ADJUST_MM = 14.0


class SolidExtrudeService:
    def __init__(self, fusion_adapter):
        self.fusion = fusion_adapter

    def clear_generated(self):
        design = self.fusion.get_active_design()
        if not design:
            return ["No active Fusion design."]
        root = design.rootComponent
        if not root:
            return ["No root component found."]
        removed = self._delete_generated_solids(root)
        self.fusion.refresh_viewport()
        return [
            "Generated cabinet objects cleared.",
            "Bodies removed: {}".format(removed["bodies"]),
            "Sketches removed: {}".format(removed["sketches"]),
            "Construction planes removed: {}".format(removed["planes"]),
            "Features removed: {}".format(removed["features"]),
        ]

    def generate(self, params):
        design = self.fusion.get_active_design()
        if not design:
            return ["No active Fusion design."]
        root = design.rootComponent
        if not root:
            return ["No root component found."]

        try:
            geometry, bottom_thickness = self._geometry_from_params(params)
        except ValueError as ex:
            return [str(ex)]

        created = []
        failed = []
        self._delete_generated_solids(root)

        body = self._extrude_vector_body(
            root,
            "BP",
            self._bp_outline(geometry),
            bottom_thickness,
            "xy",
        )
        if body:
            self._move_body_min_to(root, body, 0.0, 0.0, 0.0)
            groove_cuts = self._cut_bp_grooves(root, body, geometry, bottom_thickness)
            screw_hole_cuts = self._cut_bp_screw_holes(root, body, geometry, bottom_thickness)
        else:
            groove_cuts = 0
            screw_hole_cuts = 0
        self._track_result(body, created, failed, "BP")

        body = self._extrude_vector_body(
            root,
            "T1",
            self._rail_outline(geometry, T1_HEIGHT_MM),
            T1_THICKNESS_MM,
            "xz",
        )
        if body:
            self._move_body_min_to(
                root,
                body,
                0.0,
                T1_T2_Y_ADJUST_MM,
                self._divider_top_step_z(geometry) + T1_T2_Z_ADJUST_MM,
            )
        self._track_result(body, created, failed, "T1")

        body = self._extrude_vector_body(
            root,
            "T2",
            self._rail_outline(geometry, T1_HEIGHT_MM),
            T2_THICKNESS_MM,
            "xz",
        )
        if body:
            self._move_body_min_to(
                root,
                body,
                0.0,
                T1_THICKNESS_MM + T1_T2_Y_ADJUST_MM,
                self._divider_top_step_z(geometry) + T1_T2_Z_ADJUST_MM,
            )
            t2_screw_hole_cuts = self._cut_xz_panel_screw_holes(
                root,
                body,
                geometry["panel_screw_holes"]["T2"],
                "AUTO_SOLID_SK_T2_SCREW_HOLES",
                "AUTO_SOLID_T2_SCREW_HOLE_CUT",
                "front",
            )
        else:
            t2_screw_hole_cuts = 0
        self._track_result(body, created, failed, "T2")

        body = self._extrude_vector_body(
            root,
            "T3",
            geometry["trimmed_vectors"]["T3"],
            T3_THICKNESS_MM,
            "xy",
        )
        if body:
            self._move_body_min_to(
                root,
                body,
                0.0,
                FRONT_TOP_NOTCH_Y_OFFSET_MM + 10.0 + T3_Y_ADJUST_MM,
                self._divider_top_step_z(geometry) - T3_THICKNESS_MM + T3_Z_ADJUST_MM,
            )
            t3_screw_hole_cuts = self._cut_xy_panel_screw_holes(
                root,
                body,
                geometry["panel_screw_holes"]["T3"],
                "AUTO_SOLID_SK_T3_SCREW_HOLES",
                "AUTO_SOLID_T3_SCREW_HOLE_CUT",
            )
        else:
            t3_screw_hole_cuts = 0
        self._track_result(body, created, failed, "T3")

        body = self._extrude_vector_body(
            root,
            "T4",
            self._flip_vector_y(geometry["trimmed_vectors"]["T4"], T4_HEIGHT_MM),
            T4_THICKNESS_MM,
            "xz",
        )
        if body:
            self._move_body_min_to(
                root,
                body,
                0.0,
                geometry["cabinet"]["Cd"] - T4_THICKNESS_MM,
                geometry["cabinet"]["Ch"] - T4_HEIGHT_MM,
            )
            t4_screw_hole_cuts = self._cut_xz_panel_screw_holes(
                root,
                body,
                geometry["panel_screw_holes"]["T4"],
                "AUTO_SOLID_SK_T4_SCREW_HOLES",
                "AUTO_SOLID_T4_SCREW_HOLE_CUT",
                "back",
            )
        else:
            t4_screw_hole_cuts = 0
        self._track_result(body, created, failed, "T4")

        divider_vector = self._rotate_yz_vector_90deg(geometry["trimmed_vectors"]["DividerSide"])
        for feature in geometry["divider_features"]:
            body = self._extrude_vector_body(
                root,
                feature["id"],
                divider_vector,
                DIVIDER_THICKNESS_MM,
                "yz",
            )
            if body:
                self._move_body_min_to(
                    root,
                    body,
                    feature["XDi"] - (DIVIDER_THICKNESS_MM / 2.0),
                    0.0,
                    bottom_thickness - (bottom_thickness / 2.0),
                )
            self._track_result(body, created, failed, feature["id"])

        hidden = self._hide_generated_references(root)
        self.fusion.refresh_viewport()
        return [
            "Bodies generated and positioned from closed vectors.",
            "BP groove cuts applied: {}".format(groove_cuts),
            "BP screw hole cuts applied: {}".format(screw_hole_cuts),
            "T2 screw hole cuts applied: {}".format(t2_screw_hole_cuts),
            "T3 screw hole cuts applied: {}".format(t3_screw_hole_cuts),
            "T4 screw hole cuts applied: {}".format(t4_screw_hole_cuts),
            "Reference sketches hidden: {}".format(hidden["sketches"]),
            "Reference planes hidden: {}".format(hidden["planes"]),
            "No joins were applied.",
            "Created bodies: {}".format(len(created)),
        ] + ["- {}".format(name) for name in created] + (
            ["Failed bodies: {}".format(len(failed))] + ["- {}".format(name) for name in failed] if failed else []
        )

    def _geometry_from_params(self, params):
        cw = self._positive_float(params, "width", "Cw")
        cd = self._positive_float(params, "depth", "Cd")
        ch = self._positive_float(params, "height", "Ch")
        crd = self._positive_float(params, "routerDiameter", "Crd", DEFAULT_ROUTER_DIAMETER_MM)
        bt = self._positive_float(params, "bottomThickness", "Bt", BOTTOM_THICKNESS_MM)
        internal_xds = self._parse_number_list(params.get("internalXds", ""))
        geometry = calculate_overhead_geometry_from_internal_xds(
            cabinet_width=cw,
            cabinet_depth=cd,
            cabinet_height=ch,
            internal_xds=internal_xds,
            bottom_thickness=bt,
            divider_tongue_height=bt / 2.0,
            router_diameter=crd,
            feature_width=FEATURE_GROOVE_WIDTH_MM,
        )
        return geometry, bt

    def _bp_outline(self, geometry):
        cw = geometry["cabinet"]["Cw"]
        cd = geometry["cabinet"]["Cd"]
        return [[0.0, 0.0], [cw, 0.0], [cw, cd], [0.0, cd], [0.0, 0.0]]

    def _rail_outline(self, geometry, height_mm):
        cw = geometry["cabinet"]["Cw"]
        return [[0.0, 0.0], [cw, 0.0], [cw, height_mm], [0.0, height_mm], [0.0, 0.0]]

    def _divider_top_step_z(self, geometry):
        return geometry["cabinet"]["Ch"] - geometry["bottom_panel"]["size"][2] - T1_HEIGHT_MM

    def _flip_vector_y(self, points, height_mm):
        return [[point[0], height_mm - point[1]] for point in points]

    def _rotate_yz_vector_90deg(self, points):
        # Divider profiles are drawn in local Y/Z. Rotate around the X axis:
        # local Y becomes local Z, and local Z becomes -local Y.
        return [[-point[1], point[0]] for point in points]

    def _extrude_vector_body(self, root, body_name, points, thickness_mm, sketch_plane):
        if not points:
            return None
        sketch_name = "AUTO_SOLID_SK_{}".format(body_name)
        sketch = self._new_sketch(root, sketch_name, sketch_plane)
        self._draw_closed_profile(sketch, points, "PROFILE_{}".format(body_name), sketch_plane)
        if sketch.profiles.count < 1:
            return None
        profile = sketch.profiles.item(0)

        extrudes = root.features.extrudeFeatures
        ext_input = extrudes.createInput(profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        ext_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(self.fusion.cm(thickness_mm)))
        feature = extrudes.add(ext_input)
        feature.name = "AUTO_SOLID_EXTRUDE_{}".format(body_name)
        if feature.bodies.count < 1:
            return None
        body = feature.bodies.item(0)
        body.name = body_name
        body.attributes.add(ATTRIBUTE_GROUP, "generated_by", "auto_solid_extrude")
        return body

    def _cut_bp_grooves(self, root, bp_body, geometry, bottom_thickness):
        cut_count = 0
        top_z = bottom_thickness
        sketch = self._new_offset_xy_sketch(root, "AUTO_SOLID_SK_BP_GROOVES", top_z)
        for feature in geometry["divider_features"]:
            groove = feature["bp_groove"]
            self._draw_closed_profile(
                sketch,
                [
                    [groove["x"][0], groove["y"][0]],
                    [groove["x"][1], groove["y"][0]],
                    [groove["x"][1], groove["y"][1]],
                    [groove["x"][0], groove["y"][1]],
                    [groove["x"][0], groove["y"][0]],
                ],
                groove["id"],
                "xy",
            )

        for index in range(sketch.profiles.count):
            profile = sketch.profiles.item(index)
            extrudes = root.features.extrudeFeatures
            ext_input = extrudes.createInput(profile, adsk.fusion.FeatureOperations.CutFeatureOperation)
            ext_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(-self.fusion.cm(bottom_thickness / 2.0)))
            try:
                ext_input.participantBodies = [bp_body]
            except:
                pass
            feature = extrudes.add(ext_input)
            feature.name = "AUTO_SOLID_BP_GROOVE_CUT_{}".format(index + 1)
            cut_count += 1
        return cut_count

    def _cut_bp_screw_holes(self, root, bp_body, geometry, bottom_thickness):
        cut_count = 0
        top_z = bottom_thickness
        sketch = self._new_offset_xy_sketch(root, "AUTO_SOLID_SK_BP_SCREW_HOLES", top_z)
        for feature in geometry["divider_features"]:
            for hole_index, hole in enumerate(feature["screw_holes"], start=1):
                self._draw_circle_profile(
                    sketch,
                    hole["x"],
                    hole["y"],
                    hole["diameter"],
                    "BSH_{}_{}".format(feature["id"], hole_index),
                )

        for index in range(sketch.profiles.count):
            profile = sketch.profiles.item(index)
            extrudes = root.features.extrudeFeatures
            ext_input = extrudes.createInput(profile, adsk.fusion.FeatureOperations.CutFeatureOperation)
            ext_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(-self.fusion.cm(bottom_thickness)))
            try:
                ext_input.participantBodies = [bp_body]
            except:
                pass
            feature = extrudes.add(ext_input)
            feature.name = "AUTO_SOLID_BP_SCREW_HOLE_CUT_{}".format(index + 1)
            cut_count += 1
        return cut_count

    def _cut_xz_panel_screw_holes(self, root, body, holes, sketch_name, feature_prefix, start_side, flip_v_height=None):
        cut_count = 0
        _, min_y, min_z = self._body_min_mm(body)
        _, max_y, _ = self._body_max_mm(body)
        plane_y = (min_y + max_y) / 2.0
        cut_depth = (max_y - min_y) / 2.0 + 1.0
        sketch = self._new_offset_xz_sketch(root, sketch_name, plane_y)
        for hole in holes:
            local_v = hole["center"][1]
            if flip_v_height is not None:
                local_v = flip_v_height - local_v
            self._draw_circle_at_model_point(
                sketch,
                hole["center"][0],
                plane_y,
                min_z + local_v,
                hole["diameter"],
                "{}_{}".format(feature_prefix, hole["for_divider"]),
            )

        for index in range(sketch.profiles.count):
            profile = sketch.profiles.item(index)
            positive_cut = self._add_distance_cut(root, profile, body, cut_depth, "{}_{}_POS".format(feature_prefix, index + 1))
            negative_cut = self._add_distance_cut(root, profile, body, -cut_depth, "{}_{}_NEG".format(feature_prefix, index + 1))
            if positive_cut or negative_cut:
                cut_count += 1
        return cut_count

    def _cut_xy_panel_screw_holes(self, root, body, holes, sketch_name, feature_prefix):
        cut_count = 0
        _, min_y, _ = self._body_min_mm(body)
        _, _, max_z = self._body_max_mm(body)
        cut_depth = -self._body_thickness_z_mm(body)
        sketch = self._new_offset_xy_sketch(root, sketch_name, max_z)
        for hole in holes:
            self._draw_circle_profile(
                sketch,
                hole["center"][0],
                min_y + hole["center"][1],
                hole["diameter"],
                "{}_{}".format(feature_prefix, hole["for_divider"]),
                "xy",
            )

        for index in range(sketch.profiles.count):
            profile = sketch.profiles.item(index)
            extrudes = root.features.extrudeFeatures
            ext_input = extrudes.createInput(profile, adsk.fusion.FeatureOperations.CutFeatureOperation)
            ext_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(self.fusion.cm(cut_depth)))
            try:
                ext_input.participantBodies = [body]
            except:
                pass
            feature = extrudes.add(ext_input)
            feature.name = "{}_{}".format(feature_prefix, index + 1)
            cut_count += 1
        return cut_count

    def _add_distance_cut(self, root, profile, body, depth_mm, name):
        extrudes = root.features.extrudeFeatures
        ext_input = extrudes.createInput(profile, adsk.fusion.FeatureOperations.CutFeatureOperation)
        ext_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(self.fusion.cm(depth_mm)))
        try:
            ext_input.participantBodies = [body]
        except:
            pass
        try:
            feature = extrudes.add(ext_input)
            feature.name = name
            return True
        except:
            return False

    def _new_sketch(self, root, name, sketch_plane):
        existing = root.sketches.itemByName(name)
        if existing:
            existing.deleteMe()
        if sketch_plane == "xz":
            plane = root.xZConstructionPlane
        elif sketch_plane == "yz":
            plane = root.yZConstructionPlane
        else:
            plane = root.xYConstructionPlane
        sketch = root.sketches.add(plane)
        sketch.name = name
        return sketch

    def _new_offset_xy_sketch(self, root, name, offset_z_mm):
        existing = root.sketches.itemByName(name)
        if existing:
            existing.deleteMe()
        planes = root.constructionPlanes
        plane_input = planes.createInput()
        plane_input.setByOffset(root.xYConstructionPlane, adsk.core.ValueInput.createByReal(self.fusion.cm(offset_z_mm)))
        plane = planes.add(plane_input)
        plane.name = "{}_Plane".format(name)
        sketch = root.sketches.add(plane)
        sketch.name = name
        return sketch

    def _new_offset_xz_sketch(self, root, name, offset_y_mm):
        existing = root.sketches.itemByName(name)
        if existing:
            existing.deleteMe()
        planes = root.constructionPlanes
        plane_input = planes.createInput()
        plane_input.setByOffset(root.xZConstructionPlane, adsk.core.ValueInput.createByReal(self.fusion.cm(offset_y_mm)))
        plane = planes.add(plane_input)
        plane.name = "{}_Plane".format(name)
        sketch = root.sketches.add(plane)
        sketch.name = name
        return sketch

    def _draw_closed_profile(self, sketch, points, name, sketch_plane):
        clean_points = list(points)
        if len(clean_points) > 1 and clean_points[0] == clean_points[-1]:
            clean_points = clean_points[:-1]
        if len(clean_points) < 3:
            return

        lines = sketch.sketchCurves.sketchLines
        first_point = self._point_for_plane(clean_points[0][0], clean_points[0][1], sketch_plane)
        second_point = self._point_for_plane(clean_points[1][0], clean_points[1][1], sketch_plane)
        first_line = lines.addByTwoPoints(first_point, second_point)
        first_line.name = "{}_E1".format(name)
        start_sketch_point = first_line.startSketchPoint
        previous_end = first_line.endSketchPoint

        edge_index = 2
        for point in clean_points[2:]:
            line = lines.addByTwoPoints(previous_end, self._point_for_plane(point[0], point[1], sketch_plane))
            line.name = "{}_E{}".format(name, edge_index)
            previous_end = line.endSketchPoint
            edge_index += 1

        close_line = lines.addByTwoPoints(previous_end, start_sketch_point)
        close_line.name = "{}_E{}".format(name, edge_index)

    def _draw_circle_profile(self, sketch, x_mm, y_mm, diameter_mm, name, sketch_plane="xy"):
        circle = sketch.sketchCurves.sketchCircles.addByCenterRadius(
            self._point_for_plane(x_mm, y_mm, sketch_plane),
            self.fusion.cm(diameter_mm / 2.0),
        )
        circle.name = name

    def _draw_circle_at_model_point(self, sketch, x_mm, y_mm, z_mm, diameter_mm, name):
        model_point = adsk.core.Point3D.create(
            self.fusion.cm(x_mm),
            self.fusion.cm(y_mm),
            self.fusion.cm(z_mm),
        )
        try:
            sketch_point = sketch.modelToSketchSpace(model_point)
        except:
            sketch_point = model_point
        circle = sketch.sketchCurves.sketchCircles.addByCenterRadius(
            sketch_point,
            self.fusion.cm(diameter_mm / 2.0),
        )
        circle.name = name

    def _point_for_plane(self, a, b, sketch_plane):
        # Sketch APIs expect local sketch coordinates. The construction plane
        # maps those local X/Y coordinates into model XY, XZ, or YZ space.
        return adsk.core.Point3D.create(self.fusion.cm(a), self.fusion.cm(b), 0)

    def _move_body_min_to(self, root, body, target_x_mm, target_y_mm, target_z_mm):
        min_x, min_y, min_z = self._body_min_mm(body)
        self._move_body_by_mm(
            root,
            body,
            target_x_mm - min_x,
            target_y_mm - min_y,
            target_z_mm - min_z,
        )

    def _move_body_by_mm(self, root, body, dx_mm, dy_mm, dz_mm):
        if abs(dx_mm) < 0.001 and abs(dy_mm) < 0.001 and abs(dz_mm) < 0.001:
            return
        bodies = adsk.core.ObjectCollection.create()
        bodies.add(body)
        transform = adsk.core.Matrix3D.create()
        transform.translation = adsk.core.Vector3D.create(
            self.fusion.cm(dx_mm),
            self.fusion.cm(dy_mm),
            self.fusion.cm(dz_mm),
        )
        move_input = root.features.moveFeatures.createInput(bodies, transform)
        try:
            move_input.defineAsFreeMove(transform)
        except:
            pass
        feature = root.features.moveFeatures.add(move_input)
        feature.name = "AUTO_SOLID_MOVE_{}".format(body.name)

    def _body_min_mm(self, body):
        min_pt = body.boundingBox.minPoint
        return min_pt.x * 10.0, min_pt.y * 10.0, min_pt.z * 10.0

    def _body_max_mm(self, body):
        max_pt = body.boundingBox.maxPoint
        return max_pt.x * 10.0, max_pt.y * 10.0, max_pt.z * 10.0

    def _body_thickness_y_mm(self, body):
        _, min_y, _ = self._body_min_mm(body)
        _, max_y, _ = self._body_max_mm(body)
        return (max_y - min_y) + 1.0

    def _body_thickness_z_mm(self, body):
        _, _, min_z = self._body_min_mm(body)
        _, _, max_z = self._body_max_mm(body)
        return (max_z - min_z) + 1.0

    def _hide_generated_references(self, root):
        hidden = {"sketches": 0, "planes": 0}
        for index in range(root.sketches.count):
            sketch = root.sketches.item(index)
            if sketch and sketch.name.startswith("AUTO_SOLID_SK_"):
                self._set_visible(sketch, False)
                hidden["sketches"] += 1
        for index in range(root.constructionPlanes.count):
            plane = root.constructionPlanes.item(index)
            if plane and plane.name.startswith("AUTO_SOLID_SK_"):
                self._set_visible(plane, False)
                hidden["planes"] += 1
        return hidden

    def _set_visible(self, entity, visible):
        try:
            entity.isLightBulbOn = visible
            return
        except:
            pass
        try:
            entity.isVisible = visible
        except:
            pass

    def _delete_generated_solids(self, root):
        removed = {"bodies": 0, "sketches": 0, "planes": 0, "features": 0}
        for index in range(root.features.extrudeFeatures.count - 1, -1, -1):
            feature = root.features.extrudeFeatures.item(index)
            if feature and feature.name.startswith("AUTO_SOLID_"):
                feature.deleteMe()
                removed["features"] += 1
        for index in range(root.features.moveFeatures.count - 1, -1, -1):
            feature = root.features.moveFeatures.item(index)
            if feature and feature.name.startswith("AUTO_SOLID_"):
                feature.deleteMe()
                removed["features"] += 1
        for index in range(root.bRepBodies.count - 1, -1, -1):
            body = root.bRepBodies.item(index)
            if body and self._is_auto_body(body):
                body.deleteMe()
                removed["bodies"] += 1
        for index in range(root.sketches.count - 1, -1, -1):
            sketch = root.sketches.item(index)
            if sketch and (
                sketch.name.startswith("AUTO_SOLID_SK_")
                or sketch.name.startswith("DBG_")
            ):
                sketch.deleteMe()
                removed["sketches"] += 1
        for index in range(root.constructionPlanes.count - 1, -1, -1):
            plane = root.constructionPlanes.item(index)
            if plane and plane.name.startswith("AUTO_SOLID_SK_"):
                plane.deleteMe()
                removed["planes"] += 1
        return removed

    def _is_auto_body(self, body):
        attr = body.attributes.itemByName(ATTRIBUTE_GROUP, "generated_by")
        return bool(attr and attr.value == "auto_solid_extrude")

    def _track_result(self, body, created, failed, name):
        if body:
            created.append(body.name)
        else:
            failed.append(name)

    def _positive_float(self, params, key, label, default=None):
        raw = params.get(key, default)
        try:
            value = float(raw)
        except:
            raise ValueError("{} must be a number.".format(label))
        if value <= 0:
            raise ValueError("{} must be greater than 0.".format(label))
        return value

    def _parse_number_list(self, raw_value):
        text = str(raw_value or "").strip()
        if not text:
            return []
        values = []
        for part in text.replace(";", ",").replace("，", ",").replace("[", "").replace("]", "").split(","):
            item = part.strip()
            if not item:
                continue
            try:
                values.append(float(item))
            except:
                raise ValueError("Internal divider centerlines must be numbers separated by commas.")
        return values
