import importlib.util
import json
import os
import sys

import adsk.core
import adsk.fusion

_fusion_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "fusion"))
if _fusion_dir not in sys.path:
    sys.path.insert(0, _fusion_dir)

from geometry_ops import (
    MODEL_Z_OFFSET_MM,
    avoid_existing_at_origin,
    capture_position_snapshot,
    offset_matching_bodies_z_mm,
    sanitize_token,
)

_SOURCE_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "..",
        "Fridge Cabinet Generator",
        "fridge_flat_board_geometry.py",
    )
)

_spec = importlib.util.spec_from_file_location("_ucp_source_fridge_flat_board_geometry", _SOURCE_PATH)
_source = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_source)
_source.ATTRIBUTE_GROUP = "UnifiedCabinetPlugin"
_source.FEATURE_PREFIX = "FRIDGE_"

GEOMETRY_BUILD = "unified-wrapper-" + getattr(_source, "GEOMETRY_BUILD", "unknown")


def _resolve_generation_origin(origin_x_mm, origin_y_mm, origin_active, root):
    """Resolve spawn XY and whether to use generation-zone placement (z=0)."""
    if origin_active is not None:
        return float(origin_x_mm or 0.0), float(origin_y_mm or 0.0), bool(origin_active)
    has_explicit = origin_x_mm is not None or origin_y_mm is not None
    if has_explicit:
        return float(origin_x_mm or 0.0), float(origin_y_mm or 0.0), True
    if root is not None:
        try:
            attr = root.attributes.itemByName("UnifiedCabinet", "workZoneLayout")
            if attr and attr.value:
                layout = json.loads(attr.value)
                rect = layout.get("generation") if isinstance(layout, dict) else None
                if isinstance(rect, dict):
                    return (
                        (float(rect["x0"]) + float(rect["x1"])) / 2.0,
                        (float(rect["y0"]) + float(rect["y1"])) / 2.0,
                        True,
                    )
        except Exception:
            pass
    return 0.0, 0.0, False


def _apply_assembly_rename(result, assembly_name):
    """Rename the generated run component only (placement is already timeline-baked)."""
    if not assembly_name:
        return
    offset_info = result.get("modelZOffset") if isinstance(result.get("modelZOffset"), dict) else {}
    component_name = offset_info.get("componentName")
    if not component_name:
        return
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct) if app and app.activeProduct else None
    root = design.rootComponent if design else None
    if not root:
        return
    base = sanitize_token(assembly_name, fallback="assembly", limit=76)
    for index in range(root.occurrences.count):
        occurrence = root.occurrences.item(index)
        try:
            matches = occurrence.component.name == component_name or occurrence.name.startswith(component_name)
        except Exception:
            matches = False
        if not matches:
            continue
        renamed = None
        for candidate in [base] + ["{}_{}".format(base, i) for i in range(2, 100)]:
            try:
                occurrence.component.name = candidate
                renamed = candidate
                break
            except Exception:
                continue
        if renamed:
            offset_info["componentName"] = renamed
            result["assemblyComponentName"] = renamed
        else:
            result.setdefault("warnings", []).append("Fridge assembly rename failed for '{}'.".format(base))
        return


def generate_flat_board_bodies(
    board_plan,
    spacing_mm=100.0,
    preview_mode=None,
    assembly_name=None,
    origin_x_mm=None,
    origin_y_mm=None,
    origin_active=None,
):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct) if app and app.activeProduct else None
    root = design.rootComponent if design else None

    origin_x_mm, origin_y_mm, origin_active = _resolve_generation_origin(
        origin_x_mm, origin_y_mm, origin_active, root
    )
    avoidance_info = {"shifted": False, "slots": 0}
    footprint = None
    try:
        footprint = _source.compute_spawn_footprint_mm(board_plan, preview_mode=preview_mode)
    except Exception as ex:
        footprint = None
        avoidance_info["footprintError"] = str(ex)
    if origin_active and root is not None:
        origin_x_mm, origin_y_mm, avoidance_info = avoid_existing_at_origin(
            root, origin_x_mm, origin_y_mm, footprint
        )

    assembly_origin_z_mm = 0.0 if origin_active else None
    try:
        result = _source.generate_flat_board_bodies(
            board_plan,
            spacing_mm=spacing_mm,
            preview_mode=preview_mode,
            assembly_origin_x_mm=origin_x_mm,
            assembly_origin_y_mm=origin_y_mm,
            assembly_origin_z_mm=assembly_origin_z_mm,
        )
    except TypeError as ex:
        # Stale source module missing new placement kwargs — retry legacy call.
        if "assembly_origin" not in str(ex):
            raise
        result = _source.generate_flat_board_bodies(board_plan, spacing_mm=spacing_mm, preview_mode=preview_mode)
        result.setdefault("warnings", []).append(
            "Fridge geometry source is stale; reload the plugin. Placement-at-create skipped: {}".format(ex)
        )
    if isinstance(result, dict):
        result["geometryBuild"] = GEOMETRY_BUILD
        result.setdefault("warnings", []).append("Generated via Unified Cabinet Plugin fridge wrapper.")
        result["originAvoidance"] = avoidance_info
        result["spawnFootprintMm"] = (
            {"minX": footprint[0], "maxX": footprint[1], "minY": footprint[2], "maxY": footprint[3]}
            if footprint else None
        )
        if origin_active:
            result["originOffsetMm"] = {"x": float(origin_x_mm), "y": float(origin_y_mm), "z": 0.0}
            if avoidance_info.get("shifted"):
                result["warnings"].append(
                    "Generation spot was occupied; fridge assembly shifted +X by {:.0f} mm (slot {}).".format(
                        avoidance_info.get("shiftXMm", 0.0), avoidance_info.get("slots", 0)
                    )
                )
        try:
            _apply_assembly_rename(result, assembly_name)
        except Exception as ex:
            result.setdefault("warnings", []).append("Fridge naming failed: {}".format(ex))
        if root is not None:
            capture_position_snapshot(root)
        try:
            existing_offset = result.get("modelZOffset") if isinstance(result.get("modelZOffset"), dict) else {}
            if existing_offset.get("mode") == "componentAtModelZ":
                result["modelZOffset"] = existing_offset
            elif root is not None and not origin_active:
                result["modelZOffset"] = offset_matching_bodies_z_mm(
                    root,
                    name_prefixes=["FRIDGE_"],
                    module="fridge",
                    dz_mm=MODEL_Z_OFFSET_MM,
                    feature_prefix="FRIDGE_MODEL_Z_OFFSET_",
                )
        except Exception as ex:
            result.setdefault("warnings", []).append("Fridge model Z offset failed: {}".format(ex))
    return result
