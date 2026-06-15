# General Tall Cabinet Generator V1 — Mathematical Rules Spec

Version: V1 structural generator only  
Height model: functional zone heights are clear-space heights; generated boundary panels count toward CH  
Scope: General Tall Cabinet only. Fridge Cabinet is a separate generator and is not covered here.

---

## 0. V1 Scope

V1 generates the structural cabinet body only.

### V1 generates

- V1 / V2 / V3 / V4 vertical structural boards
- Top System
- Bottom System
- Rear top system: T4 / T5 where applicable
- Rear bottom system: B4 / B5 or H34 bottom where applicable
- Zi panels: full / half / shortened
- H supports: H13 / H24 / H34
- Vertical divider and its grooves/clearance slots
- Blank Panel H12 support rails
- Avoidance geometry
- Merge rules
- Basic validation

### V1 does not generate

- Side door panels
- Double door panels
- Drawer fronts
- Flap fronts
- Blank front panels
- Drawer boxes
- Hinge holes
- Lock cutouts
- Drawer slide holes
- Nesting
- Toolpath

### Exception

Style 2 top/bottom fixed front panels may be generated because they belong to the top/bottom structural system, not to normal functional-zone doors.

---

## 1. Coordinate System

Global cabinet coordinates:

```text
X = left → right
Y = front → rear
Z = bottom → top
units = mm
```

Core local coordinates use the same axis directions.

```text
CW = CabinetWidth
CH = CabinetHeight
CD = CabinetDepth
PT = PanelThickness
DPT = DoorPanelThickness
SC = SideClearance
FFA = FrontFaceAllowance = 16
```

Core depth:

```text
MidDepth = CD - FFA
```

Core width:

```text
MidWidth = CW - LeftSidePanelThickness - RightSidePanelThickness
```

All main structural core boards use `MidWidth` and `MidDepth`, not full `CW` / `CD`.

Global Y mapping:

```text
globalY = FFA + coreLocalY
```

Side panels may use full `CD`; core boards use `MidDepth`.

---

## 2. Core Board Families

### 2.1 Front vertical boards: V1 / V2

V1 / V2 are front structural vertical boards.

```text
profilePlane = YZ
thicknessAxis = X
Y span = 0 → 150
Z span = depends on top/bottom system and avoidance/merge rules
```

Assembly X:

```text
V1: X = 0 → PT
V2: X = MidWidth - PT → MidWidth
```

Assembly Y:

```text
core local Y = 0 → 150
global Y = FFA → FFA + 150
```

### 2.2 Rear vertical boards: V3 / V4

V3 / V4 are rear structural vertical boards.

```text
profilePlane = YZ
thicknessAxis = X
Y span = 0 → 150 in local V3/V4 profile
```

Assembly X:

```text
V3: X = 0 → PT
V4: X = MidWidth - PT → MidWidth
```

Assembly Y:

```text
core local Y = MidDepth - 150 → MidDepth
global Y = CD - 150 → CD
```

### 2.3 Side Panels

Side panels are optional and external to the core width.

```text
LeftSidePanelThickness = 0 / 15 / 16
RightSidePanelThickness = 0 / 15 / 16
```

Side panel geometry:

```text
profilePlane = YZ
Y span = 0 → CD
Z span = 0 → CH
thicknessAxis = X
```

If avoidance is enabled and side panel does not ignore avoidance, cut rear-lower corner:

```text
Y = CD - AvoidD → CD
Z = 0 → AvoidTopZ
```

---

## 3. Top / Bottom System Rules

Top and bottom systems are cabinet-level structural systems. They are not functional zones.

### 3.1 Style 1

Style 1 is a notched hinge-carrier style.

Style 1 height is not an empty clearance. The 40 mm / 53 mm values are front rail / step heights, not the complete top/bottom system heights.

Minimum front rail heights:

```text
Top Style 1 minimum height = 40
Bottom Style 1 minimum height = 53
```

