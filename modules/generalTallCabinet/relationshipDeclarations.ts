import type { Board } from "./types.ts";

/** Design-intent structural joints for General Tall style_1 skeleton boards. */
export interface RelationshipDeclaration {
  declarationId: string;
  generator: "general_tall";
  panelAId: string;
  panelBId: string;
  relationshipType: "structural_butt_joint" | "face_contact";
  geometryType: "edge_to_surface" | "surface_to_surface";
  hostPanelId: string;
  targetPanelId: string;
  ruleId: string;
  allowedHardware: string[];
}

export const GENERAL_TALL_RELATIONSHIP_DECLARATIONS: RelationshipDeclaration[] = [
  {
    declarationId: "gt_b1_b3_bottom_rail_to_deck",
    generator: "general_tall",
    panelAId: "B1",
    panelBId: "B3",
    relationshipType: "structural_butt_joint",
    geometryType: "edge_to_surface",
    hostPanelId: "B1",
    targetPanelId: "B3",
    ruleId: "general_tall_bottom_rail_deck_v1",
    allowedHardware: ["screw_hole"],
  },
  {
    declarationId: "gt_t1_t3_top_rail_to_deck",
    generator: "general_tall",
    panelAId: "T1",
    panelBId: "T3",
    relationshipType: "structural_butt_joint",
    geometryType: "edge_to_surface",
    hostPanelId: "T1",
    targetPanelId: "T3",
    ruleId: "general_tall_top_rail_deck_v1",
    allowedHardware: ["screw_hole"],
  },
  {
    declarationId: "gt_b2_b3_mid_rail_to_deck",
    generator: "general_tall",
    panelAId: "B2",
    panelBId: "B3",
    relationshipType: "structural_butt_joint",
    geometryType: "edge_to_surface",
    hostPanelId: "B2",
    targetPanelId: "B3",
    ruleId: "general_tall_mid_rail_deck_v1",
    allowedHardware: ["screw_hole"],
  },
  {
    declarationId: "gt_t2_t3_mid_rail_to_deck",
    generator: "general_tall",
    panelAId: "T2",
    panelBId: "T3",
    relationshipType: "structural_butt_joint",
    geometryType: "edge_to_surface",
    hostPanelId: "T2",
    targetPanelId: "T3",
    ruleId: "general_tall_mid_top_rail_deck_v1",
    allowedHardware: ["screw_hole"],
  },
];

export function relationshipDeclarationsForBoards(boards: Board[]): RelationshipDeclaration[] {
  const boardIds = new Set(boards.map((board) => board.id));
  return GENERAL_TALL_RELATIONSHIP_DECLARATIONS.filter((item) => {
    const required = new Set([item.panelAId, item.panelBId, item.hostPanelId, item.targetPanelId]);
    for (const boardId of required) {
      if (!boardIds.has(boardId)) {
        return false;
      }
    }
    return true;
  });
}
