const assert = require("assert");
const {
  buildPureParams,
  buildBoardPlan,
  auditBoardMetadata,
  buildAssemblyPlacementPlan,
  deriveWidthModel,
  cabinetWidthFromFridge,
  fridgeWidthFromCabinet,
  formatBoardPlacementSummary,
  getV12Profile,
  getV34Profile,
  dumpBoardVector,
  verifyVSeriesVectors,
  pointExists,
} = require("../fridge_logic");

function baseUi(overrides = {}) {
  const exteriorSide = overrides.exteriorSide || "left";
  const fridgeWidth = overrides.fridgeWidth || 550;
  const wheelAvoidance = overrides.wheelAvoidance || {
    enabled: true,
    height: 200,
    depth: 300,
  };
  return {
    cabinet: {
      width: cabinetWidthFromFridge(fridgeWidth, exteriorSide),
      depth: 600,
      height: 2100,
      panelThickness: 15,
      exteriorSide,
    },
    fridge: {
      width: fridgeWidth,
      depth: 580,
      height: overrides.fridgeHeight || 1500,
    },
    clearances: {
      top: 40,
      bottom: 53,
    },
    wheelAvoidance,
    stack: overrides.stack,
  };
}

function pickPanel(panel) {
  return {
    id: panel.id,
    z0: panel.z0,
    z1: panel.z1,
    centerZ: panel.centerZ,
    lowerType: panel.lowerType,
    upperType: panel.upperType,
    role: panel.role,
    shape: panel.shape,
    requiresHSet: panel.requiresHSet,
  };
}

function assertPanels(actual, expected) {
  assert.deepStrictEqual(actual.map(pickPanel), expected);
}

function assertZi(actual, expected) {
  assert.deepStrictEqual(actual, expected);
}

function assertHPlanes(actual, expected) {
  assert.strictEqual(actual.length, expected.length, `hPlanes length ${actual.length} vs ${expected.length}`);
  for (const exp of expected) {
    const act = actual.find((h) => h.id === exp.id);
    assert(act, `missing hPlane ${exp.id}`);
    for (const k of Object.keys(exp)) {
      assert.deepStrictEqual(act[k], exp[k], `${exp.id}.${String(k)}`);
    }
  }
}

function boardIds(boardPlan) {
  return boardPlan.boards.map((b) => b.id);
}

function hasPoint2D(vec, x, y, eps) {
  const e = eps != null ? eps : 1e-6;
  return vec.some((p) => Math.abs(p[0] - x) < e && Math.abs(p[1] - y) < e);
}

function testA() {
  const params = buildPureParams(baseUi({
    stack: [
      { id: "s1", type: "flap", height: 195 },
      { id: "s2", type: "drawer", height: 250 },
      { id: "s3", type: "fridge", height: 1500 },
    ],
  }));
  const boardPlan = buildBoardPlan(params);
  const ids = boardIds(boardPlan);
  assert.strictEqual(boardPlan.validation.ok, true);
  assert.strictEqual(boardPlan.boards.length, 29);
  assert.strictEqual(boardPlan.boards.filter((b) => b.series === "H").length, 11);
  assert.strictEqual(boardPlan.hSetGroups && boardPlan.hSetGroups.length, 4);
  const wm = boardPlan.widthModel;
  assert(wm && wm.hasSidePanel === true);
  assert.strictEqual(wm.cabinetWidth, 611);
  assert.strictEqual(wm.panelSystemWidth, 595);
  assert.strictEqual(wm.panelSystemOriginX, 16);
  assert.strictEqual(wm.sidePanelThickness, 16);
  const b1 = boardPlan.boards.find((b) => b.id === "B1");
  assert(b1 && Math.abs(Math.max(...b1.outerVector.map((p) => p[0])) - 595) < 1e-6);
  const h13p2 = boardPlan.boards.find((b) => b.id === "HSet_P2_H13");
  const h34p2 = boardPlan.boards.find((b) => b.id === "HSet_P2_H34");
  assert(h13p2 && h13p2.profilePlane === "YZ");
  assert(Math.abs(Math.max(...h13p2.outerVector.map((p) => p[0])) - 300) < 1e-6);
  assert(Math.abs(Math.max(...h13p2.outerVector.map((p) => p[1])) - 100) < 1e-6);
  assert(h34p2 && h34p2.profilePlane === "XZ");
  assert(Math.abs(Math.max(...h34p2.outerVector.map((p) => p[0])) - 565) < 1e-6);
  assert(Math.abs(Math.max(...h34p2.outerVector.map((p) => p[1])) - 100) < 1e-6);
  const sp = boardPlan.boards.find((b) => b.id === "SidePanel");
  assert(sp && sp.series === "S" && sp.profilePlane === "YZ");
  ["T1", "T2", "T3", "T4", "T5", "B1", "B2", "B3", "SidePanel", "AvoidanceFront", "AvoidanceTop", "V5", "V1", "V2", "V3", "V4"].forEach((id) => {
    assert(ids.includes(id), `missing board ${id}`);
  });
  assert.strictEqual(boardPlan.boards.filter((b) => b.series === "Zi").length, 2);
  assert.strictEqual(boardPlan.boards.filter((b) => b.type === "blank_panel").length, 0);
  assert(boardPlan.boards.some((b) => b.id === "HSet_bottom_H13" && b.type === "h13"));
  assert(boardPlan.boards.some((b) => b.id === "HSet_mid_H13" && b.type === "h13"));
  assert(boardPlan.boards.some((b) => b.id === "HSet_P2_H13" && b.type === "h13"));
  assert(boardPlan.boards.some((b) => b.id === "HSet_P2_H24" && b.type === "h24"));
  assert(boardPlan.boards.some((b) => b.id === "HSet_top_H13" && b.type === "h13"));
  assert(boardPlan.boards.some((b) => b.id === "HSet_top_H24" && b.type === "h24"));
  assert(!boardPlan.boards.some((b) => b.id === "HSet_top_H34"));
  const hTop13 = boardPlan.boards.find((b) => b.id === "HSet_top_H13");
  assert(hTop13 && hTop13.profilePlane === "YZ");
  assert(Math.abs(Math.max(...hTop13.outerVector.map((p) => p[0])) - 300) < 1e-6);
  assert(boardPlan.boards.every((b) => typeof formatBoardPlacementSummary(b.placement) === "string"));

  assert.strictEqual(params.layout.totalStackHeight, 2100);
  assertPanels(params.layout.panels, [
    { id: "P0", z0: 53, z1: 69, centerZ: 61, lowerType: "bottomClearance", upperType: "flap", role: "bottom_boundary", shape: "bottom_system", requiresHSet: false },
    { id: "P1", z0: 264, z1: 279, centerZ: 271.5, lowerType: "flap", upperType: "drawer", role: "flap_top", shape: "half", requiresHSet: false },
    { id: "P2", z0: 529, z1: 544, centerZ: 536.5, lowerType: "drawer", upperType: "fridge", role: "fridge_base", shape: "full", requiresHSet: true },
    { id: "P3", z0: 2044, z1: 2060, centerZ: 2052, lowerType: "fridge", upperType: "topClearance", role: "top_boundary", shape: "top_system", requiresHSet: false },
  ]);
  assertZi(params.layout.ziList, [
    { id: "Z1", panelId: "P1", centerZ: 271.5, z0: 264, z1: 279, role: "flap_top", shape: "half", requiresHSet: false },
    { id: "Z2", panelId: "P2", centerZ: 536.5, z0: 529, z1: 544, role: "fridge_base", shape: "full", requiresHSet: true },
  ]);
  assert.strictEqual(params.avoidance.fridgeBaseBottomZ, 529);
  assert.strictEqual(params.avoidance.fridgeGap, 329);
  assert.strictEqual(params.avoidance.finalMode, "normal");
  assert.strictEqual(params.avoidance.finalTopZ, 200);
  assert.strictEqual(params.avoidance.finalFrontBoardHeight, 185);
  assertHPlanes(params.layout.hPlanes, [
    {
      id: "HSet_bottom",
      sourcePanelId: null,
      sourceRole: "bottom_structure",
      z0: 200,
      z1: 300,
      mode: "bottom_band",
      members: ["H13", "H24", "H34"],
    },
    {
      id: "HSet_mid",
      sourcePanelId: null,
      sourceRole: "mid_gap",
      z0: 1214.5,
      z1: 1314.5,
      mode: "structural_mid_gap",
      members: ["H13", "H24", "H34"],
    },
    {
      id: "HSet_P2",
      sourcePanelId: "P2",
      sourceRole: "fridge_base",
      z0: 429,
      z1: 529,
      mode: "below_panel",
      members: ["H13", "H24", "H34"],
    },
    {
      id: "HSet_top",
      sourcePanelId: null,
      sourceRole: "top_side_connectors",
      z0: 2000,
      z1: 2100,
      mode: "top_band",
      members: ["H13", "H24"],
      role: "h_top",
      reasons: ["top_side_connectors"],
    },
  ]);
  assert.strictEqual(params.validation.ok, true);
  assert.deepStrictEqual(params.validation.errors, []);
  assert(params.validation.infos.includes("Fridge/avoidance gap >= 105 mm: below-fridge HSet will be used."));
}

