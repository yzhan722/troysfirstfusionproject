# General Tall Cabinet — Front Panel / Hinge / Push Button Lock Spec (Draft v1)

Confirmed with user on 2026-06-11. Implementation must not change existing structural board generation except where explicitly stated (FPT unification, style_2 fixed front panel thickness).

## 0. Coordinate Convention (General Tall)

```text
X = width, left -> right
Y = depth, front -> rear; Y = 0 is the cabinet FRONT face
Z = height, bottom -> top

Front panel layer occupies: Y = 0 -> FPT
Carcass starts at:          Y = FPT (= frontFaceAllowance)
midDepth = cabinetDepth - FPT
Side panels: y0 = 0 -> cabinetDepth (already cover the front layer; no change needed)
```

Note: unlike Fridge (front layer at Y = -FPT -> 0), GT puts the front layer at Y = 0 -> FPT. The Fusion adapter must use GT's own convention.

## 1. FPT Unification (confirmed)

One UI value `frontPanelThickness` (FPT, default 16) drives ALL of:

- `frontFaceAllowance` (depth reserved for front layer; affects midDepth)
- `doorPanelThickness` (front panel body thickness)
- `TopStyle2FixedFrontPanel` / `BottomStyle2FixedFrontPanel` thickness
- side panel front coverage (automatic, since side panels span y 0 -> CD)

Internally `frontFaceAllowance` and `doorPanelThickness` may remain as fields but must always equal FPT.

## 2. Zone Type Change

Replace `side_door` with two types:

```text
left_side_door   (hinge on LEFT edge,  opening/handle edge on RIGHT)
right_side_door  (hinge on RIGHT edge, opening/handle edge on LEFT)
```

Migration: existing `side_door` zones default to `left_side_door`. Update UI dropdowns (front editor zone options + any remaining selects) and generator validation.

## 3. Which Zones Generate Front Panels

```text
left_side_door   -> 1 door leaf,  hinge left,  lock options
right_side_door  -> 1 door leaf,  hinge right, lock options
double_door      -> 2 door leaves, hinges on outer edges, lock per leaf
drawer           -> 1 drawer front, no hinge, lock top
top_flap         -> 1 flap, hinge TOP, lock BOTTOM
bottom_flap      -> 1 flap, hinge BOTTOM, lock TOP
blank_panel      -> fixed front: no X clearance, FC clearance top/bottom, no hinge, no lock
open_space       -> none
open_appliance   -> none
```

`TopStyle2FixedFrontPanel` / `BottomStyle2FixedFrontPanel` stay as existing structural boards (no duplicate FP body); they participate in the front layer only as clearance neighbors and follow FPT thickness.

## 4. X Sizing

Front opening span:

```text
frontX0 = leftSidePanelThickness
frontX1 = cabinetWidth - rightSidePanelThickness
(panels sit INSIDE the side panels; confirmed)
```

Per type:

```text
doors / drawer / flaps:
  panelX0 = frontX0 + FC
  panelX1 = frontX1 - FC

blank_panel (fixed front):
  panelX0 = frontX0
  panelX1 = frontX1

double_door leaves (center seam gap = one full FC, confirmed):
  seamX = divider center X if verticalDivider with dividerCenterX, else (frontX0 + frontX1) / 2
  left leaf:  panelX0 = frontX0 + FC, panelX1 = seamX - FC / 2
  right leaf: panelX0 = seamX + FC / 2, panelX1 = frontX1 - FC
```

## 5. Y Sizing

All generated front panels: `y0 = 0, y1 = FPT`.

## 6. Z Sizing

Use `stacking.items` boundary panels (`boundary_panel` items with z0/z1/centerZ) as references. Never use UI row order.

