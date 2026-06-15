# General Tall Cabinet V1 Implementation Checkpoint

## 1. Current data flow

Current data flow:

boundaryResolver
-> stackingCalculator
-> generator
-> boards[]
-> features[]
-> V board profileVector / cutProfileVector / profileFeatures

Responsibilities:

- `boundaryResolver`: resolves functional-zone boundaries. It outputs only `none`, `full_zi`, and `half_zi`, and applies the `double_door.verticalDivider` boundary upgrade rules.
- `stackingCalculator`: calculates bottom-to-top Z stacking, including top/bottom system heights, functional zone clear-space heights, and generated boundary panel thicknesses.
- `generator`: consumes stacking and boundary results, then emits skeleton board data and feature placeholders.
- `boards[]`: stores structural board skeletons as bounding boxes and related metadata.
- `features[]`: stores non-board feature placeholders such as V board Zi slots, divider Zi grooves, and H34 clearance slots.
- V board `profileVector` / `cutProfileVector` / `profileFeatures`: stores base YZ side profile rectangles, current cut outline skeletons, and profile feature data for V1/V2/V3/V4.

## 2. Implemented modules

1. boundaryResolver

- Outputs only `none`, `full_zi`, and `half_zi`.
- Does not output `shortened_zi`.
- Supports blank / drawer / door / open / appliance / flap boundary rules.
- Supports `double_door.verticalDivider` boundary upgrade.

2. stackingCalculator

- Calculates Z stacking from bottom to top.
- Includes generated boundary panel thickness in cabinet height calculation.
- Supports Style 1 / Style 2 top and bottom system heights.
- Reports height mismatch without auto-stretching zones.

3. generator skeleton

- Outputs `boards[]`.
- Outputs `features[]`.
- Does not generate door panels, drawer fronts, hardware, nesting, or toolpath.

4. Style 1 structural boards

- Generates `T1`, `T2`, `T3`.
- Generates `B1`, `B2`, `B3`.
- `T1`, `T2`, `B1`, and `B2` remain bounding-box structural rails.
- `T3` and `B3` now have exact XY notched `profileVector`.
- `T3` and `B3` use `MidWidth`, side notch width = 16, front notch depth = 75, and full depth = 150.
- `T3` and `B3` bounding boxes, `materialThickness`, and `z0` / `z1` remain unchanged.
- `T3` and `B3` grooves and drill holes remain deferred.

5. V board slot features

- Generates `zi_slot` features on `V1`, `V2`, `V3`, and `V4`.
- Uses `boundary.centerZ`.
- Supports `shortened_zi` slot Y range after avoidance adjustment.

6. H support boards

- Generates `H13_top`, `H24_top`, `H34_top`.
- Generates `H13_bottom`, `H24_bottom`, `H34_bottom`.
- Generates `H13_mid`, `H24_mid`, `H34_mid`.
- Uses bounding boxes only.
- Merge, avoidance, and conflict movement are deferred.

7. Vertical divider skeleton

- Generated for `double_door.verticalDivider = true`.
- Uses `dividerCenterX` when provided, otherwise `MidWidth / 2`.
- Uses the double-door stacking zone `z0/z1`.
- Has global-Z YZ `profileVector`.
- Has `cutProfileVector` for effective H34 clearance rear-edge cuts.
- Tongue and groove geometry are deferred.

8. Zi groove placeholders

- Generates `zi_groove` features on `full_zi` boards for vertical divider support.
- Uses top/bottom face rules.
- Real groove cutting and through-groove merge are deferred.

9. H34 clearance slot placeholders

- Generates `h34_clearance_slot` features on vertical divider boards.
- Targets the divider only, not H34.
- Top-level `h34_clearance_slot` features remain original placeholders.
- Intersecting slots are copied into `vertical_divider.profileFeatures` as effective clamped cuts.
- Effective cut range:
  - `cutZ0 = max(slot.z0, divider.z0)`
  - `cutZ1 = min(slot.z1, divider.z1)`
- Fully non-intersecting H34 slots are not cut into `cutProfileVector`.
- Non-intersecting slots remain in top-level `features[]` and generate validation warnings.
- H34 boards themselves are not modified or cut.
- Dogbone, router compensation, and DXF/toolpath remain deferred.

10. Avoidance / shortened_zi skeleton

- Eligible `full_zi` can convert to `shortened_zi`.
- `half_zi` does not shorten.
- `double_door.verticalDivider` support Zi does not shorten.
- `ShortDepth` is applied to board Y range and related `zi_slot` Y range.
- Complex affected-zone logic is deferred.