These are minimum values, not locked fixed values. The selected Style 1 front rail / step height clamps the user value to the minimum. The complete top/bottom system height also includes the 16 mm insert slot thickness.

Top Style 1:

```text
TopStyle1FrontRailHeight = max(userTopStyle1FrontRailHeight, 40)
TopStyle1InsertSlotThickness = 16
TopSystemHeight = TopStyle1FrontRailHeight + TopStyle1InsertSlotThickness
default TopSystemHeight = 40 + 16 = 56
```

Top Style 1 Z ranges:

```text
total top system:
Z = CH - TopSystemHeight → CH

front rail / top step:
Z = CH - TopStyle1FrontRailHeight → CH

T3 insert slot zone:
Z = CH - TopSystemHeight → CH - TopStyle1FrontRailHeight
```

Bottom Style 1:

```text
BottomStyle1FrontRailHeight = max(userBottomStyle1FrontRailHeight, 53)
BottomStyle1InsertSlotThickness = 16
BottomSystemHeight = BottomStyle1FrontRailHeight + BottomStyle1InsertSlotThickness
default BottomSystemHeight = 53 + 16 = 69
```

Bottom Style 1 Z ranges:

```text
total bottom system:
Z = 0 → BottomSystemHeight

front rail / bottom step:
Z = 0 → BottomStyle1FrontRailHeight

B3 insert slot zone:
Z = BottomStyle1FrontRailHeight → BottomSystemHeight
```

Functional zone net height calculation must subtract the full selected `TopSystemHeight` and `BottomSystemHeight`, not only the front rail / step heights:

```text
FunctionalZoneHeightsTotal =
CH
- TopSystemHeight
- BottomSystemHeight
- sum(GeneratedBoundaryPanelThicknesses)
```

For default Style 1:

```text
FunctionalZoneHeightsTotal =
CH - 56 - 69 - sum(ZiThicknesses)
```

Extra height increases the Style 1 front rail / step height from the original 40 / 53 side.

V1/V2/V3/V4 notch / step height follows the selected Style 1 front rail / step height:

```text
Top notch height = TopStyle1FrontRailHeight
Bottom notch height = BottomStyle1FrontRailHeight
```

Validation uses the computed selected heights. User-entered values below the minimum are clamped by `max(...)`.

### 3.2 Style 2

Style 2 is a cabinet-level fixed blank / plain fixing system.

It is not a normal functional-zone blank panel.

Top Style 2:

```text
TopStyle2Height >= 60
TopStyle2Zone Z = CH - TopStyle2Height → CH
uses TH1 behind it
no H12
```

Bottom Style 2:

```text
BottomStyle2Height >= 60
BottomStyle2Zone Z = 0 → BottomStyle2Height
uses BH1 behind it
no H12
```

Style 2 fixed front panel may be generated in V1 because it belongs to the top/bottom structural system. It is not a `blank_panel`, side door panel, drawer front, flap front, blank front panel, or normal functional-zone door panel. It does not generate H12 and does not generate hardware holes.

Top Style 2 fixed front panel geometry:

```text
X0 = SideClearance
X1 = MidWidth - SideClearance

Y0 = 0
Y1 = DoorPanelThickness

Z0 = CH - TopStyle2Height
Z1 = CH
```

Bottom Style 2 fixed front panel geometry:

```text
X0 = SideClearance
X1 = MidWidth - SideClearance

Y0 = 0
Y1 = DoorPanelThickness

Z0 = 0
Z1 = BottomStyle2Height
```

Validation:

```text
if TopStyle2Height < 60: error
if BottomStyle2Height < 60: error
```

### 3.3 Merge Rule

If front and rear horizontal end systems are too close in depth, merge horizontal boards.

```text
frontEndDepth = 105
rearEndDepth = 105
minimumGap = 50

gap = MidDepth - frontEndDepth - rearEndDepth

if gap < 50:
  merge front/rear horizontal boards
```

Top merge:

```text
TH1 + T4 → TopMergedBoard
T5 remains
V1/V2/V3/V4 are treated as 16mm shorter at top
```

