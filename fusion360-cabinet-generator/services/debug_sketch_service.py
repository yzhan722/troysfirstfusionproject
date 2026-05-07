import adsk.core

from core.overhead_geometry import (
    BOTTOM_THICKNESS_MM,
    DEFAULT_ROUTER_DIAMETER_MM,
    FEATURE_GROOVE_WIDTH_MM,
    T1_HEIGHT_MM,
    T3_DEPTH_MM,
    T4_HEIGHT_MM,
    calculate_overhead_geometry_from_internal_xds,
)


class DebugSketchService:
    def __init__(self, fusion_adapter):
        self.fusion = fusion_adapter

    def generate(self, params):
        design = self.fusion.get_active_design()
        if not design:
            return ["No active Fusion design."]
        root = design.rootComponent
        if not root:
            return ["No root component found."]

        try:
            geometry = self._geometry_from_params(params)
        except ValueError as ex:
            return [str(ex)]

        view_mode = str(params.get("viewMode") or "bp").strip().lower()
        if view_mode not in ("bp", "t2", "t3", "t4", "divider", "all"):
            view_mode = "bp"
        warnings = self._edge_centerline_warnings(geometry)
        layout = self._debug_layout(geometry)
        self._delete_debug_sketches(root)
        created = []
        if view_mode in ("bp", "all"):
            self._create_bp_top_view(root, geometry, layout["bp"])
            created.append("DBG_BP_TopView")
        if view_mode in ("t3", "all"):
            self._create_t3_top_view(root, geometry, layout["t3"] if view_mode == "all" else layout["bp"])
            created.append("DBG_T3_TopView")
        if view_mode in ("t2", "all"):
            self._create_t2_front_view(root, geometry, layout["t2"] if view_mode == "all" else layout["bp"])
            created.append("DBG_T2_FrontView")
        if view_mode in ("t4", "all"):
            self._create_t4_front_view(root, geometry, layout["t4"] if view_mode == "all" else layout["bp"])
            created.append("DBG_T4_FrontView")
        if view_mode in ("divider", "all"):
            self._create_divider_side_view(root, geometry, layout["divider"] if view_mode == "all" else layout["bp"])
            created.append("DBG_Divider_SideView")
        self.fusion.refresh_viewport()

        return [
            "Debug sketches generated. No Fusion solids were created.",
            "View mode: {}".format(view_mode),
            "BP/T2/T3/T4/Divider views are closed profiles for extrusion.",
            "Sketches:",
        ] + ["- {}".format(name) for name in created] + [
            "Divider features: {}".format(len(geometry["divider_features"])),
        ] + warnings

    def _geometry_from_params(self, params):
        cw = self._positive_float(params, "width", "Cw")
        cd = self._positive_float(params, "depth", "Cd")
        ch = self._positive_float(params, "height", "Ch")
        crd = self._positive_float(params, "routerDiameter", "Crd", DEFAULT_ROUTER_DIAMETER_MM)
        bt = self._positive_float(params, "bottomThickness", "Bt", BOTTOM_THICKNESS_MM)
        fgw = FEATURE_GROOVE_WIDTH_MM
        dntg_h = bt / 2.0
        internal_xds = self._parse_number_list(params.get("internalXds", ""))
        return calculate_overhead_geometry_from_internal_xds(
            cabinet_width=cw,
            cabinet_depth=cd,
            cabinet_height=ch,
            internal_xds=internal_xds,
            bottom_thickness=bt,
            divider_tongue_height=dntg_h,
            router_diameter=crd,
            feature_width=fgw,
        )

    def _edge_centerline_warnings(self, geometry):
        features = geometry["divider_features"]
        if not features:
            return []
        cw = geometry["cabinet"]["Cw"]
        fgh = geometry["manufacturing"]["FGh"]
        expected_left = fgh
        expected_right = cw - fgh
        actual_left = features[0]["XDi"]
        actual_right = features[-1]["XDi"]
        return [
            "Auto edge XDs: left {:.2f}, right {:.2f}".format(expected_left, expected_right),
            "Actual edge XDs: left {:.2f}, right {:.2f}".format(actual_left, actual_right),
        ]

    def _debug_layout(self, geometry):
        cw = geometry["cabinet"]["Cw"]
        cd = geometry["cabinet"]["Cd"]
        return {
            "bp": (0.0, 0.0),
            "t3": (0.0, cd + 80.0),
            "t2": (0.0, cd + 220.0),
            "t4": (0.0, cd + 340.0),
            "divider": (cw + 100.0, 40.0),
        }

    def _create_bp_top_view(self, root, geometry, offset):
        cabinet = geometry["cabinet"]
        sketch = self._new_sketch(root, root.xYConstructionPlane, "DBG_BP_TopView", profiles_shown=True)
        cw = cabinet["Cw"]
        cd = cabinet["Cd"]
        self._draw_closed_xy_profile(
            sketch,
            [[0.0, 0.0], [cw, 0.0], [cw, cd], [0.0, cd], [0.0, 0.0]],
            "BP_OUTER_PROFILE",
            offset,
        )

        for feature in geometry["divider_features"]:
            groove = feature["bp_groove"]
            self._draw_closed_xy_profile(
                sketch,
                [
                    [groove["x"][0], groove["y"][0]],
                    [groove["x"][1], groove["y"][0]],
                    [groove["x"][1], groove["y"][1]],
                    [groove["x"][0], groove["y"][1]],
                    [groove["x"][0], groove["y"][0]],
                ],
                groove["id"],
                offset,
            )
            for index, hole in enumerate(feature["screw_holes"], start=1):
                self._draw_circle_xy(
                    sketch,
                    hole["x"],
                    hole["y"],
                    hole["diameter"],
                    "BSH_{}_{}".format(feature["id"], index),
                    offset,
                )

    def _create_t3_top_view(self, root, geometry, offset):
        sketch = self._new_sketch(root, root.xYConstructionPlane, "DBG_T3_TopView", profiles_shown=True)
        self._draw_closed_xy_profile(sketch, geometry["trimmed_vectors"]["T3"], "T3_TRIMMED_VECTOR", offset)
        self._draw_panel_screw_holes(sketch, geometry, "T3", offset)

    def _create_t2_front_view(self, root, geometry, offset):
        cw = geometry["cabinet"]["Cw"]
        sketch = self._new_sketch(root, root.xYConstructionPlane, "DBG_T2_FrontView", profiles_shown=True)
        self._draw_closed_xy_profile(
            sketch,
            [[0.0, 0.0], [cw, 0.0], [cw, T1_HEIGHT_MM], [0.0, T1_HEIGHT_MM], [0.0, 0.0]],
            "T2_FRONT_PROFILE",
            offset,
        )
        self._draw_panel_screw_holes(sketch, geometry, "T2", offset)

    def _create_t4_front_view(self, root, geometry, offset):
        sketch = self._new_sketch(root, root.xYConstructionPlane, "DBG_T4_FrontView", profiles_shown=True)
        self._draw_closed_xy_profile(sketch, geometry["trimmed_vectors"]["T4"], "T4_TRIMMED_VECTOR", offset)
        self._draw_panel_screw_holes(sketch, geometry, "T4", offset)

    def _create_divider_side_view(self, root, geometry, offset):
        vector = geometry["trimmed_vectors"]["DividerSide"]
        if not vector:
            return
        min_z = min(point[1] for point in vector)
        side_offset = (offset[0], offset[1] - min_z)
        sketch = self._new_sketch(root, root.xYConstructionPlane, "DBG_Divider_SideView", profiles_shown=True)
        self._draw_closed_xy_profile(sketch, vector, "DIVIDER_SIDE_TRIMMED_VECTOR", side_offset)

    def _new_sketch(self, root, plane, name, profiles_shown=False):
        sketch = root.sketches.add(plane)
        sketch.name = name
        try:
            sketch.areProfilesShown = profiles_shown
        except:
            pass
        return sketch

    def _delete_debug_sketches(self, root):
        names = [
            "DBG_BP_TopView",
            "DBG_T2_FrontView",
            "DBG_T3_TopView",
            "DBG_T4_FrontView",
            "DBG_Divider_SideView",
        ]
        for name in names:
            existing = root.sketches.itemByName(name)
            if existing:
                existing.deleteMe()

    def _draw_rect_xy(self, sketch, x0, y0, x1, y1, name, offset=(0.0, 0.0)):
        lines = sketch.sketchCurves.sketchLines
        points = [
            self._point_xy(x0, y0, offset),
            self._point_xy(x1, y0, offset),
            self._point_xy(x1, y1, offset),
            self._point_xy(x0, y1, offset),
        ]
        self._draw_polyline(lines, points, name)

    def _draw_rect_xz(self, sketch, x0, z0, x1, z1, name):
        lines = sketch.sketchCurves.sketchLines
        points = [
            self._point_xz(x0, z0),
            self._point_xz(x1, z0),
            self._point_xz(x1, z1),
            self._point_xz(x0, z1),
        ]
        self._draw_polyline(lines, points, name)

    def _draw_rect_yz(self, sketch, y0, z0, y1, z1, name):
        lines = sketch.sketchCurves.sketchLines
        points = [
            self._point_yz(y0, z0),
            self._point_yz(y1, z0),
            self._point_yz(y1, z1),
            self._point_yz(y0, z1),
        ]
        self._draw_polyline(lines, points, name)

    def _draw_line_xy(self, sketch, x0, y0, x1, y1, name, offset=(0.0, 0.0), construction=False):
        line = sketch.sketchCurves.sketchLines.addByTwoPoints(
            self._point_xy(x0, y0, offset),
            self._point_xy(x1, y1, offset),
        )
        line.name = name
        line.isConstruction = construction

    def _draw_line_yz(self, sketch, y0, z0, y1, z1, name):
        line = sketch.sketchCurves.sketchLines.addByTwoPoints(self._point_yz(y0, z0), self._point_yz(y1, z1))
        line.name = name

    def _draw_polyline(self, lines, points, name):
        for index in range(len(points)):
            line = lines.addByTwoPoints(points[index], points[(index + 1) % len(points)])
            line.name = "{}_E{}".format(name, index + 1)

    def _draw_xy_vector(self, sketch, points, name, offset=(0.0, 0.0)):
        clean_points = list(points)
        if len(clean_points) > 1 and clean_points[0] == clean_points[-1]:
            clean_points = clean_points[:-1]
        sketch_points = [self._point_xy(point[0], point[1], offset) for point in clean_points]
        self._draw_polyline(sketch.sketchCurves.sketchLines, sketch_points, name)

    def _draw_closed_xy_profile(self, sketch, points, name, offset=(0.0, 0.0)):
        clean_points = list(points)
        if len(clean_points) > 1 and clean_points[0] == clean_points[-1]:
            clean_points = clean_points[:-1]
        if len(clean_points) < 3:
            return

        lines = sketch.sketchCurves.sketchLines
        first_point = self._point_xy(clean_points[0][0], clean_points[0][1], offset)
        second_point = self._point_xy(clean_points[1][0], clean_points[1][1], offset)
        first_line = lines.addByTwoPoints(first_point, second_point)
        first_line.name = "{}_E1".format(name)
        start_sketch_point = first_line.startSketchPoint
        previous_end = first_line.endSketchPoint

        edge_index = 2
        for point in clean_points[2:]:
            line = lines.addByTwoPoints(previous_end, self._point_xy(point[0], point[1], offset))
            line.name = "{}_E{}".format(name, edge_index)
            previous_end = line.endSketchPoint
            edge_index += 1

        close_line = lines.addByTwoPoints(previous_end, start_sketch_point)
        close_line.name = "{}_E{}".format(name, edge_index)

    def _draw_cross_xy(self, sketch, x, y, size, name, offset=(0.0, 0.0)):
        half = size / 2.0
        self._draw_line_xy(sketch, x - half, y, x + half, y, "{}_H".format(name), offset)
        self._draw_line_xy(sketch, x, y - half, x, y + half, "{}_V".format(name), offset)

    def _draw_circle_xy(self, sketch, x, y, diameter, name, offset=(0.0, 0.0)):
        circle = sketch.sketchCurves.sketchCircles.addByCenterRadius(
            self._point_xy(x, y, offset),
            self.fusion.cm(diameter / 2.0),
        )
        circle.name = name

    def _draw_panel_screw_holes(self, sketch, geometry, part, offset):
        for hole in geometry.get("panel_screw_holes", {}).get(part, []):
            self._draw_circle_xy(
                sketch,
                hole["center"][0],
                hole["center"][1],
                hole["diameter"],
                hole["id"],
                offset,
            )

    def _add_label(self, sketch, text, x, y, offset=(0.0, 0.0), height=8.0):
        try:
            text_input = sketch.sketchTexts.createInput(
                text,
                self.fusion.cm(height),
                self._point_xy(x, y, offset),
            )
            sketch_text = sketch.sketchTexts.add(text_input)
            sketch_text.name = "LABEL_{}".format(text[:20].replace(" ", "_"))
        except:
            pass

    def _point_xy(self, x, y, offset=(0.0, 0.0)):
        return adsk.core.Point3D.create(self.fusion.cm(x + offset[0]), self.fusion.cm(y + offset[1]), 0)

    def _point_xz(self, x, z):
        return adsk.core.Point3D.create(self.fusion.cm(x), 0, self.fusion.cm(z))

    def _point_yz(self, y, z):
        return adsk.core.Point3D.create(0, self.fusion.cm(y), self.fusion.cm(z))

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
                raise ValueError("XDs must be numbers separated by commas.")
        return values