```text
adjacent zone also generates a front panel:
  upper panel z0 = boundaryCenterZ + FC / 2
  lower panel z1 = boundaryCenterZ - FC / 2

adjacent zone is open_space / open_appliance (no front panel) [A1 confirmed]:
  panel COVERS the boundary panel, then retreats one full FC from the far face
  (the face toward the open zone):
    front zone ABOVE open zone: panel z0 = boundary panel bottom face + FC
    front zone BELOW open zone: panel z1 = boundary panel top face - FC
  (same as the Fridge fridge-adjacent rule)

top-most front panel:
  style_1 top system: z1 covers T3 (z1 = T3 top face)
  style_2 top system: z1 = TopStyle2FixedFrontPanel.z0 - FC   (full FC, confirmed)

bottom-most front panel:
  style_1 bottom system: z0 covers B3 (z0 = B3 bottom face)
  style_2 bottom system: z0 = BottomStyle2FixedFrontPanel.z1 + FC

blank_panel: same Z rules as above (FC vertical clearances), X full span.
```

## 7. Hinge Rules (manual count, confirmed)

Hinge settings (same data shape as Fridge/Kitchen):

```text
cupDiameter = 35, cupDepth = 12.5, cupCenterFromEdge = 22.5
sideDistance = "auto" -> clamp(75 + (longSide - 300) * 25/300, 75, 100)
useThreeHinges = false (manual toggle; no auto count by height)
```

Placement:

```text
left_side_door:   cups on LEFT edge;  cupCenterX = panelX0 + cupCenterFromEdge
                  cup Zs: panelZ1 - sideDistance, panelZ0 + sideDistance (+ middle if 3)
                  longSide = panel height
right_side_door:  mirror on RIGHT edge (cupCenterX = panelX1 - cupCenterFromEdge)
double_door:      left leaf hinges on left edge, right leaf on right edge (outer edges)
top_flap:         cups along TOP edge;  cupCenterZ = panelZ1 - cupCenterFromEdge
                  cup Xs: panelX0 + sideDistance, panelX1 - sideDistance; longSide = panel width
bottom_flap:      cups along BOTTOM edge (cupCenterZ = panelZ0 + cupCenterFromEdge)
drawer / blank:   none
```

Machining: cup is a blind hole from the panel REAR face (Y = FPT) toward front (-Y... in GT terms: start face Y = FPT, drill toward Y = 0), depth 12.5.

## 8. Lock Rules

Global preset stays `razor_long_rounded_1`:

```text
rounded slot 55 x 15.5, radius 7.75
mountingSurfaceToSlotCenter = 30.5  (never hardcode 46.5)
```

### 8.1 Flaps and drawer (horizontal references only)

```text
drawer:       lock TOP;    centerX = panel mid X; centerZ = upper boundary panel bottom face - 30.5
top_flap:     lock BOTTOM; centerZ = lower boundary panel top face + 30.5
bottom_flap:  lock TOP;    centerZ = upper boundary panel bottom face - 30.5
```

### 8.2 Doors — lock position option (confirmed)

Per-zone option `lockPosition`:

```text
"top" | "bottom" | "side"
```

For `left_side_door` (handle edge = RIGHT); `right_side_door` mirrors all X directions; double_door leaves use the CENTER seam as their "side".

```text
top:
  horizontal cutout (55 X x 15.5 Z)
  lockSideDistance = horizontal distance from HANDLE edge toward the hinge side
    left door:  centerX = panelX1 - lockSideDistance
    right door: centerX = panelX0 + lockSideDistance
  centerZ = upper horizontal board bottom face - 30.5
  base mounts on the UPPER horizontal board's BOTTOM surface

bottom:
  horizontal cutout
  same X rule as top
  centerZ = lower horizontal board (Zi) TOP face + 30.5
  base mounts on the LOWER board's TOP surface

side:
  REQUIRES a vertical structural board at the handle edge
  (double_door center divider; or other vertical divider at that edge)
  cutout rotated 90 deg: 15.5 wide in X, 55 tall in Z
  lockSideDistance = vertical distance from panel TOP edge down to cutout center Z
  centerX = vertical board mounting face -/+ 30.5 toward the door center
  base mounts on the vertical board face; a center divider takes bases on BOTH faces
  (left leaf -> divider left face, right leaf -> divider right face)
```

