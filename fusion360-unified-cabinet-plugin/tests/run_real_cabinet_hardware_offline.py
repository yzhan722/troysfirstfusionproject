#!/usr/bin/env python3
"""Offline smoke: all 5 Connect hardware types against real Overhead declared joints."""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for path in (
    ROOT,
    os.path.join(ROOT, "modules", "hardware"),
    os.path.join(ROOT, "modules", "relationships"),
):
    if path not in sys.path:
        sys.path.insert(0, path)


def _fail(step: str, detail) -> int:
    print("[FAIL] {} -> {}".format(step, detail))
    return 1


def main() -> int:
    from generator_bridge_runner import load_params_fixture, run_overhead
    from generator_declared_service import reconcile_generator_declarations
    from generator_panel_adapter import snapshots_from_generator_result
    from hardware_rule_engine import (
        HARDWARE_TYPE_DRAWER_RUNNER_HOLE,
        HARDWARE_TYPE_HINGE_HOLE,
        HARDWARE_TYPE_LOCK_CUTOUT,
        HARDWARE_TYPE_SCREW_HOLE,
        HARDWARE_TYPE_TONGUE_GROOVE,
        dispatch_hardware_cut_plan,
        dispatch_hardware_preview,
        list_hardware_types,
    )
    from overhead_declared_relationships import extract_board_suffix
    from relationship_service import build_panel_snapshot_from_dict

    types = {row["type"]: row for row in list_hardware_types()}
    for hw_type in (
        HARDWARE_TYPE_SCREW_HOLE,
        HARDWARE_TYPE_TONGUE_GROOVE,
        HARDWARE_TYPE_HINGE_HOLE,
        HARDWARE_TYPE_DRAWER_RUNNER_HOLE,
        HARDWARE_TYPE_LOCK_CUTOUT,
    ):
        meta = types.get(hw_type) or {}
        if not (meta.get("implemented") and meta.get("cutReady")):
            return _fail("registry {}".format(hw_type), meta)
    print("[PASS] registry: 5 hardware types cutReady")

    bridge = run_overhead(load_params_fixture("overhead_edge_only.json"))
    snapshots = [
        build_panel_snapshot_from_dict(item)
        for item in snapshots_from_generator_result("overhead", bridge)
    ]
    report = reconcile_generator_declarations(
        snapshots,
        generator="overhead",
        embedded_declarations=bridge.get("relationshipDeclarations") or [],
    )
    if not report.get("ok"):
        return _fail("overhead reconcile", report.get("errors"))
    relationships = report.get("declaredRelationships") or []
    bp_d0 = next(
        (
            rel
            for rel in relationships
            if {
                extract_board_suffix((rel.get("panelA") or {}).get("panelId") or ""),
                extract_board_suffix((rel.get("panelB") or {}).get("panelId") or ""),
            }
            == {"BP", "D0"}
        ),
        None,
    )
    if not bp_d0 or bp_d0.get("verification", {}).get("level") != "generator_declared":
        return _fail("BP-D0 declared", bp_d0)
    print("[PASS] overhead BP-D0 generator_declared")

    panel_map = {snap.panelId: snap.to_dict() for snap in snapshots}
    host_id = bp_d0["roles"]["hostPanelId"]
    target_id = bp_d0["roles"]["targetPanelId"]
    panels_payload = {host_id: panel_map[host_id], target_id: panel_map[target_id]}

    for hw_type in (
        HARDWARE_TYPE_SCREW_HOLE,
        HARDWARE_TYPE_TONGUE_GROOVE,
        HARDWARE_TYPE_HINGE_HOLE,
        HARDWARE_TYPE_DRAWER_RUNNER_HOLE,
        HARDWARE_TYPE_LOCK_CUTOUT,
    ):
        preview = dispatch_hardware_preview(bp_d0, rule={"type": hw_type}, panel_snapshots=panels_payload)
        if not preview.get("ok"):
            return _fail("{} preview".format(hw_type), preview)
        plan = dispatch_hardware_cut_plan(bp_d0, rule={"type": hw_type}, panel_snapshots=panels_payload)
        if not plan.get("ok"):
            return _fail("{} cut plan".format(hw_type), plan)
        print("[PASS] {} preview + cut plan on overhead BP-D0".format(hw_type))

    print("")
    print("Real-cabinet hardware offline: ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
