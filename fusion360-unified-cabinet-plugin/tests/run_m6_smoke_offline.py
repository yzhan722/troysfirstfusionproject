#!/usr/bin/env python3
"""M6 smoke test — offline generator-declared relationship reconciliation."""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
REL_DIR = ROOT / "modules" / "relationships"
HW_DIR = ROOT / "modules" / "hardware"
TESTS_DIR = Path(__file__).resolve().parent
for path in (ROOT, TESTS_DIR, REL_DIR, HW_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from generator_bridge_runner import load_params_fixture, run_overhead  # noqa: E402
from generator_declared_service import reconcile_generator_declarations  # noqa: E402
from generator_panel_adapter import snapshots_from_generator_result  # noqa: E402
from relationship_service import build_panel_snapshot_from_dict  # noqa: E402
from screw_hole_from_relationship import plan_screw_hole_cut_from_relationship, validate_relationship_for_cut  # noqa: E402

HW_REL_DEBUG_RULE = {
    "type": "screw_hole",
    "diameterMm": 4,
    "edgeOffsetMm": 30,
    "minSpacingMm": 80,
    "depthMode": "host_thickness",
}


class StepResult:
    def __init__(self, step: str, passed: bool, notes: str = "", data: Optional[Dict[str, Any]] = None):
        self.step = step
        self.passed = passed
        self.notes = notes
        self.data = data or {}


def _overhead_snapshots():
    bridge = run_overhead(load_params_fixture("overhead_edge_only.json"))
    return [
        build_panel_snapshot_from_dict(item)
        for item in snapshots_from_generator_result("overhead", bridge)
    ]


def run_smoke() -> Tuple[List[StepResult], bool]:
    results: List[StepResult] = []
    try:
        snapshots = _overhead_snapshots()
        step1_ok = len(snapshots) >= 8
        results.append(
            StepResult("1 overhead snapshots", step1_ok, "panelCount={}".format(len(snapshots)), {"panelIds": [s.panelId for s in snapshots]})
        )
        if not step1_ok:
            return results, False

        report = reconcile_generator_declarations(snapshots, generator="overhead")
        step2_ok = bool(report.get("ok")) and int(report.get("declarationCount") or 0) >= 4
        results.append(
            StepResult(
                "2 reconcile declarations",
                step2_ok,
                "declarations={} geometryOk={}".format(report.get("declarationCount"), report.get("geometryOkCount")),
                {"report": report},
            )
        )
        if not step2_ok:
            return results, False

        rel = next(
            item["relationship"]
            for item in report.get("reconciled") or []
            if item.get("declarationId") == "oh_bp_d0_back_to_divider"
        )
        step3_ok = (
            rel.get("verification", {}).get("level") == "generator_declared"
            and rel.get("geometryValidation", {}).get("ok") is True
        )
        results.append(
            StepResult(
                "3 bp_d0 generator_declared",
                step3_ok,
                "relationshipId={}".format(rel.get("relationshipId")),
                {"verification": rel.get("verification"), "geometryValidation": rel.get("geometryValidation")},
            )
        )
        if not step3_ok:
            return results, False

        panel_map = {snap.panelId: snap.to_dict() for snap in snapshots}
        host_id = rel["roles"]["hostPanelId"]
        target_id = rel["roles"]["targetPanelId"]
        gate_ok = validate_relationship_for_cut(rel) is None
        plan = plan_screw_hole_cut_from_relationship(
            rel,
            rule=HW_REL_DEBUG_RULE,
            panel_snapshots={host_id: panel_map[host_id], target_id: panel_map[target_id]},
        )
        step4_ok = gate_ok and bool(plan.get("ok"))
        results.append(
            StepResult(
                "4 cut plan declared+geometry",
                step4_ok,
                "host={} target={}".format(host_id, target_id),
                {"planOk": plan.get("ok"), "holeCount": plan.get("holeCount")},
            )
        )
        return results, step4_ok
    except Exception:
        results.append(StepResult("error", False, traceback.format_exc()))
        return results, False


def main() -> int:
    print("M6 Generator-Declared Relationships Smoke Test (offline)")
    print("=" * 55)
    results, overall = run_smoke()
    for item in results:
        status = "PASS" if item.passed else "FAIL"
        print("\n== Step {}: {} ==".format(item.step, status))
        if item.notes:
            print(item.notes)

    out_dir = ROOT / "tests" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "m6_smoke_offline_results.json"
    out_path.write_text(
        json.dumps(
            {
                "milestone": "M6",
                "overall": "PASS" if overall else "FAIL",
                "generator": "overhead",
                "steps": [{"step": s.step, "status": "PASS" if s.passed else "FAIL", "notes": s.notes, "data": s.data} for s in results],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print("\n== Summary ==")
    print("M6 offline: {}".format("PASS" if overall else "FAIL"))
    print("Results: {}".format(out_path))
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