Bottom merge:

```text
BH1 + B4 → BottomMergedBoard
B5 remains
V1/V2/V3/V4 are treated as 16mm shorter at bottom
```

Merged board geometry:

```text
profilePlane = XY
X = 0 → MidWidth
Y = 0 → MidDepth
thickness = ZiThickness (15 by default) along Z
```

TopMergedBoard:

```text
Z = CH - 16 → CH - 1
```

BottomMergedBoard:

```text
Z = 0 → 15
```

---

## 4. Functional Zone Types

General Tall Cabinet V1 supports these functional zone types:

```text
side_door
double_door
drawer
open_space
open_appliance
top_flap
bottom_flap
blank_panel
```

V1 keeps `frontMode` / `zoneType` for structural calculation and future V2 front-panel generation, but V1 does not generate functional-zone front panels.

Functional zone heights are clear-space heights. They do not include generated boundary panel thickness. Boundary panels generated between functional zones are physical boards and must be counted separately in total cabinet height.

---

## 5. Boundary Resolver

A boundary exists between two adjacent zones:

```text
boundary = resolveBoundary(aboveZone, belowZone)
```

Boundary types:

```text
none
full_zi
half_zi
shortened_zi
```

Top System / Bottom System are not normal zones.

### 5.1 Boundary Panel Thickness and Z Stacking

The boundary resolver first outputs only:

```text
none
full_zi
half_zi
```

Avoidance adjustment is a later stage. It may transform an eligible `full_zi` into `shortened_zi` when rear avoidance shortens the usable depth. A `shortened_zi` remains a physical Zi panel and keeps the same thickness contribution to cabinet height.

Boundary panel thickness:

```text
ZiThickness = 15 by default
full_zi thickness = ZiThickness
half_zi thickness = ZiThickness
shortened_zi thickness = ZiThickness
none boundary thickness = 0
```

Functional zone heights are clear-space heights. Generated boundary panels are physical boards and must be included in the cabinet height calculation.

Total height formula:

```text
CH = TopSystemHeight
   + BottomSystemHeight
   + sum(FunctionalZoneHeights)
   + sum(GeneratedBoundaryPanelThicknesses)
```

Equivalent functional-zone net height budget:

```text
FunctionalZoneHeightsTotal =
CH - TopSystemHeight - BottomSystemHeight - sum(GeneratedBoundaryPanelThicknesses)
```

For Style 1:

```text
TopStyle1FrontRailHeight = max(userTopStyle1FrontRailHeight, 40)
BottomStyle1FrontRailHeight = max(userBottomStyle1FrontRailHeight, 53)
TopSystemHeight = TopStyle1FrontRailHeight + 16
BottomSystemHeight = BottomStyle1FrontRailHeight + 16
```

Z stacking is built from bottom to top:

```text
Bottom System
→ Zone
→ Boundary Panel Thickness if any
→ Zone
→ Boundary Panel Thickness if any
→ Top System
```

For each generated Zi / half Zi / shortened Zi boundary panel:

```text
ZiZ0 = currentZ
ZiZ1 = currentZ + ZiThickness
ZiCenterZ = ZiZ0 + ZiThickness / 2
```

V1/V2/V3/V4 slot placement uses `ZiCenterZ`, not a zone edge:

```text
slotZ0 = ZiCenterZ - 8
slotZ1 = ZiCenterZ + 8
```

---

## 6. Global Boundary Rules

### 6.1 Top System to first zone

```text
TopSystem → first functional zone = none
```

No extra Zi is generated under the Top System.

### 6.2 Last zone to Bottom System

```text
last functional zone → BottomSystem = none
```

No extra Zi is generated above the Bottom System.

### 6.3 Blank Panel above any zone

If `aboveZone = blank_panel`:

```text
blank_panel → any functional zone = none
```

This includes:

```text
Blank → Side Door = none
Blank → Double Door = none
Blank → Drawer = none
Blank → Open Space = none
Blank → Appliance = none
Blank → Bottom Flap = none
Blank → Blank = none
```

### 6.4 Any zone above Blank Panel

If `belowZone = blank_panel`, follow the above zone's bottom rule.

Typical results:

```text
Side Door → Blank = full_zi
Double Door → Blank = full_zi
Drawer → Blank = full_zi
Open Space → Blank = full_zi
Open Appliance → Blank = full_zi
Top Flap → Blank = full_zi
Bottom Flap → Blank = full_zi
Blank → Blank = none
```

---

## 7. Zone-Specific Boundary Rules

### 7.1 Side Door

```text
side_door.topRequirement = none
side_door.bottomRequirement = full_zi
```

Examples:

```text
Blank → Side Door = none
Side Door → Blank = full_zi
Side Door → Side Door = full_zi
Side Door → Open Space = full_zi
```

### 7.2 Double Door

```text
double_door.topRequirement = none
double_door.bottomRequirement = full_zi
```

If `double_door.verticalDivider = true`, upper/lower boundaries that support the divider must be full Zi unless the divider interfaces directly with a top/bottom system. If the interface is a Zi, use full Zi and cut grooves.

Double-door vertical divider boundary upgrade algorithm:

```text
if double_door.verticalDivider = true:
```

Upper boundary:

```text
if upper neighbor is top_system:
  do not generate extra Zi; handled by top system interface
else:
  force upper boundary to full_zi
```

Lower boundary:

```text
if lower neighbor is bottom_system:
  do not generate extra Zi; handled by bottom system interface
else:
  force lower boundary to full_zi
```

Upgrade rules:

```text
none -> full_zi
half_zi -> full_zi
full_zi -> full_zi
top_system interface -> no extra Zi
bottom_system interface -> no extra Zi
```

Reason: the vertical divider inside a double door zone needs full-depth upper/lower structural support unless the adjacent top/bottom system already provides the interface.

### 7.3 Drawer

Each drawer is one functional zone. There is no drawer-stack zone in V1.

```text
Drawer → Drawer = half_zi
Drawer → non-drawer = full_zi
```

Drawer top boundary depends on the above zone.

Examples:

```text
Blank → Drawer = none
Drawer → Drawer = half_zi
Drawer → Open Space = full_zi
Drawer → Side Door = full_zi
Drawer → Appliance = full_zi
Drawer → Blank = full_zi
Drawer → Bottom System = none
```

Drawer box panels are deferred to V2.

Drawer slide depth validation:

```text
drawerDepth = selectedSlideLength
selectedSlideLength <= availableDrawerDepth
```

If avoidance is enabled:

```text
availableDrawerDepth = ShortDepth
ShortDepth = MidDepth - AvoidD
```

Slide side clearance and drawer box construction are deferred.

### 7.4 Open Space

```text
open_space.topRequirement = none
open_space.bottomRequirement = full_zi
```

Examples:

```text
Blank → Open Space = none
Open Space → Blank = full_zi
Open Space → Side Door = full_zi
Open Space → Drawer = full_zi
Open Space → Bottom System = none
```

### 7.5 Open Appliance

Generic appliance bay only. Fridge-specific width/V5/cutout logic is not part of General Tall.

```text
open_appliance.topRequirement = none
open_appliance.bottomRequirement = full_zi
```

Examples:

```text
Blank → Appliance = none
Appliance → Blank = full_zi
Appliance → Open Space = full_zi
Appliance → Bottom System = none
```

### 7.6 Top Flap

Top flap is only allowed as the first functional zone below Top System.

```text
TopSystem → TopFlap = none
TopFlap → next zone = full_zi
```

Top flap hinge is at the top and opens upward.

Validation:

```text
if top_flap is not first functional zone: error
```

### 7.7 Bottom Flap

Bottom flap is only allowed as the last functional zone above Bottom System.

```text
previous zone → BottomFlap = resolved by previous zone bottom rule
Blank → BottomFlap = none
BottomFlap → BottomSystem = none
```

