import { resolveZoneBoundaries } from "./boundaryResolver.ts";
import type {
  BoundaryResult,
  BoundaryType,
  FunctionalZone,
  StackingCalculationResult,
  StackingCalculatorInput,
  StackingItem,
  SystemHeights,
  TopBottomSystemConfig,
} from "./types.ts";

const DEFAULT_ZI_THICKNESS = 15;
const DEFAULT_STYLE_1_INSERT_SLOT_THICKNESS = 16;
const TOP_STYLE_1_MIN_FRONT_RAIL_HEIGHT = 40;
const BOTTOM_STYLE_1_MIN_FRONT_RAIL_HEIGHT = 53;
const STYLE_2_MIN_HEIGHT = 60;

function numericOrDefault(value: unknown, fallback: number): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function boundaryThickness(boundaryType: BoundaryType, ziThickness: number): number {
  return boundaryType === "none" ? 0 : ziThickness;
}

function systemHeight(
  config: TopBottomSystemConfig,
  position: "top" | "bottom",
  errors: string[],
): number {
  if (!config || typeof config !== "object") {
    throw new Error(`Missing ${position} system config.`);
  }

  if (config.style === "style_1") {
    const minHeight = position === "top" ? TOP_STYLE_1_MIN_FRONT_RAIL_HEIGHT : BOTTOM_STYLE_1_MIN_FRONT_RAIL_HEIGHT;
    const frontRailHeight = Math.max(numericOrDefault(config.frontRailHeight, minHeight), minHeight);
    const insertSlotThickness = numericOrDefault(config.insertSlotThickness, DEFAULT_STYLE_1_INSERT_SLOT_THICKNESS);
    return frontRailHeight + insertSlotThickness;
  }

  if (config.style === "style_2") {
    const height = Number(config.height);
    if (!Number.isFinite(height)) {
      errors.push(`${position} Style 2 height must be a finite number.`);
      return 0;
    }
    if (height < STYLE_2_MIN_HEIGHT) {
      errors.push(`${position} Style 2 height must be >= ${STYLE_2_MIN_HEIGHT} mm.`);
    }
    return height;
  }

  throw new Error(`Unsupported ${position} system style.`);
}

export function resolveSystemHeights(
  topSystem: TopBottomSystemConfig,
  bottomSystem: TopBottomSystemConfig,
): SystemHeights & { errors: string[] } {
  const errors: string[] = [];
  return {
    topSystemHeight: systemHeight(topSystem, "top", errors),
    bottomSystemHeight: systemHeight(bottomSystem, "bottom", errors),
    errors,
  };
}

function pushItem(items: StackingItem[], item: Omit<StackingItem, "z1" | "height"> & { height: number }): number {
  const z1 = item.z0 + item.height;
  items.push({
    ...item,
    z1,
  });
  return z1;
}

function boundaryNotes(boundary: BoundaryResult): string {
  if (boundary.upgradedByDoubleDoorDivider) {
    return `${boundary.reason} Upgraded by double-door vertical divider.`;
  }
  return boundary.reason;
}

export function calculateZStacking(input: StackingCalculatorInput): StackingCalculationResult {
  if (!input || typeof input !== "object") {
    throw new Error("calculateZStacking requires an input object.");
  }
  if (!Array.isArray(input.zones)) {
    throw new Error("calculateZStacking requires input.zones to be an array.");
  }

  const expectedCabinetHeight = Number(input.cabinetHeight);
  const ziThickness = numericOrDefault(input.ziThickness, DEFAULT_ZI_THICKNESS);
  const systemHeights = resolveSystemHeights(input.topSystem, input.bottomSystem);
  const boundaryResolution = resolveZoneBoundaries(input.zones);
  const errors = [...systemHeights.errors, ...boundaryResolution.errors];
  const warnings = [...boundaryResolution.warnings];
  const items: StackingItem[] = [];

  let currentZ = 0;
  currentZ = pushItem(items, {
    id: "bottom-system",
    type: "bottom_system",
    z0: currentZ,
    height: systemHeights.bottomSystemHeight,
    notes: `${input.bottomSystem.style} bottom system.`,
  });

  input.zones.forEach((zone: FunctionalZone, index: number) => {
    currentZ = pushItem(items, {
      id: `zone-${zone.id}`,
      type: "functional_zone",
      z0: currentZ,
      height: Number(zone.height),
      zoneId: zone.id,
      notes: `${zone.type} clear-space height.`,
    });

    const boundary = boundaryResolution.boundaries[index];
    if (!boundary) return;

    const thickness = boundaryThickness(boundary.boundaryType, ziThickness);
    if (thickness <= 0) return;

    const z0 = currentZ;
    currentZ = pushItem(items, {
      id: `boundary-${boundary.aboveZoneId}-${boundary.belowZoneId}`,
      type: "boundary_panel",
      z0,
      height: thickness,
      boundaryType: boundary.boundaryType,
      centerZ: z0 + thickness / 2,
      notes: boundaryNotes(boundary),
    });
  });

  currentZ = pushItem(items, {
    id: "top-system",
    type: "top_system",
    z0: currentZ,
    height: systemHeights.topSystemHeight,
    notes: `${input.topSystem.style} top system.`,
  });

  const functionalZoneTotal = input.zones.reduce((sum, zone) => sum + Number(zone.height || 0), 0);
  const boundaryPanelTotal = boundaryResolution.boundaries.reduce(
    (sum, boundary) => sum + boundaryThickness(boundary.boundaryType, ziThickness),
    0,
  );
  const calculatedHeight =
    systemHeights.topSystemHeight + systemHeights.bottomSystemHeight + functionalZoneTotal + boundaryPanelTotal;
  const difference = calculatedHeight - expectedCabinetHeight;

  if (Number.isFinite(expectedCabinetHeight) && Math.abs(difference) > 0.001) {
    warnings.push(
      `Height mismatch: expected CH = ${expectedCabinetHeight}; calculated CH = ${calculatedHeight}; difference = ${difference}.`,
    );
  }

  return {
    items,
    boundaryResolution,
    validation: {
      errors,
      warnings,
    },
    topSystemHeight: systemHeights.topSystemHeight,
    bottomSystemHeight: systemHeights.bottomSystemHeight,
    boundaryPanelTotal,
    functionalZoneTotal,
    calculatedHeight,
    expectedCabinetHeight,
    difference,
    ziThickness,
  };
}

export type { StackingCalculationResult, StackingCalculatorInput, StackingItem };
