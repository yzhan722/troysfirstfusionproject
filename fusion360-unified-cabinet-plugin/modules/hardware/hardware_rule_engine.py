"""M9 — hardware type registry and relationship-based rule dispatch."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

HARDWARE_TYPE_SCREW_HOLE = "screw_hole"
HARDWARE_TYPE_TONGUE_GROOVE = "tongue_groove"
HARDWARE_TYPE_HINGE_HOLE = "hinge_hole"
HARDWARE_TYPE_LOCK_CUTOUT = "lock_cutout"
HARDWARE_TYPE_DRAWER_RUNNER_HOLE = "drawer_runner_hole"

IMPLEMENTED_TYPES = {HARDWARE_TYPE_SCREW_HOLE}
PREVIEW_ONLY_TYPES = {
    HARDWARE_TYPE_TONGUE_GROOVE,
    HARDWARE_TYPE_HINGE_HOLE,
    HARDWARE_TYPE_LOCK_CUTOUT,
    HARDWARE_TYPE_DRAWER_RUNNER_HOLE,
}

HARDWARE_TYPE_UI: Dict[str, Dict[str, Any]] = {
    HARDWARE_TYPE_SCREW_HOLE: {
        "label": "Screw hole",
        "status": "implemented",
        "description": "Edge-to-surface structural butt joint screw holes.",
    },
    HARDWARE_TYPE_TONGUE_GROOVE: {
        "label": "Tongue / groove",
        "status": "preview_only",
        "description": "Panel edge tongue and groove machining (scaffold).",
    },
    HARDWARE_TYPE_HINGE_HOLE: {
        "label": "Hinge hole",
        "status": "preview_only",
        "description": "Front panel hinge cup holes (scaffold).",
    },
    HARDWARE_TYPE_LOCK_CUTOUT: {
        "label": "Lock cutout",
        "status": "preview_only",
        "description": "Front panel lock pocket (scaffold).",
    },
    HARDWARE_TYPE_DRAWER_RUNNER_HOLE: {
        "label": "Drawer runner hole",
        "status": "preview_only",
        "description": "Side panel runner mounting holes (scaffold).",
    },
}


def normalize_hardware_type(rule: Optional[Dict[str, Any]]) -> str:
    if not isinstance(rule, dict):
        return HARDWARE_TYPE_SCREW_HOLE
    return str(rule.get("type") or HARDWARE_TYPE_SCREW_HOLE).strip().lower()


def list_hardware_types() -> List[Dict[str, Any]]:
    rows = []
    for key in (
        HARDWARE_TYPE_SCREW_HOLE,
        HARDWARE_TYPE_TONGUE_GROOVE,
        HARDWARE_TYPE_HINGE_HOLE,
        HARDWARE_TYPE_LOCK_CUTOUT,
        HARDWARE_TYPE_DRAWER_RUNNER_HOLE,
    ):
        meta = dict(HARDWARE_TYPE_UI.get(key) or {})
        meta["type"] = key
        meta["implemented"] = key in IMPLEMENTED_TYPES
        meta["previewOnly"] = key in PREVIEW_ONLY_TYPES
        rows.append(meta)
    return rows


def evaluate_hardware_rule(
    hardware_type: str,
    relationship: Optional[Dict[str, Any]],
    *,
    action: str = "preview",
) -> Dict[str, Any]:
    action_key = str(action or "preview").strip().lower()
    hw_type = str(hardware_type or HARDWARE_TYPE_SCREW_HOLE).strip().lower()
    if not relationship:
        return {"ok": False, "hardwareType": hw_type, "action": action_key, "errors": ["No relationship selected."]}

    if hw_type == HARDWARE_TYPE_SCREW_HOLE:
        from connect_formal_ui import evaluate_connect_action

        mapped = "preview" if action_key in ("preview", "preview_screw_holes") else action_key
        if action_key in ("cut", "create_cut", "create_screw_holes"):
            mapped = "cut"
        if action_key in ("confirm", "confirm_for_cut"):
            mapped = "confirm"
        gate = evaluate_connect_action(mapped, relationship)
        gate["hardwareType"] = hw_type
        return gate

    if hw_type in PREVIEW_ONLY_TYPES:
        if action_key in ("cut", "create_cut", "create_screw_holes"):
            return {
                "ok": False,
                "hardwareType": hw_type,
                "action": action_key,
                "errors": ["Hardware type '{}' is not cut-ready in M9 v1 (preview scaffold only).".format(hw_type)],
                "previewOnly": True,
            }
        return {
            "ok": False,
            "hardwareType": hw_type,
            "action": action_key,
            "errors": ["Hardware type '{}' preview is not implemented yet.".format(hw_type)],
            "previewOnly": True,
            "scaffold": True,
        }

    return {
        "ok": False,
        "hardwareType": hw_type,
        "action": action_key,
        "errors": ["Unsupported hardware type: {}.".format(hw_type)],
    }


def dispatch_hardware_preview(
    relationship: Dict[str, Any],
    rule: Optional[Dict[str, Any]] = None,
    panel_snapshots: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    hw_type = normalize_hardware_type(rule)
    gate = evaluate_hardware_rule(hw_type, relationship, action="preview")
    if not gate.get("ok"):
        return {
            "ok": False,
            "hardwareType": hw_type,
            "errors": list(gate.get("errors") or ["Preview gate blocked."]),
            "gate": gate,
        }
    if hw_type != HARDWARE_TYPE_SCREW_HOLE:
        return gate

    from screw_hole_from_relationship import preview_screw_holes_from_relationship

    report = preview_screw_holes_from_relationship(relationship, rule=rule, panel_snapshots=panel_snapshots)
    report["hardwareType"] = hw_type
    return report


def dispatch_hardware_cut_plan(
    relationship: Dict[str, Any],
    rule: Optional[Dict[str, Any]] = None,
    panel_snapshots: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    hw_type = normalize_hardware_type(rule)
    gate = evaluate_hardware_rule(hw_type, relationship, action="cut")
    if not gate.get("ok"):
        return {
            "ok": False,
            "hardwareType": hw_type,
            "errors": list(gate.get("errors") or ["Cut gate blocked."]),
            "gate": gate,
        }
    if hw_type != HARDWARE_TYPE_SCREW_HOLE:
        return gate

    from screw_hole_from_relationship import plan_screw_hole_cut_from_relationship

    report = plan_screw_hole_cut_from_relationship(relationship, rule=rule, panel_snapshots=panel_snapshots)
    report["hardwareType"] = hw_type
    return report
