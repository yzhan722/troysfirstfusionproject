import importlib
import json
import os
import random
import shutil
import subprocess
import sys
import time
import traceback


GENERATE_PAYLOAD_TYPE = "generateFridgeCabinet"


def _iso_now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _new_run_id():
    return "{}-{}".format(int(time.time() * 1000), random.randint(10000, 99999))


def _validation_ok(validation):
    return isinstance(validation, dict) and validation.get("ok") is True


def _validation_ok_tri_state(validation):
    if not isinstance(validation, dict) or "ok" not in validation:
        return None
    return True if validation.get("ok") is True else False


class FridgeController:
    def __init__(self, plugin_dir, fusion_adapter):
        self.plugin_dir = plugin_dir
        self.fusion = fusion_adapter

    def calculate(self, payload, _palette):
        return (
            "unifiedResult",
            {
                "ok": True,
                "module": "fridge",
                "action": "fridge.calculate",
                "message": "Calculation is handled in the palette with FridgeCabinetLogic.",
            },
        )

    def validate(self, payload, _palette):
        params = self._extract_pure_params(payload)
        validation = params.get("validation") if isinstance(params, dict) else None
        return (
            "fridgeCabinetResult",
            {
                "finalStatus": "pass" if _validation_ok(validation) else "fail",
                "diagnosticsOnly": True,
                "pureParamsValidationOk": _validation_ok_tri_state(validation),
                "errors": list(validation.get("errors", [])) if isinstance(validation, dict) else ["Missing PureParams validation."],
                "warnings": list(validation.get("warnings", [])) if isinstance(validation, dict) else [],
                "infos": list(validation.get("infos", [])) if isinstance(validation, dict) else [],
            },
        )

    def generate(self, payload, _palette):
        pure_params = self._extract_pure_params(payload)
        diagnostics = {
            "runId": str(payload.get("runId") or _new_run_id()) if isinstance(payload, dict) else _new_run_id(),
            "pythonSteps": [],
            "pythonStartedAt": _iso_now(),
        }
        assembly_name = payload.get("assemblyName") if isinstance(payload, dict) else None

        origin_x_mm = origin_y_mm = 0.0
        origin_active = False
        try:
            import work_zones

            root = self.fusion.get_root_component() if self.fusion else None
            origin_x_mm, origin_y_mm = work_zones.resolve_origin_from_payload(payload, root)
            if isinstance(payload, dict):
                origin_active = (
                    payload.get("originXMm") is not None
                    or payload.get("originYMm") is not None
                    or (root is not None and work_zones.load_zone_layout(root) is not None)
                )
        except Exception:
            if isinstance(payload, dict):
                try:
                    origin_x_mm = float(payload.get("originXMm") or 0.0)
                except Exception:
                    origin_x_mm = 0.0
                try:
                    origin_y_mm = float(payload.get("originYMm") or 0.0)
                except Exception:
                    origin_y_mm = 0.0
                origin_active = payload.get("originXMm") is not None or payload.get("originYMm") is not None

        result = self._handle_generate_fridge_cabinet(
            pure_params,
            diagnostics,
            diagnostics_only=bool(payload.get("diagnosticsOnly", False)) if isinstance(payload, dict) else False,
            received_board_plan=payload.get("boardPlan") if isinstance(payload, dict) else None,
            received_v_verify=payload.get("vVerify") if isinstance(payload, dict) else None,
            preview_mode=payload.get("previewMode", "assembly_3d") if isinstance(payload, dict) else "assembly_3d",
            assembly_name=(str(assembly_name).strip() or None) if assembly_name else None,
            origin_x_mm=origin_x_mm,
            origin_y_mm=origin_y_mm,
            origin_active=origin_active,
        )
        return ("fridgeCabinetResult", result)

    def _extract_pure_params(self, payload):
        if not isinstance(payload, dict):
            return {}
        params = payload.get("params")
        if isinstance(params, dict):
            return params
        if "validation" in payload and "layout" in payload:
            return payload
        return {}

    def _run_board_plan_bridge(self, pure_params):
        meta = {
            "nodeExecutableFound": False,
            "nodePath": None,
            "nodeExitCode": None,
            "boardPlanParsed": False,
            "boardCount": 0,
            "boardPlanValidationOk": None,
            "stderrPreview": "",
            "stdoutPreview": "",
        }
        script = os.path.join(self.plugin_dir, "scripts", "boardplan_from_pureparams.js")
        if not os.path.isfile(script):
            return None, "Bridge script not found: {}".format(script), meta
        node_exe = shutil.which("node")
        meta["nodeExecutableFound"] = node_exe is not None
        meta["nodePath"] = node_exe
        if not node_exe:
            return None, "Node.js is required for boardPlan generation but was not found in PATH.", meta
        try:
            proc = subprocess.run(
                [node_exe, script],
                cwd=self.plugin_dir,
                input=json.dumps(pure_params, ensure_ascii=False),
                capture_output=True,
                text=True,
                timeout=120,
            )
        except Exception as ex:
            return None, "BoardPlan bridge failed: {}".format(ex), meta
        meta["nodeExitCode"] = proc.returncode
        meta["stderrPreview"] = (proc.stderr or "")[:300]
        raw_stdout = proc.stdout or ""
        meta["stdoutPreview"] = raw_stdout[:300]
        if proc.returncode != 0:
            return None, "Node bridge exited with code {}. stderr: {!r}".format(proc.returncode, proc.stderr), meta
        try:
            data = json.loads(raw_stdout)
            meta["boardPlanParsed"] = isinstance(data, dict)
            if isinstance(data, dict):
                board_plan = data.get("boardPlan")
                if isinstance(board_plan, dict) and isinstance(board_plan.get("boards"), list):
                    meta["boardCount"] = len(board_plan["boards"])
                    meta["boardPlanValidationOk"] = _validation_ok_tri_state(board_plan.get("validation"))
            return data, None, meta
        except Exception as ex:
            return None, "Node bridge JSON parse failed: {!r}".format(ex), meta

    def _handle_generate_fridge_cabinet(
        self,
        pure_params,
        diagnostics,
        diagnostics_only=False,
        received_board_plan=None,
        received_v_verify=None,
        preview_mode="assembly_3d",
        assembly_name=None,
        origin_x_mm=0.0,
        origin_y_mm=0.0,
        origin_active=False,
    ):
        if preview_mode not in ("flat_xy", "assembly_3d"):
            preview_mode = "assembly_3d"
        result = {
            "finalStatus": "fail",
            "failedStep": None,
            "generateRunId": diagnostics.get("runId"),
            "diagnostics": diagnostics,
            "diagnosticsOnly": diagnostics_only,
            "previewMode": preview_mode,
            "pureParamsValidationOk": _validation_ok_tri_state(pure_params.get("validation") if isinstance(pure_params, dict) else None),
            "boardPlanValidationOk": None,
            "vVerifyOk": None,
            "createdBodies": 0,
            "skippedBoards": [],
            "errors": [],
            "warnings": [],
            "assemblyGeometryOk": None,
        }

        if not isinstance(pure_params, dict) or not pure_params:
            result["failedStep"] = "python_extract_pureParams"
            result["errors"].append("Missing PureParams payload.")
            return self._finish(result)

        data = None
        v_verify_source = None
        if isinstance(received_board_plan, dict) and received_board_plan:
            board_count = len(received_board_plan.get("boards") or [])
            diagnostics["pythonSteps"].append(
                {
                    "id": "python_build_boardPlan",
                    "side": "Python",
                    "status": "pass",
                    "summary": "Using boardPlan received from JS; Node bridge skipped",
                    "details": {
                        "source": "js_payload",
                        "boardCount": board_count,
                        "boardPlanValidationOk": _validation_ok_tri_state(received_board_plan.get("validation")),
                    },
                }
            )
            data = {"boardPlan": received_board_plan, "vVerify": received_v_verify}
            v_verify_source = "js_payload" if isinstance(received_v_verify, dict) else None
        else:
            data, err, bridge_meta = self._run_board_plan_bridge(pure_params)
            diagnostics["pythonSteps"].append(
                {
                    "id": "python_build_boardPlan",
                    "side": "Python",
                    "status": "fail" if err else "pass",
                    "summary": err or "BoardPlan built via Node bridge",
                    "details": bridge_meta,
                }
            )
            if err:
                result["failedStep"] = "python_build_boardPlan"
                result["errors"].append(err)
                return self._finish(result)
            v_verify_source = "node_bridge"

        board_plan = data.get("boardPlan") if isinstance(data, dict) else None
        v_verify = data.get("vVerify") if isinstance(data, dict) else None
        if not isinstance(board_plan, dict):
            result["failedStep"] = "python_build_boardPlan"
            result["errors"].append("bridge_missing_boardPlan")
            return self._finish(result)

        result["boardPlanValidationOk"] = _validation_ok_tri_state(board_plan.get("validation"))
        result["vVerifyOk"] = _validation_ok_tri_state(v_verify) if isinstance(v_verify, dict) else None
        val_errors = []
        if not _validation_ok(pure_params.get("validation")):
            val_errors.append("pureParams.validation.ok is not true.")
        if not _validation_ok(board_plan.get("validation")):
            val_errors.append("boardPlan.validation.ok is not true.")
        if not isinstance(v_verify, dict) or v_verify.get("ok") is not True:
            val_errors.append("verifyVSeriesVectors.ok is not true.")
        diagnostics["pythonSteps"].append(
            {
                "id": "python_verify_v_series",
                "side": "Python",
                "status": "pass" if not val_errors else "fail",
                "summary": "vVerify source={!r}; gate errors={}".format(v_verify_source, len(val_errors)),
                "details": {"vVerifyOk": result["vVerifyOk"], "gateErrorsSample": val_errors[:5]},
            }
        )
        if val_errors:
            result["failedStep"] = "python_verify_v_series"
            result["errors"].extend(val_errors)
            return self._finish(result)

        if diagnostics_only:
            result["finalStatus"] = "pass"
            result["warnings"].append("diagnosticsOnly: Fusion bodies not created.")
            return self._finish(result)

        diagnostics["geometryStartedAt"] = _iso_now()
        try:
            fusion_dir = os.path.join(self.plugin_dir, "fusion")
            if fusion_dir not in sys.path:
                sys.path.insert(0, fusion_dir)
            modules_dir = os.path.join(self.plugin_dir, "modules", "fridge")
            if modules_dir not in sys.path:
                sys.path.insert(0, modules_dir)
            import geometry_ops
            import flat_board_geometry

            importlib.reload(geometry_ops)
            importlib.reload(flat_board_geometry)
            geo = flat_board_geometry.generate_flat_board_bodies(
                board_plan, 100.0, preview_mode=preview_mode,
                assembly_name=assembly_name,
                origin_x_mm=origin_x_mm,
                origin_y_mm=origin_y_mm,
                origin_active=origin_active,
            )
            result.update(
                {
                    "geometryBuild": geo.get("geometryBuild"),
                    "previewMode": geo.get("previewMode", preview_mode),
                    "createdBodies": int(geo.get("createdBodies", 0)),
                    "skippedBoards": geo.get("skippedBoards", []),
                    "boardPlanBoardCount": geo.get("boardPlanBoardCount"),
                    "createdBoardIds": list(geo.get("createdBoardIds") or []),
                    "skippedBoardIds": list(geo.get("skippedBoardIds") or []),
                    "bodyAudit": list(geo.get("bodyAudit") or []),
                    "assemblyBodyAudit": list(geo.get("assemblyBodyAudit") or []),
                    "flatPreviewRows": list(geo.get("flatPreviewRows") or []),
                    "assemblyGeometryOk": bool(geo.get("assemblyGeometryOk")) if preview_mode == "assembly_3d" else None,
                    "originOffsetMm": geo.get("originOffsetMm"),
                    "originAvoidance": geo.get("originAvoidance"),
                    "spawnFootprintMm": geo.get("spawnFootprintMm"),
                }
            )
            result["errors"].extend(geo.get("errors", []))
            result["warnings"].extend(geo.get("warnings", []))
        except Exception:
            result["errors"].append(traceback.format_exc())
        diagnostics["geometryFinishedAt"] = _iso_now()

        if result["errors"]:
            result["failedStep"] = "python_create_fusion_bodies"
            result["finalStatus"] = "fail"
        elif preview_mode == "assembly_3d" and result.get("assemblyGeometryOk") is not True:
            result["failedStep"] = "assembly_geometry_audit"
            result["finalStatus"] = "fail"
        else:
            result["failedStep"] = None
            result["finalStatus"] = "pass"
        return self._finish(result)

    def _finish(self, result):
        diagnostics = result.get("diagnostics")
        if isinstance(diagnostics, dict):
            diagnostics["pythonFinishedAt"] = _iso_now()
        return result