Bottom flap hinge is at the bottom and opens downward.

Validation:

```text
if bottom_flap is not last functional zone: error
```

### 7.8 Blank Panel

Blank Panel does not generate Zi.

V1 Blank Panel generates H12 only. The front fixed panel is deferred to V2.

Blank Panel rules:

```text
blank_panel.topRequirement = none
blank_panel.bottomRequirement = none
if blank_panel is above any zone: boundary = none
if blank_panel is below a zone: follow above zone bottom rule
```

---

## 8. Boundary Result Matrix

| Above Zone | Below Zone | Expected Boundary | Reason |
|---|---|---|---|
| Top System | Any | none | Top system already provides cabinet top structure |
| Any | Bottom System | none | Bottom system already provides cabinet bottom structure |
| Blank | Any | none | Blank above does not force lower top boundary |
| Side Door | Blank | full_zi | Door bottom requires full Zi |
| Double Door | Blank | full_zi | Door bottom requires full Zi |
| Drawer | Blank | full_zi | Drawer to non-drawer requires full Zi |
| Open Space | Blank | full_zi | Open space bottom requires full Zi |
| Open Appliance | Blank | full_zi | Appliance bottom requires full Zi |
| Drawer | Drawer | half_zi | Drawer-to-drawer support |
| Drawer | Open Space | full_zi | Drawer to non-drawer |
| Drawer | Side Door | full_zi | Drawer to non-drawer |
| Side Door | Side Door | full_zi | Upper door bottom requires full Zi |
| Open Space | Side Door | full_zi | Open space bottom requires full Zi |
| Blank | Drawer | none | Blank above overrides to none |
| Blank | Open Space | none | Blank above overrides to none |
| Blank | Appliance | none | Blank above overrides to none |
| Top Flap | Any next zone | full_zi | Top flap bottom requires full Zi |
| Blank | Bottom Flap | none | Blank above overrides to none |
| Any non-blank | Bottom Flap | follows above bottom rule | Bottom flap top does not force Zi |

---

## 9. Zi Panel Rules

### 9.1 Full Zi

Full Zi spans the core depth and is a physical boundary panel between clear-space functional zones.

```text
profilePlane = XY
thickness = ZiThickness (15 by default) along Z
X span = 0 → MidWidth
Y span = 0 → MidDepth
```

Full Zi inserts into V1/V2 and V3/V4. Its Z range is assigned during bottom-to-top stacking:

```text
ZiZ0 = currentZ
ZiZ1 = currentZ + ZiThickness
ZiCenterZ = ZiZ0 + ZiThickness / 2
```

V1/V2 slot:

```text
Y = 100 → 150
Z = ZiCenterZ - 8 → ZiCenterZ + 8
```

V3/V4 slot:

```text
Y = 0 → 50
Z = ZiCenterZ - 8 → ZiCenterZ + 8
```

Full Zi outline vector:

```text
[
  (15, 0),
  (15, 105),
  (0, 105),
  (0, MidDepth - 105),
  (15, MidDepth - 105),
  (15, MidDepth),

  (MidWidth - 15, MidDepth),
  (MidWidth - 15, MidDepth - 105),
  (MidWidth, MidDepth - 105),
  (MidWidth, 105),
  (MidWidth - 15, 105),
  (MidWidth - 15, 0),

  (15, 0)
]
```

### 9.2 Half Zi

Half Zi is mainly for drawer-to-drawer support. It is a physical boundary panel between clear-space functional zones and has `ZiThickness` (15 by default).

```text
profilePlane = XY
thickness = ZiThickness (15 by default) along Z
Y depth = 150
```

Half Zi inserts into V1/V2 only. Its Z range is assigned during bottom-to-top stacking:

```text
ZiZ0 = currentZ
ZiZ1 = currentZ + ZiThickness
ZiCenterZ = ZiZ0 + ZiThickness / 2
```

V1/V2 slot:

```text
Y = 100 → 150
Z = ZiCenterZ - 8 → ZiCenterZ + 8
```

Half Zi outline vector:

```text
[
  (15, 0),
  (MidWidth - 15, 0),
  (MidWidth - 15, 105),
  (MidWidth, 105),
  (MidWidth, 150),
  (0, 150),
  (0, 105),
  (15, 105),
  (15, 0)
]
```

### 9.3 Shortened Zi

Boundary resolver must never output `shortened_zi` directly. Boundary resolver outputs only:

```text
none
full_zi
half_zi
```

`shortened_zi` is produced only in the avoidance adjustment stage.

Only `full_zi` can become `shortened_zi`.

```text
half_zi cannot become shortened_zi
none cannot become shortened_zi
```

A `full_zi` is eligible to become `shortened_zi` only if:

```text
1. boundary = full_zi
2. avoidance is enabled
3. the Zi is in an avoidance-affected position
4. the Zi is not part of Top System or Bottom System
5. the Zi is not required as support for double_door.verticalDivider
```

Do not shorten:

```text
double_door vertical divider upper/lower support Zi
Top System / Bottom System structural boards
Style 1 / Style 2 structural boards
half_zi
H boards
```

Shortened Zi geometry:

```text
ShortDepth = MidDepth - AvoidD
Y range = 0 → ShortDepth
```

Shortened full Zi keeps front connection but does not reach V3/V4. Only Y depth changes. Thickness remains `ZiThickness` (15 by default) and still counts toward `CH`.

Its Z range is assigned during bottom-to-top stacking:

```text
ZiZ0 = currentZ
ZiZ1 = currentZ + ZiThickness
ZiCenterZ = ZiZ0 + ZiThickness / 2
```

Outline vector:

```text
[
  (15, 0),
  (15, 105),
  (0, 105),
  (0, ShortDepth),

  (MidWidth, ShortDepth),
  (MidWidth, 105),
  (MidWidth - 15, 105),
  (MidWidth - 15, 0),

  (15, 0)
]
```

---

## 10. Blank Panel H12

Blank Panel does not generate Zi and does not generate a front panel in V1.

It generates H12 support rails behind the future blank front panel.

H12 geometry:

```text
profilePlane = XZ
thicknessAxis = Y
X = PT → MidWidth - PT
Y = 0 → 15
```

Global Y:

```text
globalY = FFA → FFA + 15
```

Let:

```text
BlankHeight = blankZ1 - blankZ0
```

If:

```text
BlankHeight < 300
```

Generate one full-height H12:

```text
H12 Z = blankZ0 → blankZ1
```

If:

```text
BlankHeight >= 300
```

Generate two H12 rails:

```text
H12_bottom Z = blankZ0 → blankZ0 + 100
H12_top    Z = blankZ1 - 100 → blankZ1
```

No hinge / lock / fixing hole logic in V1.

---

## 11. H Support Rules

### 11.1 H13 / H24

H13 / H24 connect front and rear vertical boards along the side.

```text
H13/H24 length = MidDepth - 300
H13/H24 height = 100
thickness = 15
```

Positions:

```text
H13:
X = 0 → 15
Y = 150 → MidDepth - 150

H24:
X = MidWidth - 15 → MidWidth
Y = 150 → MidDepth - 150
```

Top:

```text
if no top merge:
  Z = CH - 100 → CH
if top merge:
  Z = CH - 116 → CH - 16
```

Bottom:

```text
if no avoidance:
  Z = 0 → 100
if avoidance:
  H13/H24 are shortened in Y to avoid rear avoidance region
```

If avoidance:

```text
ShortDepth = MidDepth - AvoidD
H13/H24 shortened Y = 150 → ShortDepth
```

Mid:

```text
H_mid.z0 = CH / 2 - 50
H_mid.z1 = CH / 2 + 50
```

If H13/H24 mid conflicts with full Zi:

```text
move H13/H24 mid below the full Zi
```

### 11.2 H34

H34 is rear left-right connector.

