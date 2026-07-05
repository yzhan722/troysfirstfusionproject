#!/usr/bin/env python3
"""Connect pipeline smoke — run INSIDE Fusion 360 (Scripts and Add-Ins → Run).

Unified M6–M9 verification. Replaces m6_connect_smoke.py and m7_connect_smoke.py.

Add from plugin folder:
  fusion360-unified-cabinet-plugin/connect_pipeline_smoke.py

Results: fusion360-unified-cabinet-plugin/tests/output/connect_pipeline_fusion_smoke_results.json
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


def _run_smoke(plugin_dir: str, helpers, fusion, rel_ctrl, hw_ctrl, overhead_ctrl, screw_mod, import_meta) -> Dict[str, Any]:
    steps: List[Dict[str, Any]] = []
    root = fusion.get_root_component()
    cut_report: Dict[str, Any] = {}

    params = helpers.load_json_fixture(plugin_dir, "tests", "fixtures", "generator_params", "overhead_edge_only.json")
    run_label = datetime.now(timezone.utc).strftime("connect_smoke_%Y%m%d_%H%M%S")
    _ev, gen_payload = overhead_ctrl.create_fusion_rough_bodies(
        {"params": params, "assemblyName": "CONNECT_PIPELINE_SMOKE", "caseName": run_label},
        None,
    )
    step1_ok = bool(gen_payload.get("ok")) and int(gen_payload.get("createdBodies") or 0) >= 8
    steps.append({"step": "1 generate overhead", "status": "PASS" if step1_ok else "FAIL", "data": gen_payload})
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
    declared_rel = _find_declared_relationship(reconcile_report, TARGET_DECLARATION_ID)
    step2_ok = (
        reconcile_report.get("ok") is True
        and int(reconcile_report.get("declarationCount") or 0) >= 4
        and declared_rel is not None
        and (declared_rel.get("verification") or {}).get("level") == "generator_declared"
    )
    steps.append(
        {
            "step": "2 M6 reconcile declarations",
            "status": "PASS" if step2_ok else "FAIL",
            "data": {
                "declarationCount": reconcile_report.get("declarationCount"),
                "geometryOkCount": reconcile_report.get("geometryOkCount"),
                "relationshipId": (declared_rel or {}).get("relationshipId"),
            },
        }
    )
    if not step2_ok or not declared_rel:
        return {"overall": "FAIL", "pluginDir": plugin_dir, "importMeta": import_meta, "steps": steps, "reconcile": reconcile_report}

    _ev, scan_payload = rel_ctrl.scan({"scope": "all", "toleranceMm": 0.5}, None)
    _ev, connect_view = rel_ctrl.connect_list(
        {
            "scanResult": scan_payload,
            "reconcileResult": reconcile_report,
            "selectedRelationshipId": declared_rel.get("relationshipId"),
            "filters": {"geometryType": "edge_to_surface"},
        },
        None,
    )
    actions = connect_view.get("actions") or {}
    step3_ok = connect_view.get("ok") and actions.get("preview", {}).get("ok") and actions.get("cut", {}).get("ok")
    steps.append(
        {
            "step": "3 M7 connect_list declared",
            "status": "PASS" if step3_ok else "FAIL",
            "data": {"filteredCount": connect_view.get("filteredCount"), "actions": actions},
        }
    )
    if not step3_ok:
        return {"overall": "FAIL", "pluginDir": plugin_dir, "importMeta": import_meta, "steps": steps}

    bbox_rel = next(
        (
            rel
            for rel in (scan_payload.get("relationships") or [])
            if (rel.get("verification") or {}).get("level") == "bbox_candidate"
            and rel.get("geometryType") == "edge_to_surface"
        ),
        None,
    )
    _ev, bbox_cut_gate = rel_ctrl.connect_execute({"action": "cut", "relationship": bbox_rel}, None)
    step4_ok = bbox_rel is not None and bbox_cut_gate.get("ok") is False
    steps.append(
        {
            "step": "4 M7 bbox_candidate cut blocked",
            "status": "PASS" if step4_ok else "FAIL",
            "data": {"gate": bbox_cut_gate},
        }
    )
    if not step4_ok:
        return {"overall": "FAIL", "pluginDir": plugin_dir, "importMeta": import_meta, "steps": steps}

    panel_map = helpers.panels_map(scan_payload)
    host_id = declared_rel["roles"]["hostPanelId"]
    target_id = declared_rel["roles"]["targetPanelId"]
    panel_snapshots = {host_id: panel_map[host_id], target_id: panel_map[target_id]}

    _ev, preview_gate = rel_ctrl.connect_execute({"action": "preview", "relationship": declared_rel}, None)
    preview_report = screw_mod.preview_screw_holes_from_relationship(
        declared_rel,
        rule=helpers.HW_REL_DEBUG_RULE,
        panel_snapshots=panel_snapshots,
    )
    step5_ok = preview_gate.get("ok") and preview_report.get("ok")
    steps.append(
        {
            "step": "5 preview gate + hardware",
            "status": "PASS" if step5_ok else "FAIL",
            "data": {"previewGate": preview_gate, "holeCount": preview_report.get("holeCount")},
        }
    )
    if not step5_ok:
        return {"overall": "FAIL", "pluginDir": plugin_dir, "importMeta": import_meta, "steps": steps}

    _ev, cut_gate = rel_ctrl.connect_execute({"action": "cut", "relationship": declared_rel}, None)
    cut_payload = helpers.build_cut_payload(declared_rel, scan_payload)
    cut_payload["panels"] = panel_snapshots
    _ev, cut_report = hw_ctrl.create_screw_holes_from_relationship(cut_payload, None)
    step6_ok = (
        cut_gate.get("ok")
        and cut_report.get("ok")
        and cut_report.get("metadataWritten") is True
        and cut_report.get("panelWriteback") is True
    )
    steps.append(
        {
            "step": "6 cut + M8 panel writeback",
            "status": "PASS" if step6_ok else "FAIL",
            "data": {
                "cutGate": cut_gate,
                "panelWriteback": cut_report.get("panelWriteback"),
                "panelFeatureCount": cut_report.get("panelFeatureCount"),
                "writeback": cut_report.get("writeback"),
            },
        }
    )
    if not step6_ok:
        return {"overall": "FAIL", "pluginDir": plugin_dir, "importMeta": import_meta, "steps": steps, "cutAudit": cut_report}

    import importlib

    import hardware_rule_engine

    hardware_rule_engine = importlib.reload(hardware_rule_engine)
    types = hardware_rule_engine.list_hardware_types()
    tongue_gate = hardware_rule_engine.evaluate_hardware_rule(
        hardware_rule_engine.HARDWARE_TYPE_TONGUE_GROOVE,
        bbox_rel,
        action="cut",
    )
    step7_ok = len(types) >= 5 and tongue_gate.get("ok") is False and tongue_gate.get("previewOnly") is True
    steps.append(
        {
            "step": "7 M9 hardware registry",
            "status": "PASS" if step7_ok else "FAIL",
            "data": {"hardwareTypes": [row["type"] for row in types], "tongueGate": tongue_gate},
        }
    )

    cut_name = cut_report.get("cutFeatureName")
    step8_ok = helpers.cut_feature_exists(root, cut_name)
    steps.append(
        {
            "step": "8 visual timeline",
            "status": "PASS" if step8_ok else "FAIL",
            "data": {"cutFeatureName": cut_name, "cutFeatureInTimeline": step8_ok},
        }
    )

    overall = all(item["status"] == "PASS" for item in steps)
    return {
        "overall": "PASS" if overall else "FAIL",
        "milestone": "M6-M9",
        "generator": "overhead",
        "pluginDir": plugin_dir,
        "importMeta": import_meta,
        "fusionVersion": adsk.core.Application.get().version if adsk.core.Application.get() else "",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "steps": steps,
        "reconcile": reconcile_report,
        "connectView": connect_view,
        "cutAudit": cut_report,
    }


def _notify(ui, message: str) -> None:
    if ui:
        ui.messageBox(message)
        return
    app = adsk.core.Application.get()
    if app:
        try:
            app.log("Connect pipeline smoke", message[:3500])
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
        out_path = helpers.write_smoke_results(plugin_dir, __file__, "connect_pipeline_fusion_smoke_results.json", result)
        _notify(
            ui,
            "Connect pipeline smoke: {}\nDeclarations: {} / {} geometry OK\nPanel writeback: {}\nPlugin: {}\nResults: {}".format(
                result.get("overall"),
                result.get("reconcile", {}).get("declarationCount"),
                result.get("reconcile", {}).get("geometryOkCount"),
                (result.get("cutAudit") or {}).get("panelWriteback"),
                plugin_dir,
                out_path,
            ),
        )
    except Exception:
        msg = traceback.format_exc()
        _notify(ui, "Connect pipeline smoke FAILED:\n{}".format(msg))
        raise
