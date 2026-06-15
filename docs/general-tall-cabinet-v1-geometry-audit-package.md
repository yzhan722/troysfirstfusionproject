# General Tall Cabinet V1 Geometry Audit Package

Generated for external geometry review. This package is a snapshot of the current General Tall Cabinet V1 generator output for the UI default-style test case below. It is intentionally descriptive only: no TypeScript, UI, Fridge Cabinet Generator, or feature implementation changes are included.

## 1. Test case input

Primary test input:

```json
{
  "cabinetHeight": 2000,
  "cabinetWidth": 600,
  "cabinetDepth": 584,
  "panelThickness": 16,
  "frontFaceAllowance": 16,
  "sideClearance": 3,
  "topSystem": {
    "style": "style_1",
    "frontRailHeight": 40
  },
  "bottomSystem": {
    "style": "style_1",
    "frontRailHeight": 53
  },
  "avoidance": {
    "enabled": false,
    "depth": 200,
    "height": 400
  },
  "zones": [
    { "id": "zone-1", "type": "side_door", "height": 600 },
    { "id": "zone-2", "type": "drawer", "height": 300 },
    { "id": "zone-3", "type": "double_door", "height": 945, "verticalDivider": true }
  ]
}
```

Height check:

| calculated CH | expected CH | difference | status |
|---:|---:|---:|---|
| 2000 | 2000 | 0 | PASS |

## 2. Derived dimensions

| value | result | notes |
|---|---:|---|
| CabinetWidth | 600 | Input `CW` |
| CabinetDepth | 584 | Input `CD` |
| CabinetHeight | 2000 | Input `CH` |
| MidWidth | 600 | No side panels in this test |
| MidDepth | 568 | `CD - FrontFaceAllowance = 584 - 16` |
| TopSystemHeight | 56 | Style 1 top rail 40 + insert slot 16 |
| BottomSystemHeight | 69 | Style 1 bottom rail 53 + insert slot 16 |
| TopRailHeight | 40 | Style 1 top front rail height |
| BottomRailHeight | 53 | Style 1 bottom front rail height |
| TopPanelBottomZ | 1944 | `CH - TopSystemHeight` |
| TopPanelTopZ | 1960 | `CH - TopRailHeight` |
| BottomRailTopZ | 53 | `BottomRailHeight` |
| BottomPanelTopZ | 69 | `BottomSystemHeight` |
| ZiThickness | 15 | Default |
| HHeight | 100 | Current H support height used in output |
| HThickness | 15 | Default |
| SideClearance | 3 | Input |
| FrontFaceAllowance | 16 | Input |
| DoorPanelThickness | 16 | Default debug value |

## 3. Stacking output

| item id | type | z0 | z1 | height | centerZ | boundary / zone | notes |
|---|---|---:|---:|---:|---:|---|---|
| bottom-system | bottom_system | 0 | 69 | 69 | - | - | style_1 bottom system. |
| zone-zone-1 | functional_zone | 69 | 669 | 600 | - | zone-1 | side_door clear-space height. |
| boundary-zone-1-zone-2 | boundary_panel | 669 | 684 | 15 | 676.5 | full_zi | side_door bottom rule requires full Zi. |
| zone-zone-2 | functional_zone | 684 | 984 | 300 | - | zone-2 | drawer clear-space height. |
| boundary-zone-2-zone-3 | boundary_panel | 984 | 999 | 15 | 991.5 | full_zi | drawer bottom rule requires full Zi. Double-door vertical divider support requires full Zi. |
| zone-zone-3 | functional_zone | 999 | 1944 | 945 | - | zone-3 | double_door clear-space height. |
| top-system | top_system | 1944 | 2000 | 56 | - | - | style_1 top system. |

Stacking totals:

| topSystemHeight | bottomSystemHeight | boundaryPanelTotal | functionalZoneTotal | calculatedHeight | expectedCabinetHeight | difference |
|---:|---:|---:|---:|---:|---:|---:|
| 56 | 69 | 30 | 1845 | 2000 | 2000 | 0 |

Boundary resolution:

| index | aboveZoneId | belowZoneId | boundaryType | reason |
|---:|---|---|---|---|
| 0 | zone-1 | zone-2 | full_zi | side_door bottom rule requires full Zi. |
| 1 | zone-2 | zone-3 | full_zi | drawer bottom rule requires full Zi. Double-door vertical divider support requires full Zi. |

Debug-only boundaries:

| index | aboveZoneId | belowZoneId | boundaryType | reason |
|---:|---|---|---|---|
| -1 | top_system | zone-1 | none | Top System already provides the upper structural interface. |
| 2 | zone-3 | bottom_system | none | Bottom System already provides the lower structural interface. |

## 4. Boards summary

