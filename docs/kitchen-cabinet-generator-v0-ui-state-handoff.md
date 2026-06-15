# Kitchen Cabinet Generator V0 UI / State Handoff

This document captures the current Kitchen Cabinet Generator UI state model and behavior.
It is intended as input for deriving later geometry / board generation rules.

Current scope:

- UI + state model
- X-Z front elevation schematic preview
- Column / zone editing
- Wheel avoidance overlay
- Preset save/load JSON
- V0 geometry debug generation bridge

Out of scope for current UI stage:

- Real Fusion 360 3D board generation
- DXF / CNC / toolpath / nesting
- Top view
- Full Y-Z section editor
- Real front gap / hinge / runner / appliance geometry

## Coordinate System

- `X` = kitchen length direction
- `Y` = cabinet depth direction
- `Z` = cabinet height direction

The current schematic preview only shows front elevation:

- Horizontal axis = `X`
- Vertical axis = `Z`
- No top view is shown

## Global Settings

```ts
type KitchenGlobalSettings = {
  length: number;              // total kitchen length, X direction
  depth: number;               // cabinet depth, Y direction
  height: number;              // cabinet height, Z direction
  materialThickness: number;   // default 15
  frontThickness: number;      // default 16
  bottomClearanceHeight: number;
  bottomClearanceStyle: "style_1" | "style_2";
};
```

Default:

```ts
const defaultKitchenSettings: KitchenGlobalSettings = {
  length: 2131,
  depth: 600,
  height: 890,
  materialThickness: 15,
  frontThickness: 16,
  bottomClearanceHeight: 70,
  bottomClearanceStyle: "style_1",
};
```

`bottomClearanceStyle` is intentionally extensible. Current UI has:

- `style_1`
- `style_2`

More styles can be added later without changing the main state shape.

## Function Types

V0 uses one shared function type list for column and zone functions:

```ts
type KitchenFunctionType =
  | "left_door"
  | "right_door"
  | "drawer"
  | "open"
  | "down_flap"
  | "stove"
  | "custom";

type KitchenColumnType = KitchenFunctionType;

type KitchenZoneType =
  | KitchenFunctionType
  | "unassigned";
```

Labels:

```ts
const kitchenTypeLabels: Record<KitchenZoneType, string> = {
  left_door: "Left Door",
  right_door: "Right Door",
  drawer: "Drawer",
  open: "Open",
  down_flap: "Down Flap",
  stove: "Stove",
  custom: "Custom",
  unassigned: "Unassigned",
};
```

Notes:

- `open` means an explicitly requested open bay.
- `unassigned` means the zone is not yet assigned and should not become final geometry.
- `custom` is a catch-all placeholder for mixed or unknown function combinations.

## Main State Shape

```ts
type KitchenZone = {
  id: string;
  height: number;
  zoneType: KitchenZoneType;
  shelfHeight?: number; // door zones only; shelf top height measured upward from zone z0
};

type KitchenColumn = {
  id: string;
  width: number;
  columnType: KitchenColumnType;
  zones: KitchenZone[];
};

type WheelAvoidance = {
  id: string;
  x0: number;
  x1: number;
  height: number; // Z direction
  depth: number;  // Y direction, from rear forward
};

type KitchenLayoutState = {
  globalSettings: KitchenGlobalSettings;
  columns: KitchenColumn[];
  wheelAvoidances: WheelAvoidance[];
};
```

Important invariant:

- Do not store `x0`, `x1`, `z0`, or `z1` as primary data.
- Ranges are computed from `width`, `height`, and global settings.

## Default Layout

Editable height:

```ts
editableHeight = height - bottomClearanceHeight
editableHeight = 890 - 70 = 820
```

Default state:

```ts
const defaultKitchenLayout: KitchenLayoutState = {
  globalSettings: {
    length: 2131,
    depth: 600,
    height: 890,
    materialThickness: 15,
    frontThickness: 16,
    bottomClearanceHeight: 70,
    bottomClearanceStyle: "style_1",
  },
  columns: [
    {
      id: "k-col-1",
      width: 700,
      columnType: "stove",
      zones: [
        { id: "k-zone-1a", height: 450, zoneType: "stove" },
        { id: "k-zone-1b", height: 220, zoneType: "drawer" },
        { id: "k-zone-1c", height: 150, zoneType: "down_flap" },
      ],
    },
    {
      id: "k-col-2",
      width: 340,
      columnType: "left_door",
      zones: [
        { id: "k-zone-2a", height: 820, zoneType: "left_door", shelfHeight: 410 },
      ],
    },
    {
      id: "k-col-3",
      width: 660,
      columnType: "right_door",
      zones: [
        { id: "k-zone-3a", height: 820, zoneType: "right_door", shelfHeight: 410 },
      ],
    },
    {
      id: "k-col-4",
      width: 431,
      columnType: "drawer",
      zones: [
        { id: "k-zone-4a", height: 195, zoneType: "drawer" },
        { id: "k-zone-4b", height: 210, zoneType: "drawer" },
        { id: "k-zone-4c", height: 210, zoneType: "drawer" },
        { id: "k-zone-4d", height: 105, zoneType: "drawer" },
        { id: "k-zone-4e", height: 100, zoneType: "down_flap" },
      ],
    },
  ],
  wheelAvoidances: [],
};
```

## X Range Calculation

Columns define X ranges. `columns[0]` starts at `X = 0`.

```ts
function getColumnXRange(columns: KitchenColumn[], index: number) {
  const x0 = columns
    .slice(0, index)
    .reduce((sum, column) => sum + column.width, 0);

  return {
    x0,
    x1: x0 + columns[index].width,
  };
}
```

Example default X ranges:

```text
Column 1: x0 = 0,    x1 = 700
Column 2: x0 = 700,  x1 = 1040
Column 3: x0 = 1040, x1 = 1700
Column 4: x0 = 1700, x1 = 2131
```

## Z Range Calculation

Zone array order is top-to-bottom.

This is important:

- `zones[0]` is the top zone.
- Later zones go downward.
- `stove` should usually appear near the top.
- `down_flap` should usually appear near the bottom.

Bottom clearance is global and is not part of any column zones.

```ts
function getZoneZRange(
  kitchen: KitchenGlobalSettings,
  column: KitchenColumn,
  zoneIndex: number
) {
  const topZ = kitchen.height;

  const z1 =
    topZ -
    column.zones
      .slice(0, zoneIndex)
      .reduce((sum, zone) => sum + zone.height, 0);

  const z0 = z1 - column.zones[zoneIndex].height;

  return { z0, z1 };
}
```

For default stove column:

```text
Kitchen height = 890
Bottom clearance = 70
Editable height = 820

Stove zone:
  height = 450
  z0 = 440
  z1 = 890

Drawer zone:
  height = 220
  z0 = 220
  z1 = 440

Down flap zone:
  height = 150
  z0 = 70
  z1 = 220
```

Each column's zones should sum to:

```ts
editableHeight = kitchen.height - kitchen.bottomClearanceHeight
```

## Bottom Clearance

Bottom clearance is one continuous global band:

```text
X = 0 -> kitchen.length
Z = 0 -> bottomClearanceHeight
```

It is not owned by any column.

UI behavior:

- It is displayed as a full-width bottom band.
- It can be clicked.
- Right properties panel can edit:
  - `bottomClearanceHeight`
  - `bottomClearanceStyle`
- Height/style changes update preview immediately.
- Current styles are `style_1` and `style_2`.

Geometry question for future stage:

- Define board/void/plinth/toe-kick behavior for each bottom clearance style.
- Decide which boards are global continuous boards vs per-column boards.

## Column Behavior

### Add Column

Default added column:

```ts
{
  width: 400,
  columnType: "drawer",
  zones: createDefaultZonesForColumnType("drawer", editableHeight),
}
```

Current UI increases `globalSettings.length` by the new column width.

### Delete Column

Deleting a column preserves total kitchen length by merging deleted width:

```text
delete column i:
  if right neighbor exists:
    rightNeighbor.width += deletedColumn.width
  else:
    leftNeighbor.width += deletedColumn.width
```

At least one column remains.

### Duplicate Column

Duplicates:

- width
- columnType
- zones
- zone heights
- zone types

The duplicate receives new IDs.

Current UI increases `globalSettings.length` by the duplicate width.

### Move Column

Column move left/right moves the entire column object:

- width
- columnType
- zones
- zone heights
- zone types

### Resize Column

Column width can be edited by:

- dragging vertical boundary in the column strip
- typing width in properties

Dragging a boundary changes only the two adjacent columns and preserves their combined width.

