const assert = require("assert");
const path = require("path");
const logic = require(path.resolve(__dirname, "..", "..", "Fridge Cabinet Generator", "fridge_logic.js"));

function findBoard(plan, id) {
  return (plan.boards || []).find((board) => board.id === id);
}

function sampleUi(ledGroove) {
  return {
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
      ledGroove,
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
}

const pureParams = logic.buildPureParams(sampleUi(true));
assert.strictEqual(pureParams.validation.ok, true, "sample PureParams should validate");
assert.strictEqual(pureParams.base.ledGroove, true);

const plan = logic.buildBoardPlan(pureParams);
assert.ok(plan && Array.isArray(plan.boards), "boardPlan should build");

const b3 = findBoard(plan, "B3");
const t3 = findBoard(plan, "T3");
assert(b3, "B3 board missing");
assert(t3, "T3 board missing");

const b3Led = (b3.grooves || []).find((g) => g.type === "b3_groove");
const t3Led = (t3.grooves || []).find((g) => g.type === "t3_groove");
assert(b3Led, "B3 LED groove missing");
assert(t3Led, "T3 LED groove missing");

assert.strictEqual(b3Led.face, "bottom");
assert.strictEqual(t3Led.face, "top");
assert.strictEqual(b3Led.width, 14.5);
assert.strictEqual(b3Led.depth, 6.5);
assert.strictEqual(b3Led.frontOffset, 25.25);
assert.strictEqual(b3Led.branchEndInset, 80);
assert.ok(b3Led.branchLength > 20, "branches should extend to rear edge");
assert.deepStrictEqual(
  { y0: b3Led.main.y0, y1: b3Led.main.y1 },
  { y0: 18, y1: 32.5 },
);
assert.strictEqual(b3Led.branches.length, 2);
assert.strictEqual(b3Led.branches[0].y1, 150);
assert.strictEqual(b3Led.branches[1].y1, 150);
assert.deepStrictEqual(t3Led.main, b3Led.main);
assert.deepStrictEqual(t3Led.branches, b3Led.branches);

const offPlan = logic.buildBoardPlan(logic.buildPureParams(sampleUi(false)));
assert.strictEqual(findBoard(offPlan, "B3").grooves.length, 0);
assert.strictEqual(findBoard(offPlan, "T3").grooves.length, 0);

console.log("TEST fridge LED B3/T3 grooves: PASS");