| id | boardType | category | materialThickness | profilePlane | thicknessAxis | x0/x1 | y0/y1 | z0/z1 | notes |
|---|---|---|---:|---|---|---|---|---|---|
| V1 | V1 | vertical_structure | 16 | YZ | X | 0/16 | 0/568 | 0/2000 | Exact side profile cut vector deferred; profileFeatures contain slot/notch data |
| V2 | V2 | vertical_structure | 16 | YZ | X | 584/600 | 0/568 | 0/2000 | Exact side profile cut vector deferred; profileFeatures contain slot/notch data |
| V3 | V3 | vertical_structure | 16 | YZ | X | 0/16 | 418/568 | 0/2000 | V3/V4 exact geometry deferred; Exact side profile cut vector deferred; profileFeatures contain slot/notch data |
| V4 | V4 | vertical_structure | 16 | YZ | X | 584/600 | 418/568 | 0/2000 | V3/V4 exact geometry deferred; Exact side profile cut vector deferred; profileFeatures contain slot/notch data |
| B1 | B1 | bottom_system | 16 | XZ | Y | 0/600 | 0/16 | 0/53 | Style 1 bottom front rail |
| B2 | B2 | bottom_system | 15 | XZ | Y | 0/600 | 16/31 | 0/53 | Style 1 second bottom rail behind B1 |
| B3 | B3 | bottom_system | 15 | XY | Z | 0/600 | 0/150 | 53/69 | Style 1 bottom inserted board; Exact Style 1 B3 notched profileVector implemented; Groove/drill features deferred |
| T1 | T1 | top_system | 16 | XZ | Y | 0/600 | 0/16 | 1960/2000 | Style 1 top front rail |
| T2 | T2 | top_system | 15 | XZ | Y | 0/600 | 16/31 | 1960/2000 | Style 1 second top rail behind T1 |
| T3 | T3 | top_system | 15 | XY | Z | 0/600 | 0/150 | 1944/1960 | Style 1 top inserted board; Exact Style 1 T3 notched profileVector implemented; Drill/groove features deferred |
| Zi1 | full_zi | boundary_panel | 15 | XY | Z | 0/600 | 0/568 | 669/684 | - |
| Zi2 | full_zi | boundary_panel | 15 | XY | Z | 0/600 | 0/568 | 984/999 | - |
| H13_bottom | H13 | h_support | 15 | YZ | X | 0/15 | 150/418 | 0/100 | Bottom H support skeleton; Avoidance adjustment deferred |
| H24_bottom | H24 | h_support | 15 | YZ | X | 585/600 | 150/418 | 0/100 | Bottom H support skeleton; Avoidance adjustment deferred |
| H34_bottom | H34 | h_support | 15 | XZ | Y | 15/585 | 553/568 | 0/100 | Bottom H support skeleton; Avoidance adjustment deferred |
| H13_mid | H13 | h_support | 15 | YZ | X | 0/15 | 150/418 | 884/984 | Mid H support skeleton; Zi conflict adjustment deferred; Moved below Zi conflict by Stage 2 H conflict adjustment |
| H24_mid | H24 | h_support | 15 | YZ | X | 585/600 | 150/418 | 884/984 | Mid H support skeleton; Zi conflict adjustment deferred; Moved below Zi conflict by Stage 2 H conflict adjustment |
| H34_mid | H34 | h_support | 15 | XZ | Y | 15/585 | 553/568 | 999/1099 | Mid H support skeleton; Zi conflict adjustment deferred; Moved above Zi conflict by Stage 2 H conflict adjustment |
| H13_top | H13 | h_support | 15 | YZ | X | 0/15 | 150/418 | 1900/2000 | Top H support skeleton; Top merge adjustment deferred |
| H24_top | H24 | h_support | 15 | YZ | X | 585/600 | 150/418 | 1900/2000 | Top H support skeleton; Top merge adjustment deferred |
| H34_top | H34 | h_support | 15 | XZ | Y | 15/585 | 553/568 | 1900/2000 | Top H support skeleton; Top merge adjustment deferred |
| VD_zone-3 | vertical_divider | vertical_divider | 15 | YZ | X | 292.5/307.5 | 0/568 | 999/1944 | Vertical divider skeleton; Tongue/groove features deferred; H34 clearance slot deferred; H34 clearance cutProfileVector implemented from effective placeholder cuts |

## 5. Features summary

