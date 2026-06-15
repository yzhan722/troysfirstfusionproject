# Overhead Cabinet Generator v1 - Algorithm and Geometry Handoff

> Note: UI title still says **Cabinet Generator**, but this is actually the first standalone **Overhead Cabinet Generator** prototype. Do not infer any General Tall Cabinet semantics from this UI or code.

## Scope

This document summarizes the current Overhead Cabinet v1 algorithm, geometry rules, and generated output so another GPT/chat can continue development without reading General Tall history.

Primary source files:

- `fusion360-cabinet-generator/palette.html` - legacy UI shown as "Cabinet Generator"
- `fusion360-cabinet-generator/core/overhead_geometry.py` - original Python geometry source of truth
- `fusion360-cabinet-generator/services/solid_extrude_service.py` - legacy Fusion body/sketch generation
- `modules/overheadCabinet/geometry.ts` - TypeScript port of the Python geometry
- `modules/overheadCabinet/generator.ts` - unified plugin generator wrapper
- `modules/overheadCabinet/generator.test.ts` - golden tests ported from Python

## Non-Goals

Do not use these concepts here:

- General Tall `style_1` / `style_2`
- General Tall board ids such as `V1`, `V2`, `H34`, `VD`, `Zi`, `T4/T5`
- General Tall clearance slots, stacking zones, boundary resolver, V-board matrix

Overhead v1 has its own simple taxonomy: `BP`, `T1`, `T2`, `T3`, `T4`, and dividers `D0...Dn`.

## UI Inputs

The legacy palette collects:

- `width` / `Cw`: cabinet width in mm
- `depth` / `Cd`: cabinet depth in mm
- `height` / `Ch`: cabinet height in mm
- `bottomThickness` / `Bt`: bottom panel thickness in mm
- `routerDiameter` / `Crd`: router diameter in mm
- `internalXds`: comma-separated internal divider centerlines only
- `viewMode`: debug sketch selector, one of `bp`, `t2`, `t3`, `t4`, `divider`, `all`

Important UI rule:

- User only enters **internal divider centerlines**.
- Edge divider centerlines are automatic.
- Left edge divider centerline = `FGw / 2`
- Right edge divider centerline = `Cw - FGw / 2`

Example from current UI:

```text
Cw = 2000
Cd = 400
Ch = 400
Bt = 15
Crd = 10
internalXds = [600, 1400]
```

Computed divider centerlines:

```text
FGw = 16
edge left = 8
edge right = 1992
all XDi = [8, 600, 1400, 1992]
```

## Coordinate System

All geometry is in mm.

- `X`: left to right across cabinet width
- `Y`: front to rear across cabinet depth
- `Z`: vertical height

Many generated vectors are 2D local profiles:

- `XY` vectors are plan/top-down outlines
- `XZ` vectors are front/back rail profiles
- `YZ` vectors are divider side profiles

Legacy `bottom_panel` uses local origin label `left-top-front`, but the actual bbox behavior is:

```text
global_origin = [0, 0, Bt]
size = [Cw, Cd, Bt]
local_bounds.x = [0, Cw]
local_bounds.y = [0, Cd]
local_bounds.z = [-Bt, 0]
```

## Constants

Current constants preserved from the Python implementation:

- `DEFAULT_ROUTER_DIAMETER_MM = 10`
- `DIVIDER_THICKNESS_MM = 15`
- `FEATURE_CLEARANCE_MM = 1`
- `FEATURE_GROOVE_WIDTH_MM / FGw = 16`
- `SCREW_HOLE_DIAMETER_MM = 3`
- `SCREW_HOLE_DEPTH_MM = 15`
- `BOTTOM_THICKNESS_MM / Bt = 15`
- `DIVIDER_TONGUE_HEIGHT_MM / Dntg_h = Bt / 2 = 7.5`
- `T1_HEIGHT_MM = 40`
- `T3_DEPTH_MM = 90`
- `T3_THICKNESS_MM = 15`
- `T3_NOTCH_DEPTH_MM = 20`
- `T4_THICKNESS_MM = 15`
- `T4_HEIGHT_MM = 50`
- `T4_NOTCH_HEIGHT_MM = 20`
- `T4_SCREW_HOLE_NOTCH_CLEARANCE_MM = 8`
- `T4_SCREW_HOLE_UP_SHIFT_MM = 10`
- `FRONT_TOP_NOTCH_Y_OFFSET_MM = 70`
- `FRONT_TOP_STEP_Y_MM = 10`
- `FRONT_TOP_STEP_DROP_MM = FGw = 16`
- `REAR_TOP_NOTCH_HEIGHT_MM = T4_HEIGHT - 15 = 35`