11. V board profile skeleton

- `V1`, `V2`, `V3`, and `V4` have base YZ rectangle `profileVector`.
- Style 1 top/bottom insert slots are stored as `profileFeatures`.
- `zi_slot` features are copied to V board `profileFeatures`.
- V boards keep base `profileVector` as original rectangle.
- V boards now also have `cutProfileVector`.
- `cutProfileVector` currently supports:
  1. `zi_slot` rear/local-rear rectangular notches.
  2. Style 1 top/bottom front insert slot notches.
- `cutProfileVector` does not yet support:
  - H34 clearance cut.
  - Avoidance rear cutout.
  - Dogbone.
  - Router compensation.
  - DXF/toolpath output.

12. V board cutProfileVector

- `profileVector` remains unchanged as base rectangle.
- `cutProfileVector` is generated deterministically.
- Rear edge includes `zi_slot` cuts sorted by `z0` ascending.
- Front edge includes Style 1 insert slot cuts sorted by `z0` descending.
- `shortened_zi` `zi_slot` uses its own feature `y1` / `ShortDepth`.
- Style 2 does not generate Style 1 insert slot cuts.

13. Zi board profileVector

- `full_zi`, `half_zi`, and `shortened_zi` now have XY `profileVector` skeletons.
- `full_zi` uses bounding rectangle X = 0 -> MidWidth, Y = 0 -> MidDepth.
- `half_zi` currently uses bounding rectangle and keeps exact half Zi profile deferred note.
- `shortened_zi` uses bounding rectangle X = 0 -> MidWidth, Y = 0 -> ShortDepth.
- `zi_groove` remains a feature placeholder and is not cut into Zi `profileVector` yet.

14. T3 / B3 feature placeholders

- `T3` now generates `t3_drill_hole` placeholder features.
- `T3` drill-hole placeholders:
  - `targetBoardId = "T3"`
  - Y positions = 100, 125
  - X = `MidWidth / 2`
  - diameter = 5
  - `through = true`
  - exact drill pattern deferred
- `B3` now generates a `b3_groove` placeholder feature.
- `B3` groove placeholder:
  - width = 14.5
  - depth = 6.5
  - `branchCount = 2`
  - `branchWidth = 20`
  - exact connected groove path deferred
- `B3` now generates `b3_drill_hole` placeholder features.
- `B3` drill-hole placeholders:
  - Y positions = 92.5, 103, 140
  - two X columns:
    - `MidWidth / 3`
    - `MidWidth * 2 / 3`
  - diameter = 5
  - `through = true`
  - exact drill pattern deferred
- These are top-level `features[]` only.
- They do not modify `T3` / `B3` `profileVector`.
- They are not real CNC cut geometry.

15. Divider tongue feature placeholders

- `divider_tongue` is now implemented as a top-level `features[]` placeholder.
- `divider_tongue` is generated only from existing `zi_groove` features.
- It is not copied into `vertical_divider.profileFeatures`.
- It does not modify `vertical_divider.profileVector`.
- It does not modify `vertical_divider.cutProfileVector`.
- It does not modify Zi `profileVector`.
- It does not perform real tongue cutting.
- If `zi_groove.face = "bottom"`:
  - `divider_tongue.position = "top"`
  - `z0 = divider.z1 - 7`
  - `z1 = divider.z1`
- If `zi_groove.face = "top"`:
  - `divider_tongue.position = "bottom"`
  - `z0 = divider.z0`
  - `z1 = divider.z0 + 7`
- Y range:
  - `y0 = MidDepth / 3`
  - `y1 = MidDepth * 2 / 3`
- Relationship fields:
  - `targetBoardId = vertical_divider board id`
  - `relatedZiBoardId = full_zi board id`
  - `relatedGrooveFeatureId = zi_groove feature id`
  - `zoneId`
  - `boundaryId`

16. Merge / H Conflict Stage 1 detection

- Stage 1 only detects conflicts and merge candidates.
- It does not generate `TopMergedBoard` / `BottomMergedBoard`.
- It does not change V board `cutProfileVector`.
- Current debug output is stored in `debug.mergeAndConflict`:
  - `topMergeCandidate`
  - `bottomMergeCandidate`
  - `depthGap`
  - `topBottomHSystemOverlapExpected`
  - `hZiConflicts[]`
- Top / bottom merge candidate detection:
  - `gap = MidDepth - 105 - 105`
  - if `gap < 50`:
    - `topMergeCandidate = true`
    - `bottomMergeCandidate = true`