| id | type | targetBoardId | related board ids | x0/x1 or x | y0/y1 or y | z0/z1 | face / position | notes |
|---|---|---|---|---|---|---|---|---|
| V1_boundary-zone-1-zone-2_zi_slot | zi_slot | V1 | boundary-zone-1-zone-2 | - | 518/568 | 668.5/684.5 | - | Rear Zi slot placeholder; exact side profile vector deferred |
| V2_boundary-zone-1-zone-2_zi_slot | zi_slot | V2 | boundary-zone-1-zone-2 | - | 518/568 | 668.5/684.5 | - | Rear Zi slot placeholder; exact side profile vector deferred |
| V3_boundary-zone-1-zone-2_zi_slot | zi_slot | V3 | boundary-zone-1-zone-2 | - | 518/568 | 668.5/684.5 | - | Rear Zi slot placeholder; exact side profile vector deferred |
| V4_boundary-zone-1-zone-2_zi_slot | zi_slot | V4 | boundary-zone-1-zone-2 | - | 518/568 | 668.5/684.5 | - | Rear Zi slot placeholder; exact side profile vector deferred |
| V1_boundary-zone-2-zone-3_zi_slot | zi_slot | V1 | boundary-zone-2-zone-3 | - | 518/568 | 983.5/999.5 | - | Rear Zi slot placeholder; exact side profile vector deferred |
| V2_boundary-zone-2-zone-3_zi_slot | zi_slot | V2 | boundary-zone-2-zone-3 | - | 518/568 | 983.5/999.5 | - | Rear Zi slot placeholder; exact side profile vector deferred |
| V3_boundary-zone-2-zone-3_zi_slot | zi_slot | V3 | boundary-zone-2-zone-3 | - | 518/568 | 983.5/999.5 | - | Rear Zi slot placeholder; exact side profile vector deferred |
| V4_boundary-zone-2-zone-3_zi_slot | zi_slot | V4 | boundary-zone-2-zone-3 | - | 518/568 | 983.5/999.5 | - | Rear Zi slot placeholder; exact side profile vector deferred |
| Zi2_VD_zone-3_bottom_zi_groove | zi_groove | Zi2 | divider=VD_zone-3, boundary-zone-2-zone-3 | 292/308 | 184.33333333333334/383.6666666666667 | - | bottom | Zi groove placeholder; exact groove cutting deferred; Through groove merge deferred |
| VD_zone-3_Zi2_VD_zone-3_bottom_zi_groove_top_divider_tongue | divider_tongue | VD_zone-3 | Zi2, groove=Zi2_VD_zone-3_bottom_zi_groove | - | 189.33333333333334/378.6666666666667 | 1937/1944 | top | Divider tongue placeholder generated from zi_groove; Exact tongue outline deferred; Zi groove real cutting deferred |
| VD_zone-3_H34_bottom_h34_clearance_slot | h34_clearance_slot | VD_zone-3 | H34_bottom | - | 552/568 | -5/105 | - | H34 clearance slot placeholder; Exact H34/divider interaction deferred |
| VD_zone-3_H34_mid_h34_clearance_slot | h34_clearance_slot | VD_zone-3 | H34_mid | - | 552/568 | 994/1104 | - | H34 clearance slot placeholder; Exact H34/divider interaction deferred |
| VD_zone-3_H34_top_h34_clearance_slot | h34_clearance_slot | VD_zone-3 | H34_top | - | 552/568 | 1895/2005 | - | H34 clearance slot placeholder; Exact H34/divider interaction deferred |
| T3_drill_hole_y100 | t3_drill_hole | T3 | - | x=300 | y=100 | - | through=true | T3 drill-hole placeholder; Exact drill pattern deferred |
| T3_drill_hole_y125 | t3_drill_hole | T3 | - | x=300 | y=125 | - | through=true | T3 drill-hole placeholder; Exact drill pattern deferred |
| B3_groove_placeholder | b3_groove | B3 | - | - | - | - | width=14.5, depth=6.5, branchCount=2, branchWidth=20 | B3 connected groove placeholder; Exact connected groove path deferred |
| B3_drill_hole_y92.5_x1 | b3_drill_hole | B3 | - | x=200 | y=92.5 | - | through=true | B3 drill-hole placeholder; Exact drill pattern deferred |
| B3_drill_hole_y92.5_x2 | b3_drill_hole | B3 | - | x=400 | y=92.5 | - | through=true | B3 drill-hole placeholder; Exact drill pattern deferred |
| B3_drill_hole_y103_x1 | b3_drill_hole | B3 | - | x=200 | y=103 | - | through=true | B3 drill-hole placeholder; Exact drill pattern deferred |
| B3_drill_hole_y103_x2 | b3_drill_hole | B3 | - | x=400 | y=103 | - | through=true | B3 drill-hole placeholder; Exact drill pattern deferred |
| B3_drill_hole_y140_x1 | b3_drill_hole | B3 | - | x=200 | y=140 | - | through=true | B3 drill-hole placeholder; Exact drill pattern deferred |
| B3_drill_hole_y140_x2 | b3_drill_hole | B3 | - | x=400 | y=140 | - | through=true | B3 drill-hole placeholder; Exact drill pattern deferred |

