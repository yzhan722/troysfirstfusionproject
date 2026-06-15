# General Tall V-board Style Semantic Audit

This audit is based on runtime data already captured in `docs/general-tall-v-board-yz-point-matrix.md`.  
No generator or Fusion code changes were made for this audit.

## 1. Current findings

### CASE-A (`topStyle=style_1`, `bottomStyle=style_1`)
- **V1/V2 same?** Yes (`vector Y: 0->150`, `pointCount: 21` for both)
- **V3/V4 same?** Yes (`vector Y: 0->150`, `pointCount: 13` for both)
- **V1/V2 vs V3/V4 different?** Yes (point count differs; both are stile-depth vectors)
- **Semantically aligned with front/rear structural definition?** Yes
  - V1/V2 keep front-stile behavior
  - V3/V4 keep rear-stile behavior

### CASE-B (`topStyle=style_1`, `bottomStyle=style_2`)
- **V1/V2/V3/V4 all same vector depth behavior?** Yes (`vector Y: 0->624`)
- **V3/V4 bbox vs vector conflict?** Yes
  - V3/V4 `bbox Y: 474->624` (150 depth)
  - V3/V4 `vector Y: 0->624` (full depth)
- This is semantically inconsistent for local-vector interpretation.

### CASE-C (`topStyle=style_2`, `bottomStyle=style_1`)
- **V1/V2/V3/V4 all same vector depth behavior?** Yes (`vector Y: 0->624`)
- **V3/V4 bbox vs vector conflict?** Yes
  - V3/V4 `bbox Y: 474->624`
  - V3/V4 `vector Y: 0->624`

### CASE-D (`topStyle=style_2`, `bottomStyle=style_2`)
- **V1/V2/V3/V4 all same vector depth behavior?** Yes (`vector Y: 0->624`)
- **V3/V4 bbox vs vector conflict?** Yes
  - V3/V4 `bbox Y: 474->624`
  - V3/V4 `vector Y: 0->624`

## 2. Semantic conflict

Current taxonomy/definition in project context:
- `V1/V2` = front structural/profile boards
- `V3/V4` = rear structural/profile boards
- `SidePanel_L/R` = separate side-panel board category

Therefore:
- `V1/V2` should not implicitly become full-depth side panels.
- `V3/V4` should not implicitly become full-depth side panels.
- Full-depth side behavior should belong to `SidePanel_L/R` (or another explicit side-panel board type), not V-board reuse.

## 3. BBox/Vector consistency rule

For local vectors, Fusion mapping is:

- `worldY = bbox.y0 + local.y`

So local `vector Y` range should normally match board local depth:

- `localYMax ~= bbox.y1 - bbox.y0`

Unless board explicitly declares a world-coordinate vector mode (e.g. `vectorCoordinateMode = "world"`), which is currently absent.

Implication for `V3/V4`:
- With `bbox Y = 474->624`, local depth is 150.
- Expected local vector Y is typically `0->150`.
- Current `0->624` in CASE-B/C/D is inconsistent with bbox-local semantics.

## 4. Style responsibility

`topStyle` should affect:
- top notch/step segments
- top system interaction

`bottomStyle` should affect:
- bottom notch/step segments
- bottom system interaction

They should **not** reclassify `V3/V4` from rear stiles into full-depth side panels.

## 5. Recommended correction (do not implement here)

### Option A (recommended)
Keep V-boards as structural stiles in all style combinations:
- `V1/V2`: local Y range remains stile/front profile depth (currently 150 logic)
- `V3/V4`: local Y range remains rear-stile depth (150)
- `topStyle` only modifies top local profile segments
- `bottomStyle` only modifies bottom local profile segments
- Full-depth side behavior remains only in `SidePanel_L/R`

### Option B
If `style_2` intentionally means full-depth side board behavior, generate explicit side-panel boards (or new boardType), do not overload `V1/V2/V3/V4`.

## 6. Expected corrected matrix (high-level)

For all 4 style combinations:
- `V1` and `V2` should match each other.
- `V3` and `V4` should match each other.
- `V1/V2` and `V3/V4` may differ by profile details.
- `V3/V4` local `vector Y max` should be `150`.
- `V1/V2` local `vector Y max` should remain stile-range (currently 150 unless explicitly redesigned).
- `SidePanel_L/R` local Y max should carry full side-panel depth semantics (`CD` or `MidDepth` per side-panel spec), not V-boards.

## 7. Fusion implication

Current Fusion profile-body mapping (`world = bbox origin + local vector`) is semantically correct for local vectors.

The inconsistency is in V-board data semantics (CASE-B/C/D), not in Fusion mapping logic.  
Fusion adapter should not add compensating hacks for this V-data mismatch.

## 8. Recommended next implementation prompt

Use this as the next coding prompt (implementation stage):

> Do not change Fusion mapping.  
> In `generator.ts`, refactor V-board profile generation so `V1/V2/V3/V4` remain structural stile semantics across all style combinations.  
> Ensure local vector Y ranges are bbox-consistent for V-boards (`V3/V4` local depth 150, not 624).  
> Keep side-panel/full-depth behavior only in `SidePanel_L/R`.  
> Re-generate `docs/general-tall-v-board-yz-point-matrix.md` after fix and verify CASE-B/C/D no longer produce V3/V4 `vector Y 0->624` with `bbox Y 474->624`.