- H mid vs Zi conflict detection:
  - H mid boards checked:
    - `H13_mid`
    - `H24_mid`
    - `H34_mid`
  - Zi boards checked:
    - `full_zi`
    - `shortened_zi`
    - `half_zi`
  - Z overlap rule:
    - `H.z0 < Zi.z1 && H.z1 > Zi.z0`
  - `full_zi` overlap warning: movement deferred.
  - `shortened_zi` overlap warning: movement deferred.
  - `half_zi` overlap warning: half Zi movement rule deferred.

17. Merge / H Conflict Stage 2 H mid movement

- `H13_mid` / `H24_mid` move below `full_zi` or `shortened_zi` conflicts.
- `H34_mid` moves above `full_zi` or `shortened_zi` conflicts.
- `half_zi` remains warning-only and does not move H boards.
- Multiple `full_zi` / `shortened_zi` conflicts use the first conflict by ascending `Zi.z0` for deterministic V1 behavior.
- Out-of-bounds movement is skipped with validation warning; there is no silent clamp and no throw.
- Moved H boards include movement notes.
- `debug.mergeAndConflict.hZiConflicts` includes movement metadata:
  - `moved`
  - `originalZ0` / `originalZ1`
  - `newZ0` / `newZ1`
  - `movementDirection`
  - `skippedReason`
- H34 clearance dependency:
  - `h34_clearance_slot` features are generated after H movement.
  - If `H34_mid` moves, `h34_clearance_slot` uses moved `H34_mid.z0`.
  - `vertical_divider.cutProfileVector` follows the moved H34 slot.
  - No stale old `H34_mid` notch should remain.

18. Avoidance affected-zone refinement

- `avoidance.enabled = true` now requires `avoidance.height`.
- If `avoidance.height` is missing, non-finite, or `< 0`, no Zi boards are converted and the generator does not throw.
- `AvoidH = 0` is valid and means there is no affected Z range, so no `shortened_zi` is generated.
- If `AvoidH > CH`, a warning is emitted and `EffectiveAvoidH = CH` is used for overlap tests.
- The input `avoidance.height` is not mutated when `AvoidH > CH`.
- Affected Z range:
  - `0 -> EffectiveAvoidH`
- `full_zi` affected rule:
  - `Zi.z0 < EffectiveAvoidH && Zi.z1 > 0`
- Only affected `full_zi` boards that are not protected support Zi can convert to `shortened_zi`.
- `double_door.verticalDivider` support Zi remains `full_zi`.
- `half_zi` remains `half_zi`.
- `shortened_zi` keeps the same stacking height and Z range.
- `shortened_zi` only changes board Y depth and related `zi_slot` Y range.
- H conflict movement naturally recognizes whether the conflict source is `full_zi` or `shortened_zi`.
- Explicitly not implemented in this refinement:
  - H13/H24 bottom Y shortening.
  - H34_bottom Z = AvoidTopZ.
  - H avoidance movement.
  - V rear avoidance cutout.
  - Dogbone / router compensation.
  - DXF / toolpath.
  - Front panels / hardware.

## 3. Current allowed boardTypes

- `V1`
- `V2`
- `V3`
- `V4`
- `T1`
- `T2`
- `T3`
- `B1`
- `B2`
- `B3`
- `top_system_placeholder`
- `bottom_system_placeholder`
- `style2_fixed_front_panel`
- `full_zi`
- `half_zi`
- `shortened_zi`
- `H12`
- `H13`
- `H24`
- `H34`
- `vertical_divider`

Note: H12 naming contract is resolved. Current code emits H12 boards with `boardType = "H12"`.

## 4. Current allowed feature types

- `zi_slot`: rear slot placeholder for V boards, derived from non-none boundary panels and `boundary.centerZ`.
- `zi_groove`: placeholder groove on `full_zi` boards for vertical divider support.
- `h34_clearance_slot`: placeholder clearance slot on vertical divider boards where H34 boards intersect the divider area.
- `t3_drill_hole`: placeholder drill holes on the Style 1 `T3` board.
- `b3_groove`: placeholder connected groove feature on the Style 1 `B3` board.
- `b3_drill_hole`: placeholder drill holes on the Style 1 `B3` board.
- `divider_tongue`: placeholder tongue feature on vertical divider boards, generated from `zi_groove`.

## 5. Explicit V1 non-goals

V1 currently does not implement:

