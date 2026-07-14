# GT replaces Fridge — user-effect parity

**Goal:** Hide standalone Fridge Cabinet UI. Users build fridge cabinets only via General Tall.

**Bar:** Same *user-visible* outcome, not Fridge board-ID / `flat_xy` / PureParams clone.

## Acceptance (must)

- [x] Zone `fridge` + appliance W/D/H; cavity has no front panel
- [x] `exteriorSide` → SidePanel + CW = W+45/61
- [x] V5 opposite exterior
- [x] Avoidance gap &lt; 105 → raised + `H*_fridge`; else normal
- [x] Drawer / flap fronts + hinge/lock via GT front hardware
- [x] Connect decls: SidePanel↔V, V5 mate
- [x] Offline user-effect smoke: `tests/run_gt_fridge_user_parity_offline.py`
- [x] Palette: Fridge module hidden; GT “Load fridge layout” one-shot
- [ ] Fusion hand-check once: load fridge layout → Generate → Create rough bodies

## Explicit YAGNI (do not port)

- Fridge `flat_xy` / `outerVector` / `HSet_P*` naming
- Fridge-only PureParams boardPlan JSON shape
- Cabinet-level duplicate `fridgeWidth` fields
- Standalone Fridge `generator_declared`
- Multi-fridge multi-V5

## Rollback

Set `SHOW_FRIDGE_MODULE = true` in `palette.html` (near module nav) to re-show Fridge.
