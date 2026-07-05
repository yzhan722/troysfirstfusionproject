# M7 Formal Connect UI Checklist

**Milestone:** M7 — Formal Connect UI  
**Status:** ✅ **SEALED** (2026-07-05)

---

## Scope (v1)

- Product-facing Connect card in palette (relationship list, filters, detail, action buttons)
- Offline view-model: `connect_formal_ui.build_connect_view_model`
- Action gates: preview / confirm / cut via `evaluate_connect_action`
- Controller routes: `relationships.connectList`, `relationships.connectExecute`
- UI wires gates to existing hardware preview/cut routes (no bypass)
- `bbox_candidate` cut blocked; manual confirm enables session cut; `generator_declared` cut allowed

---

## Runners

| Script | Environment |
|--------|-------------|
| `tests/test_connect_formal_ui.py` | Terminal — unit tests |
| `tests/run_connect_pipeline_smoke_offline.py` | Terminal — **M6–M9 unified offline** (includes M7 step) |
| **`connect_pipeline_smoke.py`** | Fusion — **M6–M9 unified smoke** |

Install: `powershell -ExecutionPolicy Bypass -File scripts/install_connect_pipeline_smoke.ps1`

Per-milestone `m7_connect_smoke.py` removed — use `connect_pipeline_smoke`.

---

## UI Features

- [x] List relationships (table: pair, geometry, verification, preview/cut flags, confidence)
- [x] Filter by geometry type and verification level; cut-safe-only toggle
- [x] Inspect selected relationship (roles, verification badge, confidence)
- [x] Preview hardware (gate → `hardware.previewScrewHolesFromRelationship`)
- [x] Confirm relationship (session `manual_confirmed`)
- [x] Create cut (gate → `hardware.createScrewHolesFromRelationship`)
- [x] Operation result panel (non-raw-JSON summary)
- [x] Verification tone badges (warn for bbox_candidate, ok for cut-safe levels)

---

## Acceptance Criteria

- [x] User can inspect relationships without reading raw JSON
- [x] Preview allowed for eligible edge_to_surface / surface_to_surface
- [x] Confirm applies session manual_confirmed for structural butt joints
- [x] Cut only when `safeForCut=true` and verification level in cut-safe set
- [x] `bbox_candidate` direct cut blocked in UI and controller gate
- [x] Operation metadata shown after preview/cut

---

## After M7 (next milestones)

1. **M8 Panel Metadata Writeback** — body-level `features[]` sync after cut
2. **M9 Expand Hardware Types** — tongue/groove, hinge, lock, runner
3. **M6 extension** — General Tall generator declarations (parallel, not blocking)

See [`CabinetNC_Connect_Relationship_Hardware_Roadmap.md`](../CabinetNC_Connect_Relationship_Hardware_Roadmap.md).
