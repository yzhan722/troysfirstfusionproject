# M8 Panel Metadata Writeback Checklist

**Milestone:** M8 — Panel Metadata Writeback Integration  
**Status:** ✅ **SEALED** (2026-07-05)

---

## Scope (v1)

- After successful screw-hole cut, append hardware feature to host body `metadata.features[]`
- Dedupe by `featureId` / `sourceRelationshipId + operationType`
- Cut feature metadata unchanged (M3); body writeback is additive
- Metadata scan can find written hardware features

---

## Runners

| Script | Environment |
|--------|-------------|
| `tests/test_panel_metadata_writeback.py` | Terminal — unit tests |
| `tests/run_connect_pipeline_smoke_offline.py` | Terminal — M6–M9 offline (includes M8 step) |
| **`connect_pipeline_smoke.py`** | Fusion — M6–M9 unified smoke |

Install: `powershell -ExecutionPolicy Bypass -File scripts/install_connect_pipeline_smoke.ps1`

---

## Completed

- [x] `panel_metadata_writeback.py` — read/append/write body metadata
- [x] `build_panel_feature_record` — screw-hole → nesting-compatible feature row
- [x] `writeback_screw_hole_feature` wired in `HardwareController.create_screw_holes_from_relationship`
- [x] Duplicate write protection (unless `allow_duplicate=True`)

---

## After M8

See [`CabinetNC_Connect_Relationship_Hardware_Roadmap.md`](../CabinetNC_Connect_Relationship_Hardware_Roadmap.md) — M9 Expand Hardware Types.
