"""Convert generator board/panel output into relationship PanelSnapshot payloads."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


def _vector_bbox(outer_vector: Sequence[Sequence[float]]) -> Optional[Tuple[float, float, float, float]]:
    if not outer_vector:
        return None
    xs = [float(point[0]) for point in outer_vector if isinstance(point, (list, tuple)) and len(point) >= 2]
    ys = [float(point[1]) for point in outer_vector if isinstance(point, (list, tuple)) and len(point) >= 2]
    if not xs or not ys:
        return None
    return min(xs), max(xs), min(ys), max(ys)


def _bbox_dict(x0: float, y0: float, z0: float, x1: float, y1: float, z1: float) -> Dict[str, float]:
    return {
        "x0": float(x0),
        "x1": float(x1),
        "y0": float(y0),
        "y1": float(y1),
        "z0": float(z0),
        "z1": float(z1),
    }


def snapshot_dict_from_bbox_board(board: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """General Tall / Overhead / Kitchen boards with x0..z1 fields."""
    try:
        bbox = _bbox_dict(
            board["x0"],
            board["y0"],
            board["z0"],
            board["x1"],
            board["y1"],
            board["z1"],
        )
    except (KeyError, TypeError, ValueError):
        return None
    panel_id = str(board.get("id") or board.get("panelId") or "")
    if not panel_id:
        return None
    return {
        "panelId": panel_id,
        "bodyName": str(board.get("name") or panel_id),
        "boardType": board.get("boardType") or board.get("type") or board.get("category"),
        "role": board.get("category"),
        "sourceBoardId": panel_id,
        "bbox": bbox,
    }


def snapshot_dict_from_fridge_board(board: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Fridge BoardPlan board using assembly origin + profile-plane outerVector AABB."""
    panel_id = str(board.get("id") or "")
    outer_vector = board.get("outerVector")
    if not panel_id or not outer_vector:
        return None
    bounds = _vector_bbox(outer_vector)
    if not bounds:
        return None
    min_u, max_u, min_v, max_v = bounds
    width_u = max_u - min_u
    height_v = max_v - min_v
    thickness = float(board.get("thickness") or 15)
    profile_plane = str(board.get("profilePlane") or "XY").upper()
    if profile_plane == "XZ":
        size_x, size_y, size_z = width_u, thickness, height_v
    elif profile_plane == "YZ":
        size_x, size_y, size_z = thickness, width_u, height_v
    else:
        size_x, size_y, size_z = width_u, height_v, thickness

    assembly = (board.get("placement") or {}).get("assembly") or {}
    origin = assembly.get("originMm") or {"x": 0, "y": 0, "z": 0}
    x0 = float(origin.get("x") or 0)
    y0 = float(origin.get("y") or 0)
    z0 = float(origin.get("z") or 0)
    return {
        "panelId": panel_id,
        "bodyName": panel_id,
        "boardType": board.get("series") or board.get("boardType"),
        "role": board.get("series"),
        "sourceBoardId": panel_id,
        "bbox": _bbox_dict(x0, y0, z0, x0 + size_x, y0 + size_y, z0 + size_z),
    }


def snapshot_dict_from_lounge_panel(panel: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Lounge panels with explicit 3D placement boxes."""
    panel_id = str(panel.get("id") or "")
    placement = panel.get("placement") or {}
    required = ("x0", "x1", "y0", "y1", "z0", "z1")
    if not panel_id or not all(key in placement for key in required):
        return None
    return {
        "panelId": panel_id,
        "bodyName": panel_id,
        "boardType": panel.get("kind") or panel.get("type"),
        "role": panel.get("kind"),
        "sourceBoardId": panel_id,
        "bbox": _bbox_dict(
            placement["x0"],
            placement["y0"],
            placement["z0"],
            placement["x1"],
            placement["y1"],
            placement["z1"],
        ),
    }


def snapshots_from_generator_result(generator: str, result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract normalized snapshot dicts from a generator bridge result."""
    snapshots: List[Dict[str, Any]] = []
    generator_key = str(generator or "").strip().lower()

    if generator_key == "fridge":
        board_plan = result.get("boardPlan") or {}
        for board in board_plan.get("boards") or []:
            payload = snapshot_dict_from_fridge_board(board)
            if payload:
                snapshots.append(payload)
        return snapshots

    if generator_key == "lounge":
        for panel in result.get("panels") or []:
            payload = snapshot_dict_from_lounge_panel(panel)
            if payload:
                snapshots.append(payload)
        return snapshots

    for board in result.get("boards") or []:
        payload = snapshot_dict_from_bbox_board(board)
        if payload:
            snapshots.append(payload)
    return snapshots
