# Fridge Cabinet Generator Current Module Handoff

This document summarizes the existing Fridge Cabinet Generator module so future design work can extend it with front panel clearance, hinge cup holes, and lock cutouts without first rediscovering the current architecture.

## Scope Today

The fridge module is a vertical stack cabinet generator for a fridge opening, drawers/flaps, top and bottom clearances, optional exterior side panel, wheel avoidance, and generated structural boards.

Current capabilities:

- Palette UI for cabinet/fridge dimensions, stack sections, clearances, exterior side panel, and wheel avoidance.
- JavaScript calculation of validated `PureParams`.
- JavaScript bridge from `PureParams` to `BoardPlan`.
- Python/Fusion generation from `BoardPlan` into either flat preview or 3D assembly preview.
- Board profile vectors for horizontal Zi panels, vertical V panels, H connectors, top/bottom strips, side panel, and wheel avoidance pieces.

Current non-goals:

- No front door/drawer panel clearance system yet.
- No hinge cup holes.
- No push-button lock cutouts.
- No drawer box / runner geometry.
- No dedicated front-panel board entities.

## Key Files

### Unified Plugin Integration

- `fusion360-unified-cabinet-plugin/palette.html`
  - Main unified UI.
  - Loads fridge logic through `FridgeCabinetLogic`.
  - Sends `fridge.generate` payloads to Python.

- `fusion360-unified-cabinet-plugin/modules/fridge/controller.py`
  - Python route handler for `fridge.calculate`, `fridge.validate`, and `fridge.generate`.
  - Accepts `PureParams`, optional precomputed `boardPlan`, optional `vVerify`, and `previewMode`.
  - Runs bridge script if `boardPlan` is not supplied.
  - Calls `modules/fridge/flat_board_geometry.py`.

- `fusion360-unified-cabinet-plugin/modules/fridge/flat_board_geometry.py`
  - Thin wrapper around standalone `Fridge Cabinet Generator/fridge_flat_board_geometry.py`.
  - Overrides `ATTRIBUTE_GROUP` and `FEATURE_PREFIX` for unified plugin.

- `fusion360-unified-cabinet-plugin/scripts/boardplan_from_pureparams.js`
  - Node bridge script.
  - Reads `PureParams` JSON from stdin.
  - Returns `{ boardPlan, vVerify }`.

- `fusion360-unified-cabinet-plugin/tests/run_fridge_bridge_tests.js`
  - Smoke test for logic and bridge alignment.

### Standalone Source Still Used

- `Fridge Cabinet Generator/fridge_logic.js`
  - Main JavaScript calculation engine.
  - Exposes `FridgeCabinetLogic`.
  - Builds `PureParams`, normalized layout, structural board plan, and validations.

- `Fridge Cabinet Generator/fridge_flat_board_geometry.py`
  - Main Fusion body generation implementation currently used by the unified wrapper.
  - Creates flat/assembly bodies from `BoardPlan`.

- `Fridge Cabinet Generator/palette.html`
  - Older standalone palette.

- `Fridge Cabinet Generator/README.md`
  - Old scope note; says original prototype was UI-first.

## Data Pipeline

Current pipeline:

```text
Palette UI
  -> FridgeCabinetLogic.buildPureParams(ui)
  -> PureParams.validation
  -> buildBoardPlan(pureParams)
  -> verifyVSeriesVectors(pureParams, boardPlan)
  -> Python FridgeController.generate()
  -> flat_board_geometry.generate_flat_board_bodies(boardPlan, spacing, previewMode)
  -> Fusion bodies
```

The unified palette may pass `boardPlan` and `vVerify` directly to Python. If it does not, Python reruns:

```text
node scripts/boardplan_from_pureparams.js
```

## Main UI / Input Model

The current fridge UI model contains:

```ts
type FridgeUiState = {
  cabinet: {
    width: number;
    depth: number;
    height: number;
    panelThickness: number;
    exteriorSide: "none" | "left" | "right";
  };
  fridge: {
    width: number;
    depth: number;
    height: number;
  };
  clearances: {
    top: number;
    bottom: number;
  };
  wheelAvoidance: {
    enabled: boolean;
    height: number;
    depth: number;
  };
  stack: Array<{
    id: string;
    type: "flap" | "drawer" | "fridge" | "blankPanel" | string;
    height: number;
  }>;
};
```

Important constants in `fridge_logic.js`:

```ts
DEFAULT_TOP_CLEARANCE_MM = 40;
DEFAULT_BOTTOM_CLEARANCE_MM = 53;
HSET_HEIGHT = 100;
HSET_Z_MERGE_TOL_MM = 3;
HSET_MIN_GAP_FOR_STRUCTURAL_MID_MM = 80;
H_CONNECTOR_FRONT_V_DEPTH_MM = 150;
H_CONNECTOR_REAR_V_DEPTH_MM = 150;
H34_ASSEMBLY_Y_OFFSET_MM = 135;
SIDE_PANEL_THICKNESS_MM = 16;
T1_T2_ASSEMBLY_Y_OFFSET_MM = 39;
```

## Width Model

`deriveWidthModel(ui)` controls cabinet width behavior.

Rules:

- If `exteriorSide === "none"`:
  - no side panel
  - panel system width equals cabinet width
  - panel system origin X = 0

- If exterior side is `left` or `right`:
  - side panel thickness = `16`
  - panel system width = cabinet width - 16
  - if side panel is left, panel system origin X = 16
  - if side panel is right, panel system origin X = 0

Related helper:

```ts
cabinetWidthFromFridge(fridgeWidth, exteriorSide)
```

Current rule:

```text
fridgeWidth + 45 if no exterior side
fridgeWidth + 61 if exterior side exists
```

## Vertical Stack / Layout Model

`buildNormalizedLayout(ui)` builds:

- `bottomClearanceRegion`
- function `sections`
- horizontal separator `panels`
- `topClearanceRegion`
- `displaySegments`
- `totalStackHeight`

Stack order is bottom to top in generated Z:

```text
bottom clearance
P0 horizontal boundary panel
section 0
P1 horizontal panel
section 1
...
top horizontal boundary panel
top clearance
```

Panel thickness:

- first/bottom boundary panel uses `boundaryPanelThickness(panelThickness)`
- top boundary panel also uses boundary thickness
- middle horizontal panels use cabinet panel thickness

`boundaryPanelThickness(panelThickness)` currently returns:

```ts
panelThickness + 1
```

Panel classification is done by `classifyPanel(panel)`:

- `bottom_boundary`
- `top_boundary`
- `fridge_base`
- `fridge_top`
- `flap_bottom`
- `flap_top`
- `generic_separator`

Classification determines:

- `shape`: `full`, `half`, `bottom_system`, `top_system`
- whether HSet connectors are required

## Zi / Horizontal Panel Profiles

Zi panels are generated from classified horizontal panels.

Full Zi profile:

```text
front/rear notch-style profile using 15mm returns and 105mm depth regions.
```

`getZiFullProfile(CW, CD)` returns a 2D vector in panel-local XY.

Half Zi profile:

```text
depth 150mm style profile
front tongue/return region 45mm -> 150mm
```

`getZiHalfProfile(CW)` returns a 2D vector.

These profiles already encode some functional board tongue/slot style geometry. Any future front panel layer should not confuse Zi profiles with door/drawer front panels. Zi are structural horizontal boards, not visible front panels.

## BoardPlan

`buildBoardPlan(pureParams)` produces a `boardPlan` with:

```ts
type BoardPlan = {
  boards: BoardPlanBoard[];
  validation: {
    ok: boolean;
    errors: string[];
    warnings: string[];
    infos: string[];
  };
  // plus debug/metadata fields
};
```

Each board generally includes:

```ts
type BoardPlanBoard = {
  id: string;
  name?: string;
  series?: "B" | "V" | "Zi" | "H" | "T" | "S" | string;
  profilePlane: "XY" | "XZ" | "YZ";
  thickness: number;
  outerVector: Array<[number, number]>;
  placement?: {
    assembly?: {
      originMm?: { x: number; y: number; z: number };
      // other placement metadata
    };
  };
  holes?: unknown[];
  grooves?: unknown[];
  // other board-specific metadata
};
```

The exact shape of each board varies by series.

## Board Series

Current structural series seen in the Fusion geometry layer:

- `B`: bottom boards, e.g. `B1`, `B2`, `B3`
- `T`: top strips / support boards, e.g. `T1`, `T2`, `T3`, `T4`, `T5`
- `V`: vertical panels / stiles, e.g. `V1` to `V5`
- `Zi`: horizontal separator panels
- `H`: HSet connector boards, e.g. `HSet_*_H13`, `HSet_*_H24`, `HSet_*_H34`
- `S`: side panel
- avoidance tail boards: `AvoidanceFront`, `AvoidanceTop`

`fridge_flat_board_geometry.py` has a stable 3D assembly creation order:

```text
SidePanel
B1 B2 B3
T1 T2 T3 T4 T5
V1 V2 V3 V4 V5
Zi...
HSet_*_H13/H24/H34...
AvoidanceFront AvoidanceTop
```

## Fusion Generation Modes

`FridgeController.generate()` passes `previewMode` to geometry.

Allowed modes:

```text
flat_xy
assembly_3d
```

### flat_xy

Boards are laid out as readable flat preview rows.