## Default Zone Templates By Column Type

When the user changes a column type from the properties panel, the column's zones are rebuilt from a default template.

### Stove Column

Top-to-bottom:

```text
[Stove]
[Drawer]
[Down Flap]
```

Default proportional heights are based on:

```ts
[450, 220, 150]
```

These are scaled to the current editable height.

### Drawer Column

Top-to-bottom:

```text
[Drawer]
[Drawer]
[Drawer]
[Drawer]
[Down Flap]
```

Default proportional heights are based on:

```ts
[195, 210, 210, 105, 100]
```

These are scaled to the current editable height.

### Single-Zone Columns

These create one full-height editable zone:

- `left_door`
- `right_door`
- `open`
- `down_flap`
- `custom`

Example:

```ts
[
  { height: editableHeight, zoneType: columnType }
]
```

For `left_door` and `right_door`, the default zone also receives:

```ts
shelfHeight = Math.round(editableHeight / 2)
```

## Door Shelf Parameter

Door zones can contain an internal shelf.

This is currently represented as:

```ts
type KitchenZone = {
  id: string;
  height: number;
  zoneType: KitchenZoneType;
  shelfHeight?: number;
};
```

Rules:

- `shelfHeight` is only shown for `left_door` and `right_door` zones.
- UI label: `Shelf Top Height`.
- The user input is the shelf top height measured upward from the zone bottom (`z0`).
- Shelf top Z is:

```ts
shelfTopZ = zone.z0 + shelfHeight
```

- Valid range:

```text
0 <= shelfHeight <= zone.height
```

- If a zone changes from door to a non-door type, `shelfHeight` is removed.
- If a zone changes into a door type, a missing `shelfHeight` defaults to half the zone height.
- If a door zone height changes, `shelfHeight` is clamped to the new zone height.
- The current SVG preview draws the shelf top as a dashed horizontal line.
- Geometry layer should convert this user-facing top height into the board center position:

```ts
shelfCenterZ = shelfTopZ - CPT / 2
shelfBoardZ0 = shelfTopZ - CPT
shelfBoardZ1 = shelfTopZ
```

Geometry question for future stage:

- Decide whether `shelfHeight` creates one physical horizontal shelf board.
- Shelf board thickness should use `CPT` unless a later override is added.
- Decide shelf board depth, front setback, side clearances, and whether it sits between vertical panels or uses dados/pins.
- Decide whether multiple shelf heights are needed later. V0 has one shelf only.

## Zone Behavior

### Zone Type Edit

Changing a zone type updates the zone immediately.

Then the parent column type is re-inferred from all zones.

Inference rule:

```ts
function inferKitchenColumnTypeFromZones(column: KitchenColumn): KitchenColumnType {
  const zoneTypes = column.zones
    .map((zone) => zone.zoneType)
    .filter((type) => type !== "unassigned");

  if (zoneTypes.length === 0) return "custom";
  if (zoneTypes.includes("stove")) return "stove";
  if (zoneTypes.every((type) => type === "drawer" || type === "down_flap")) return "drawer";
  if (zoneTypes.every((type) => type === zoneTypes[0])) return zoneTypes[0];
  return "custom";
}
```

Examples:

```text
[stove, drawer, down_flap]      -> stove
[drawer, drawer, down_flap]     -> drawer
[left_door]                     -> left_door
[right_door]                    -> right_door
[open]                          -> open
[drawer, open]                  -> custom
[unassigned, unassigned]        -> custom
```

### Split Zone

Splitting a selected zone:

```text
Before:
[Original Zone H]

After:
[Original Zone Type H/2]
[Unassigned H/2]
```

The new unassigned zone is inserted below the original zone.

### Delete Zone

Default delete behavior does not remove the zone and does not merge heights.

It becomes:

```ts
zoneType: "unassigned"
```

Height remains unchanged.

Then the parent column type is re-inferred.

Drawer special case:

- If the selected zone is `drawer`
- and the immediately upper adjacent zone is also `drawer`
- then delete removes the selected drawer zone
- its height is merged into the upper drawer zone
- selection moves to the merged upper drawer

Example:

```text
Before, top-to-bottom:
[Drawer 195]
[Drawer 210]  <- delete this
[Drawer 210]
[Down Flap 205]

After:
[Drawer 405]
[Drawer 210]
[Down Flap 205]
```

If there is no upper drawer, the default `unassigned` behavior is used.