```text
profilePlane = XZ
thicknessAxis = Y
height = 100
Y = MidDepth - 15 → MidDepth
X = 15 → MidWidth - 15
```

H34 does not split around vertical divider.

If H34 intersects vertical divider, cut a clearance slot in the divider:

```text
Y = MidDepth - 16 → MidDepth
Z = H34.z0 - 5 → H34.z0 + 105
slot size = 16 × 110
```

H34 mid default height can match H13/H24 mid, but may move independently.

If H34 conflicts with full Zi:

```text
move H34 above the full Zi
```

H34 bottom:

```text
if no avoidance:
  H34_bottom.z0 = baseZi.topZ
  H34_bottom.z1 = baseZi.topZ + 100

if avoidance:
  H34_bottom.z0 = AvoidTopZ
  H34_bottom.z1 = AvoidTopZ + 100
```

---

## 12. Vertical Divider Rules

Vertical divider is optional, mainly used in double-door vertical divider mode.

```text
DividerThickness = 15
GrooveWidth = 16
TongueInsert = 7
GrooveDepth = 7.5
```

Default X:

```text
DividerCenterX = MidWidth / 2
```

Custom X allowed later.

When divider inserts into full Zi:

```text
EffectiveDepth = MidDepth
TongueY0 = MidDepth / 3
TongueY1 = MidDepth * 2 / 3
```

Groove on lower Zi top face / upper Zi bottom face:

```text
GrooveX0 = DividerCenterX - 8
GrooveX1 = DividerCenterX + 8
GrooveY0 = TongueY0 - 5
GrooveY1 = TongueY1 + 5
GrooveDepth = 7.5
```

If a Zi has divider grooves from both top and bottom, cut through:

```text
through groove depth = ZiThickness
```

If using shortened Zi:

```text
ShortDepth = MidDepth - AvoidD
ShortTongueY0 = ShortDepth / 3
ShortTongueY1 = ShortDepth * 2 / 3
GrooveY0 = ShortTongueY0 - 5
GrooveY1 = ShortTongueY1 + 5
```

H34 clearance slot in vertical divider:

```text
Y = MidDepth - 16 → MidDepth
Z = H34.z0 - 5 → H34.z0 + 105
```

---

## 13. Avoidance Rules

Avoidance is a cabinet-level rear-lower cutout/clearance.

```text
AvoidD = avoidance depth from rear forward
AvoidTopZ = avoidance top height
ShortDepth = MidDepth - AvoidD
```

Side panels may cut rear-lower corner:

```text
Y = CD - AvoidD → CD
Z = 0 → AvoidTopZ
```

V3/V4 lower rear area may be removed if avoidance overlaps rear vertical board:

```text
Y = 0 → 150
Z = 0 → AvoidTopZ
```

Drawer validation under avoidance:

```text
selectedSlideLength <= ShortDepth
```

Open shelf and side door do not add special rules beyond the cabinet avoidance geometry.

---

## 14. Validation Rules

Basic V1 validation should include:

### Cabinet dimensions

```text
CW > 0
CH > 0
CD > FFA
MidWidth > 0
MidDepth > 300 recommended for H13/H24
```

### Top / Bottom style

```text
TopStyle1FrontRailHeight = max(userTopStyle1FrontRailHeight, 40) if top style = Style 1
TopSystemHeight = TopStyle1FrontRailHeight + 16 if top style = Style 1
BottomStyle1FrontRailHeight = max(userBottomStyle1FrontRailHeight, 53) if bottom style = Style 1
BottomSystemHeight = BottomStyle1FrontRailHeight + 16 if bottom style = Style 1
TopStyle2Height >= 60 if top style = Style 2
BottomStyle2Height >= 60 if bottom style = Style 2
```

### Zone height

Functional zone heights are clear-space heights. Generated boundary panels (`full_zi`, `half_zi`, `shortened_zi`) have physical thickness and must be counted in `CH`.