## Main Algorithm

The core geometry call is:

```ts
calculateOverheadGeometry({
  cabinetWidth,
  cabinetDepth,
  cabinetHeight,
  bottomThickness,
  dividerTongueHeight,
  routerDiameter,
  featureWidth,
  internalDividerCenterlines,
})
```

It computes:

1. Edge + internal divider centerlines.
2. One feature bundle per divider.
3. Bottom panel geometry.
4. Screw holes for top panels.
5. Trimmed outline vectors for `T3`, `T4`, and divider side panels.

Result shape:

```ts
{
  cabinet: { Cw, Cd, Ch },
  manufacturing: { Crd, Crr, FGw, FGh },
  bottom_panel,
  divider_features,
  panel_screw_holes: { T2, T3, T4 },
  trimmed_vectors: { T3, T4, DividerSide }
}
```

## Divider Centerlines

Feature groove width:

```text
FGw = divider thickness + clearance = 15 + 1 = 16
halfFGw = FGw / 2 = 8
```

Edge centerlines:

```text
left = halfFGw
right = Cw - halfFGw
```

All divider ids are assigned in order:

```text
D0 = left edge divider
D1...D(n-2) = user internal centerlines
D(n-1) = right edge divider
```

For any divider centerline `XDi`, the feature X range is:

```text
x0 = XDi - FGw / 2
x1 = XDi + FGw / 2
```

This intentionally makes edge divider notches flush to cabinet sides:

```text
D0 at XDi=8    -> x=[0,16]
right at 1992 -> x=[1984,2000] when Cw=2000
```

## BP Bottom Panel

`BP` is the bottom panel.

Basic rectangle:

```text
x = [0, Cw]
y = [0, Cd]
z = [0, Bt] in generated Fusion body
```

Legacy geometry object:

```text
origin = left-top-front
global_origin = [0, 0, Bt]
size = [Cw, Cd, Bt]
local z bounds = [-Bt, 0]
```

## BP Divider Grooves

For every divider, the bottom panel receives a groove.

X range:

```text
x = [XDi - FGw/2, XDi + FGw/2]
```

Y range:

```text
y0 = Cd / 3
y1 = 2 * Cd / 3
length_y = Cd / 3
```

Z range:

```text
z = [0, -Dntg_h]
depth_z = Dntg_h
```

Default:

```text
Dntg_h = Bt / 2 = 7.5
```

For the current UI example `Cd=400`:

```text
BP groove y = [133.3333333333, 266.6666666667]
BP groove length = 133.3333333333
BP groove z = [0, -7.5]
```

## Divider Tongue

Each divider has a tongue that fits into the BP groove.

Y range is offset inward by router radius:

```text
Crr = Crd / 2
y0 = Cd / 3 + Crr
y1 = 2 * Cd / 3 - Crr
length_y = Cd / 3 - Crd
```

Z range:

```text
z = [-Dntg_h, 0]
```

For `Cd=400`, `Crd=10`:

```text
divider tongue y = [138.3333333333, 261.6666666667]
divider tongue length = 123.3333333333
divider tongue z = [-7.5, 0]
```

## Screw Holes

There are two screw hole systems.

### Divider / BP screw holes

Each divider centerline gets two holes on the bottom panel:

```text
hole 1 = { x: XDi, y: Cd / 6, diameter: 3 }
hole 2 = { x: XDi, y: 5 * Cd / 6, diameter: 3 }
```

For `Cd=400`:

```text
y = [66.6666666667, 333.3333333333]
diameter = 3
```

### T2 / T3 / T4 panel screw holes

For each part, each divider centerline receives one screw hole at the panel-local midline:

```text
T2 center = [XDi, T1_HEIGHT / 2] = [XDi, 20]
T3 center = [XDi, T3_DEPTH / 2] = [XDi, 45]
T4 center = [XDi, T4_NOTCH_HEIGHT + clearance + up_shift]
          = [XDi, 20 + 8 + 10]
          = [XDi, 38]
```

Each hole:

```text
diameter = 3
depth = 15
axis = thickness
id = <part>SH_D<index>
```

## T3 Notches and Trimmed Outline

`T3` is a top/rear panel with depth `90` and divider notches cut from the rear side.

For each divider:

```text
x = [XDi - FGw/2, XDi + FGw/2]
y = [T3_DEPTH - T3_NOTCH_DEPTH, T3_DEPTH]
  = [70, 90]
z = [0, -T3_THICKNESS]
  = [0, -15]
```