- Side door panels.
- Double door panels.
- Drawer fronts.
- Flap fronts.
- Blank front panels.
- Drawer box.
- Hinge holes.
- Lock cutouts.
- Slide holes.
- Hardware import.
- Exact CNC toolpath.
- Nesting.
- DXF export.
- Dogbone / router compensation.
- Remaining side profile cuts beyond current `zi_slot` and Style 1 insert slot skeleton.

## 6. Deferred implementation list

1. Remaining V side profile cuts:
   - Avoidance rear cutout exact profile.
   - Dogbone / router compensation.
   - Production-ready final DXF outline cleanup.
2. T3 / B3 remaining refinements:
   - T3 / B3 real drill cutting remains deferred.
   - B3 real connected groove path remains deferred.
   - Dogbone / router compensation remains deferred.
   - Production-ready T3 / B3 DXF cleanup remains deferred.
3. Zi board profile refinements:
   - Exact half_zi final profile vector remains deferred.
   - Real Zi groove cutting remains deferred.
   - Through groove merge remains deferred.
   - Production-ready Zi DXF cleanup remains deferred.
4. H13/H24/H34 conflict movement:
   - Stage 1 detection is implemented.
   - Stage 2 H13/H24/H34 mid movement is implemented.
5. H34/divider remaining refinements:
   - H34/divider cutProfileVector implemented for `vertical_divider`.
   - H34 clearance regeneration after H movement is implemented for `H34_mid`.
   - H34/divider dogbone/router compensation remains deferred.
   - H34/divider production DXF cleanup remains deferred.
6. Zi groove / divider tongue remaining refinements:
   - Real divider tongue outline remains deferred.
   - Dogbone / router compensation remains deferred.
   - DXF / toolpath cleanup remains deferred.
7. Avoidance remaining refinements:
   - H avoidance adjustment remains deferred.
   - H13/H24 bottom Y shortening remains deferred.
   - H34_bottom Z = AvoidTopZ remains deferred.
   - V rear avoidance cutout remains deferred.
8. Style 2 exact structural boards beyond fixed front panel.
9. Merge logic refinement:
   - Merge / H Conflict Stage 1 detection is implemented.
   - Merge / H Conflict Stage 2 H mid movement is implemented.
   - Real top/bottom merge remains deferred.
   - `TopMergedBoard` / `BottomMergedBoard` generation remains deferred.
   - V effective height changes remain deferred.
10. V3/V4 exact geometry.
11. Dogbone / router compensation.
12. DXF / toolpath cleanup.
13. Front panel / hardware V2.

## 7. Test status

Current test command:

```powershell
node "modules/generalTallCabinet/boundaryResolver.test.ts"; node "modules/generalTallCabinet/stackingCalculator.test.ts"; node "modules/generalTallCabinet/generator.test.ts"; node "modules/generalTallCabinet/generalTallCabinet.regression.test.ts"
```

Current status:

All tests passed.

## 8. General Tall Cabinet V1 Structural Freeze

Verdict:

FREEZE V1 STRUCTURAL

Meaning:

General Tall Cabinet V1 structural scope is ready to freeze.
Remaining items should be tracked as V1.1 production geometry or V2 front/hardware scope.

Freeze includes:

- `boundaryResolver`
- `stackingCalculator`
- Deterministic `boards[]` generation
- Deterministic `features[]` generation
- Style 1 structural boards
- T3/B3 `profileVector`
- T3/B3 placeholders
- V board `profileVector` / `cutProfileVector`
- Zi / `shortened_zi` logic
- H support boards
- H mid conflict detection and movement
- H34 clearance following moved H34
- `vertical_divider`
- `zi_groove`
- `divider_tongue`
- Avoidance affected-zone refinement
- Regression tests

Frozen V1 non-goals:

- Real top/bottom merge
- `TopMergedBoard` / `BottomMergedBoard`
- V effective height changes
- H avoidance adjustment
- V rear avoidance cutout
- Style 2 full structural production boards
- `half_zi` exact profile
- V3/V4 exact geometry
- Dogbone/router compensation
- DXF/toolpath
- Nesting
- V2 front panels / drawer fronts / flap fronts / hardware

Next recommended phase:

1. Connect General Tall V1 to UI / preview.
2. Add board table / debug table.
3. Add simple visual validation.
4. Then decide whether to implement Style 2 structural boards or move to V1.1 production geometry.

Test status:

All tests passed.

## 9. General Tall Cabinet V1 UI-1 Integration

Status:

PASS

Meaning:

General Tall Cabinet V1 is now connected to the existing CabinetNC palette as a data/table interface.

