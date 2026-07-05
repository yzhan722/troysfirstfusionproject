#!/usr/bin/env python3
"""M6 Connect smoke — run INSIDE Fusion 360 (Scripts and Add-Ins → Run).

Add from plugin folder:
  fusion360-unified-cabinet-plugin/m6_connect_smoke.py

Flow: generate Overhead → reconcile generator declarations → preview → cut (BP↔D0)

Results: fusion360-unified-cabinet-plugin/tests/output/m6_fusion_smoke_results.json
"""

from __future__ import annotations

import os
import sys
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import adsk.core

DEFAULT_REPO_PLUGIN_DIR = r"d:\project\troysfirstfusionproject-main\fusion360-unified-cabinet-plugin"
TARGET_DECLARATION_ID = "oh_bp_d0_back_to_divider"


def _bootstrap_imports(script_file: str):
    script_dir = os.path.dirname(os.path.abspath(script_file))
    candidates = [
        script_dir,
        os.path.join(script_dir, "fusion360-unified-cabinet-plugin"),
        os.path.dirname(script_dir),
        os.environ.get("CABINETNC_PLUGIN_DIR") or "",
        DEFAULT_REPO_PLUGIN_DIR,
    ]
    plugin_dir = None
    for candidate in candidates:
        if not candidate:
            continue
        if os.path.isfile(os.path.join(candidate, "UnifiedCabinetPlugin.py")):
            plugin_dir = candidate
            break
    if not plugin_dir:
        plugin_dir = DEFAULT_REPO_PLUGIN_DIR

    tests_dir = os.path.join(plugin_dir, "tests")
    for path in (tests_dir, plugin_dir, script_dir):
        if path and path not in sys.path:
            sys.path.insert(0, path)

    import smoke_connect_helpers as helpers  # noqa: WPS433

    return plugin_dir, helpers


def _find_declared_relationship(report: Dict[str, Any], declaration_id: str) -> Optional[Dict[str, Any]]:
    for item in report.get("reconciled") or []:
        if item.get("declarationId") == declaration_id and item.get("relationship"):
            return item["relationship"]
    for rel in report.get("declaredRelationships") or []:
        if rel.get("declaration", {}).get("declarationId") == declaration_id:
            return rel
    return None


def _scan_payload_from_panels(report: Dict[str, Any]) -> Dict[str, Any]:
    rels = report.get("declaredRelationships") or []
    return {
        "ok": bool(report.get("ok")),
        "panels": [],
        "relationships": rels,
        "relationshipCount": len(rels),
    }


