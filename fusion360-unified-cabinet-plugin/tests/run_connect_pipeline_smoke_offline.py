#!/usr/bin/env python3
"""Connect pipeline smoke — offline verification for M6–M9.

Replaces per-milestone run_m6_smoke_offline.py and run_m7_smoke_offline.py.
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
REL_DIR = ROOT / "modules" / "relationships"
HW_DIR = ROOT / "modules" / "hardware"
PANEL_ATTR_DIR = ROOT / "panel_attributes"
TESTS_DIR = Path(__file__).resolve().parent
for path in (ROOT, TESTS_DIR, REL_DIR, HW_DIR, PANEL_ATTR_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from connect_demo_pack import find_first_screw_eligible  # noqa: E402
from connect_formal_ui import build_connect_view_model, evaluate_connect_action  # noqa: E402
from generator_bridge_runner import load_params_fixture, run_overhead  # noqa: E402
from generator_declared_service import reconcile_generator_declarations  # noqa: E402
from generator_panel_adapter import snapshots_from_generator_result  # noqa: E402
from hardware_rule_engine import (  # noqa: E402
    HARDWARE_TYPE_SCREW_HOLE,
    HARDWARE_TYPE_TONGUE_GROOVE,
    dispatch_hardware_cut_plan,
    dispatch_hardware_preview,
    evaluate_hardware_rule,
    list_hardware_types,
)
from panel_metadata_writeback import (  # noqa: E402
    OPERATION_TYPE,
    append_hardware_feature,
    build_panel_feature_record,
    find_hardware_features,
)
from relationship_fixtures import build_fixture_snapshots, expected_fixture_cases  # noqa: E402
from relationship_report import build_scan_report  # noqa: E402
from relationship_service import build_panel_snapshot_from_dict, scan_relationships  # noqa: E402
from screw_hole_from_relationship import build_cut_feature_metadata, plan_screw_hole_cut_from_relationship  # noqa: E402

HW_REL_DEBUG_RULE = {
    "type": "screw_hole",
    "diameterMm": 4,
    "edgeOffsetMm": 30,
    "minSpacingMm": 80,
    "depthMode": "host_thickness",
}
TARGET_DECLARATION_ID = "oh_bp_d0_back_to_divider"


class StepResult:
    def __init__(self, step: str, passed: bool, notes: str = "", data: Optional[Dict[str, Any]] = None):
        self.step = step
        self.passed = passed
        self.notes = notes
        self.data = data or {}


def _fixture_scan() -> Dict[str, Any]:
    panels = build_fixture_snapshots()
    _, relationships = scan_relationships(panels, tolerance_mm=0.5, include_none=True)
    return build_scan_report(
        action="relationships.scan",
        panels=panels,
        relationships=relationships,
        scope="fixture",
        tolerance_mm=0.5,
        expected_fixtures=expected_fixture_cases(),
    )


def _overhead_reconcile():
    snapshots = [
        build_panel_snapshot_from_dict(item)
        for item in snapshots_from_generator_result("overhead", run_overhead(load_params_fixture("overhead_edge_only.json")))
    ]
    report = reconcile_generator_declarations(snapshots, generator="overhead")
    declared = next(
        item["relationship"]
        for item in report.get("reconciled") or []
        if item.get("declarationId") == TARGET_DECLARATION_ID
    )
    return snapshots, report, declared


def run_smoke() -> Tuple[List[StepResult], bool]:
    results: List[StepResult] = []
    try:
        snapshots, reconcile, declared = _overhead_reconcile()
        step_m6_ok = (
            bool(reconcile.get("ok"))
            and int(reconcile.get("declarationCount") or 0) >= 4
            and declared.get("verification", {}).get("level") == "generator_declared"
        )
        results.append(
            StepResult(
                "M6 reconcile generator_declared",
                step_m6_ok,
                "declarations={} geometryOk={}".format(
                    reconcile.get("declarationCount"), reconcile.get("geometryOkCount")
                ),
                {"declarationId": TARGET_DECLARATION_ID},
            )
        )
        if not step_m6_ok:
            return results, False

        scan = _fixture_scan()
        rel = find_first_screw_eligible(scan.get("relationships") or [])
        view = build_connect_view_model(
            scan,
            filters={"geometryType": "edge_to_surface"},
            selected_relationship_id=(rel or {}).get("relationshipId"),
        )
        step_m7_ok = (
            view.get("filteredCount", 0) >= 1
            and view["actions"]["preview"]["ok"]
            and view["actions"]["confirm"]["ok"]
            and not view["actions"]["cut"]["ok"]
        )
        results.append(
            StepResult(
                "M7 connect list + gates",
                step_m7_ok,
                "filtered={}/{} cutBlocked={}".format(
                    view.get("filteredCount"), view.get("relationshipCount"), not view["actions"]["cut"]["ok"]
                ),
                {"actions": view.get("actions")},
            )
        )
        if not step_m7_ok:
            return results, False

        confirm_gate = evaluate_connect_action("confirm", rel)
        confirmed = confirm_gate.get("confirmedRelationship")
        panel_map = {panel.panelId: panel.to_dict() for panel in build_fixture_snapshots()}
        host_id = rel["roles"]["hostPanelId"]
        target_id = rel["roles"]["targetPanelId"]
        plan = plan_screw_hole_cut_from_relationship(
            confirmed,
            rule=HW_REL_DEBUG_RULE,
            panel_snapshots={host_id: panel_map[host_id], target_id: panel_map[target_id]},
        )
        cut_meta = build_cut_feature_metadata(
            plan["feature"],
            relationship_id=plan["relationshipId"],
            host_panel_id=host_id,
            target_panel_id=target_id,
        )
        record = build_panel_feature_record(plan["feature"], cut_metadata=cut_meta, cut_feature_name="HW_REL_SCREW_HOLE_TEST")
        metadata, appended, _ = append_hardware_feature({"schemaVersion": 1, "features": []}, record)
        found = find_hardware_features(metadata, source_relationship_id=plan["relationshipId"], operation_type=OPERATION_TYPE)
        step_m8_ok = bool(plan.get("ok")) and appended and len(found) == 1
        results.append(
            StepResult(
                "M8 panel metadata writeback",
                step_m8_ok,
                "featureCount={} featureId={}".format(len(found), found[0].get("featureId") if found else None),
                {"featureRecord": record, "found": found},
            )
        )
        if not step_m8_ok:
            return results, False

        declared_view = build_connect_view_model(
            {
                "ok": True,
                "panels": [s.to_dict() for s in snapshots],
                "relationships": reconcile.get("declaredRelationships") or [],
            },
            selected_relationship_id=declared.get("relationshipId"),
        )
        types = list_hardware_types()
        preview = dispatch_hardware_preview(
            declared,
            rule={"type": HARDWARE_TYPE_SCREW_HOLE},
            panel_snapshots={s.panelId: s.to_dict() for s in snapshots},
        )
        tongue_cut = evaluate_hardware_rule(HARDWARE_TYPE_TONGUE_GROOVE, rel, action="cut")
        declared_cut = dispatch_hardware_cut_plan(
            declared,
            rule={"type": HARDWARE_TYPE_SCREW_HOLE},
            panel_snapshots={s.panelId: s.to_dict() for s in snapshots},
        )
        step_m9_ok = (
            len(types) >= 5
            and preview.get("ok")
            and declared_view["actions"]["cut"]["ok"]
            and declared_cut.get("ok")
            and tongue_cut.get("ok") is False
            and tongue_cut.get("previewOnly") is True
        )
        results.append(
            StepResult(
                "M9 hardware types + dispatch",
                step_m9_ok,
                "types={} screwPreview={} declaredCut={} tongueBlocked={}".format(
                    len(types), preview.get("ok"), declared_cut.get("ok"), not tongue_cut.get("ok")
                ),
                {"hardwareTypes": [row["type"] for row in types]},
            )
        )
        return results, step_m9_ok
    except Exception:
        results.append(StepResult("error", False, traceback.format_exc()))
        return results, False


def main() -> int:
    print("Connect Pipeline Smoke Test (offline M6–M9)")
    print("=" * 55)
    results, overall = run_smoke()
    for item in results:
        status = "PASS" if item.passed else "FAIL"
        print("\n== Step {}: {} ==".format(item.step, status))
        if item.notes:
            print(item.notes)

    out_dir = ROOT / "tests" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "connect_pipeline_smoke_offline_results.json"
    out_path.write_text(
        json.dumps(
            {
                "milestone": "M6-M9",
                "overall": "PASS" if overall else "FAIL",
                "steps": [
                    {"step": s.step, "status": "PASS" if s.passed else "FAIL", "notes": s.notes, "data": s.data}
                    for s in results
                ],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print("\n== Summary ==")
    print("Connect pipeline offline: {}".format("PASS" if overall else "FAIL"))
    print("Results: {}".format(out_path))
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
