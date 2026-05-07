import unittest

from core.overhead_geometry import (
    BOTTOM_THICKNESS_MM,
    DIVIDER_THICKNESS_MM,
    DIVIDER_TONGUE_HEIGHT_MM,
    FEATURE_CLEARANCE_MM,
    FEATURE_GROOVE_WIDTH_MM,
    REAR_TOP_NOTCH_HEIGHT_MM,
    SCREW_HOLE_DEPTH_MM,
    T1_HEIGHT_MM,
    T3_DEPTH_MM,
    T4_HEIGHT_MM,
    T4_NOTCH_HEIGHT_MM,
    T4_SCREW_HOLE_NOTCH_CLEARANCE_MM,
    T4_SCREW_HOLE_UP_SHIFT_MM,
    bp_groove_y_range,
    divider_side_trimmed_outline_points,
    divider_tongue_length,
    divider_tongue_y_range,
    edge_divider_centerlines,
    feature_x_range,
    panel_screw_holes,
    screw_hole_positions,
    t3_notch_y_range,
    t4_notch_z_range,
    calculate_overhead_geometry_from_internal_xds,
    calculate_overhead_geometry_from_xds,
    test_case_001_geometry,
)


class TestOverheadGeometry(unittest.TestCase):
    def test_edge_feature_centerlines(self):
        left, right = edge_divider_centerlines(500.0, FEATURE_GROOVE_WIDTH_MM)

        self.assertEqual(left, 8.0)
        self.assertEqual(right, 492.0)

    def test_edge_bp_groove_x_ranges(self):
        left, right = edge_divider_centerlines(500.0, FEATURE_GROOVE_WIDTH_MM)

        self.assertEqual(feature_x_range(left, FEATURE_GROOVE_WIDTH_MM), [0.0, 16.0])
        self.assertEqual(feature_x_range(right, FEATURE_GROOVE_WIDTH_MM), [484.0, 500.0])

    def test_bp_groove_y_range(self):
        self.assertEqual(bp_groove_y_range(300.0), [100.0, 200.0])

    def test_screw_hole_positions(self):
        holes = screw_hole_positions(8.0, 300.0)

        self.assertEqual(holes[0], {"x": 8.0, "y": 50.0, "diameter": 3.0})
        self.assertEqual(holes[1], {"x": 8.0, "y": 250.0, "diameter": 3.0})

    def test_panel_screw_holes_use_local_midline(self):
        holes = panel_screw_holes(
            "T4",
            [8.0, 125.0],
            T4_NOTCH_HEIGHT_MM + T4_SCREW_HOLE_NOTCH_CLEARANCE_MM + T4_SCREW_HOLE_UP_SHIFT_MM,
        )

        self.assertEqual(
            holes[0],
            {
                "id": "T4SH_D0",
                "part": "T4",
                "for_divider": "D0",
                "center": [8.0, 38.0],
                "diameter": 3.0,
                "depth": SCREW_HOLE_DEPTH_MM,
                "axis": "thickness",
            },
        )
        self.assertEqual(holes[1]["center"], [125.0, 38.0])

    def test_divider_tongue_y_range(self):
        self.assertEqual(divider_tongue_length(300.0, 10.0), 90.0)
        self.assertEqual(divider_tongue_y_range(300.0, 10.0), [105.0, 195.0])
        self.assertEqual(BOTTOM_THICKNESS_MM, 15.0)
        self.assertEqual(DIVIDER_TONGUE_HEIGHT_MM, 7.5)
        self.assertEqual(DIVIDER_THICKNESS_MM, 15.0)
        self.assertEqual(FEATURE_CLEARANCE_MM, 1.0)
        self.assertEqual(FEATURE_GROOVE_WIDTH_MM, 16.0)
        self.assertEqual(T1_HEIGHT_MM, 40.0)
        self.assertEqual(REAR_TOP_NOTCH_HEIGHT_MM, 35.0)

    def test_t3_notch_y_range(self):
        self.assertEqual(t3_notch_y_range(90.0, 20.0), [70.0, 90.0])

    def test_t4_notch_z_range(self):
        self.assertEqual(t4_notch_z_range(20.0), [0.0, 20.0])

    def test_test_case_001_output_contains_expected_features(self):
        geometry = test_case_001_geometry()
        features = geometry["divider_features"]

        self.assertEqual([feature["XDi"] for feature in features], [8.0, 125.0, 250.0, 375.0, 492.0])
        self.assertEqual(features[0]["bp_groove"]["x"], [0.0, 16.0])
        self.assertEqual(features[-1]["bp_groove"]["x"], [484.0, 500.0])
        self.assertEqual(features[0]["bp_groove"]["y"], [100.0, 200.0])
        self.assertEqual(features[0]["bp_groove"]["z"], [0.0, -7.5])
        self.assertEqual(features[0]["bp_groove"]["depth_z"], 7.5)
        self.assertEqual(features[0]["divider_tongue"]["z"], [-7.5, 0.0])
        self.assertEqual(features[0]["t3_notch"]["x"], [0.0, 16.0])
        self.assertEqual(features[-1]["t3_notch"]["x"], [484.0, 500.0])
        self.assertEqual(features[0]["t4_notch"]["z"], [0.0, 20.0])
        self.assertEqual(features[-1]["t4_notch"]["x"], [484.0, 500.0])
        self.assertEqual(geometry["panel_screw_holes"]["T2"][0]["center"], [8.0, T1_HEIGHT_MM / 2.0])
        self.assertEqual(geometry["panel_screw_holes"]["T3"][0]["center"], [8.0, T3_DEPTH_MM / 2.0])
        self.assertEqual(
            geometry["panel_screw_holes"]["T4"][0]["center"],
            [8.0, T4_NOTCH_HEIGHT_MM + T4_SCREW_HOLE_NOTCH_CLEARANCE_MM + T4_SCREW_HOLE_UP_SHIFT_MM],
        )

    def test_divider_side_trimmed_outline_points(self):
        self.assertEqual(
            divider_side_trimmed_outline_points(
                cabinet_depth=415.0,
                cabinet_height=415.0,
                bottom_thickness=15.0,
                tongue_height=7.5,
                router_diameter=10.0,
                rear_notch_width=16.0,
            )[5:14],
            [
                [415.0, 0.0],
                [415.0, 365.0],
                [399.0, 365.0],
                [399.0, 400.0],
                [70.0, 400.0],
                [70.0, 360.0],
                [80.0, 360.0],
                [80.0, 344.0],
                [0.0, 344.0],
            ],
        )

    def test_explicit_xds_geometry_uses_given_centerlines(self):
        geometry = calculate_overhead_geometry_from_xds(
            cabinet_width=500.0,
            cabinet_depth=300.0,
            cabinet_height=400.0,
            xds=[8.0, 125.0, 250.0, 375.0, 492.0],
            bottom_thickness=15.0,
            divider_tongue_height=7.5,
            router_diameter=10.0,
            feature_width=16.0,
        )
        features = geometry["divider_features"]

        self.assertEqual(geometry["cabinet"], {"Cw": 500.0, "Cd": 300.0, "Ch": 400.0})
        self.assertEqual([feature["id"] for feature in features], ["D0", "D1", "D2", "D3", "D4"])
        self.assertEqual([feature["XDi"] for feature in features], [8.0, 125.0, 250.0, 375.0, 492.0])
        self.assertEqual(features[1]["bp_groove"]["id"], "BG_D1")
        self.assertEqual(features[1]["t3_notch"]["id"], "T3N_D1")
        self.assertEqual(features[1]["t4_notch"]["id"], "T4N_D1")
        self.assertEqual(features[1]["bp_groove"]["x"], [117.0, 133.0])
        self.assertEqual(features[3]["t3_notch"]["x"], [367.0, 383.0])
        self.assertEqual(
            geometry["trimmed_vectors"]["T3"],
            [
                [0.0, 0.0],
                [500.0, 0.0],
                [500.0, 70.0],
                [484.0, 70.0],
                [484.0, 90.0],
                [383.0, 90.0],
                [383.0, 70.0],
                [367.0, 70.0],
                [367.0, 90.0],
                [258.0, 90.0],
                [258.0, 70.0],
                [242.0, 70.0],
                [242.0, 90.0],
                [133.0, 90.0],
                [133.0, 70.0],
                [117.0, 70.0],
                [117.0, 90.0],
                [16.0, 90.0],
                [16.0, 70.0],
                [0.0, 70.0],
                [0.0, 0.0],
            ],
        )
        self.assertEqual(geometry["trimmed_vectors"]["T4"][0:4], [[0.0, 50.0], [500.0, 50.0], [500.0, 20.0], [484.0, 20.0]])

    def test_internal_xds_auto_add_edge_centerlines(self):
        geometry = calculate_overhead_geometry_from_internal_xds(
            cabinet_width=2000.0,
            cabinet_depth=415.0,
            cabinet_height=415.0,
            internal_xds=[125.0, 250.0, 375.0, 492.0],
            bottom_thickness=15.0,
            router_diameter=10.0,
        )
        features = geometry["divider_features"]

        self.assertEqual([feature["XDi"] for feature in features], [8.0, 125.0, 250.0, 375.0, 492.0, 1992.0])
        self.assertEqual(features[0]["t3_notch"]["x"], [0.0, 16.0])
        self.assertEqual(features[-1]["t3_notch"]["x"], [1984.0, 2000.0])
        self.assertEqual(features[0]["bp_groove"]["depth_z"], 7.5)


if __name__ == "__main__":
    unittest.main()