Implemented UI-1 scope:

- Independent General Tall Cabinet module/sidebar item
- General Tall local form state
- Default config
- Zone editor
- Generate action
- Python route `generalTall.generate`
- Node bridge `general_tall_from_params.js`
- Validation output
- `boards[]` table
- `features[]` table
- Stacking summary
- Boundary summary
- `debug.mergeAndConflict` output

Confirmed not implemented:

- 2D preview
- 3D preview
- Fusion body creation
- DXF/export
- Nesting
- Front panels / drawer fronts / flap fronts / hardware
- Production geometry

Verification result:

- Default config generated result
- Boards count: 22
- Features count: 22
- Errors count: 0
- Warnings count: 9
- `debug.mergeAndConflict` exists
- `vertical_divider` exists
- H conflict movement is visible in debug / board notes
- Fridge bridge still passed
- General Tall and Fridge state are isolated

Test status:

- General Tall tests passed
- General Tall Node bridge test passed
- Existing unified Fridge bridge test passed
- Lints: no errors
- Python compile not run because `python` / `py` executable unavailable in shell; environment limitation

Next recommended phase:

1. UI-2 simple V board YZ side profile preview.
2. UI-3 simple 3D bounding-box preview.
3. Style 2 structural boards / `half_zi` exact profile / V3-V4 geometry.
4. V1.1 production geometry.
5. V2 front panels / hardware.
6. DXF / nesting later.

## 10. Next recommended steps

1. Finalize board/feature naming contracts.
2. Add regression tests for the current full V1 skeleton.
3. Implement final V side profile boolean-cut outline.
4. Implement exact half Zi and Zi groove cut refinements.
5. Implement more refined avoidance.
6. Only after structural V1 is stable, start V2 door panels and hardware.

# General Tall Cabinet V1/V2 Style 1 Real Side Profile

Status:
PASS

Meaning:
V1/V2 Style 1 side profile is no longer a skeleton full-MidDepth rectangle.
It now uses a real local machining YZ profile.

Implemented:

- Applies only to V1/V2 when top and bottom systems are `style_1`.
- Local YZ coordinates:
  - Y = 0 front
  - Y = 150 rear
  - Z = 0 bottom
  - Z = CH top
- V1/V2 vector Y range = 0 -> 150.
- Rear Zi slot uses Y 100 -> 150.
- Front contour uses stepped shape with Y 70 / 80 / 0.
- Default top step uses Z 1944 / 1960.
- Default bottom step uses Z 53 / 69.
- V1/V2 `profileVector` and `cutProfileVector` match the real 21-point stepped sequence.

Confirmed unchanged:

- V3/V4 exact geometry remains deferred.
- Style 2 real profile remains deferred.
- `boundaryResolver`.
- `stackingCalculator`.
- H movement.
- H34 clearance.
- `vertical_divider` geometry.
- T3/B3 `profileVector`.
- Zi board `profileVector`.
- Fridge Cabinet Generator.
- Fusion body / DXF / nesting / hardware not implemented.

Default verification:

- V1/V2 exact vector PASS.
- V1/V2 Y range = 0 -> 150.
- V1/V2 no longer use y=518 or y=568.
- Zi slots use y=100 -> 150.
- Stepped front contour PASS.
- Tests PASS.
- General Tall bridge smoke test PASS.
- Fridge bridge smoke test PASS.

Deferred:

- V3/V4 exact geometry.
- Style 2 real side profile.
- `half_zi` exact profile.
- Zi groove real cutting.
- Divider tongue real outline.
- Fusion body.
- DXF / dogbone / CNC cleanup.

## General Tall flap position rule

Status: PASS

Confirmed:

- `zones` array is bottom-to-top.
- `bottom_flap` is valid only at `index === 0`.
- `top_flap` is valid only at `index === zones.length - 1`.
- Middle flap is invalid.
- Validation preset V1.1 updated and rerun.
- `GT-03-top-flap-valid` is now READY.
- `GT-04-bottom-flap-valid`, `GT-08-extra-tall-valid`, and `GT-09-low-cabinet-valid` are now READY.
- `NEG-02-middle-flap-invalid` still FAILs as expected.

H34 validation cleanup:

- Expected H34 clearance clamp / no-intersection messages are no longer emitted as validation warnings.
- Normal H34 clearance diagnostics are retained in `debug.h34Clearance`.
- Geometry semantics are unchanged: H34 clearance placeholder generation, clamp behavior, and VD `cutProfileVector` cuts are unchanged.