## 6. V board geometry deep dump

All four current V board `profileVector` and `cutProfileVector` values use the same current skeleton point sequence. V1/V2 differ only in X placement. V3/V4 have rear-board bounds (`y0=418`, `y1=568`) but their vectors still use the same full `0 -> MidDepth` skeleton; this is explicitly deferred.

### V1

Board bounds: `x0=0`, `x1=16`, `y0=0`, `y1=568`, `z0=0`, `z1=2000`  
Board Y range: `0 -> 568`  
Board Z range: `0 -> 2000`  
profilePlane: `YZ`  
boardType: `V1`

profileVector Y range: `0 -> 568`  
profileVector Z range: `0 -> 2000`

profileVector:

1. `{ y: 0, z: 0 }`
2. `{ y: 568, z: 0 }`
3. `{ y: 568, z: 2000 }`
4. `{ y: 0, z: 2000 }`
5. `{ y: 0, z: 0 }`

cutProfileVector Y range: `0 -> 568`  
cutProfileVector Z range: `0 -> 2000`

cutProfileVector:

1. `{ y: 0, z: 0 }`
2. `{ y: 568, z: 0 }`
3. `{ y: 568, z: 668.5 }`
4. `{ y: 518, z: 668.5 }`
5. `{ y: 518, z: 684.5 }`
6. `{ y: 568, z: 684.5 }`
7. `{ y: 568, z: 983.5 }`
8. `{ y: 518, z: 983.5 }`
9. `{ y: 518, z: 999.5 }`
10. `{ y: 568, z: 999.5 }`
11. `{ y: 568, z: 2000 }`
12. `{ y: 0, z: 2000 }`
13. `{ y: 0, z: 1960 }`
14. `{ y: 150, z: 1960 }`
15. `{ y: 150, z: 1944 }`
16. `{ y: 0, z: 1944 }`
17. `{ y: 0, z: 69 }`
18. `{ y: 150, z: 69 }`
19. `{ y: 150, z: 53 }`
20. `{ y: 0, z: 53 }`
21. `{ y: 0, z: 0 }`

profileFeatures:

- `style1_top_insert_slot`: `y0=0`, `y1=150`, `z0=1944`, `z1=1960`; notes: Exact top style side notch vector deferred.
- `style1_bottom_insert_slot`: `y0=0`, `y1=150`, `z0=53`, `z1=69`; notes: Exact bottom style side notch vector deferred.
- `zi_slot`: `y0=518`, `y1=568`, `z0=668.5`, `z1=684.5`, `boundaryId=boundary-zone-1-zone-2`, `boundaryType=full_zi`.
- `zi_slot`: `y0=518`, `y1=568`, `z0=983.5`, `z1=999.5`, `boundaryId=boundary-zone-2-zone-3`, `boundaryType=full_zi`.

### V2

Board bounds: `x0=584`, `x1=600`, `y0=0`, `y1=568`, `z0=0`, `z1=2000`  
Board Y range: `0 -> 568`  
Board Z range: `0 -> 2000`  
profilePlane: `YZ`  
boardType: `V2`

profileVector and cutProfileVector are identical to V1. profileFeatures are identical to V1, with target board `V2` in top-level features.

### V3

Board bounds: `x0=0`, `x1=16`, `y0=418`, `y1=568`, `z0=0`, `z1=2000`  
Board Y range: `418 -> 568`  
Board Z range: `0 -> 2000`  
profilePlane: `YZ`  
boardType: `V3`  
notes: `V3/V4 exact geometry deferred`; `Exact side profile cut vector deferred; profileFeatures contain slot/notch data`

profileVector Y range: `0 -> 568`  
profileVector Z range: `0 -> 2000`

profileVector:

1. `{ y: 0, z: 0 }`
2. `{ y: 568, z: 0 }`
3. `{ y: 568, z: 2000 }`
4. `{ y: 0, z: 2000 }`
5. `{ y: 0, z: 0 }`

cutProfileVector: identical to V1.  
profileFeatures: identical ranges to V1, with target board `V3` in top-level features.

### V4

Board bounds: `x0=584`, `x1=600`, `y0=418`, `y1=568`, `z0=0`, `z1=2000`  
Board Y range: `418 -> 568`  
Board Z range: `0 -> 2000`  
profilePlane: `YZ`  
boardType: `V4`  
notes: `V3/V4 exact geometry deferred`; `Exact side profile cut vector deferred; profileFeatures contain slot/notch data`

profileVector Y range: `0 -> 568`  
profileVector Z range: `0 -> 2000`

profileVector:

1. `{ y: 0, z: 0 }`
2. `{ y: 568, z: 0 }`
3. `{ y: 568, z: 2000 }`
4. `{ y: 0, z: 2000 }`
5. `{ y: 0, z: 0 }`

cutProfileVector: identical to V1.  
profileFeatures: identical ranges to V1, with target board `V4` in top-level features.

V board geometry audit note:

- Current vectors are skeletons.
- Current V1/V2 vector Y range is full `MidDepth = 568`, not the spec-local `0 -> 150` front stile range.
- Current rear Zi slots use `MidDepth - 50 -> MidDepth` (`518 -> 568`), not `100 -> 150`.
- Current front contour is mostly rectangular with two 16 mm-high Style 1 insert notches.

## 7. T/B board geometry dump

### T1

Board bounds: `x0=0`, `x1=600`, `y0=0`, `y1=16`, `z0=1960`, `z1=2000`  
profilePlane: `XZ`  
profileVector: none  
cutProfileVector: none  
related features: none  
notes: Style 1 top front rail.

### T2

Board bounds: `x0=0`, `x1=600`, `y0=16`, `y1=31`, `z0=1960`, `z1=2000`  
profilePlane: `XZ`  
profileVector: none  
cutProfileVector: none  
related features: none  
notes: Style 1 second top rail behind T1.

### T3

Board bounds: `x0=0`, `x1=600`, `y0=0`, `y1=150`, `z0=1944`, `z1=1960`  
profilePlane: `XY`  
cutProfileVector: none  
related features: `T3_drill_hole_y100`, `T3_drill_hole_y125`

profileVector:

1. `{ x: 16, y: 0 }`
2. `{ x: 16, y: 75 }`
3. `{ x: 0, y: 75 }`
4. `{ x: 0, y: 150 }`
5. `{ x: 600, y: 150 }`
6. `{ x: 600, y: 75 }`
7. `{ x: 584, y: 75 }`
8. `{ x: 584, y: 0 }`
9. `{ x: 16, y: 0 }`

Notes: exact notched XY `profileVector` implemented; drill/groove details deferred.

### B1

Board bounds: `x0=0`, `x1=600`, `y0=0`, `y1=16`, `z0=0`, `z1=53`  
profilePlane: `XZ`  
profileVector: none  
cutProfileVector: none  
related features: none  
notes: Style 1 bottom front rail.

### B2

Board bounds: `x0=0`, `x1=600`, `y0=16`, `y1=31`, `z0=0`, `z1=53`  
profilePlane: `XZ`  
profileVector: none  
cutProfileVector: none  
related features: none  
notes: Style 1 second bottom rail behind B1.

### B3

Board bounds: `x0=0`, `x1=600`, `y0=0`, `y1=150`, `z0=53`, `z1=69`  
profilePlane: `XY`  
cutProfileVector: none  
related features: `B3_groove_placeholder`, all `B3_drill_hole_*`

profileVector:

1. `{ x: 16, y: 0 }`
2. `{ x: 16, y: 75 }`
3. `{ x: 0, y: 75 }`
4. `{ x: 0, y: 150 }`
5. `{ x: 600, y: 150 }`
6. `{ x: 600, y: 75 }`
7. `{ x: 584, y: 75 }`
8. `{ x: 584, y: 0 }`
9. `{ x: 16, y: 0 }`

Notes: exact notched XY `profileVector` implemented; groove/drill details deferred.

## 8. Zi board geometry dump

### Zi1

boardType: `full_zi`  
boundary id: `boundary-zone-1-zone-2`  
related zones: `zone-1` to `zone-2`  
Board bounds: `x0=0`, `x1=600`, `y0=0`, `y1=568`, `z0=669`, `z1=684`  
profilePlane: `XY`

profileVector:

1. `{ x: 0, y: 0 }`
2. `{ x: 600, y: 0 }`
3. `{ x: 600, y: 568 }`
4. `{ x: 0, y: 568 }`
5. `{ x: 0, y: 0 }`

related zi_slot:

- V1/V2/V3/V4 slots at `y0=518`, `y1=568`, `z0=668.5`, `z1=684.5`, centerZ `676.5`.

related zi_groove: none  
related divider_tongue: none  
geometry status: full rectangle skeleton; exact production Zi outline is not cut into the vector.

### Zi2

boardType: `full_zi`  
boundary id: `boundary-zone-2-zone-3`  
related zones: `zone-2` to `zone-3`  
Board bounds: `x0=0`, `x1=600`, `y0=0`, `y1=568`, `z0=984`, `z1=999`  
profilePlane: `XY`

profileVector:

1. `{ x: 0, y: 0 }`
2. `{ x: 600, y: 0 }`
3. `{ x: 600, y: 568 }`
4. `{ x: 0, y: 568 }`
5. `{ x: 0, y: 0 }`

