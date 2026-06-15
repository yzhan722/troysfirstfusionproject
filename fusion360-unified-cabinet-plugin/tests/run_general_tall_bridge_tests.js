const assert = require("assert");
const path = require("path");
const { spawnSync } = require("child_process");

const bridgeScript = path.resolve(__dirname, "..", "scripts", "general_tall_from_params.js");

const baseParams = {
    cabinetHeight: 2000,
    cabinetWidth: 600,
    cabinetDepth: 584,
    panelThickness: 16,
    frontFaceAllowance: 16,
    sideClearance: 3,
    ziThickness: 15,
    hThickness: 15,
    topSystem: { style: "style_1", frontRailHeight: 40 },
    bottomSystem: { style: "style_1", frontRailHeight: 53 },
    avoidance: { enabled: false, depth: 200, height: 400 },
    zones: [
      { id: "zone-1", type: "side_door", height: 550 },
      { id: "zone-2", type: "drawer", height: 300 },
      { id: "zone-3", type: "double_door", height: 995, verticalDivider: true },
    ],
};

function runBridge(params) {
  const proc = spawnSync(process.execPath, [bridgeScript], {
    input: JSON.stringify({ params }),
    encoding: "utf8",
  });
  assert.strictEqual(proc.status, 0, proc.stderr);
  const data = JSON.parse(proc.stdout);
  assert.strictEqual(data.ok, true, "bridge should return ok");
  return data.result || {};
}

const result = runBridge(baseParams);
const validation = result.validation || {};
const stacking = result.stacking || {};
const boards = result.boards || [];
assert.strictEqual(Array.isArray(boards), true, "boards should be an array");
assert.strictEqual((validation.errors || []).length, 0, "default case should have no validation errors");
assert.strictEqual(stacking.difference, 0, "default case should have zero height difference");

const boardIds = new Set(boards.map((board) => board.id));
[
  "V1", "V2", "V3", "V4",
  "B1", "B2", "B3",
  "T1", "T2", "T3",
  "Zi1", "Zi2",
  "H13_bottom", "H24_bottom", "H34_bottom",
  "H13_mid", "H24_mid", "H34_mid",
  "H13_top", "H24_top", "T4", "T5",
  "VD_zone-3",
].forEach((id) => assert(boardIds.has(id), `expected board id ${id}`));

for (const board of boards) {
  const widthX = Number(board.x1) - Number(board.x0);
  const depthY = Number(board.y1) - Number(board.y0);
  const heightZ = Number(board.z1) - Number(board.z0);
  assert(Number.isFinite(widthX) && widthX > 0, `board ${board.id} width must be > 0`);
  assert(Number.isFinite(depthY) && depthY > 0, `board ${board.id} depth must be > 0`);
  assert(Number.isFinite(heightZ) && heightZ > 0, `board ${board.id} height must be > 0`);
}

const sidePanelResult = runBridge({
  ...baseParams,
  leftSidePanelThickness: 16,
  rightSidePanelThickness: 16,
  avoidance: { enabled: true, depth: 200, height: 400 },
});
const sidePanelBoards = sidePanelResult.boards || [];
const sidePanelIds = new Set(sidePanelBoards.map((board) => board.id));
assert(sidePanelIds.has("SidePanel_L"), "SidePanel_L should be generated when enabled");
assert(sidePanelIds.has("SidePanel_R"), "SidePanel_R should be generated when enabled");
assert.strictEqual(sidePanelBoards.length, boards.length + 4, "side panels and avoidance supports should add four boards");

const sidePanelL = sidePanelBoards.find((board) => board.id === "SidePanel_L");
const sidePanelR = sidePanelBoards.find((board) => board.id === "SidePanel_R");
assert.deepStrictEqual(
  {
    x0: sidePanelL.x0,
    x1: sidePanelL.x1,
    y0: sidePanelL.y0,
    y1: sidePanelL.y1,
    z0: sidePanelL.z0,
    z1: sidePanelL.z1,
    profilePlane: sidePanelL.profilePlane,
    thicknessAxis: sidePanelL.thicknessAxis,
    vectorSource: Array.isArray(sidePanelL.profileVector) ? "profileVector" : "bboxFallback",
  },
  {
    x0: 0,
    x1: 16,
    y0: -16,
    y1: 568,
    z0: 0,
    z1: 2000,
    profilePlane: "YZ",
    thicknessAxis: "X",
    vectorSource: "profileVector",
  },
);
assert.deepStrictEqual(
  {
    x0: sidePanelR.x0,
    x1: sidePanelR.x1,
    y0: sidePanelR.y0,
    y1: sidePanelR.y1,
    z0: sidePanelR.z0,
    z1: sidePanelR.z1,
    profilePlane: sidePanelR.profilePlane,
    thicknessAxis: sidePanelR.thicknessAxis,
    vectorSource: Array.isArray(sidePanelR.profileVector) ? "profileVector" : "bboxFallback",
  },
  {
    x0: 584,
    x1: 600,
    y0: -16,
    y1: 568,
    z0: 0,
    z1: 2000,
    profilePlane: "YZ",
    thicknessAxis: "X",
    vectorSource: "profileVector",
  },
);
assert(sidePanelResult.debug?.sidePanelOverlapAudit, "side panel overlap audit should be present");
assert(sidePanelIds.has("avoidance_horizontal"), "avoidance_horizontal should be generated when avoidance enabled");
assert(sidePanelIds.has("Avoidance_Vertical"), "Avoidance_Vertical should be generated when avoidance enabled");

const frontPanels = result.frontPanels || [];
assert(Array.isArray(frontPanels), "frontPanels should be an array");
// side_door + drawer + double_door (2 leaves) = 4 front panels
assert.strictEqual(frontPanels.length, 4, `expected 4 front panels, got ${frontPanels.length}`);
const fpIds = new Set(frontPanels.map((panel) => panel.id));
["FP_zone-1", "FP_zone-2", "FP_zone-3_L", "FP_zone-3_R"].forEach((id) => assert(fpIds.has(id), `expected front panel ${id}`));
for (const panel of frontPanels) {
  assert(panel.width > 0, `front panel ${panel.id} width must be > 0`);
  assert(panel.height > 0, `front panel ${panel.id} height must be > 0`);
  assert.strictEqual(panel.y1, 0, `front panel ${panel.id} y1 should be 0`);
  assert.strictEqual(panel.y0, -16, `front panel ${panel.id} y0 should be -16`);
}
const doorPanel = frontPanels.find((panel) => panel.id === "FP_zone-1");
assert(doorPanel.hingeHoles && doorPanel.hingeHoles.length >= 2, "side door should have hinge cups");
assert(doorPanel.lockCutout, "side door should have a lock cutout");
const doubleLeft = frontPanels.find((panel) => panel.id === "FP_zone-3_L");
assert.strictEqual(doubleLeft.lockCutout?.orientation, "vertical", "double door leaf with divider should default to side lock");

console.log(`OK general tall bridge: ${boards.length} boards, ${sidePanelBoards.length} with side panels/avoidance supports, ${frontPanels.length} front panels`);