The trimmed `T3` outline is an `XY` polygon generated by walking all notch X ranges from right to left.

Algorithm:

1. Start at `[0,0]`, then `[Cw,0]`.
2. Sort divider notch X ranges descending by `x0`.
3. If the rightmost notch touches or crosses `Cw`, create an edge notch from `[Cw,70]` to its `x0`.
4. For each internal notch, add a rectangular step:
   - `[x1,90]`
   - `[x1,70]`
   - `[x0,70]`
   - `[x0,90]`
5. If the leftmost notch touches `x<=0`, close through `[x1,90]`, `[x1,70]`, `[0,70]`, `[0,0]`.
6. Remove duplicated adjacent points.

Purpose:

- Produces one closed profile containing all divider notches.
- Edge divider notches naturally open at the cabinet side.

## T4 Notches and Trimmed Outline

`T4` is a top/front rail-like panel with height `50` and bottom notches.

For each divider:

```text
x = [XDi - FGw/2, XDi + FGw/2]
y = [0, T4_THICKNESS] = [0, 15]
z = [0, T4_NOTCH_HEIGHT] = [0, 20]
```

The trimmed `T4` vector is another 2D polygon. It uses `x` and local vertical height:

```text
top height = 50
notch height = 20
```

Algorithm:

1. Start at `[0,50]`, then `[Cw,50]`.
2. Sort divider notch X ranges descending by `x0`.
3. If the rightmost notch touches or crosses `Cw`, create edge notch down to height `20`.
4. For every internal notch, add a notch step:
   - `[x1,0]`
   - `[x1,20]`
   - `[x0,20]`
   - `[x0,0]`
5. If the leftmost notch touches `x<=0`, close through `[x1,0]`, `[x1,20]`, `[0,20]`, `[0,50]`.
6. Remove duplicated adjacent points.

## Divider Side Profile

`DividerSide` is a `YZ` local vector for side shape of every divider.

It is only generated when `cabinetHeight` is provided. If `Ch` is missing, `DividerSide = []`.

Derived values:

```text
dividerHeight = Ch - Bt
tongue_y = [Cd/3 + Crd/2, 2*Cd/3 - Crd/2]
tongue_z0 = -Dntg_h

front_y0 = 70
front_z0 = dividerHeight - T1_HEIGHT

rear_y0 = Cd - FGw
rear_z0 = dividerHeight - REAR_TOP_NOTCH_HEIGHT

front_step_y1 = front_y0 + 10
front_step_z1 = front_z0 - FGw
```

Point sequence:

```text
[0, 0]
[tongue_y0, 0]
[tongue_y0, -Dntg_h]
[tongue_y1, -Dntg_h]
[tongue_y1, 0]
[Cd, 0]
[Cd, rear_z0]
[Cd - FGw, rear_z0]
[Cd - FGw, dividerHeight]
[70, dividerHeight]
[70, front_z0]
[80, front_z0]
[80, front_z0 - FGw]
[80 - (T3_DEPTH - 10), front_z0 - FGw]
[0, 0]
```

For current UI example `Cd=400`, `Ch=400`, `Bt=15`, `Crd=10`, `FGw=16`:

```text
dividerHeight = 385
tongue_y = [138.3333333333, 261.6666666667]
rear_y0 = 384
rear_z0 = 350
front_z0 = 345
front_step_z1 = 329

DividerSide =
[
  [0, 0],
  [138.3333333333, 0],
  [138.3333333333, -7.5],
  [261.6666666667, -7.5],
  [261.6666666667, 0],
  [400, 0],
  [400, 350],
  [384, 350],
  [384, 385],
  [70, 385],
  [70, 345],
  [80, 345],
  [80, 329],
  [0, 329],
  [0, 0]
]
```

## Generated Board Taxonomy

Current TypeScript unified generator emits:

- `BP`: bottom panel
- `T3`: top rear panel, with `profileVector = trimmed_vectors.T3`
- `T4`: top front panel, with `profileVector = trimmed_vectors.T4`
- `D0...Dn`: dividers, each using bbox plus `cutProfileVector = trimmed_vectors.DividerSide` when available

Legacy Fusion body generator additionally creates:

- `T1`: rectangular rail profile, height `40`, thickness `16`
- `T2`: rectangular rail profile, height `40`, thickness `15`, with screw holes
- `T3`: trimmed `XY` vector, thickness `15`, with screw holes
- `T4`: flipped trimmed vector, thickness `15`, with screw holes
- `BP`: rectangular bottom panel with groove cuts and screw holes
- `D0...Dn`: divider bodies from rotated `DividerSide` vector