related zi_slot:

- V1/V2/V3/V4 slots at `y0=518`, `y1=568`, `z0=983.5`, `z1=999.5`, centerZ `991.5`.

related zi_groove:

- `Zi2_VD_zone-3_bottom_zi_groove`: `x0=292`, `x1=308`, `y0=184.33333333333334`, `y1=383.6666666666667`, `face=bottom`, `depth=7.5`.

related divider_tongue:

- `VD_zone-3_Zi2_VD_zone-3_bottom_zi_groove_top_divider_tongue`: target `VD_zone-3`, `position=top`, `y0=189.33333333333334`, `y1=378.6666666666667`, `z0=1937`, `z1=1944`, `insertionDepth=7`.

geometry status: full rectangle skeleton; real groove cutting and through-groove merge are deferred.

### half_zi

No `half_zi` board is present in this test case.

### shortened_zi

No `shortened_zi` board is present in this test case because avoidance is disabled.

## 9. H board geometry dump

Movement metadata is taken from `debug.mergeAndConflict.hZiConflicts` where available. Only the mid H boards moved in this test.

| board id | bounds x0/x1 | bounds y0/y1 | originalZ0/Z1 | finalZ0/Z1 | moved by H conflict logic | notes |
|---|---|---|---|---|---|---|
| H13_top | 0/15 | 150/418 | - | 1900/2000 | no | Top H support skeleton; Top merge adjustment deferred |
| H24_top | 585/600 | 150/418 | - | 1900/2000 | no | Top H support skeleton; Top merge adjustment deferred |
| H34_top | 15/585 | 553/568 | - | 1900/2000 | no | Top H support skeleton; Top merge adjustment deferred |
| H13_mid | 0/15 | 150/418 | 950/1050 | 884/984 | yes, below Zi2 | Mid H support skeleton; Zi conflict adjustment deferred; Moved below Zi conflict by Stage 2 H conflict adjustment |
| H24_mid | 585/600 | 150/418 | 950/1050 | 884/984 | yes, below Zi2 | Mid H support skeleton; Zi conflict adjustment deferred; Moved below Zi conflict by Stage 2 H conflict adjustment |
| H34_mid | 15/585 | 553/568 | 950/1050 | 999/1099 | yes, above Zi2 | Mid H support skeleton; Zi conflict adjustment deferred; Moved above Zi conflict by Stage 2 H conflict adjustment |
| H13_bottom | 0/15 | 150/418 | - | 0/100 | no | Bottom H support skeleton; Avoidance adjustment deferred |
| H24_bottom | 585/600 | 150/418 | - | 0/100 | no | Bottom H support skeleton; Avoidance adjustment deferred |
| H34_bottom | 15/585 | 553/568 | - | 0/100 | no | Bottom H support skeleton; Avoidance adjustment deferred |

H movement audit note:

- `H13_mid` and `H24_mid` originally overlapped Zi2 (`984 -> 999`) and moved below it to `884 -> 984`.
- `H34_mid` originally overlapped Zi2 and moved above it to `999 -> 1099`.
- H34 clearance slot generation follows the moved `H34_mid` final position.

## 10. Vertical divider geometry dump

Vertical divider exists.

Board id: `VD_zone-3`  
Board bounds: `x0=292.5`, `x1=307.5`, `y0=0`, `y1=568`, `z0=999`, `z1=1944`  
profilePlane: `YZ`  
materialThickness: `15`

profileVector:

1. `{ y: 0, z: 999 }`
2. `{ y: 568, z: 999 }`
3. `{ y: 568, z: 1944 }`
4. `{ y: 0, z: 1944 }`
5. `{ y: 0, z: 999 }`

cutProfileVector:

1. `{ y: 0, z: 999 }`
2. `{ y: 568, z: 999 }`
3. `{ y: 568, z: 999 }`
4. `{ y: 552, z: 999 }`
5. `{ y: 552, z: 1104 }`
6. `{ y: 568, z: 1104 }`
7. `{ y: 568, z: 1895 }`
8. `{ y: 552, z: 1895 }`
9. `{ y: 552, z: 1944 }`
10. `{ y: 568, z: 1944 }`
11. `{ y: 568, z: 1944 }`
12. `{ y: 0, z: 1944 }`
13. `{ y: 0, z: 999 }`

profileFeatures:

- `h34_clearance_slot`: `y0=552`, `y1=568`, `z0=999`, `z1=1104`, `h34BoardId=H34_mid`; clamped effective H34 clearance cut on vertical divider.
- `h34_clearance_slot`: `y0=552`, `y1=568`, `z0=1895`, `z1=1944`, `h34BoardId=H34_top`; clamped effective H34 clearance cut on vertical divider.

Related `h34_clearance_slot` top-level features:

| h34BoardId | placeholder z0/z1 | effective cut z0/z1 | intersects divider range `999 -> 1944` | result |
|---|---|---|---|---|
| H34_bottom | -5/105 | none | no | skipped, warning emitted |
| H34_mid | 994/1104 | 999/1104 | yes | copied into divider `profileFeatures` and `cutProfileVector` |
| H34_top | 1895/2005 | 1895/1944 | yes | copied into divider `profileFeatures` and `cutProfileVector` |

Related `zi_groove`:

- `Zi2_VD_zone-3_bottom_zi_groove`: groove placeholder on `Zi2`, `face=bottom`; real groove cutting deferred.

Related `divider_tongue`:

- `VD_zone-3_Zi2_VD_zone-3_bottom_zi_groove_top_divider_tongue`: `position=top`, `y0=189.33333333333334`, `y1=378.6666666666667`, `z0=1937`, `z1=1944`; exact tongue outline deferred.

Vertical divider audit note:

- `cutProfileVector` follows moved `H34_mid`.
- The top-level H34 placeholder slots remain original placeholders; only intersecting effective cuts are copied into the divider board.
- Duplicate consecutive points exist at `{ y: 568, z: 999 }` and `{ y: 568, z: 1944 }`; these are harmless for current skeleton data but should be considered before DXF/CNC cleanup.

## 11. Debug / conflict data

`debug.mergeAndConflict`:

```json
{
  "topMergeCandidate": false,
  "bottomMergeCandidate": false,
  "depthGap": 358,
  "topBottomHSystemOverlapExpected": true,
  "hZiConflicts": [
    {
      "hBoardId": "H13_mid",
      "hBoardType": "H13",
      "ziBoardId": "Zi2",
      "ziBoardType": "full_zi",
      "overlapZ0": 984,
      "overlapZ1": 999,
      "action": "movement_applied",
      "moved": true,
      "originalZ0": 950,
      "originalZ1": 1050,
      "newZ0": 884,
      "newZ1": 984,
      "movementDirection": "below"
    },
    {
      "hBoardId": "H24_mid",
      "hBoardType": "H24",
      "ziBoardId": "Zi2",
      "ziBoardType": "full_zi",
      "overlapZ0": 984,
      "overlapZ1": 999,
      "action": "movement_applied",
      "moved": true,
      "originalZ0": 950,
      "originalZ1": 1050,
      "newZ0": 884,
      "newZ1": 984,
      "movementDirection": "below"
    },
    {
      "hBoardId": "H34_mid",
      "hBoardType": "H34",
      "ziBoardId": "Zi2",
      "ziBoardType": "full_zi",
      "overlapZ0": 984,
      "overlapZ1": 999,
      "action": "movement_applied",
      "moved": true,
      "originalZ0": 950,
      "originalZ1": 1050,
      "newZ0": 999,
      "newZ1": 1099,
      "movementDirection": "above"
    }
  ]
}
```

Validation / warnings:

```json
[
  "H mid overlaps full_zi; Stage 2 movement evaluated. H13_mid overlaps Zi2.",
  "H mid overlaps full_zi; Stage 2 movement evaluated. H24_mid overlaps Zi2.",
  "H mid overlaps full_zi; Stage 2 movement evaluated. H34_mid overlaps Zi2.",
  "H34 clearance slot extends outside divider Z range: VD_zone-3 / H34_bottom.",
  "H34 clearance slot extends outside divider Z range: VD_zone-3 / H34_mid.",
  "H34 clearance slot extends outside divider Z range: VD_zone-3 / H34_top.",
  "H34 clearance slot has no intersection with divider Z range; cut skipped: VD_zone-3 / H34_bottom."
]
```

## 12. Known deferred geometry