function testB() {
  const params = buildPureParams(baseUi({
    stack: [
      { id: "s1", type: "drawer", height: 250 },
      { id: "s2", type: "flap", height: 195 },
      { id: "s3", type: "fridge", height: 1500 },
    ],
  }));
  assert.strictEqual(params.layout.totalStackHeight, 2100);
  assertPanels(params.layout.panels, [
    { id: "P0", z0: 53, z1: 69, centerZ: 61, lowerType: "bottomClearance", upperType: "drawer", role: "bottom_boundary", shape: "bottom_system", requiresHSet: false },
    { id: "P1", z0: 319, z1: 334, centerZ: 326.5, lowerType: "drawer", upperType: "flap", role: "flap_bottom", shape: "full", requiresHSet: true },
    { id: "P2", z0: 529, z1: 544, centerZ: 536.5, lowerType: "flap", upperType: "fridge", role: "fridge_base", shape: "full", requiresHSet: true },
    { id: "P3", z0: 2044, z1: 2060, centerZ: 2052, lowerType: "fridge", upperType: "topClearance", role: "top_boundary", shape: "top_system", requiresHSet: false },
  ]);
  assertZi(params.layout.ziList, [
    { id: "Z1", panelId: "P1", centerZ: 326.5, z0: 319, z1: 334, role: "flap_bottom", shape: "full", requiresHSet: true },
    { id: "Z2", panelId: "P2", centerZ: 536.5, z0: 529, z1: 544, role: "fridge_base", shape: "full", requiresHSet: true },
  ]);
  assertHPlanes(params.layout.hPlanes, [
    {
      id: "HSet_bottom",
      sourcePanelId: null,
      sourceRole: "bottom_structure",
      z0: 200,
      z1: 300,
      mode: "bottom_band",
      members: ["H13", "H24", "H34"],
    },
    { id: "HSet_P1", sourcePanelId: "P1", sourceRole: "flap_bottom", z0: 219, z1: 319, mode: "below_panel", members: ["H13", "H24", "H34"] },
    {
      id: "HSet_mid",
      sourcePanelId: null,
      sourceRole: "mid_gap",
      z0: 1214.5,
      z1: 1314.5,
      mode: "structural_mid_gap",
      members: ["H13", "H24", "H34"],
    },
    { id: "HSet_P2", sourcePanelId: "P2", sourceRole: "fridge_base", z0: 429, z1: 529, mode: "below_panel", members: ["H13", "H24", "H34"] },
    {
      id: "HSet_top",
      sourcePanelId: null,
      sourceRole: "top_side_connectors",
      z0: 2000,
      z1: 2100,
      mode: "top_band",
      members: ["H13", "H24"],
      role: "h_top",
      reasons: ["top_side_connectors"],
    },
  ]);
  assert.strictEqual(params.avoidance.fridgeBaseBottomZ, 529);
  assert.strictEqual(params.avoidance.fridgeGap, 329);
  assert.strictEqual(params.avoidance.finalMode, "normal");
  assert.strictEqual(params.validation.ok, true);
  assert.deepStrictEqual(params.validation.errors, []);
}

