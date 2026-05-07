from dataclasses import dataclass
from typing import Sequence


DEFAULT_ROUTER_DIAMETER_MM = 10.0
DIVIDER_THICKNESS_MM = 15.0
FEATURE_CLEARANCE_MM = 1.0
FEATURE_GROOVE_WIDTH_MM = DIVIDER_THICKNESS_MM + FEATURE_CLEARANCE_MM
SCREW_HOLE_DIAMETER_MM = 3.0
SCREW_HOLE_DEPTH_MM = 15.0
BOTTOM_THICKNESS_MM = 15.0
DIVIDER_TONGUE_HEIGHT_MM = BOTTOM_THICKNESS_MM / 2.0
T1_HEIGHT_MM = 40.0
T3_DEPTH_MM = 90.0
T3_THICKNESS_MM = 15.0
T3_NOTCH_DEPTH_MM = 20.0
T4_THICKNESS_MM = 15.0
T4_HEIGHT_MM = 50.0
T4_NOTCH_HEIGHT_MM = 20.0
T4_SCREW_HOLE_NOTCH_CLEARANCE_MM = 8.0
T4_SCREW_HOLE_UP_SHIFT_MM = 10.0
FRONT_TOP_NOTCH_Y_OFFSET_MM = 70.0
FRONT_TOP_STEP_Y_MM = 10.0
FRONT_TOP_STEP_DROP_MM = FEATURE_GROOVE_WIDTH_MM
REAR_TOP_NOTCH_HEIGHT_MM = T4_HEIGHT_MM - 15.0


@dataclass(frozen=True)
class OverheadCabinetInputs:
    cabinet_width: float
    cabinet_depth: float
    cabinet_height: float = None
    bottom_thickness: float = BOTTOM_THICKNESS_MM
    divider_tongue_height: float = DIVIDER_TONGUE_HEIGHT_MM
    router_diameter: float = DEFAULT_ROUTER_DIAMETER_MM
    feature_width: float = FEATURE_GROOVE_WIDTH_MM
    internal_divider_centerlines: Sequence[float] = ()


def edge_divider_centerlines(cabinet_width, feature_width=FEATURE_GROOVE_WIDTH_MM):
    half_width = feature_width / 2.0
    return half_width, cabinet_width - half_width


def divider_centerlines(cabinet_width, internal_centerlines, feature_width=FEATURE_GROOVE_WIDTH_MM):
    left, right = edge_divider_centerlines(cabinet_width, feature_width)
    return [left] + list(internal_centerlines) + [right]


def feature_x_range(centerline_x, feature_width=FEATURE_GROOVE_WIDTH_MM):
    half_width = feature_width / 2.0
    return [centerline_x - half_width, centerline_x + half_width]


def bp_groove_y_range(cabinet_depth):
    return [cabinet_depth / 3.0, 2.0 * cabinet_depth / 3.0]


def bp_groove_length(cabinet_depth):
    return cabinet_depth / 3.0


def screw_hole_positions(centerline_x, cabinet_depth, diameter=SCREW_HOLE_DIAMETER_MM):
    return [
        {"x": centerline_x, "y": cabinet_depth / 6.0, "diameter": diameter},
        {"x": centerline_x, "y": 5.0 * cabinet_depth / 6.0, "diameter": diameter},
    ]


def panel_screw_holes(part, centers, local_midline, diameter=SCREW_HOLE_DIAMETER_MM, depth=SCREW_HOLE_DEPTH_MM):
    return [
        {
            "id": "{}SH_D{}".format(part, index),
            "part": part,
            "for_divider": "D{}".format(index),
            "center": [centerline_x, local_midline],
            "diameter": diameter,
            "depth": depth,
            "axis": "thickness",
        }
        for index, centerline_x in enumerate(centers)
    ]


def divider_tongue_y_range(cabinet_depth, router_diameter=DEFAULT_ROUTER_DIAMETER_MM):
    return [
        cabinet_depth / 3.0 + router_diameter / 2.0,
        2.0 * cabinet_depth / 3.0 - router_diameter / 2.0,
    ]


def divider_tongue_length(cabinet_depth, router_diameter=DEFAULT_ROUTER_DIAMETER_MM):
    return cabinet_depth / 3.0 - router_diameter


def t3_notch_y_range(t3_depth=T3_DEPTH_MM, notch_depth=T3_NOTCH_DEPTH_MM):
    return [t3_depth - notch_depth, t3_depth]


def t4_notch_z_range(notch_height=T4_NOTCH_HEIGHT_MM):
    return [0.0, notch_height]


