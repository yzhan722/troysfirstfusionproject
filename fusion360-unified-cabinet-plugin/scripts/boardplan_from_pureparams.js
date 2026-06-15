#!/usr/bin/env node

const path = require("path");

const logicPath = path.resolve(__dirname, "..", "..", "Fridge Cabinet Generator", "fridge_logic.js");
const logic = require(logicPath);

function readStdin() {
  return new Promise((resolve, reject) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk) => {
      data += chunk;
    });
    process.stdin.on("end", () => resolve(data));
    process.stdin.on("error", reject);
  });
}

(async function main() {
  try {
    const raw = await readStdin();
    const pureParams = JSON.parse(raw || "{}");
    const boardPlan = logic.buildBoardPlan(pureParams);
    logic.buildAssemblyPlacementPlan(pureParams, boardPlan);
    const vVerify = logic.verifyVSeriesVectors(pureParams, boardPlan);
    process.stdout.write(JSON.stringify({ boardPlan, vVerify }));
  } catch (error) {
    process.stderr.write(error && error.stack ? error.stack : String(error));
    process.exit(1);
  }
})();