function testC() {
  const params = buildPureParams(baseUi({
    stack: [
      { id: "s1", type: "fridge", height: 1500 },
      { id: "s2", type: "flap", height: 195 },
      { id: "s3", type: "drawer", height: 250 },
    ],
  }));
  assert.strictEqual(params.layout.totalStackHeight, 2100);
  assertPanels(params.layout.panels, [
    { id: "P0", z0: 53, z1: 69, centerZ: 61, lowerType: "bottomClearance", upperType: "fridge", role: "bottom_boundary", shape: "bottom_system", requiresHSet: false },
    { id: "P1", z0: 1569, z1: 1584, centerZ: 1576.5, lowerType: "fridge", upperType: "flap", role: "fridge_top", shape: "full", requiresHSet: true },
    { id: "P2", z0: 1779, z1: 1794, centerZ: 1786.5, lowerType: "flap", upperType: "drawer", role: "flap_top", shape: "half", requiresHSet: false },
    { id: "P3", z0: 2044, z1: 2060, centerZ: 2052, lowerType: "drawer", upperType: "topClearance", role: "top_boundary", shape: "top_system", requiresHSet: false },
  ]);
  assertZi(params.layout.ziList, [
    { id: "Z1", panelId: "P1", centerZ: 1576.5, z0: 1569, z1: 1584, role: "fridge_top", shape: "full", requiresHSet: true },
    { id: "Z2", panelId: "P2", centerZ: 1786.5, z0: 1779, z1: 1794, role: "flap_top", shape: "half", requiresHSet: false },
  ]);
  assert.strictEqual(params.avoidance.finalMode, "none");
  assert.strictEqual(params.avoidance.fridgeBaseBottomZ, 0);
  assert.strictEqual(params.avoidance.fridgeGap, 0);
  assert.strictEqual(params.validation.ok, false);
  assert(params.validation.errors.includes("No fridge_base panel found."));
}

function testD() {
  const params = buildPureParams(baseUi({
    stack: [
      { id: "s1", type: "drawer", height: 250 },
      { id: "s2", type: "flap", height: 165 },
      { id: "s3", type: "empty", height: 25 },
      { id: "s4", type: "fridge", height: 1490 },
    ],
  }));
  assert.strictEqual(params.layout.totalStackHeight, 2100);
  assertPanels(params.layout.panels, [
    { id: "P0", z0: 53, z1: 69, centerZ: 61, lowerType: "bottomClearance", upperType: "drawer", role: "bottom_boundary", shape: "bottom_system", requiresHSet: false },
    { id: "P1", z0: 319, z1: 334, centerZ: 326.5, lowerType: "drawer", upperType: "flap", role: "flap_bottom", shape: "full", requiresHSet: true },
    { id: "P2", z0: 499, z1: 514, centerZ: 506.5, lowerType: "flap", upperType: "blankPanel", role: "flap_top", shape: "half", requiresHSet: false },
    { id: "P3", z0: 539, z1: 554, centerZ: 546.5, lowerType: "blankPanel", upperType: "fridge", role: "fridge_base", shape: "full", requiresHSet: true },
    { id: "P4", z0: 2044, z1: 2060, centerZ: 2052, lowerType: "fridge", upperType: "topClearance", role: "top_boundary", shape: "top_system", requiresHSet: false },
  ]);
  assertZi(params.layout.ziList, [
    { id: "Z1", panelId: "P1", centerZ: 326.5, z0: 319, z1: 334, role: "flap_bottom", shape: "full", requiresHSet: true },
    { id: "Z2", panelId: "P2", centerZ: 506.5, z0: 499, z1: 514, role: "flap_top", shape: "half", requiresHSet: false },
    { id: "Z3", panelId: "P3", centerZ: 546.5, z0: 539, z1: 554, role: "fridge_base", shape: "full", requiresHSet: true },
  ]);
  assertHPlanes(params.layout.hPlanes, [
    {
      id: "HSet_bottom",
      sourcePanelId: null,
      sourceRole: "bottom_structure",
      z0: 200,
      z1: 300,
      mode: "bottom_band",
      members: ["H13", "H24", "H34"],
    },
    { id: "HSet_P1", sourcePanelId: "P1", sourceRole: "flap_bottom", z0: 219, z1: 319, mode: "below_panel", members: ["H13", "H24", "H34"] },
    {
      id: "HSet_mid",
      sourcePanelId: null,
      sourceRole: "mid_gap",
      z0: 1219.5,
      z1: 1319.5,
      mode: "structural_mid_gap",
      members: ["H13", "H24", "H34"],
    },
    { id: "HSet_P3", sourcePanelId: "P3", sourceRole: "fridge_base", z0: 439, z1: 539, mode: "below_panel", members: ["H13", "H24", "H34"] },
    {
      id: "HSet_top",
      sourcePanelId: null,
      sourceRole: "top_side_connectors",
      z0: 2000,
      z1: 2100,
      mode: "top_band",
      members: ["H13", "H24"],
      role: "h_top",
      reasons: ["top_side_connectors"],
    },
  ]);
  assert.strictEqual(params.avoidance.fridgeBaseBottomZ, 539);
  assert.strictEqual(params.avoidance.fridgeGap, 339);
  assert.strictEqual(params.avoidance.finalMode, "normal");
  assert.strictEqual(params.validation.ok, true);
  assert.deepStrictEqual(params.validation.errors, []);
}