def bp_groove(divider_id, centerline_x, cabinet_depth, feature_width=FEATURE_GROOVE_WIDTH_MM, tongue_height=None):
    z1 = -tongue_height if tongue_height is not None else "TODO:Dntg_h"
    x0, x1 = feature_x_range(centerline_x, feature_width)
    y0, y1 = bp_groove_y_range(cabinet_depth)
    return {
        "id": "BG_{}".format(divider_id),
        "part": "BP",
        "for_divider": divider_id,
        "x": [x0, x1],
        "y": [y0, y1],
        "z": [0.0, z1],
        "width_x": feature_width,
        "length_y": bp_groove_length(cabinet_depth),
        "depth_z": tongue_height if tongue_height is not None else "TODO:Dntg_h",
    }


def t3_notch(divider_id, centerline_x, feature_width=FEATURE_GROOVE_WIDTH_MM):
    return {
        "id": "T3N_{}".format(divider_id),
        "part": "T3",
        "for_divider": divider_id,
        "x": feature_x_range(centerline_x, feature_width),
        "y": t3_notch_y_range(),
        "z": [0.0, -T3_THICKNESS_MM],
        "width_x": feature_width,
        "depth_y": T3_NOTCH_DEPTH_MM,
    }


def t4_notch(divider_id, centerline_x, feature_width=FEATURE_GROOVE_WIDTH_MM):
    return {
        "id": "T4N_{}".format(divider_id),
        "part": "T4",
        "for_divider": divider_id,
        "x": feature_x_range(centerline_x, feature_width),
        "y": [0.0, T4_THICKNESS_MM],
        "z": t4_notch_z_range(),
        "width_x": feature_width,
        "height_z": T4_NOTCH_HEIGHT_MM,
    }


def t3_trimmed_outline_points(cabinet_width, notch_x_ranges, t3_depth=T3_DEPTH_MM, notch_depth=T3_NOTCH_DEPTH_MM):
    rear_y = t3_depth
    notch_y = t3_depth - notch_depth
    ranges = sorted(notch_x_ranges, key=lambda item: item[0], reverse=True)
    points = [[0.0, 0.0], [cabinet_width, 0.0]]

    if ranges and ranges[0][1] >= cabinet_width:
        x0, _ = ranges.pop(0)
        points.extend([[cabinet_width, notch_y], [x0, notch_y], [x0, rear_y]])
        current_x = x0
    else:
        points.append([cabinet_width, rear_y])
        current_x = cabinet_width

    while ranges:
        x0, x1 = ranges.pop(0)
        if x0 <= 0.0:
            points.extend([[x1, rear_y], [x1, notch_y], [0.0, notch_y], [0.0, 0.0]])
            return _dedupe_points(points)
        points.extend([[x1, rear_y], [x1, notch_y], [x0, notch_y], [x0, rear_y]])
        current_x = x0

    if current_x > 0.0:
        points.extend([[0.0, rear_y], [0.0, 0.0]])
    return _dedupe_points(points)


def t4_trimmed_outline_points(cabinet_width, notch_x_ranges, t4_height=T4_HEIGHT_MM, notch_height=T4_NOTCH_HEIGHT_MM):
    ranges = sorted(notch_x_ranges, key=lambda item: item[0], reverse=True)
    points = [[0.0, t4_height], [cabinet_width, t4_height]]

    if ranges and ranges[0][1] >= cabinet_width:
        x0, _ = ranges.pop(0)
        points.extend([[cabinet_width, notch_height], [x0, notch_height], [x0, 0.0]])
        current_x = x0
    else:
        points.append([cabinet_width, 0.0])
        current_x = cabinet_width

    while ranges:
        x0, x1 = ranges.pop(0)
        if x0 <= 0.0:
            points.extend([[x1, 0.0], [x1, notch_height], [0.0, notch_height], [0.0, t4_height]])
            return _dedupe_points(points)
        points.extend([[x1, 0.0], [x1, notch_height], [x0, notch_height], [x0, 0.0]])
        current_x = x0

    if current_x > 0.0:
        points.extend([[0.0, 0.0], [0.0, t4_height]])
    return _dedupe_points(points)


