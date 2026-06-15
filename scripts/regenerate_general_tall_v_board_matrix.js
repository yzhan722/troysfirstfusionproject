const fs = require("fs");
const path = require("path");

const { generateGeneralTallCabinet } = require("../modules/generalTallCabinet/generator.ts");
function zone(id, type, height) {
  return { id, type, height, verticalDivider: false };
}

function matrixBaseParams() {
  return {
    cabinetHeight: 2000,
    cabinetWidth: 600,
    cabinetDepth: 640,
    panelThickness: 16,
    frontFaceAllowance: 16,
    sideClearance: 3,
    topSystem: { style: "style_1", frontRailHeight: 40 },
    bottomSystem: { style: "style_1", frontRailHeight: 53 },
    avoidance: { enabled: true, depth: 380, height: 220 },
    leftSidePanelThickness: 16,
    rightSidePanelThickness: 16,
    leftSidePanelAdaptAvoidance: true,
    rightSidePanelAdaptAvoidance: false,
    zones: [
      zone("zone-1", "side_door", 600),
      zone("zone-2", "drawer", 500),
      { ...zone("zone-3", "double_door", 690), verticalDivider: true },
    ],
  };
}

function buildCaseOutputs() {
  const combos = [
    { name: "CASE-A", top: { style: "style_1", frontRailHeight: 40 }, bottom: { style: "style_1", frontRailHeight: 53 } },
    { name: "CASE-B", top: { style: "style_1", frontRailHeight: 40 }, bottom: { style: "style_2", height: 100 } },
    { name: "CASE-C", top: { style: "style_2", height: 80 }, bottom: { style: "style_1", frontRailHeight: 53 } },
    { name: "CASE-D", top: { style: "style_2", height: 80 }, bottom: { style: "style_2", height: 100 } },
  ];
  const boardIds = ["V1", "V2", "V3", "V4"];

  return combos.map((combo) => {
    const params = {
      ...matrixBaseParams(),
      topSystem: combo.top,
      bottomSystem: combo.bottom,
    };
    const result = generateGeneralTallCabinet(params);

    const boardData = boardIds
      .map((id) => result.boards.find((board) => board.id === id))
      .filter(Boolean)
      .map((board) => {
        const points = (board.cutProfileVector && board.cutProfileVector.length > 0 ? board.cutProfileVector : board.profileVector) || [];
        const ys = points.map((point) => point.y);
        const zs = points.map((point) => point.z);
        return {
          id: board.id,
          bboxY: [board.y0, board.y1],
          bboxZ: [board.z0, board.z1],
          vectorY: [Math.min(...ys), Math.max(...ys)],
          vectorZ: [Math.min(...zs), Math.max(...zs)],
          points,
        };
      });

    return { combo, params, result, boardData };
  });
}

function toMarkdown(caseOutputs) {
  let out = "# General Tall V-board YZ Point Matrix\n\n";
  out += "Regenerated from `generateGeneralTallCabinet()` runtime output after V-board semantic correction.\n\n";
  out += "## Compact Summary\n\n";
  out += "| Case | Board | vector Y range |\n";
  out += "|---|---|---|\n";
  for (const c of caseOutputs) {
    const v12 = c.boardData.find((board) => board.id === "V1");
    const v34 = c.boardData.find((board) => board.id === "V3");
    out += `| ${c.combo.name} | V1/V2 | ${v12.vectorY[0]} -> ${v12.vectorY[1]} |\n`;
    out += `| ${c.combo.name} | V3/V4 | ${v34.vectorY[0]} -> ${v34.vectorY[1]} |\n`;
  }
  out += "\n";

  for (const c of caseOutputs) {
    const debug = c.result.debug;
    out += `## ${c.combo.name} topStyle=${c.combo.top.style} bottomStyle=${c.combo.bottom.style}\n\n`;
    out += "### Input summary\n\n";
    out += "| Param | Value |\n";
    out += "|---|---:|\n";
    out += `| CH | ${c.params.cabinetHeight} |\n`;
    out += `| CD | ${c.params.cabinetDepth} |\n`;
    out += "| FrontFaceAllowance | 16 |\n";
    out += `| MidDepth | ${debug.midDepth} |\n`;
    out += `| MidWidth | ${debug.midWidth} |\n`;
    out += "| PT | 16 |\n";
    out += `| topStyle | ${c.combo.top.style} |\n`;
    out += `| bottomStyle | ${c.combo.bottom.style} |\n`;
    out += `| calculatedHeight | ${debug.calculatedHeight ?? "n/a"} |\n`;
    out += `| heightDiff | ${debug.heightDiff ?? "n/a"} |\n\n`;

    out += "### V-board details\n\n";
    for (const board of c.boardData) {
      out += `#### ${board.id}\n\n`;
      out += "| Field | Value |\n";
      out += "|---|---|\n";
      out += `| bbox Y range | ${board.bboxY[0]} -> ${board.bboxY[1]} |\n`;
      out += `| bbox Z range | ${board.bboxZ[0]} -> ${board.bboxZ[1]} |\n`;
      out += `| vector Y range | ${board.vectorY[0]} -> ${board.vectorY[1]} |\n`;
      out += `| vector Z range | ${board.vectorZ[0]} -> ${board.vectorZ[1]} |\n`;
      out += `| point count | ${board.points.length} |\n\n`;
      out += "~~~json\n";
      out += `${JSON.stringify(board.points, null, 2)}\n`;
      out += "~~~\n\n";
    }
  }
  return out;
}

function main() {
  const caseOutputs = buildCaseOutputs();
  const markdown = toMarkdown(caseOutputs);
  const outputPath = path.join(__dirname, "..", "docs", "general-tall-v-board-yz-point-matrix.md");
  fs.writeFileSync(outputPath, markdown);
  console.log(`Regenerated ${outputPath}`);
}

main();