```text
CH = TopSystemHeight
   + BottomSystemHeight
   + sum(FunctionalZoneHeights)
   + sum(GeneratedBoundaryPanelThicknesses)
```

```text
full_zi boundary thickness = ZiThickness
half_zi boundary thickness = ZiThickness
shortened_zi boundary thickness = ZiThickness
none boundary thickness = 0
```

Z stacking must be validated from bottom to top:

```text
Bottom System
→ Zone
→ Boundary Panel Thickness if any
→ Zone
→ Boundary Panel Thickness if any
→ Top System
```

Warn/error if mismatch.

### Flap placement

```text
top_flap must be first functional zone
bottom_flap must be last functional zone
```

### Boundary generation

Check every adjacent pair resolves to a valid initial boundary type:

```text
none / full_zi / half_zi
```

Avoidance adjustment may later transform eligible `full_zi` boundaries into:

```text
shortened_zi
```

The transformed `shortened_zi` still has `ZiThickness` and still counts toward `CH`.

Eligibility:

```text
only full_zi can become shortened_zi
half_zi cannot become shortened_zi
none cannot become shortened_zi
do not shorten double_door vertical divider support Zi
do not shorten Top/Bottom System, Style 1, Style 2, or H boards
```

### Blank Panel

```text
Blank panel generates H12 only
if BlankHeight < 300: one H12
if BlankHeight >= 300: two H12 rails
```

### Drawer

```text
Drawer box generation deferred
if slide preset exists and avoidance enabled:
  selectedSlideLength <= ShortDepth
```

### Vertical divider

If double-door vertical divider is enabled:

```text
force upper boundary to full_zi unless upper neighbor is top_system
force lower boundary to full_zi unless lower neighbor is bottom_system
ensure Zi grooves if Zi exists
ensure H34 clearance slot if H34 intersects divider
```

### H34

```text
H34 does not split
vertical divider receives 16 × 110 clearance slot
```

---

## 15. Implementation Notes for Cursor

### Recommended files

```text
modules/generalTallCabinet/
  types.ts
  defaults.ts
  boundaryResolver.ts
  generator.ts
  validation.ts
  h12.ts
  ziRules.ts
  hSupportRules.ts
  dividerRules.ts
```

### Boundary resolver pseudocode

```ts
function resolveBoundary(above: ZoneLike, below: ZoneLike): BoundaryType {
  if (above.type === 'top_system') return 'none';
  if (below.type === 'bottom_system') return 'none';

  if (above.type === 'blank_panel') return 'none';

  if (above.type === 'drawer' && below.type === 'drawer') return 'half_zi';

  if (above.type === 'top_flap') return 'full_zi';

  if (above.type === 'side_door') return 'full_zi';
  if (above.type === 'double_door') return 'full_zi';
  if (above.type === 'drawer') return 'full_zi';
  if (above.type === 'open_space') return 'full_zi';
  if (above.type === 'open_appliance') return 'full_zi';
  if (above.type === 'bottom_flap') return 'full_zi';

  return 'none';
}
```

Note: this pseudocode reflects confirmed directional rules. It intentionally outputs only `none`, `full_zi`, and `half_zi`. Double-door vertical divider upgrade runs after boundary resolution and may force a non-system upper/lower boundary to `full_zi`. Avoidance adjustment runs after that and may transform an eligible `full_zi` into `shortened_zi`; the transformed panel still has `ZiThickness` and still counts toward `CH`. Adjust only if future rules override it.

---

## 16. Open Questions

No blocking open questions for V1 structural implementation based on the current decisions.

---

## 17. V2 Deferred Features

These are intentionally not part of V1:

- Functional-zone door panels
- Double door front panels
- Drawer fronts
- Flap fronts
- Blank front panels
- Hinge cup holes
- Push lock cutouts
- Lock receiver holes
- Drawer slide holes
- Drawer box construction
- Edge banding automation
- Nesting
- Toolpath / post-processing

The V1 data model should preserve zone type and front mode so V2 can add these later without rewriting the structural generator.