### Resize Zone

Zone height can be edited by:

- dragging horizontal boundary in the X-Z front elevation
- typing height in properties

Dragging a boundary changes only two adjacent zones and preserves their combined height.

Because zone order is top-to-bottom:

- dragging boundary downward increases the upper zone height
- dragging boundary upward decreases the upper zone height

Total column editable height should remain:

```ts
kitchen.height - kitchen.bottomClearanceHeight
```

## Selection Model

```ts
type KitchenSelection =
  | { type: "kitchen" }
  | { type: "column"; columnId: string }
  | { type: "zone"; columnId: string; zoneId: string }
  | { type: "bottom_clearance" }
  | { type: "wheel_avoidance"; avoidanceId: string };
```

Selection behavior:

- Click blank canvas -> `kitchen`
- Click column strip column -> `column`
- Click front elevation zone -> `zone`
- Click bottom band -> `bottom_clearance`
- Click wheel overlay or wheel settings row -> `wheel_avoidance`

## Properties Panel Behavior

### Kitchen Selected

Shows:

- Add Column
- Add Wheel Avoidance
- General note to edit global dimensions in main panel

### Column Selected

Shows:

- Column Type
- Width
- Computed X0
- Computed X1
- Move Left
- Move Right

Changing Column Type rebuilds zones from that type's default template.

### Zone Selected

Shows:

- Parent Column Type
- Zone Type
- Zone Height
- Shelf Height, for `left_door` / `right_door` zones only
- Computed X0
- Computed X1
- Computed Z0
- Computed Z1
- Split Zone
- Delete Zone

Changing Zone Type updates the parent Column Type using inference rules.

### Bottom Clearance Selected

Shows:

- Bottom Clearance Height
- Bottom Clearance Style

### Wheel Avoidance Selected

Shows:

- X0
- X1
- Height
- Depth
- Delete Wheel Avoidance

The wheel settings list also has per-row:

- Edit
- Delete

## Wheel Avoidance

Current state:

```ts
type WheelAvoidance = {
  id: string;
  x0: number;
  x1: number;
  height: number;
  depth: number;
};
```

In current X-Z preview:

```text
X = x0 -> x1
Z = 0 -> height
```

This is only a front elevation overlay. It does not show real `Y` depth.

Default added wheel avoidance:

```ts
{
  x0: 25,
  x1: min(125, kitchen.length),
  height: 250,
  depth: kitchen.depth,
}
```

Geometry question for future stage:

- Decide how `depth` cuts into boards in Y direction.
- Decide whether avoidance affects side panels, vertical dividers, back panels, bottom boards, shelves, and door fronts.
- Decide whether avoidance should split boards, notch profiles, or create clearance voids only.

## Warnings

Current UI warnings are non-blocking:

- Column width too small
- Zone height too small
- Unassigned zone exists
- Total column widths != kitchen length
- Zone heights sum != editable height
- Wheel avoidance overlaps column area

No operation is currently blocked by warnings.

## Preset JSON

Current preset shape:

```ts
type KitchenLayoutPreset = {
  version: 1;
  name: string;
  globalSettings: KitchenGlobalSettings;
  columns: KitchenColumn[];
  wheelAvoidances: WheelAvoidance[];
};
```

The UI currently stores this JSON in localStorage:

```text
cabinetnc.kitchenPreset.v1
```

The UI also exposes the JSON in a textarea for manual copy/paste.

## Geometry Rule Questions To Resolve Next

Key open questions for geometry generation:

1. What are the physical board types for a kitchen cabinet row?
2. Are vertical boundaries generated as full-height V panels from `Z = 0`, or only from `bottomClearanceHeight`?
3. How do bottom clearance styles change side panel / toe-kick / plinth geometry?
4. How are front faces generated for each zone type?
5. Does each column generate independent internal boards, or are long horizontal boards continuous across columns?
6. How should `down_flap` differ from `drawer` in board geometry and front panel geometry?
7. How should `stove` reserve appliance space, ventilation gaps, and surrounding panels?
8. How does wheel avoidance alter side panels, dividers, base boards, back boards, and fronts?
9. Which dimensions need front gaps, reveals, clearances, overlays, or hardware offsets?
10. Which generated objects should become Fusion bodies/components later?

## Suggested Geometry Input Contract

The future geometry generator should accept a state object equivalent to:

```ts
type KitchenGeometryInput = KitchenLayoutState;
```

It should compute:

```ts
type ComputedKitchenColumn = KitchenColumn & {
  x0: number;
  x1: number;
};

type ComputedKitchenZone = KitchenZone & {
  columnId: string;
  x0: number;
  x1: number;
  z0: number;
  z1: number;
};
```

Then derive board objects / features from those computed ranges.

## Geometry Decisions Confirmed After UI Handoff

These decisions should override earlier open questions when implementing the geometry layer:

1. Door shelf UI input is shelf top height, not board center height. Geometry must convert top height to shelf board center/Z extents using `CPT`.
2. Double-sided half-slot conflicts can be resolved through a UI dialog/popup. The geometry result should emit enough data to ask the user for a `VPanelMachiningMode` when needed.
3. `B4` does not need wheel avoidance segmentation. It should sit above the avoidance where needed; do not split B4 by wheel avoidance X range in V0.
4. Hard-coded construction dimensions should be parameterized as named constants/config values where practical.
5. Stove cut should only cut the clear opening, not the full logical column width.

Suggested geometry constants:

```ts
type KitchenGeometryConstants = {
  notchAllowanceExtra: number;       // default 1, so NA = CPT + 1
  style1ToeKickY: number;            // default 70
  bottomSlotRearY: number;           // default 80
  receiverNotchDepth: number;        // default 85
  supportStripWidth: number;         // default 100
  b3Depth: number;                   // default 150
  b3InternalNotchDepth: number;      // default 75
  supportStripNotchDepth: number;    // default 20
  minStripSegmentLength: number;     // default 30
};
```

Stove cut should use clear opening X:

```ts
stoveCutX0 = stoveColumn.clearX0;
stoveCutX1 = stoveColumn.clearX1;
```

Where:

```ts
clearX0 = leftV.x1;
clearX1 = rightV.x0;
```

## Current Implementation Notes

The first Kitchen geometry layer now exists as a pure TypeScript generator:

```text
modules/kitchenCabinet/types.ts
modules/kitchenCabinet/generator.ts
```

Unified plugin bridge:

```text
fusion360-unified-cabinet-plugin/scripts/kitchen_from_params.js
fusion360-unified-cabinet-plugin/modules/kitchen/controller.py
```

Palette route:

```text
kitchen.generateGeometry
```

Current generated debug output includes:

- computed columns
- computed zones
- V panels with Y-Z profiles
- boards
- slot requests
- resolved slots
- warnings/errors
- SVG front elevation debug
- SVG V panel profile debug
- SVG board top-view debug with slot overlays

Known current behavior:

- Default layout has matching opposite half-slot requests at `V2`; these are automatically merged to a through slot because the left/right slot geometry is identical.
- The UI only shows the machining conflict popup for unresolved double-sided half-slot conflicts where opposite half slots cannot be matched/merged automatically.
- The selected mode is stored in `vPanelMachiningPreferences` and included in presets.
- Choosing `through` for a true unresolved conflict resolves the blocking error but may emit visible-through warnings.
- Geometry debug previews are shown in the center Kitchen workspace, not the right properties panel.
- The board debug area has a board selector; selecting a board shows that board's actual `profileXY` outline with its related slot requests overlaid.
- Board debug preview now respects `profilePlane`:
  - `XY` boards render X/Y.
  - `XZ` boards render X/Z with Z upward.
  - `YZ` boards render Y/Z with Z upward.
  - Example: `B4` default is `X 0 -> 2131`, `Y 585 -> 600`, `Z 0 -> 100`, so its debug view must be an XZ rectangle `2131 x 100`, not an XY strip `2131 x 15`.
- V panel debug preview has a V panel selector for `V0..Vn`; each selected V panel YZ profile overlays its own resolved slot requests, including end panels at `X0` and `Xn`.
- `B3` now has front notches for every V panel center, including `V0` and `Vn`; end notches are clamped to the board X bounds.
- Functional boards now draw protruding tongues in their SVG profile:
  - `drawer_divider`: main body is `Y = 0 -> 150`, tongues protrude only at `Y = 50 -> 150`.
  - `full_depth_shelf` / `door_shelf`: main body is `Y = 0 -> CD`, tongues protrude across the centered one-third depth band.
  - Tongue length follows resolved slot type: `through = CPT`, `half = CPT / 2`.