| item | current status | affects preview? | affects Fusion body? | affects DXF/CNC? | blocker before Fusion body? |
|---|---|---|---|---|---|
| V1/V2 real side profile | Current vector is skeleton rectangle + slot notches; real stepped contour not implemented | Yes | Yes | Yes | Yes, if Fusion body should reflect production side profile |
| V3/V4 exact geometry | Explicitly deferred; current vector reuses full skeleton | Yes | Yes | Yes | Yes for production rear stiles |
| half_zi exact profile | No half_zi in this test; checkpoint says exact profile deferred | Potentially | Yes when present | Yes | Yes when half_zi is in a Fusion body |
| Style 2 structural boards | Not relevant to this Style 1 case; exact Style 2 beyond fixed front panel deferred | Yes for Style 2 cases | Yes | Yes | Yes for Style 2 production geometry |
| Real top/bottom merge | Merge detection exists; `TopMergedBoard` / `BottomMergedBoard` generation deferred | Maybe | Yes when depth gap requires merge | Yes | Yes when merge candidate is true |
| H avoidance adjustment | Deferred | Maybe | Yes with avoidance enabled | Yes | Yes for avoidance-enabled production |
| V rear avoidance cutout | Deferred | Yes with avoidance enabled | Yes | Yes | Yes for avoidance-enabled production |
| T3/B3 drill/groove cutting | Placeholder features only; T3/B3 outline vector implemented | Maybe | Yes for holes/grooves | Yes | Yes for production body/CNC details |
| Zi groove real cutting | Placeholder only | Maybe | Yes | Yes | Yes for production body/CNC details |
| Divider tongue real outline | Placeholder only | Maybe | Yes | Yes | Yes for production body/CNC details |
| H34/divider dogbone/router compensation | Deferred | No/low | Possibly | Yes | No for rough Fusion body; yes before CNC |
| Dogbone/router compensation in general | Deferred | No/low | Possibly | Yes | No for rough Fusion body; yes before CNC |
| DXF/toolpath | Deferred | No | No | Yes | No for Fusion body; yes before manufacturing |
| Front panel / hardware V2 | Deferred by scope | Yes for full cabinet preview | Yes | Yes | No for structural-only V1 body |

## 13. Geometry risk checklist

| check | status | evidence / notes |
|---|---|---|
| V1/V2 vector Y range uses local `0 -> 150` or full `MidDepth`? | WARNING | Current V1/V2 vectors use `0 -> 568` full `MidDepth`, not local `0 -> 150`. |
| V1/V2 rear Zi slots use `Y 100 -> 150` or `MidDepth - 50 -> MidDepth`? | WARNING | Current slots use `518 -> 568`. |
| V1/V2 front contour is stepped or mostly rectangle? | WARNING | Mostly rectangle; only 16 mm-high Style 1 insert notches at `53 -> 69` and `1944 -> 1960`. |
| V3/V4 exact geometry implemented or placeholder? | WARNING | Explicit note: `V3/V4 exact geometry deferred`; vector skeleton still uses `0 -> 568`. |
| T3/B3 profileVector uses correct notched shape? | PASS | Both have implemented 9-point notched XY profile using side notch width 16, front notch depth 75, depth 150. |
| Zi board profileVector is exact or placeholder? | WARNING | Current full_zi vectors are bounding rectangles; exact production profile/groove cuts deferred. |
| H mid movement final positions make sense? | PASS | H13/H24 moved below Zi2 to `884 -> 984`; H34 moved above Zi2 to `999 -> 1099`. |
| H34 clearance follows moved H34? | PASS | H34_mid clearance placeholder uses moved H34 range `994 -> 1104`; effective divider cut is `999 -> 1104`. |
| vertical_divider cutProfileVector matches H34 slots? | PASS | Effective cuts exist for H34_mid and H34_top; H34_bottom is skipped as non-intersecting. |
| board bbox and profileVector coordinate systems are clearly separated? | WARNING | V3/V4 board bounds are rear-local `418 -> 568`, while profile vectors use `0 -> 568`; this is skeleton behavior and may confuse reviewers. |
| UI preview should be marked skeleton or production-ready? | WARNING | Should be marked skeleton until V side production contours are implemented. |

## 14. Final audit notes

Files inspected:

- `docs/general-tall-cabinet-v1-implementation-checkpoint.md`
- `docs/general-tall-cabinet-v1-math-spec.md`
- `modules/generalTallCabinet/types.ts`
- `modules/generalTallCabinet/generator.ts` was exercised through its public generator output for this package.

Commands run:

```powershell
node --input-type=module -e "import { generateGeneralTallCabinet } from './modules/generalTallCabinet/generator.ts'; /* generated JSON snapshot for the test input */"
node "modules/generalTallCabinet/boundaryResolver.test.ts"; node "modules/generalTallCabinet/stackingCalculator.test.ts"; node "modules/generalTallCabinet/generator.test.ts"; node "modules/generalTallCabinet/generalTallCabinet.regression.test.ts"
```

Test results:

- General Tall Cabinet tests passed:
  - `boundaryResolver.test.ts`
  - `stackingCalculator.test.ts`
  - `generator.test.ts`
  - `generalTallCabinet.regression.test.ts`
- Generated result for this package:
  - boards count: 22
  - features count: 22
  - validation errors: 0
  - warnings: 7
  - calculated height difference: 0

Linter errors:

- No TypeScript/UI/Fridge code was edited for this package.
- No linter errors were observed from this markdown-only generation step.

Environment limitations:

- This audit package is based on the Node generator output in the current workspace.
- No Fusion 360 body generation, DXF export, nesting, router compensation, dogbone pass, or Fridge Cabinet Generator execution was performed.
- This file is an audit artifact, not an implementation change.