Row order:

```text
S, B, V, Zi, H, T, Other
```

### assembly_3d

Bodies are oriented and placed into a 3D assembly approximation.

Important implementation details:

- Fusion internal units are cm.
- Board profile vectors are in mm.
- Canonical flat body uses:
  - local X = profile U
  - local Y = profile V
  - local Z = thickness
- Profile plane remap:
  - `XY`: sizeX = spanU, sizeY = spanV, sizeZ = thickness
  - `XZ`: sizeX = spanU, sizeY = thickness, sizeZ = spanV
  - `YZ`: sizeX = thickness, sizeY = spanU, sizeZ = spanV

`fridge_flat_board_geometry.py` includes manual transforms for some assembly parts, especially V boards and connector boards. The geometry layer has grown around practical Fusion orientation fixes, so future front panel work should be careful not to reuse these transforms blindly.

## Validation / Diagnostics

Validation gates in Python:

1. `PureParams.validation.ok`
2. `boardPlan.validation.ok`
3. `verifyVSeriesVectors.ok`

If any fail, generation stops before Fusion body creation.

Python result contains:

```ts
{
  finalStatus: "pass" | "fail";
  failedStep?: string;
  diagnosticsOnly: boolean;
  pureParamsValidationOk: boolean | null;
  boardPlanValidationOk: boolean | null;
  vVerifyOk: boolean | null;
  createdBodies: number;
  skippedBoards: unknown[];
  errors: string[];
  warnings: string[];
  assemblyGeometryOk: boolean | null;
}
```

`diagnosticsOnly` allows validation without Fusion body creation.

## Current Front / Door Concepts

The fridge module currently has stack section types:

- `flap`
- `drawer`
- `fridge`
- `blankPanel` / empty

But these are currently logical stack sections, not separately generated visible front panels.

Important distinction for future design:

- Existing `flap` and `drawer` sections define vertical stack cavities/regions.
- Existing Zi and HSet geometry are structural internals.
- Future visible front panels should likely be a new layer, not a mutation of Zi boards.

## Recommended Extension Points for Front Panels

Future front panel work should likely add:

```ts
type FridgeFrontSettings = {
  frontPanelThickness: number;
  frontClearance: number;
};
```

and a new generated array:

```ts
type FridgeFrontPanel = {
  id: string;
  sectionId: string;
  type: "drawer" | "flap" | "door" | string;
  x0: number;
  x1: number;
  y0: number; // likely -FPT
  y1: number; // likely 0
  z0: number;
  z1: number;
  width: number;
  height: number;
  thickness: number;
  hingeHoles?: HingeCupHole[];
  lockCutout?: PushButtonLockCutout;
};
```

This should be parallel to `boardPlan.boards`, not mixed into structural board generation at first.

Suggested phases:

1. Add UI state fields for front thickness and front clearance.
2. Generate front panel rectangles from stack sections.
3. Add SVG preview overlay for front panels.
4. Add hinge settings for `flap` if needed.
5. Add lock preset settings and cutout metadata.
6. Add front panel Fusion body generation.
7. Add hinge and lock cut features.

## Front Panel Sizing Questions To Resolve

Before implementation, decide:

1. Which fridge stack section types get visible front panels?
   - Likely `drawer` and `flap`.
   - `fridge` probably does not get a front panel.
   - `blankPanel` might or might not.

2. What are front panel X edges?
   - If no exterior side panel, should front panels span cabinet full width minus clearance?
   - If exterior side panel exists, should front panels cover panel-system width or full cabinet width?

3. What is the Y reference?
   - Kitchen uses visible fronts at `Y = -FPT -> 0`.
   - Fridge should probably use the same convention for consistency.

4. What are Z gaps?
   - Use uniform `frontClearance` between stacked front panels?
   - Bottom/top clearances need special rules.

5. Lock mounting surface:
   - For drawer/flap fronts, what structural board is the upper receiver mounted to?
   - Existing Zi panels have center/top Z values that may be reused.

6. Hinge side:
   - Flap hinge likely bottom or top depending on opening direction.
   - Drawer fronts likely no hinge.

## Suggested GPT Prompt For Next Design Step

Use this prompt for a design model:

```text
Read docs/fridge-cabinet-current-module-handoff.md.
Design a front panel / hinge / push-button-lock extension for the existing Fridge Cabinet Generator.
Do not redesign the existing structural boardPlan pipeline.
Add a parallel frontPanel layer using the current coordinate system and PureParams/BoardPlan conventions.
Specify UI state additions, generated geometry types, sizing formulas, hinge placement rules, lock placement rules, SVG preview changes, and Fusion generation phases.
Keep implementation incremental and compatible with current fridge.generate pipeline.
```