## TypeScript Output Envelope

`generateOverheadCabinet(params)` returns:

```ts
{
  params,
  boards,
  features,
  validation: { errors, warnings },
  debug: {
    phase: "geometry_v1",
    legacyReference: "fusion360-cabinet-generator/core/overhead_geometry.py",
    dividerCenterlines,
    legacyGeometry
  }
}
```

Important:

- `features` is currently the raw `divider_features` array.
- Full legacy geometry is available under `debug.legacyGeometry`.
- Fusion body generation in the unified plugin is still pending.

## Legacy Fusion Body Generation

Legacy body generation path:

```text
palette.html
  -> action generateBodies
  -> SolidExtrudeService.generate(params)
  -> calculate_overhead_geometry_from_internal_xds(...)
  -> create sketches and extrude/cut bodies
```

Input parsing:

- `width`, `depth`, `height`, `bottomThickness`, `routerDiameter` must be positive numbers.
- `internalXds` accepts comma, semicolon, Chinese comma, and optional brackets.
- `divider_tongue_height` is forced to `Bt / 2`.
- `feature_width` is fixed at `16`.

Generated bodies and placement:

- `BP`:
  - extrude rectangular `XY` outline by `Bt`
  - move min point to `[0,0,0]`
  - cut BP grooves from top face by `Bt / 2`
  - cut BP screw holes through bottom thickness

- `T1`:
  - extrude rectangular `XZ` rail outline, height `40`, thickness `16`
  - move to:
    - `x = 0`
    - `y = 39`
    - `z = divider_top_step_z + 15`

- `T2`:
  - extrude rectangular `XZ` rail outline, height `40`, thickness `15`
  - move to:
    - `x = 0`
    - `y = 16 + 39`
    - `z = divider_top_step_z + 15`
  - cut panel screw holes

- `T3`:
  - extrude `trimmed_vectors.T3` on `XY`, thickness `15`
  - move to:
    - `x = 0`
    - `y = FRONT_TOP_NOTCH_Y_OFFSET + 10 - 80`
    - `z = divider_top_step_z - T3_THICKNESS + 14`
  - cut panel screw holes

- `T4`:
  - use `trimmed_vectors.T4`, flipped by local height `50`
  - extrude on `XZ`, thickness `15`
  - move to:
    - `x = 0`
    - `y = Cd - 15`
    - `z = Ch - 50`
  - cut panel screw holes from the back side

- Dividers `D0...Dn`:
  - rotate `DividerSide` vector 90 degrees for Fusion local sketch use:
    - local transform: `[y,z] -> [-z,y]`
  - extrude on `YZ`, thickness `15`
  - move each divider min point to:
    - `x = XDi - 7.5`
    - `y = 0`
    - `z = Bt - Bt/2`

Cleanup:

- Generated bodies get attribute group `CabinetGenerator`, value `generated_by=auto_solid_extrude`.
- Auto sketches and planes use prefixes like `AUTO_SOLID_SK_`.
- Clear deletes generated bodies, sketches, planes, extrude features, and move features.

## Debug Sketch Modes

Legacy debug mode selector:

- `bp`: BP only, easiest first check
- `t2`: T2 only
- `t3`: T3 only
- `t4`: T4 only
- `divider`: divider side only
- `all`: all views

This is for visual verification before solid generation.

## Known Current State

Implemented:

- Python legacy overhead geometry
- TypeScript geometry port
- Golden tests for centerlines, BP grooves, divider tongue, T3/T4 notches, screw holes, divider side vector
- Unified plugin bridge returning `geometry_v1`

Pending:

- Unified plugin palette UI for overhead
- Unified plugin Fusion adapter/body generation
- Clean feature typing for `features`
- More explicit production-ready board taxonomy in TypeScript

## Acceptance Tests

Current tests:

```bash
node modules/overheadCabinet/generator.test.ts
node fusion360-unified-cabinet-plugin/tests/run_overhead_bridge_tests.js
```

Expected status:

```text
generator.test.ts: all legacy golden checks pass
run_overhead_bridge_tests.js: geometry_v1 bridge checks pass
```

## Important Instruction For Next GPT

Treat this as an Overhead Cabinet module only.

Do not import General Tall assumptions. Continue from the formulas in `overhead_geometry.py` / `geometry.ts`, then wire the unified plugin UI and Fusion generation around these outputs.