def divider_side_trimmed_outline_points(
    cabinet_depth,
    cabinet_height,
    bottom_thickness=BOTTOM_THICKNESS_MM,
    tongue_height=None,
    router_diameter=DEFAULT_ROUTER_DIAMETER_MM,
    rear_notch_width=FEATURE_GROOVE_WIDTH_MM,
):
    if cabinet_height is None:
        return []

    if tongue_height is None:
        tongue_height = bottom_thickness / 2.0

    divider_height = cabinet_height - bottom_thickness
    tongue_y0, tongue_y1 = divider_tongue_y_range(cabinet_depth, router_diameter)
    tongue_z0 = -tongue_height

    front_y0 = FRONT_TOP_NOTCH_Y_OFFSET_MM
    front_z0 = divider_height - T1_HEIGHT_MM

    rear_y0 = cabinet_depth - rear_notch_width
    rear_z0 = divider_height - REAR_TOP_NOTCH_HEIGHT_MM
    front_step_y1 = front_y0 + FRONT_TOP_STEP_Y_MM
    front_step_z1 = front_z0 - FRONT_TOP_STEP_DROP_MM

    return _dedupe_points(
        [
            [0.0, 0.0],
            [tongue_y0, 0.0],
            [tongue_y0, tongue_z0],
            [tongue_y1, tongue_z0],
            [tongue_y1, 0.0],
            [cabinet_depth, 0.0],
            [cabinet_depth, rear_z0],
            [rear_y0, rear_z0],
            [rear_y0, divider_height],
            [front_y0, divider_height],
            [front_y0, front_z0],
            [front_step_y1, front_z0],
            [front_step_y1, front_step_z1],
            [front_step_y1 - (T3_DEPTH_MM - 10.0), front_step_z1],
            [0.0, 0.0],
        ]
    )


def _dedupe_points(points):
    out = []
    for point in points:
        if out and out[-1] == point:
            continue
        out.append(point)
    return out


def bottom_panel(inputs):
    bottom_thickness = inputs.bottom_thickness if inputs.bottom_thickness is not None else "TODO:Bt"
    return {
        "origin": "left-top-front",
        "global_origin": [0.0, 0.0, bottom_thickness],
        "size": [inputs.cabinet_width, inputs.cabinet_depth, bottom_thickness],
        "local_bounds": {
            "x": [0.0, inputs.cabinet_width],
            "y": [0.0, inputs.cabinet_depth],
            "z": [-inputs.bottom_thickness, 0.0] if inputs.bottom_thickness is not None else "TODO:Bt",
        },
    }


def divider_feature(divider_id, centerline_x, inputs):
    return {
        "id": divider_id,
        "XDi": centerline_x,
        "bp_groove": bp_groove(
            divider_id,
            centerline_x,
            inputs.cabinet_depth,
            inputs.feature_width,
            inputs.divider_tongue_height,
        ),
        "screw_holes": screw_hole_positions(centerline_x, inputs.cabinet_depth),
        "divider_tongue": {
            "length_y": divider_tongue_length(inputs.cabinet_depth, inputs.router_diameter),
            "y": divider_tongue_y_range(inputs.cabinet_depth, inputs.router_diameter),
            "z": [-inputs.divider_tongue_height, 0.0]
            if inputs.divider_tongue_height is not None
            else "TODO:Dntg_h",
        },
        "t3_notch": t3_notch(divider_id, centerline_x, inputs.feature_width),
        "t4_notch": t4_notch(divider_id, centerline_x, inputs.feature_width),
    }


def calculate_overhead_geometry(inputs):
    centers = divider_centerlines(
        inputs.cabinet_width,
        inputs.internal_divider_centerlines,
        inputs.feature_width,
    )
    divider_ids = ["D{}".format(index) for index in range(len(centers))]
    return {
        "cabinet": {
            "Cw": inputs.cabinet_width,
            "Cd": inputs.cabinet_depth,
            "Ch": inputs.cabinet_height,
        },
        "manufacturing": {
            "Crd": inputs.router_diameter,
            "Crr": inputs.router_diameter / 2.0,
            "FGw": inputs.feature_width,
            "FGh": inputs.feature_width / 2.0,
        },
        "bottom_panel": bottom_panel(inputs),
        "divider_features": [
            divider_feature(divider_id, centerline_x, inputs)
            for divider_id, centerline_x in zip(divider_ids, centers)
        ],
        "panel_screw_holes": {
            "T2": panel_screw_holes("T2", centers, T1_HEIGHT_MM / 2.0),
            "T3": panel_screw_holes("T3", centers, T3_DEPTH_MM / 2.0),
            "T4": panel_screw_holes(
                "T4",
                centers,
                T4_NOTCH_HEIGHT_MM + T4_SCREW_HOLE_NOTCH_CLEARANCE_MM + T4_SCREW_HOLE_UP_SHIFT_MM,
            ),
        },
        "trimmed_vectors": {
            "T3": t3_trimmed_outline_points(
                inputs.cabinet_width,
                [feature_x_range(centerline_x, inputs.feature_width) for centerline_x in centers],
            ),
            "T4": t4_trimmed_outline_points(
                inputs.cabinet_width,
                [feature_x_range(centerline_x, inputs.feature_width) for centerline_x in centers],
            ),
            "DividerSide": divider_side_trimmed_outline_points(
                inputs.cabinet_depth,
                inputs.cabinet_height,
                inputs.bottom_thickness,
                inputs.divider_tongue_height,
                inputs.router_diameter,
                inputs.feature_width,
            ),
        },
    }


