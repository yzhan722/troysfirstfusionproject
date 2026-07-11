# Real-cabinet hardware offline smoke

**Status:** offline sealed (2026-07-11).

## Scope

Run all five Connect hardware types (preview + cut plan) against a **real generator** declared joint: Overhead BP↔D0 from `overhead_edge_only.json`.

Does **not** add hardware types. Does **not** require Fusion Play.

## Runner

```powershell
cd fusion360-unified-cabinet-plugin
python tests/run_real_cabinet_hardware_offline.py
```

Wired into `tests/run_plugin_offline_regression.py`.

## Acceptance

- [x] Registry: 5 types `cutReady`
- [x] Overhead reconcile → BP↔D0 `generator_declared`
- [x] screw / tongue_groove / hinge / runner / lock: preview + cut plan OK