function testH() {
  const params = buildPureParams(baseUi({
    stack: [
      { id: "s1", type: "drawer", height: 250 },
      { id: "s2", type: "blankPanel", height: 25 },
      { id: "s3", type: "flap", height: 180 },
      { id: "s4", type: "fridge", height: 1475 },
    ],
  }));
  const boardPlan = buildBoardPlan(params);
  const blankBoard = boardPlan.boards.find((b) => b.id === "BlankPanel_s2");
  assert(blankBoard);
  assert.strictEqual(blankBoard.type, "blank_panel");
  assert.strictEqual(blankBoard.thickness, 16);
  assert.strictEqual(blankBoard.placement.widthX, 550);
  assert.strictEqual(blankBoard.placement.heightZ, 25);
  assert.deepStrictEqual(blankBoard.source, { sectionId: "s2", sectionType: "blankPanel" });

  assert.strictEqual(params.layout.sections[1].type, "blankPanel");
  assert.strictEqual(params.layout.sections[1].height, 25);
  assertPanels(params.layout.panels.slice(1, 4), [
    { id: "P1", z0: 319, z1: 334, centerZ: 326.5, lowerType: "drawer", upperType: "blankPanel", role: "generic_separator", shape: "half", requiresHSet: false },
    { id: "P2", z0: 359, z1: 374, centerZ: 366.5, lowerType: "blankPanel", upperType: "flap", role: "flap_bottom", shape: "full", requiresHSet: true },
    { id: "P3", z0: 554, z1: 569, centerZ: 561.5, lowerType: "flap", upperType: "fridge", role: "fridge_base", shape: "full", requiresHSet: true },
  ]);
  assert.strictEqual(params.layout.ziList[0].role, "generic_separator");
  assert.strictEqual(params.layout.ziList[1].role, "flap_bottom");
  assert.strictEqual(params.layout.ziList[2].role, "fridge_base");
}

function testE() {
  const params = buildPureParams(baseUi({
    fridgeHeight: 1875,
    wheelAvoidance: { enabled: true, height: 120, depth: 300 },
    stack: [
      { id: "s1", type: "flap", height: 85 },
      { id: "s2", type: "fridge", height: 1875 },
    ],
  }));
  assert.strictEqual(params.layout.totalStackHeight, 2100);
  assertPanels(params.layout.panels, [
    { id: "P0", z0: 53, z1: 69, centerZ: 61, lowerType: "bottomClearance", upperType: "flap", role: "bottom_boundary", shape: "bottom_system", requiresHSet: false },
    { id: "P1", z0: 154, z1: 169, centerZ: 161.5, lowerType: "flap", upperType: "fridge", role: "fridge_base", shape: "full", requiresHSet: true },
    { id: "P2", z0: 2044, z1: 2060, centerZ: 2052, lowerType: "fridge", upperType: "topClearance", role: "top_boundary", shape: "top_system", requiresHSet: false },
  ]);
  assert.strictEqual(params.avoidance.fridgeBaseBottomZ, 154);
  assert.strictEqual(params.avoidance.fridgeGap, 34);
  assert.strictEqual(params.avoidance.finalMode, "raised");
  assert.strictEqual(params.avoidance.finalTopZ, 154);
  assert.strictEqual(params.avoidance.finalFrontBoardHeight, 139);
  assertZi(params.layout.ziList, [
    { id: "Z1", panelId: "P1", centerZ: 161.5, z0: 154, z1: 169, role: "fridge_base", shape: "full", requiresHSet: true },
  ]);
  assertHPlanes(params.layout.hPlanes, [
    { id: "HSet_P1", sourcePanelId: "P1", sourceRole: "fridge_base", z0: 169, z1: 269, mode: "above_panel", members: ["H13", "H24", "H34"] },
    {
      id: "HSet_mid",
      sourcePanelId: null,
      sourceRole: "mid_gap",
      z0: 1084.5,
      z1: 1184.5,
      mode: "structural_mid_gap",
      members: ["H13", "H24", "H34"],
    },
    {
      id: "HSet_top",
      sourcePanelId: null,
      sourceRole: "top_side_connectors",
      z0: 2000,
      z1: 2100,
      mode: "top_band",
      members: ["H13", "H24"],
      role: "h_top",
      reasons: ["top_side_connectors"],
    },
  ]);
  assert.strictEqual(params.validation.ok, true);
  assert.deepStrictEqual(params.validation.errors, []);
  assert(params.validation.infos.includes("Fridge/avoidance gap < 105 mm: raised avoidance mode and above-fridge HSet will be used."));
}

function testF() {
  const params = buildPureParams(baseUi({
    fridgeHeight: 1875,
    wheelAvoidance: { enabled: true, height: 140, depth: 300 },
    stack: [
      { id: "s1", type: "flap", height: 85 },
      { id: "s2", type: "fridge", height: 1875 },
    ],
  }));
  assert.strictEqual(params.validation.ok, false);
  assert(params.validation.errors.includes("Fridge base panel bottom must be >= Avoidance Height + panel thickness."));
}

function testG() {
  const params = buildPureParams(baseUi({
    exteriorSide: "none",
    stack: [
      { id: "s1", type: "flap", height: 195 },
      { id: "s2", type: "drawer", height: 250 },
      { id: "s3", type: "fridge", height: 1500 },
    ],
  }));
  const boardPlan = buildBoardPlan(params);
  const ids = boardIds(boardPlan);
  assert.strictEqual(params.base.Cw, 595);
  assert.strictEqual(params.base.Cd, 600);
  assert.strictEqual(params.base.FCh, 2100);
  assert.strictEqual(params.base.Pt, 15);
  assert.strictEqual(params.base.exteriorSide, "none");
  assert.strictEqual(params.base.hasSidePanel, false);
  assert.strictEqual(params.base.sidePanelSide, "none");
  assert.strictEqual(params.base.hasV5, true);
  assert.strictEqual(params.base.v5Side, "left");
  assert.strictEqual(params.base.fridgeW, 550);
  assert.strictEqual(params.base.fridgeD, 580);
  assert.strictEqual(params.base.fridgeH, 1500);
  assert.strictEqual(params.layout.ziList[1].shape, "full");
  assert(ids.includes("V5"), "V5 is emitted when stack includes fridge (side optional)");
  assert(!ids.includes("SidePanel"));
  const wm = params.base.widthModel;
  assert(wm && wm.hasSidePanel === false);
  assert.strictEqual(wm.panelSystemWidth, wm.cabinetWidth);
  assert(ids.includes("AvoidanceFront") && ids.includes("AvoidanceTop"));
  assert(ids.includes("V1") && ids.includes("V2") && ids.includes("V3") && ids.includes("V4"));
  const apG = buildAssemblyPlacementPlan(params, boardPlan);
  assert(apG.placements.V5 && apG.placements.V5.originMm);
  assert.strictEqual(apG.placements.V5.originMm.x, 15);
  assert.strictEqual(apG.placements.V5.originMm.y, 0);
  assert.strictEqual(apG.placements.V5.originMm.z, 544);
}