Constraint (confirmed): if the structure at the chosen lock location is a HORIZONTAL board, the lock cannot rotate and cannot float at arbitrary height — only `top` / `bottom` placements are valid. If `side` is selected but no vertical board exists at the handle edge: warning + fallback to `top`.

`double_door`: each leaf gets its own lock (2 total), default `side` referencing the center divider when present; if no vertical divider, default `top`.

## 9. New Data Structures

```ts
type GeneralTallResolvedFrontType =
  | "left_door" | "right_door"        // from left/right_side_door and double_door leaves
  | "drawer" | "top_flap" | "bottom_flap" | "fixed_panel";

interface GeneralTallFrontPanel {
  id: string;                  // FP_<zoneId> or FP_<zoneId>_L / _R for double door
  zoneId: string;
  resolvedType: GeneralTallResolvedFrontType;
  x0: number; x1: number;
  y0: 0; y1: number;           // y1 = FPT
  z0: number; z1: number;
  width: number; height: number; thickness: number;
  z0Source: string; z1Source: string;   // "boundary", "T3", "B3", "style2_fixed_panel", "open_zone_fc", ...
  hingeHoles?: HingeCupHole[];
  lockCutout?: LockCutout;     // adds orientation: "horizontal" | "vertical" and mounting reference
  warnings: string[];
}
```

Result extension: `GeneralTallCabinetResult.frontPanels: GeneralTallFrontPanel[]` (parallel layer; `boards` untouched).

## 10. UI Changes

Left params panel — new "Front Panels / Hardware" card:

- FPT (replaces separate FrontFaceAllowance input; one number)
- Front Clearance FC (default 2.5)
- Locks enabled + preset
- Default hinge settings (cup diameter/depth/from-edge, side distance auto, use-3-hinges)

Right `gtZoneOptionsPanel`, per zone type:

- doors: Front Enabled, Hinge settings, Lock Enabled, Lock Position (top/bottom/side), Lock Side Distance, computed X0/X1/Z0/Z1 + lock center + warnings
- drawer: Front Enabled, Lock Enabled, computed values
- flaps: Front Enabled, Hinge settings, Lock Enabled, computed values
- blank_panel: Front Enabled, computed values
- open zones: "No front panel."

Zone type dropdowns: replace `side_door` with `left_side_door` / `right_side_door`.

## 11. Fusion Generation

- FP bodies: profilePlane XZ, thickness along Y, body at y 0 -> FPT (GT convention; NOT fridge's -FPT -> 0).
- Hinge/lock cuts use the staged-cut pattern proven in Fridge: move FP body far away, cut, move back — never let cut profiles intersect structural boards.
- Hinge cup: blind hole from rear face (y = FPT) toward front, depth 12.5.
- Lock slot: through cut, horizontal or vertical capsule per `lockCutout.orientation`.
- `frontPanelCutAudit` in the Fusion result.

## 12. Validation / Warnings

```text
width/height <= 0
hinge cup outside panel
lock cutout outside panel
side lock without vertical board -> warning + fallback top
missing T3/B3/style2 fixed panel reference for edge panels
open-zone adjacency fallback used        [A1]
double door seam outside leaf bounds
```

Preview: warnings OK. Fusion generation: invalid cutouts and missing references block FP generation (structural boards still generate).

## 13. Implementation Order

1. Types + zone type split (left/right side door) + UI dropdown migration.
2. FPT unification (single UI input; frontFaceAllowance = doorPanelThickness = FPT; style_2 fixed panel thickness follows).
3. `frontPanels[]` metadata in generator + tests.
4. Front editor overlay (panels, hinges, locks) + right-panel zone options.
5. Fusion FP bodies (flat + assembly) with staged hinge/lock cuts.
6. Validation pass + regression tests.

All assumptions confirmed; no open items.
