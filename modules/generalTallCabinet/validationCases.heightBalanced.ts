export type ValidationZoneInputType =
  | "side_door"
  | "double_door"
  | "drawer"
  | "top_flap"
  | "bottom_flap"
  | "open_space";

export interface ValidationZoneInput {
  id: string;
  height: number;
  type: ValidationZoneInputType;
  verticalDivider?: boolean;
}

export interface ValidationCaseInput {
  caseId: string;
  cabinetHeight: number;
  cabinetWidth: number;
  cabinetDepth: number;
  avoidance?: { enabled: boolean; depth?: number; height?: number };
  zones: ValidationZoneInput[];
}

export interface NegativeValidationCaseInput extends ValidationCaseInput {
  expectedStatus: "BLOCKED" | "FAIL";
  expectedReason: string;
}

// V1.1 clean main validation presets. All main GT cases are expected to be height-balanced.
export const GENERAL_TALL_VALIDATION_CASES_V1_1: ValidationCaseInput[] = [
  {
    caseId: "GT-01-standard-3-zone",
    cabinetHeight: 2000,
    cabinetWidth: 600,
    cabinetDepth: 584,
    zones: [
      { id: "zone-1", height: 550, type: "side_door" },
      { id: "zone-2", height: 300, type: "drawer" },
      { id: "zone-3", height: 995, type: "double_door", verticalDivider: true },
    ],
  },
  {
    caseId: "GT-02-simple-2-zone",
    cabinetHeight: 1800,
    cabinetWidth: 600,
    cabinetDepth: 584,
    zones: [
      { id: "zone-1", height: 700, type: "side_door" },
      { id: "zone-2", height: 960, type: "double_door" },
    ],
  },
  {
    caseId: "GT-03-top-flap-valid",
    cabinetHeight: 2000,
    cabinetWidth: 600,
    cabinetDepth: 584,
    zones: [
      { id: "zone-1", height: 700, type: "side_door" },
      { id: "zone-2", height: 500, type: "drawer" },
      { id: "zone-3", height: 645, type: "top_flap" },
    ],
  },
  {
    caseId: "GT-04-bottom-flap-valid",
    cabinetHeight: 2000,
    cabinetWidth: 600,
    cabinetDepth: 584,
    zones: [
      { id: "zone-1", height: 350, type: "bottom_flap" },
      { id: "zone-2", height: 400, type: "drawer" },
      { id: "zone-3", height: 1095, type: "double_door", verticalDivider: true },
    ],
  },
  {
    caseId: "GT-05-avoidance-valid",
    cabinetHeight: 2000,
    cabinetWidth: 600,
    cabinetDepth: 584,
    avoidance: { enabled: true, depth: 200, height: 650 },
    zones: [
      { id: "zone-1", height: 500, type: "side_door" },
      { id: "zone-2", height: 300, type: "drawer" },
      { id: "zone-3", height: 1045, type: "double_door", verticalDivider: true },
    ],
  },
  {
    caseId: "GT-06-narrow-width-valid",
    cabinetHeight: 1800,
    cabinetWidth: 450,
    cabinetDepth: 584,
    zones: [
      { id: "zone-1", height: 600, type: "side_door" },
      { id: "zone-2", height: 1060, type: "double_door", verticalDivider: true },
    ],
  },
  {
    caseId: "GT-07-shallow-depth-valid",
    cabinetHeight: 2000,
    cabinetWidth: 600,
    cabinetDepth: 450,
    zones: [
      { id: "zone-1", height: 550, type: "side_door" },
      { id: "zone-2", height: 300, type: "drawer" },
      { id: "zone-3", height: 995, type: "double_door", verticalDivider: true },
    ],
  },
  {
    caseId: "GT-08-extra-tall-valid",
    cabinetHeight: 2400,
    cabinetWidth: 600,
    cabinetDepth: 584,
    zones: [
      { id: "zone-1", height: 350, type: "bottom_flap" },
      { id: "zone-2", height: 400, type: "drawer" },
      { id: "zone-3", height: 650, type: "side_door" },
      { id: "zone-4", height: 830, type: "double_door", verticalDivider: true },
    ],
  },
  {
    caseId: "GT-09-low-cabinet-valid",
    cabinetHeight: 1500,
    cabinetWidth: 600,
    cabinetDepth: 584,
    zones: [
      { id: "zone-1", height: 250, type: "bottom_flap" },
      { id: "zone-2", height: 300, type: "drawer" },
      { id: "zone-3", height: 795, type: "side_door" },
    ],
  },
  {
    caseId: "GT-10-mixed-functions-valid",
    cabinetHeight: 2100,
    cabinetWidth: 600,
    cabinetDepth: 584,
    zones: [
      { id: "zone-1", height: 500, type: "side_door" },
      { id: "zone-2", height: 300, type: "drawer" },
      { id: "zone-3", height: 400, type: "side_door" },
      { id: "zone-4", height: 730, type: "double_door", verticalDivider: true },
    ],
  },
];