function testWidthModelRightSidePanelPlacement() {
  const ui = baseUi({
    exteriorSide: "right",
    stack: [
      { id: "s1", type: "flap", height: 195 },
      { id: "s2", type: "drawer", height: 250 },
      { id: "s3", type: "fridge", height: 1500 },
    ],
  });
  const wm = deriveWidthModel(ui);
  assert.strictEqual(wm.panelSystemOriginX, 0);
  assert.strictEqual(wm.panelSystemWidth, 595);
  assert.strictEqual(wm.cabinetWidth, 611);
  const params = buildPureParams(ui);
  const bp = buildBoardPlan(params);
  assert(bp.boards.some((b) => b.id === "SidePanel"));
  const ap = buildAssemblyPlacementPlan(params, bp);
  assert.strictEqual(ap.placements.SidePanel.originMm.x, 611 - 16);
  assert.strictEqual(ap.placements.V1.originMm.x, 0);
  assert.strictEqual(ap.placements.V2.originMm.x, 595 - 15);
  assert.deepStrictEqual(ap.placements.V5.originMm, { x: 15, y: 0, z: 544 });
}

function testWidthAndDepthValidation() {
  assert.strictEqual(cabinetWidthFromFridge(550, "right"), 611);
  assert.strictEqual(fridgeWidthFromCabinet(611, "right"), 550);
  assert.strictEqual(cabinetWidthFromFridge(550, "none"), 595);
  assert.strictEqual(fridgeWidthFromCabinet(595, "none"), 550);

  const ui = baseUi({
    stack: [
      { id: "s1", type: "flap", height: 195 },
      { id: "s2", type: "drawer", height: 250 },
      { id: "s3", type: "fridge", height: 1500 },
    ],
  });
  ui.fridge.depth = 585;
  const params = buildPureParams(ui);
  assert.strictEqual(params.validation.ok, false);
  assert(params.validation.errors.includes("Cabinet depth minus panel thickness must be greater than fridge depth."));
}

function testBoardPlanInvalidPure() {
  const params = buildPureParams(baseUi({
    stack: [
      { id: "s1", type: "fridge", height: 1500 },
      { id: "s2", type: "flap", height: 195 },
      { id: "s3", type: "drawer", height: 250 },
    ],
  }));
  assert.strictEqual(params.validation.ok, false);
  const boardPlan = buildBoardPlan(params);
  assert.strictEqual(boardPlan.validation.ok, false);
  assert(boardPlan.validation.errors.length > 0);
  const ids = boardIds(boardPlan);
  assert(ids.includes("T1") && ids.includes("B1"));
  assert(boardPlan.boards.length >= 21);
}

function testBoardPlanCoreBoards() {
  const params = buildPureParams(baseUi({
    stack: [
      { id: "s1", type: "flap", height: 195 },
      { id: "s2", type: "drawer", height: 250 },
      { id: "s3", type: "fridge", height: 1500 },
    ],
  }));
  assert.strictEqual(params.validation.ok, true);
  const boardPlan = buildBoardPlan(params);
  const ids = boardIds(boardPlan);
  ["T1", "T2", "T3", "T4", "T5", "B1", "B2", "B3", "SidePanel", "AvoidanceFront", "AvoidanceTop", "V1", "V2", "V3", "V4"].forEach((id) => {
    assert(ids.includes(id), `BoardPlanCoreBoards missing ${id}`);
  });
  assert(ids.some((id) => id.endsWith("_H13") && id.indexOf("HSet_") === 0));
  assert(ids.some((id) => id.endsWith("_H24")));
  assert(ids.some((id) => id.endsWith("_H34")));
  assert(ids.includes("V5"));
}

function testBoardPlanVSeriesExists() {
  const params = buildPureParams(baseUi({
    stack: [
      { id: "s1", type: "flap", height: 195 },
      { id: "s2", type: "drawer", height: 250 },
      { id: "s3", type: "fridge", height: 1500 },
    ],
  }));
  assert.strictEqual(params.validation.ok, true);
  const ids = boardIds(buildBoardPlan(params));
  ["V1", "V2", "V3", "V4"].forEach((id) => assert(ids.includes(id), `missing ${id}`));
}

function testV12IncludesAllZiSlots() {
  const params = buildPureParams(baseUi({
    stack: [
      { id: "s1", type: "flap", height: 195 },
      { id: "s2", type: "drawer", height: 250 },
      { id: "s3", type: "fridge", height: 1500 },
    ],
  }));
  const v1 = buildBoardPlan(params).boards.find((b) => b.id === "V1");
  assert(v1);
  const ov = v1.outerVector;
  assert(hasPoint2D(ov, 100, 271.5 - 8));
  assert(hasPoint2D(ov, 100, 271.5 + 8));
  assert(hasPoint2D(ov, 100, 536.5 - 8));
  assert(hasPoint2D(ov, 100, 536.5 + 8));
  const ref = getV12Profile(2000, [
    { centerZ: 500, shape: "half" },
    { centerZ: 1000, shape: "full" },
  ]);
  assert(hasPoint2D(ref, 150, 492));
  assert(hasPoint2D(ref, 100, 992));
}

