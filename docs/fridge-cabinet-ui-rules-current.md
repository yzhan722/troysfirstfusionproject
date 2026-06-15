# Fridge Cabinet Module Current UI Rules

This document captures the current Fridge module UI behavior in the unified plugin so another GPT/design pass can extend it with front panels, clearance, hinges, and locks without rediscovering the existing interaction model.

## Scope

The Fridge module is currently a vertical stack editor for a fridge cabinet. It supports cabinet/fridge dimensions, top and bottom clearances, optional exterior side panel, wheel avoidance, function zones, validation output, and Fusion body generation.

Current UI does not yet include:

- Front door/drawer panel clearance options.
- Hinge cup settings.
- Lock cutout settings.
- Dedicated front panel geometry preview.

## Main File

The active unified UI is implemented in:

- `fusion360-unified-cabinet-plugin/palette.html`

It loads the fridge logic from:

- `Fridge Cabinet Generator/fridge_logic.js`

The UI builds state, then calls `FridgeCabinetLogic.buildPureParams(ui)`, `buildBoardPlan(pureParams)`, and `verifyVSeriesVectors(pureParams, boardPlan)`.

## Layout Structure

The unified page has four columns:

- Module navigation.
- Module parameter panel.
- Main workspace.
- Validation/options panel.

For the Fridge module:

- Left parameter panel remains visible.
- Main workspace contains the cabinet preview and function zone editor.
- Right panel contains selected function zone options, validation, structural mode, and generation result.

## Left Parameter Panel

### Cabinet Parameters

Fields:

- `cabinetWidth`
- `cabinetDepth`
- `cabinetHeight`
- `panelThickness`
- `exteriorSide`

`exteriorSide` options:

- `right`
- `left`
- `none`

Width synchronization rule:

- If `exteriorSide !== "none"`, `cabinetWidth = fridgeWidth + 61`.
- If `exteriorSide === "none"`, `cabinetWidth = fridgeWidth + 45`.
- Editing `fridgeWidth`, `cabinetWidth`, or `exteriorSide` triggers the sync functions.

### Fridge Parameters

Fields:

- `fridgeWidth`
- `fridgeDepth`
- `fridgeHeight`

Height synchronization rule:

- Changing `fridgeHeight` updates the first stack section whose `type === "fridge"`.
- Changing the selected fridge zone height also updates the `fridgeHeight` input.

### Clearance and Avoidance

Fields:

- `topClearance`
- `bottomClearance`
- `avoidanceEnabled`
- `avoidanceHeight`
- `avoidanceDepth`

These values are passed into `currentUiState()` and then into `buildPureParams()`.

## Core UI State

The Fridge module keeps its editable function zones in a global `stack` array.

Current default:

```js
let stack = [
  { id: "flap", type: "flap", height: 195 },
  { id: "drawer", type: "drawer", height: 250 },
  { id: "fridge", type: "fridge", height: 1470 },
];
```

The selected function zone is tracked separately:

```js
const fridgeState = {
  selectedZoneId: stack[0]?.id || null,
};
```

Important ordering rule:

- `stack` is stored bottom-to-top.
- `displayStackTopDown()` reverses it for display/editing.
- Drag/drop operates on the top-down display order, then writes back to `stack` by reversing again.

## Function Zone Types

Current zone editor type options:

- `fridge`
- `drawer`
- `flap`
- `blankPanel`
- `fixedPanel`

Visual CSS class rule:

- `zoneClass(type)` returns `type`, except `empty` maps to `blankPanel`.

## Main Workspace

### Action Buttons

Top workspace buttons:

- `Calculate`
- `Validate`
- `Generate Bodies`

Routing:

- `calculate()` builds local fridge data and sends `fridge.calculate`.
- `validate()` builds local fridge data and sends `fridge.validate`.
- `generate()` builds local fridge data and sends `fridge.generate`.

The generate payload includes:

- `type: "fridge.generate"`
- `runId`
- `params: pureParams`
- `boardPlan`
- `vVerify`
- `diagnosticsOnly: false`
- `previewMode: "assembly_3d"`

## Cabinet Preview

The main preview host is:

- `cabinetPreview`

Preview source:

- `pureParams.layout.sections`

Rendering rule:

- Each function zone is rendered as an absolutely positioned vertical block.
- `top = 100 - (section.z1 / cabinetHeight * 100)`.
- `height = max(4, section.height / cabinetHeight * 100)`.
- The block label displays zone type and height.

Selection rule:

- Clicking a preview zone sets `fridgeState.selectedZoneId`.
- The selected preview zone gets a blue outline.
- After selection, `calculate()` is called, which re-renders all fridge UI.

## Function Zone Editor

The function zone editor host is:

- `zoneInputs`

Rows are rendered top-down using `displayStackTopDown()`.

Each row contains:

- Drag handle.
- Type select.
- Height input.
- Delete button.

Selection rule:

- Clicking a row outside inputs/buttons sets `fridgeState.selectedZoneId`.
- The selected row gets a blue outline and light blue background.

Type change rule:

- Changing a row type updates `stack[index].type`.
- If the new type is `fridge`, the zone height is set from the `fridgeHeight` input.
- Then `calculate()` runs.

Height change rule:

- Changing row height updates `stack[index].height`.
- If that zone is type `fridge`, `fridgeHeight` input is synchronized to the zone height.
- Then `calculate()` runs.

Delete rule:

- Deleting the selected zone moves selection to the next stack item if available, otherwise previous, otherwise `null`.
- Then the zone is removed and `calculate()` runs.

Add rule:

- The `Add` button inserts a new drawer zone at the front of the array with:

```js
{ id: `zone_${Date.now()}`, type: "drawer", height: 250 }
```

- The new zone becomes selected.
- Then `calculate()` runs.

Drag/drop rule:

- Drag handles support pointer drag, mouse drag, and native drag/drop.
- Rows are dragged in top-down display order.
- `swapDisplayStack()` swaps displayed rows, then converts the display array back to bottom-to-top `stack`.
- Drag reorder calls `calculate()`.

## Right Panel: Function Zone Options

The right panel host is:

- `fridgeZoneOptionsPanel`

Source:

- `pureParams.layout.sections`
- selected by `fridgeState.selectedZoneId`
- falls back to the first section if selection is missing

Displayed fields:

- Selected type/id badge.
- Type, read-only.
- Height, editable.
- Z0, read-only.
- Z1, read-only.

Current placeholder:

- Reserved for future front panel, hinge, and lock options.

Height edit rule:

- Editing right-panel height finds the matching item in `stack` by `selected.id`.
- The stack zone height is updated.
- If the zone type is `fridge`, `fridgeHeight` input is synchronized.
- Then `calculate()` runs.

Important future extension point:

- This right panel is the intended place for per-zone front panel, hinge, and lock settings.
- Add future per-zone settings to `stack` entries or an adjacent keyed state object, then include them in `currentUiState()`.

## Layout Table

The lower table host is:

- `layoutRows`

Source:

- `pureParams.layout.displaySegments`

Rendering rule:

- Display segments are reversed for top-down visual order.
- Function zones show their type and height.
- Panel segments show a panel label from `segmentLabel()`.
- End clearances show `end clearance`.
- Columns include swatch, display index, type, height, panel, z0, z1.

## Validation and Result Panel

### Validation and Warnings

Host:

- `validationMessages`

Rules:

- Shows `pureParams.validation.errors`.
- Shows `pureParams.validation.warnings`.
- Shows `pureParams.validation.infos`.
- If `pureParams.validation.ok`, `boardPlan.validation.ok`, and `vVerify.ok`, an OK message is prepended with generated board count.

### Generated Structural Mode

Host:

- `structuralMode`

Displayed fields:

- `fridgeHSetMode`
- `avoidanceRaised`
- `sidePanelSide`
- `V5 Side`

### Generation Result

Host:

- `resultBox`

For `calculate()`, it shows summary JSON:

- `pureParamsOk`
- `boardCount`
- `vVerifyOk`

For Python responses, the handler writes parsed JSON or raw response text here.

## Re-render Contract

`buildAll()` is the main local refresh path:

```text
currentUiState()
  -> FridgeCabinetLogic.buildPureParams(ui)
  -> FridgeCabinetLogic.buildBoardPlan(pureParams)
  -> optional buildAssemblyPlacementPlan(pureParams, boardPlan)
  -> verifyVSeriesVectors(pureParams, boardPlan)
  -> render(pureParams, boardPlan, vVerify)
```

`render()` always updates:

- Zone editor rows.
- Cabinet preview.
- Layout table.
- Right-panel function zone options.
- Validation messages.
- Structural mode.
- Stack height difference in the bottom status bar.
- Status text.

## Current Validity Rule

Unlike the newer General Tall UI, Fridge function zone heights are not automatically normalized by the palette UI.

Instead:

- User-entered stack heights are sent to `buildPureParams()`.
- `pureParams.validation` decides if stack/cabinet height is valid.
- The bottom status bar displays `Stack difference: {totalStackHeight - cabinetHeight} mm`.

If a future design wants Kitchen/Tall-style always-valid zone sums, that should be a deliberate behavior change, not assumed from the current Fridge UI.

## Recommended Extension Direction

For future front panels, hinges, and locks:

- Keep the current `stack` as the editable per-zone source of truth.
- Add optional per-zone fields such as `frontPanel`, `frontClearance`, `hingeSettings`, and `lockSettings`.
- Render those fields in `fridgeZoneOptionsPanel` only for relevant zone types.
- Preserve read-only `Z0/Z1` display from `pureParams.layout.sections`.
- Extend `currentUiState()` so new per-zone settings reach the fridge logic layer.
- Add front panel preview overlays to `cabinetPreview` or a new generated front elevation preview once geometry exists.
