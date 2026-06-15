const assert = require("assert");
const path = require("path");
const { spawnSync } = require("child_process");

const logic = require(path.resolve(__dirname, "..", "..", "Fridge Cabinet Generator", "fridge_logic.js"));
const bridgeScript = path.resolve(__dirname, "..", "scripts", "boardplan_from_pureparams.js");

const ui = {
  cabinet: {
    width: 611,
    depth: 616,
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
    { id: "flap", type: "flap", height: 195 },
    { id: "drawer", type: "drawer", height: 250 },
    { id: "fridge", type: "fridge", height: 1500 },
  ],
};

const pureParams = logic.buildPureParams(ui);
assert.strictEqual(pureParams.validation.ok, true, "sample PureParams should validate");

const proc = spawnSync(process.execPath, [bridgeScript], {
  input: JSON.stringify(pureParams),
  encoding: "utf8",
});

assert.strictEqual(proc.status, 0, proc.stderr);
const data = JSON.parse(proc.stdout);
assert.ok(data.boardPlan, "bridge should return boardPlan");
assert.ok(Array.isArray(data.boardPlan.boards), "boardPlan.boards should be an array");
assert.ok(data.boardPlan.boards.length > 0, "bridge should create boards");
assert.strictEqual(data.boardPlan.validation.ok, true, "boardPlan should validate");
assert.ok(data.vVerify, "bridge should return vVerify");
assert.strictEqual(data.vVerify.ok, true, "V-series verification should pass");

console.log(`OK fridge bridge: ${data.boardPlan.boards.length} boards`);