function testV12ClearanceAndV5HeightFollowLayout() {
  const params = buildPureParams({
    cabinet: {
      width: cabinetWidthFromFridge(550, "left"),
      depth: 600,
      height: 2200,
      panelThickness: 15,
      exteriorSide: "left",
    },
    fridge: {
      width: 550,
      depth: 580,
      height: 1497,
    },
    clearances: {
      top: 60,
      bottom: 80,
    },
    wheelAvoidance: {
      enabled: true,
      height: 200,
      depth: 300,
    },
    stack: [
      { id: "s1", type: "flap", height: 195 },
      { id: "s2", type: "drawer", height: 220 },
      { id: "s3", type: "fridge", height: 1583 },
    ],
  });
  assert.strictEqual(params.validation.ok, true, params.validation.errors.join("; "));
  const boardPlan = buildBoardPlan(params);
  const ap = buildAssemblyPlacementPlan(params, boardPlan);
  const v1 = boardPlan.boards.find((b) => b.id === "V1");
  assert(v1);
  assert(hasPoint2D(v1.outerVector, 80, 80));
  assert(hasPoint2D(v1.outerVector, 80, 96));
  assert(hasPoint2D(v1.outerVector, 80, 2124));
  assert(hasPoint2D(v1.outerVector, 80, 2140));
  assert.deepStrictEqual(ap.placements.T3.originMm, { x: 16, y: 0, z: 2124 });

  const v5 = boardPlan.boards.find((b) => b.id === "V5");
  assert(v5);
  assert.strictEqual(Math.max(...v5.outerVector.map((p) => p[1])), 1583);
  assert.strictEqual(v5.placement.height, 1583);
  assert.strictEqual(v5.placement.fridgeInputHeight, 1497);
}

function testV34IncludesOnlyFullSlots() {
  const params = buildPureParams(baseUi({
    stack: [
      { id: "s1", type: "flap", height: 195 },
      { id: "s2", type: "drawer", height: 250 },
      { id: "s3", type: "fridge", height: 1500 },
    ],
  }));
  const finalTop = params.avoidance.finalTopZ;
  assert.strictEqual(finalTop, 200);
  const v3 = buildBoardPlan(params).boards.find((b) => b.id === "V3");
  const ov = v3.outerVector;
  const halfLocalTop = 271.5 - finalTop + 8;
  assert(!hasPoint2D(ov, 50, halfLocalTop));
  const fullLocalTop = 536.5 - finalTop + 8;
  assert(hasPoint2D(ov, 50, fullLocalTop));
}

function testV34UsesFinalAvoidanceTop() {
  const params = buildPureParams(baseUi({
    fridgeHeight: 1875,
    wheelAvoidance: { enabled: true, height: 120, depth: 300 },
    stack: [
      { id: "s1", type: "flap", height: 85 },
      { id: "s2", type: "fridge", height: 1875 },
    ],
  }));
  assert.strictEqual(params.avoidance.finalMode, "raised");
  assert.strictEqual(params.avoidance.finalTopZ, 154);
  const V34h = 2100 - 154;
  assert.strictEqual(V34h, 1946);
  const v3 = buildBoardPlan(params).boards.find((b) => b.id === "V3");
  assert.strictEqual(v3.placement.height, V34h);
  assert.strictEqual(v3.source.finalAvoidanceTopZ, 154);
  const maxZ = Math.max.apply(null, v3.outerVector.map((p) => p[1]));
  assert.strictEqual(maxZ, V34h);
}

function testV34TopLSlot() {
  const params = buildPureParams(baseUi({
    fridgeHeight: 1875,
    wheelAvoidance: { enabled: true, height: 120, depth: 300 },
    stack: [
      { id: "s1", type: "flap", height: 85 },
      { id: "s2", type: "fridge", height: 1875 },
    ],
  }));
  const FCh = 2100;
  const finalTop = 154;
  const V34h = FCh - finalTop;
  const ov = getV34Profile(FCh, finalTop, params.layout.ziList);
  assert(hasPoint2D(ov, 150, V34h - 121));
  assert(hasPoint2D(ov, 134, V34h - 121));
  assert(hasPoint2D(ov, 134, V34h - 16));
  assert(hasPoint2D(ov, 45, V34h - 16));
  assert(hasPoint2D(ov, 45, V34h));
}

function uiVSeriesStandard() {
  return {
    cabinet: {
      width: cabinetWidthFromFridge(550, "right"),
      depth: 600,
      height: 2100,
      panelThickness: 15,
      exteriorSide: "right",
    },
    fridge: {
      width: 550,
      depth: 580,
      height: 1500,
    },
    clearances: {
      top: 40,
      bottom: 53,
    },
    wheelAvoidance: {
      enabled: true,
      height: 200,
      depth: 300,
    },
    stack: [
      { id: "s1", type: "flap", height: 195 },
      { id: "s2", type: "drawer", height: 250 },
      { id: "s3", type: "fridge", height: 1500 },
    ],
  };
}

function testVSeriesVerifyNormalCase() {
  const params = buildPureParams(uiVSeriesStandard());
  assert.strictEqual(params.validation.ok, true);
  const boardPlan = buildBoardPlan(params);
  const result = verifyVSeriesVectors(params, boardPlan);
  assert.strictEqual(result.ok, true, result.errors.join("; "));
}

function testV12IncludesHalfAndFullZi() {
  const params = buildPureParams(uiVSeriesStandard());
  const boardPlan = buildBoardPlan(params);
  const v1 = boardPlan.boards.find((b) => b.id === "V1");
  const half = params.layout.ziList.find((z) => z.shape === "half");
  const full = params.layout.ziList.find((z) => z.shape === "full");
  assert(half && full);
  const zh = half.centerZ;
  const zf = full.centerZ;
  [[150, zh - 8], [100, zh - 8], [100, zh + 8], [150, zh + 8]].forEach((pt) => {
    assert(pointExists(v1.outerVector, pt), `V1 missing half Zi slot point ${JSON.stringify(pt)}`);
  });
  [[150, zf - 8], [100, zf - 8], [100, zf + 8], [150, zf + 8]].forEach((pt) => {
    assert(pointExists(v1.outerVector, pt), `V1 missing full Zi slot point ${JSON.stringify(pt)}`);
  });
}