def _run_smoke(plugin_dir: str, helpers, fusion, rel_ctrl, hw_ctrl, overhead_ctrl, screw_mod, import_meta) -> Dict[str, Any]:
    steps: List[Dict[str, Any]] = []
    root = fusion.get_root_component()
    cut_report: Dict[str, Any] = {}

    params = helpers.load_json_fixture(plugin_dir, "tests", "fixtures", "generator_params", "overhead_edge_only.json")
    run_label = datetime.now(timezone.utc).strftime("m6_smoke_%Y%m%d_%H%M%S")
    _ev, gen_payload = overhead_ctrl.create_fusion_rough_bodies(
        {
            "params": params,
            "assemblyName": "M6_OH_SMOKE",
            "caseName": run_label,
        },
        None,
    )
    step1_ok = bool(gen_payload.get("ok")) and int(gen_payload.get("createdBodies") or 0) >= 8
    steps.append(
        {
            "step": "1 generate overhead",
            "status": "PASS" if step1_ok else "FAIL",
            "data": {
                "createdBodies": gen_payload.get("createdBodies"),
                "createdBoardIds": gen_payload.get("createdBoardIds"),
                "errors": gen_payload.get("errors"),
            },
        }
    )
    if not step1_ok:
        return {"overall": "FAIL", "pluginDir": plugin_dir, "importMeta": import_meta, "steps": steps}

    run_label = str(gen_payload.get("runLabel") or run_label)
    _ev, reconcile_report = rel_ctrl.reconcile_generator_declarations(
        {
            "generator": "overhead",
            "toleranceMm": 0.5,
            "runLabel": run_label,
            "assemblyComponentName": gen_payload.get("assemblyComponentName"),
            "bboxSource": "design_preferred",
        },
        None,
    )
    step2_ok = (
        reconcile_report.get("ok") is True
        and int(reconcile_report.get("declarationCount") or 0) >= 4
        and int(reconcile_report.get("geometryOkCount") or 0) >= 4
    )
    steps.append(
        {
            "step": "2 reconcile declarations",
            "status": "PASS" if step2_ok else "FAIL",
            "data": {
                "declarationCount": reconcile_report.get("declarationCount"),
                "geometryOkCount": reconcile_report.get("geometryOkCount"),
                "errors": reconcile_report.get("errors"),
            },
        }
    )
    if not step2_ok:
        return {"overall": "FAIL", "pluginDir": plugin_dir, "importMeta": import_meta, "steps": steps, "reconcile": reconcile_report}

    declared_rel = _find_declared_relationship(reconcile_report, TARGET_DECLARATION_ID)
    verification = (declared_rel or {}).get("verification") or {}
    geom_val = (declared_rel or {}).get("geometryValidation") or {}
    step3_ok = (
        declared_rel is not None
        and verification.get("level") == "generator_declared"
        and geom_val.get("ok") is True
        and verification.get("safeForCut") is True
    )
    steps.append(
        {
            "step": "3 bp_d0 generator_declared",
            "status": "PASS" if step3_ok else "FAIL",
            "data": {
                "relationshipId": (declared_rel or {}).get("relationshipId"),
                "verification": verification,
                "geometryValidation": geom_val,
                "declaration": (declared_rel or {}).get("declaration"),
            },
        }
    )
    if not step3_ok or not declared_rel:
        return {"overall": "FAIL", "pluginDir": plugin_dir, "importMeta": import_meta, "steps": steps, "reconcile": reconcile_report}

    _ev, scan_payload = rel_ctrl.scan({"scope": "all", "toleranceMm": 0.5}, None)
    panel_map = helpers.panels_map(scan_payload)
    host_id = declared_rel["roles"]["hostPanelId"]
    target_id = declared_rel["roles"]["targetPanelId"]
    panel_snapshots = {host_id: panel_map[host_id], target_id: panel_map[target_id]}

    preview_report = screw_mod.preview_screw_holes_from_relationship(
        declared_rel,
        rule=helpers.HW_REL_DEBUG_RULE,
        panel_snapshots=panel_snapshots,
    )
    step4_ok = preview_report.get("ok") and int(preview_report.get("holeCount") or 0) >= 1
    steps.append(
        {
            "step": "4 preview declared",
            "status": "PASS" if step4_ok else "FAIL",
            "data": {
                "holeCount": preview_report.get("holeCount"),
                "verificationLevel": (preview_report.get("audit") or {}).get("verificationLevel"),
            },
        }
    )
    if not step4_ok:
        return {"overall": "FAIL", "pluginDir": plugin_dir, "importMeta": import_meta, "steps": steps, "reconcile": reconcile_report}

    blocked = screw_mod.plan_screw_hole_cut_from_relationship(
        next(
            rel
            for rel in (scan_payload.get("relationships") or [])
            if {rel.get("panelA", {}).get("panelId"), rel.get("panelB", {}).get("panelId")} == {host_id, target_id}
        ),
        rule=helpers.HW_REL_DEBUG_RULE,
        panel_snapshots=panel_snapshots,
    )
    step5_ok = blocked.get("ok") is False
    steps.append(
        {
            "step": "5 negative bbox-only cut",
            "status": "PASS" if step5_ok else "FAIL",
            "data": {"errors": blocked.get("errors")},
        }
    )
    if not step5_ok:
        return {"overall": "FAIL", "pluginDir": plugin_dir, "importMeta": import_meta, "steps": steps, "reconcile": reconcile_report}

    scan_stub = _scan_payload_from_panels(reconcile_report)
    scan_stub["panels"] = list(panel_map.values())
    cut_payload = helpers.build_cut_payload(declared_rel, scan_stub)
    cut_payload["panels"] = panel_snapshots
    _ev, cut_report = hw_ctrl.create_screw_holes_from_relationship(cut_payload, None)
    step6_ok = (
        cut_report.get("ok") is True
        and cut_report.get("operationType") == "SCREW_HOLE_FROM_RELATIONSHIP"
        and bool(cut_report.get("cutFeatureName"))
        and cut_report.get("metadataWritten") is True
        and cut_report.get("targetBodyModified") is False
    )
    steps.append({"step": "6 cut generator_declared", "status": "PASS" if step6_ok else "FAIL", "data": cut_report})

    cut_name = cut_report.get("cutFeatureName")
    step7_ok = step6_ok and helpers.cut_feature_exists(root, cut_name)
    steps.append(
        {
            "step": "7 visual timeline",
            "status": "PASS" if step7_ok else "FAIL",
            "data": {
                "cutFeatureName": cut_name,
                "cutFeatureInTimeline": helpers.cut_feature_exists(root, cut_name),
            },
        }
    )

    overall = all(item["status"] == "PASS" for item in steps)
    return {
        "overall": "PASS" if overall else "FAIL",
        "milestone": "M6",
        "generator": "overhead",
        "pluginDir": plugin_dir,
        "importMeta": import_meta,
        "fusionVersion": adsk.core.Application.get().version if adsk.core.Application.get() else "",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "steps": steps,
        "reconcile": reconcile_report,
        "cutAudit": cut_report,
    }


def _notify(ui, message: str) -> None:
    if ui:
        ui.messageBox(message)
        return
    app = adsk.core.Application.get()
    if app:
        try:
            app.log("M6 smoke", message[:3500])
        except Exception:
            pass
    print(message)


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface if app else None
        plugin_dir, helpers = _bootstrap_imports(__file__)
        fusion, rel_ctrl, hw_ctrl, screw_mod, import_meta = helpers.import_plugin_modules(plugin_dir)

        import importlib

        overhead_mod = importlib.import_module("modules.overhead.controller")
        overhead_ctrl = overhead_mod.OverheadController(plugin_dir, fusion)

        result = _run_smoke(plugin_dir, helpers, fusion, rel_ctrl, hw_ctrl, overhead_ctrl, screw_mod, import_meta)
        out_path = helpers.write_smoke_results(plugin_dir, __file__, "m6_fusion_smoke_results.json", result)
        decl = ((result.get("reconcile") or {}).get("reconciled") or [{}])[0]
        _notify(
            ui,
            "M6 Connect smoke: {}\nDeclarations: {} / {} geometry OK\nPlugin: {}\nResults: {}".format(
                result.get("overall"),
                result.get("reconcile", {}).get("declarationCount"),
                result.get("reconcile", {}).get("geometryOkCount"),
                plugin_dir,
                out_path,
            ),
        )
    except Exception:
        msg = traceback.format_exc()
        _notify(ui, "M6 Connect smoke FAILED:\n{}".format(msg))
        raise