def calculate_overhead_geometry_from_xds(
    cabinet_width,
    cabinet_depth,
    cabinet_height,
    xds,
    bottom_thickness=BOTTOM_THICKNESS_MM,
    divider_tongue_height=DIVIDER_TONGUE_HEIGHT_MM,
    router_diameter=DEFAULT_ROUTER_DIAMETER_MM,
    feature_width=FEATURE_GROOVE_WIDTH_MM,
):
    centers = list(xds)
    divider_ids = ["D{}".format(index) for index in range(len(centers))]
    inputs = OverheadCabinetInputs(
        cabinet_width=cabinet_width,
        cabinet_depth=cabinet_depth,
        cabinet_height=cabinet_height,
        bottom_thickness=bottom_thickness,
        divider_tongue_height=divider_tongue_height,
        router_diameter=router_diameter,
        feature_width=feature_width,
        internal_divider_centerlines=centers[1:-1],
    )
    return {
        "cabinet": {
            "Cw": inputs.cabinet_width,
            "Cd": inputs.cabinet_depth,
            "Ch": inputs.cabinet_height,
        },
        "manufacturing": {
            "Crd": inputs.router_diameter,
            "Crr": inputs.router_diameter / 2.0,
            "FGw": inputs.feature_width,
            "FGh": inputs.feature_width / 2.0,
        },
        "bottom_panel": bottom_panel(inputs),
        "divider_features": [
            divider_feature(divider_id, centerline_x, inputs)
            for divider_id, centerline_x in zip(divider_ids, centers)
        ],
        "panel_screw_holes": {
            "T2": panel_screw_holes("T2", centers, T1_HEIGHT_MM / 2.0),
            "T3": panel_screw_holes("T3", centers, T3_DEPTH_MM / 2.0),
            "T4": panel_screw_holes(
                "T4",
                centers,
                T4_NOTCH_HEIGHT_MM + T4_SCREW_HOLE_NOTCH_CLEARANCE_MM + T4_SCREW_HOLE_UP_SHIFT_MM,
            ),
        },
        "trimmed_vectors": {
            "T3": t3_trimmed_outline_points(
                inputs.cabinet_width,
                [feature_x_range(centerline_x, inputs.feature_width) for centerline_x in centers],
            ),
            "T4": t4_trimmed_outline_points(
                inputs.cabinet_width,
                [feature_x_range(centerline_x, inputs.feature_width) for centerline_x in centers],
            ),
            "DividerSide": divider_side_trimmed_outline_points(
                inputs.cabinet_depth,
                inputs.cabinet_height,
                inputs.bottom_thickness,
                inputs.divider_tongue_height,
                inputs.router_diameter,
                inputs.feature_width,
            ),
        },
    }


def calculate_overhead_geometry_from_internal_xds(
    cabinet_width,
    cabinet_depth,
    cabinet_height,
    internal_xds,
    bottom_thickness=BOTTOM_THICKNESS_MM,
    divider_tongue_height=DIVIDER_TONGUE_HEIGHT_MM,
    router_diameter=DEFAULT_ROUTER_DIAMETER_MM,
    feature_width=FEATURE_GROOVE_WIDTH_MM,
):
    divider_tongue_height = bottom_thickness / 2.0
    left_xd, right_xd = edge_divider_centerlines(cabinet_width, feature_width)
    return calculate_overhead_geometry_from_xds(
        cabinet_width=cabinet_width,
        cabinet_depth=cabinet_depth,
        cabinet_height=cabinet_height,
        xds=[left_xd] + list(internal_xds) + [right_xd],
        bottom_thickness=bottom_thickness,
        divider_tongue_height=divider_tongue_height,
        router_diameter=router_diameter,
        feature_width=feature_width,
    )


def test_case_001_geometry():
    return calculate_overhead_geometry_from_internal_xds(
        cabinet_width=500.0,
        cabinet_depth=300.0,
        cabinet_height=None,
        internal_xds=(125.0, 250.0, 375.0),
        router_diameter=10.0,
        feature_width=16.0,
    )