function testV34OnlyFullZi() {
  const params = buildPureParams(uiVSeriesStandard());
  const boardPlan = buildBoardPlan(params);
  const result = verifyVSeriesVectors(params, boardPlan);
  assert.strictEqual(result.ok, true);
  const v3 = boardPlan.boards.find((b) => b.id === "V3");
  const finalTop = params.avoidance.finalTopZ;
  const full = params.layout.ziList.find((z) => z.shape === "full");
  const half = params.layout.ziList.find((z) => z.shape === "half");
  const lzFull = full.centerZ - finalTop;
  assert(
    [[0, lzFull - 8], [50, lzFull - 8], [50, lzFull + 8], [0, lzFull + 8]].every((pt) => pointExists(v3.outerVector, pt)),
  );
  const lzHalf = half.centerZ - finalTop;
  const quad = [
    [0, lzHalf - 8],
    [50, lzHalf - 8],
    [50, lzHalf + 8],
    [0, lzHalf + 8],
  ];
  const allHalf = quad.every((pt) => pointExists(v3.outerVector, pt));
  assert(!allHalf, "V3 must not contain full half-Zi front slot quad");
}

function testV34UsesFinalAvoidanceTopRaised() {
  const params = buildPureParams({
    cabinet: {
      width: cabinetWidthFromFridge(550, "left"),
      depth: 600,
      height: 2100,
      panelThickness: 15,
      exteriorSide: "left",
    },
    fridge: { width: 550, depth: 580, height: 1875 },
    clearances: { top: 40, bottom: 53 },
    wheelAvoidance: { enabled: true, height: 120, depth: 300 },
    stack: [
      { id: "s1", type: "flap", height: 85 },
      { id: "s2", type: "fridge", height: 1875 },
    ],
  });
  assert.strictEqual(params.avoidance.finalMode, "raised");
  const boardPlan = buildBoardPlan(params);
  const result = verifyVSeriesVectors(params, boardPlan);
  assert.strictEqual(result.ok, true, result.errors.join("; "));
  const V34h = 2100 - params.avoidance.finalTopZ;
  assert.strictEqual(V34h, 1946);
  assert.strictEqual(params.avoidance.finalTopZ, 154);
}

function testDumpBoardVectorWorks() {
  const params = buildPureParams(uiVSeriesStandard());
  const boardPlan = buildBoardPlan(params);
  const dump = dumpBoardVector(boardPlan, "V1");
  assert.strictEqual(dump.id, "V1");
  assert(dump.pointCount > 4);
  assert.strictEqual(dump.isClosed, true);
  assert(dump.bbox.width > 0);
  assert(dump.bbox.height > 0);
}

function testBoardMetadataAudit() {
  const params = buildPureParams(baseUi());
  const boardPlan = buildBoardPlan(params);
  const audit = auditBoardMetadata(boardPlan);
  assert.strictEqual(audit.ok, true, audit.errors.join("; "));
  assert.strictEqual(audit.boardCount, boardPlan.boards.length);
  assert.strictEqual(audit.checkedBoardIds.length, boardPlan.boards.length);
  assert(audit.widthModel && audit.widthModel.panelSystemWidth === 595);
  const b0 = boardPlan.boards[0];
  assert(b0.geometry && typeof b0.geometry === "object");
  assert.strictEqual(b0.profilePlane, b0.geometry.profilePlane);
  assert.strictEqual(b0.outerVector, b0.geometry.outerVector);
  assert.strictEqual(b0.thickness, b0.geometry.thickness);
}