export const GENERAL_TALL_VALIDATION_CASES_HEIGHT_BALANCED = GENERAL_TALL_VALIDATION_CASES_V1_1;

export const GENERAL_TALL_NEGATIVE_VALIDATION_CASES_V1_1: NegativeValidationCaseInput[] = [
  {
    caseId: "NEG-01-height-mismatch-blocked",
    cabinetHeight: 2000,
    cabinetWidth: 600,
    cabinetDepth: 584,
    zones: [
      { id: "zone-1", height: 550, type: "side_door" },
      { id: "zone-2", height: 300, type: "drawer" },
      { id: "zone-3", height: 700, type: "double_door", verticalDivider: true },
    ],
    expectedStatus: "BLOCKED",
    expectedReason: "Zones do not fill cabinet height",
  },
  {
    caseId: "NEG-02-middle-flap-invalid",
    cabinetHeight: 2100,
    cabinetWidth: 600,
    cabinetDepth: 584,
    zones: [
      { id: "zone-1", height: 520, type: "drawer" },
      { id: "zone-2", height: 480, type: "top_flap" },
      { id: "zone-3", height: 420, type: "drawer" },
      { id: "zone-4", height: 510, type: "side_door" },
    ],
    expectedStatus: "FAIL",
    expectedReason: "Flap must be bottom_flap or top_flap only",
  },
  {
    caseId: "NEG-03-over-height-blocked",
    cabinetHeight: 1200,
    cabinetWidth: 600,
    cabinetDepth: 584,
    zones: [
      { id: "zone-1", height: 600, type: "side_door" },
      { id: "zone-2", height: 500, type: "drawer" },
      { id: "zone-3", height: 500, type: "side_door" },
    ],
    expectedStatus: "BLOCKED",
    expectedReason: "Zones exceed cabinet height",
  },
  {
    caseId: "NEG-04-fill-last-zone-invalid",
    cabinetHeight: 900,
    cabinetWidth: 600,
    cabinetDepth: 584,
    zones: [
      { id: "zone-1", height: 500, type: "side_door" },
      { id: "zone-2", height: 500, type: "drawer" },
    ],
    expectedStatus: "BLOCKED",
    expectedReason: "Cannot fill remaining height into last zone",
  },
  {
    caseId: "NEG-05-invalid-avoidance",
    cabinetHeight: 2000,
    cabinetWidth: 600,
    cabinetDepth: 584,
    avoidance: { enabled: true, depth: -1, height: 400 },
    zones: [
      { id: "zone-1", height: 550, type: "side_door" },
      { id: "zone-2", height: 300, type: "drawer" },
      { id: "zone-3", height: 995, type: "double_door", verticalDivider: true },
    ],
    expectedStatus: "FAIL",
    expectedReason: "Avoidance parameters invalid",
  },
];
