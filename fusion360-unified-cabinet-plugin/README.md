# CabinetNC Unified Fusion Plugin

MVP unified Fusion 360 add-in for cabinet generators.

## MVP Scope

- Working module: Fridge Cabinet, powered by the existing Fridge Cabinet Generator logic.
- Working module: General Tall Cabinet, powered by `modules/generalTallCabinet/`.
- Skeleton module: Overhead Cabinet (`modules/overheadCabinet/`, bridge wired, geometry port pending).
- Reserved module: Automation Tools.
- UI: Figma-inspired top action bar, module sidebar, parameter panel, central workspace, validation panel, and status footer.

## Fusion Entry

- Manifest: `UnifiedCabinetPlugin.manifest`
- Main file: `UnifiedCabinetPlugin.py`
- Fusion palette: `palette.html`

Install or link this folder as a Fusion 360 add-in folder, then run `CabinetNC` from the Scripts and Add-ins dialog.

## Fridge Flow

```text
palette.html
  -> FridgeCabinetLogic.buildPureParams()
  -> FridgeCabinetLogic.buildBoardPlan()
  -> FridgeCabinetLogic.verifyVSeriesVectors()
  -> Python action fridge.generate
  -> modules/fridge/controller.py
  -> modules/fridge/flat_board_geometry.py
```

The MVP intentionally keeps the proven JavaScript `PureParams` and board-plan rules as the source of truth.

## Manual Fusion Validation

1. Load the `CabinetNC` add-in.
2. Confirm the palette opens with the Figma-style layout.
3. Click `Calculate` and confirm validation/status panels update.
4. Click `Validate` and confirm Python returns a `fridgeCabinetResult`.
5. Click `Generate Bodies` in an active design.
6. Confirm generated bodies use `UnifiedCabinetPlugin` attributes and `FRIDGE_` feature prefixes.
7. Re-run generation after changing stack heights and confirm errors are surfaced in the right panel.

## Overhead Flow (skeleton_v0)

```text
palette.html
  -> overhead.generate
  -> modules/overhead/controller.py
  -> scripts/overhead_from_params.js
  -> modules/overheadCabinet/generator.ts
```

See `docs/overhead-cabinet-spec-v0.1.md` and `docs/overhead-cabinet-new-chat-handoff.md`.

## Later Modules

- Phase 2: port legacy `fusion360-cabinet-generator/core/overhead_geometry.py` into `modules/overheadCabinet/`.
- Phase 3: migrate `fusion360-basic-addin` services as Automation Tools.