function testAssemblyPlacementPlanV01() {
  const params = buildPureParams(
    baseUi({
      stack: [
        { id: "s1", type: "flap", height: 195 },
        { id: "s2", type: "drawer", height: 250 },
        { id: "s3", type: "fridge", height: 1500 },
      ],
    }),
  );
  const boardPlan = buildBoardPlan(params);
  const ap = buildAssemblyPlacementPlan(params, boardPlan);
  assert.strictEqual(ap.ok, true, (ap.errors && ap.errors.join("; ")) || "");
  assert.strictEqual(ap.placementDimensionAuditOk, true);
  assert(Array.isArray(ap.placementDimensionAudit) && ap.placementDimensionAudit.length === 6);
  assert(ap.placementDimensionAudit.every((r) => r.status === "ok"));
  assert(ap.placements.V1 && ap.placements.V1.originMm);
  assert.strictEqual(ap.placements.V1.mode, "assembly_v0_1");
  assert.strictEqual(boardPlan.boards.find((b) => b.id === "V1").placement.assembly.boardId, "V1");
  const fch = params.layout.cabinetHeight;
  assert.deepStrictEqual(ap.placements.B1.originMm, { x: 16, y: 39, z: 0 });
  assert.deepStrictEqual(ap.placements.B2.originMm, { x: 16, y: 55, z: 0 });
  assert.deepStrictEqual(ap.placements.B3.originMm, { x: 16, y: 0, z: 53 });
  assert.deepStrictEqual(ap.placements.T1.originMm, { x: 16, y: 39, z: fch - 40 });
  assert.deepStrictEqual(ap.placements.T2.originMm, { x: 16, y: 39 + 16, z: fch - 40 });
  assert.deepStrictEqual(ap.placements.T3.originMm, { x: 16, y: 0, z: fch - 56 });
  const cd = params.base.Cd != null ? params.base.Cd : params.input.cabinet.depth;
  assert.deepStrictEqual(ap.placements.T4.originMm, { x: 16, y: cd - 100, z: fch - 16 });
  assert.strictEqual(ap.placements.T4.placementRuleUsed, "t4_rear_top_v0_3");
  assert.deepStrictEqual(ap.placements.T5.originMm, { x: 16, y: cd - 15, z: fch - 121 });
  assert.strictEqual(ap.placements.T5.placementRuleUsed, "t5_rear_top_vertical_v0_3");
  assert.strictEqual(ap.placements.T5.orientation.profilePlane, "XZ");
  assert.strictEqual(ap.placements.V1.originMm.x, 16);
  assert.strictEqual(ap.placements.V2.originMm.x, 16 + 595 - 15);
  assert.deepStrictEqual(ap.placements.V5.originMm, { x: 581, y: 0, z: 544 });
  assert.strictEqual(ap.placements.V5.placementRuleUsed, "v5_opposite_side_inset_v0_1");
  assert.strictEqual(ap.placements.V5.v5OppositeSideOk, true);
  assert.strictEqual(ap.placements.V5.v5BottomMatchesZiFullTop, true);
  assert.strictEqual(ap.placements.V5.v5InsetOneBoardThicknessOk, true);
  assert.strictEqual(ap.placements.SidePanel.originMm.x, 0);
  assert.strictEqual(ap.placements.SidePanel.placementRuleUsed, "side_panel_v0_1");
  const ziBoards = boardPlan.boards.filter((b) => /^Z\d+$/.test(String(b.id)));
  assert(ziBoards.length >= 1);
  assert(ziBoards.every((b) => b.placement.assembly != null));
  const v3Asm = boardPlan.boards.find((b) => b.id === "V3");
  const v4Asm = boardPlan.boards.find((b) => b.id === "V4");
  assert(v3Asm && v3Asm.placement.assembly && v4Asm && v4Asm.placement.assembly);
  assert.strictEqual(v3Asm.placement.assembly.originMm.x, 16);
  assert.strictEqual(v4Asm.placement.assembly.originMm.x, 16 + 595 - 15);
  const v34h = Number(v3Asm.placement.height) || 0;
  assert(Math.abs(v3Asm.placement.assembly.originMm.z - (fch - v34h)) < 1e-6);
  assert(Math.abs(v4Asm.placement.assembly.originMm.z - (fch - v34h)) < 1e-6);
  const h13 = boardPlan.boards.find((b) => b.id === "HSet_P2_H13");
  assert(h13 && h13.placement.assembly, "HSet_P2 H13 should have assembly placement v0.3");
  assert.strictEqual(h13.placement.assembly.placementRuleUsed, "hset_all_groups_v0_3");
  assert.strictEqual(h13.placement.assembly.hSetGroupId, "HSet_P2");
  assert.strictEqual(h13.placement.assembly.hSetMember, "H13");
  assert.strictEqual(h13.placement.assembly.groupRole, "H mid");
  assert.strictEqual(h13.placement.assembly.z0, 429);
  assert.strictEqual(h13.placement.assembly.z1, 529);
  assert.strictEqual(h13.placement.assembly.originMm.x, 16);
  assert.strictEqual(h13.placement.assembly.originMm.y, 150);
  const h24 = boardPlan.boards.find((b) => b.id === "HSet_P2_H24");
  const h34 = boardPlan.boards.find((b) => b.id === "HSet_P2_H34");
  assert(h24 && h24.placement.assembly && h34 && h34.placement.assembly);
  assert.strictEqual(h24.placement.assembly.originMm.x, 16 + 595 - 15);
  assert.strictEqual(h24.placement.assembly.originMm.y, 150);
  assert.strictEqual(h34.placement.assembly.originMm.x, 16 + 15);
  assert.strictEqual(h34.placement.assembly.originMm.y, 600 - 150 + 135);
  const ht13 = boardPlan.boards.find((b) => b.id === "HSet_top_H13");
  const ht24 = boardPlan.boards.find((b) => b.id === "HSet_top_H24");
  assert(ht13 && ht13.placement.assembly && ht24 && ht24.placement.assembly);
  assert.strictEqual(ht13.placement.assembly.originMm.x, 16);
  assert.strictEqual(ht13.placement.assembly.originMm.y, 150);
  assert.strictEqual(ht13.placement.assembly.originMm.z, 2000);
  assert.strictEqual(ht24.placement.assembly.originMm.x, 16 + 595 - 15);
  assert.strictEqual(ht24.placement.assembly.originMm.y, 150);
  assert.strictEqual(ht24.placement.assembly.originMm.z, 2000);
  assert.strictEqual(ht13.placement.assembly.groupRole, "H upper");
  const af = boardPlan.boards.find((b) => b.id === "AvoidanceFront");
  const at = boardPlan.boards.find((b) => b.id === "AvoidanceTop");
  assert(af && af.placement.assembly && at && at.placement.assembly);
  assert.strictEqual(af.placement.assembly.placementRuleUsed, "avoidance_front_v0_2");
  assert.strictEqual(at.placement.assembly.placementRuleUsed, "avoidance_top_v0_2");
  assert(
    !ap.warnings.some((w) => String(w).indexOf("Only one HSet group exists in BoardPlan") !== -1),
    "multiple HSet groups expected for standard fridge stack",
  );
  assert(
    ap.warnings.some((w) => String(w).indexOf("T5 assembly placement uses temporary vertical interpretation") !== -1),
  );
}

const tests = [
  ["A", testA],
  ["B", testB],
  ["C", testC],
  ["D", testD],
  ["E", testE],
  ["F", testF],
  ["G", testG],
  ["WidthModelRight", testWidthModelRightSidePanelPlacement],
  ["WidthAndDepthValidation", testWidthAndDepthValidation],
  ["H", testH],
  ["BoardPlanInvalid", testBoardPlanInvalidPure],
  ["BoardPlanCoreBoards", testBoardPlanCoreBoards],
  ["BoardPlanVSeriesExists", testBoardPlanVSeriesExists],
  ["V12IncludesAllZiSlots", testV12IncludesAllZiSlots],
  ["V12ClearanceAndV5HeightFollowLayout", testV12ClearanceAndV5HeightFollowLayout],
  ["V34IncludesOnlyFullSlots", testV34IncludesOnlyFullSlots],
  ["V34UsesFinalAvoidanceTop", testV34UsesFinalAvoidanceTop],
  ["V34TopLSlot", testV34TopLSlot],
  ["VSeriesVerifyNormalCase", testVSeriesVerifyNormalCase],
  ["V12IncludesHalfAndFullZi", testV12IncludesHalfAndFullZi],
  ["V34OnlyFullZi", testV34OnlyFullZi],
  ["V34UsesFinalAvoidanceTopRaised", testV34UsesFinalAvoidanceTopRaised],
  ["DumpBoardVectorWorks", testDumpBoardVectorWorks],
  ["BoardMetadataAudit", testBoardMetadataAudit],
  ["AssemblyPlacementPlanV01", testAssemblyPlacementPlanV01],
];

for (const [name, test] of tests) {
  test();
  console.log(`TEST ${name}: PASS`);
}
