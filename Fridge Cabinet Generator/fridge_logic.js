(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
  root.FridgeCabinetLogic = api;
})(typeof self !== "undefined" ? self : this, function () {
  const VERSION = "0.2.1";
  const UNIT = "mm";
  const DEFAULT_TOP_CLEARANCE_MM = 40;
  const DEFAULT_BOTTOM_CLEARANCE_MM = 53;
  const HSET_HEIGHT = 100;
  const HSET_Z_MERGE_TOL_MM = 3;
  const HSET_MIN_GAP_FOR_STRUCTURAL_MID_MM = 80;
  /** Front / rear vertical stile depth along Y before H13/H24 connector span (mm). */
  const H_CONNECTOR_FRONT_V_DEPTH_MM = 150;
  const H_CONNECTOR_REAR_V_DEPTH_MM = 150;
  /** H34 rear connector: extra +Y (toward cabinet rear) for assembly origin (mm). */
  const H34_ASSEMBLY_Y_OFFSET_MM = 135;
  const SIDE_PANEL_THICKNESS_MM = 16;
  const T1_T2_ASSEMBLY_Y_OFFSET_MM = 39;
  const DEFAULT_FRONT_PANEL_THICKNESS_MM = 16;
  const DEFAULT_FRONT_CLEARANCE_MM = 2.5;
  const DEFAULT_HINGE_CUP_DIAMETER_MM = 35;
  const DEFAULT_HINGE_CUP_DEPTH_MM = 12.5;
  const DEFAULT_HINGE_CUP_CENTER_FROM_EDGE_MM = 22.5;
  const LOCK_PRESETS = {
    razor_long_rounded_1: {
      id: "razor_long_rounded_1",
      name: "Razor Long Rounded 1",
      cutoutShape: "rounded_slot",
      cutoutWidth: 55,
      cutoutHeight: 15.5,
      cutoutRadius: 7.75,
      mountingSurfaceToSlotCenter: 30.5,
    },
  };

  function cabinetWidthFromFridge(fridgeWidth, exteriorSide) {
    return fridgeWidth + (exteriorSide === "none" ? 45 : 61);
  }

  function fridgeWidthFromCabinet(cabinetWidth, exteriorSide) {
    return cabinetWidth - (exteriorSide === "none" ? 45 : 61);
  }

  function normalizeSectionType(type) {
    if (type === "empty") return "blankPanel";
    return type;
  }

  function deriveWidthModel(ui) {
    const cab = ui && ui.cabinet ? ui.cabinet : {};
    const cabinetWidth = Number(cab.width) || 0;
    const exteriorSide = cab.exteriorSide != null ? String(cab.exteriorSide) : "none";
    const hasSidePanel = exteriorSide === "left" || exteriorSide === "right";
    let sidePanelThickness = 0;
    let panelSystemWidth = cabinetWidth;
    let panelSystemOriginX = 0;
    let sidePanelSide = null;
    if (hasSidePanel) {
      sidePanelThickness = SIDE_PANEL_THICKNESS_MM;
      panelSystemWidth = cabinetWidth - sidePanelThickness;
      sidePanelSide = exteriorSide;
      panelSystemOriginX = exteriorSide === "left" ? SIDE_PANEL_THICKNESS_MM : 0;
    }
    return {
      cabinetWidth,
      sidePanelThickness,
      hasSidePanel,
      sidePanelSide,
      panelSystemWidth,
      panelSystemOriginX,
    };
  }

  function boundaryPanelThickness(panelThickness) {
    const pt = Number(panelThickness);
    return (Number.isFinite(pt) ? pt : 15) + 1;
  }

  function boolDefault(value, fallback) {
    if (value === true || value === false) return value;
    return fallback;
  }

  function normalizeFrontHardwareSettings(ui) {
    const source = (ui && ui.frontHardwareSettings) || {};
    const hinge = source.defaultHingeSettings || {};
    const lockPresetId = LOCK_PRESETS[source.lockPresetId] ? source.lockPresetId : "razor_long_rounded_1";
    return {
      frontPanelsEnabled: boolDefault(source.frontPanelsEnabled, true),
      frontPanelThickness:
        Number.isFinite(Number(source.frontPanelThickness)) && Number(source.frontPanelThickness) > 0
          ? Number(source.frontPanelThickness)
          : DEFAULT_FRONT_PANEL_THICKNESS_MM,
      frontClearance:
        Number.isFinite(Number(source.frontClearance)) && Number(source.frontClearance) >= 0
          ? Number(source.frontClearance)
          : DEFAULT_FRONT_CLEARANCE_MM,
      locksEnabled: boolDefault(source.locksEnabled, true),
      lockPresetId,
      defaultHingeSettings: {
        cupDiameter:
          Number.isFinite(Number(hinge.cupDiameter)) && Number(hinge.cupDiameter) > 0
            ? Number(hinge.cupDiameter)
            : DEFAULT_HINGE_CUP_DIAMETER_MM,
        cupDepth:
          Number.isFinite(Number(hinge.cupDepth)) && Number(hinge.cupDepth) > 0
            ? Number(hinge.cupDepth)
            : DEFAULT_HINGE_CUP_DEPTH_MM,
        cupCenterFromEdge:
          Number.isFinite(Number(hinge.cupCenterFromEdge)) && Number(hinge.cupCenterFromEdge) > 0
            ? Number(hinge.cupCenterFromEdge)
            : DEFAULT_HINGE_CUP_CENTER_FROM_EDGE_MM,
        useThreeHinges: boolDefault(hinge.useThreeHinges, false),
        sideDistance:
          hinge.sideDistance === "auto" || hinge.sideDistance == null || hinge.sideDistance === ""
            ? "auto"
            : Number(hinge.sideDistance),
      },
    };
  }

  function deriveBaseParams(ui) {
    const exteriorSide = ui.cabinet.exteriorSide || "none";
    const hasSidePanel = exteriorSide === "left" || exteriorSide === "right";
    const widthModel = deriveWidthModel(ui);
    const frontHardwareSettings = normalizeFrontHardwareSettings(ui);
    const cabinetDepth = Number(ui.cabinet.depth) || 0;
    const midDepth = Math.max(0, cabinetDepth - Number(frontHardwareSettings.frontPanelThickness || 0));
    return {
      Cw: ui.cabinet.width,
      Cd: midDepth,
      cabinetDepth,
      totalDepth: cabinetDepth,
      midDepth,
      FCh: ui.cabinet.height,
      Pt: ui.cabinet.panelThickness,
      exteriorSide,
      hasSidePanel,
      sidePanelSide: hasSidePanel ? exteriorSide : "none",
      hasV5: false,
      v5Side: exteriorSide === "left" ? "right" : exteriorSide === "right" ? "left" : "left",
      fridgeW: ui.fridge.width,
      fridgeD: ui.fridge.depth,
      fridgeH: ui.fridge.height,
      topClearance: ui.clearances.top,
      bottomClearance: ui.clearances.bottom,
      avoidanceEnabled: ui.wheelAvoidance.enabled,
      avoidanceH: ui.wheelAvoidance.enabled ? ui.wheelAvoidance.height : 0,
      avoidanceD: ui.wheelAvoidance.enabled ? ui.wheelAvoidance.depth : 0,
      widthModel,
      frontHardwareSettings,
    };
  }

  function classifyPanel(panel) {
    const { lowerType, upperType } = panel;
    if (lowerType === "bottomClearance") {
      return { ...panel, role: "bottom_boundary", shape: "bottom_system", requiresHSet: false };
    }
    if (upperType === "topClearance") {
      return { ...panel, role: "top_boundary", shape: "top_system", requiresHSet: false };
    }
    if (upperType === "fridge") {
      return { ...panel, role: "fridge_base", shape: "full", requiresHSet: true };
    }
    if (lowerType === "fridge") {
      return { ...panel, role: "fridge_top", shape: "full", requiresHSet: true };
    }
    if (upperType === "flap") {
      return { ...panel, role: "flap_bottom", shape: "full", requiresHSet: true };
    }
    if (lowerType === "flap") {
      return { ...panel, role: "flap_top", shape: "half", requiresHSet: false };
    }
    return { ...panel, role: "generic_separator", shape: "half", requiresHSet: false };
  }

  function buildNormalizedLayout(ui) {
    const Pt = ui.cabinet.panelThickness;
    const boundaryPt = boundaryPanelThickness(Pt);
    const stack = (ui.stack || []).map((section) => ({
      ...section,
      type: normalizeSectionType(section.type),
    }));
    let currentZ = 0;

    const bottomEndHeight = Number(ui.clearances.bottom);
    const topEndHeight = Number(ui.clearances.top);

    const bottomClearanceRegion = {
      z0: currentZ,
      z1: currentZ + bottomEndHeight,
    };
    currentZ += bottomEndHeight;

    const sections = [];
    const panels = [];

    for (let index = 0; index < stack.length; index += 1) {
      const currentSection = stack[index];
      const panelThickness = index === 0 ? boundaryPt : Pt;
      const panel = classifyPanel({
        id: `P${index}`,
        z0: currentZ,
        z1: currentZ + panelThickness,
        centerZ: currentZ + panelThickness / 2,
        lowerType: index === 0 ? "bottomClearance" : stack[index - 1].type,
        upperType: currentSection.type,
        panelThickness,
        panelThicknessRule: index === 0 ? "boundary" : "middle",
      });
      panels.push(panel);
      currentZ += panelThickness;

      const section = {
        id: currentSection.id,
        type: currentSection.type,
        height: currentSection.height,
        z0: currentZ,
        z1: currentZ + currentSection.height,
      };
      sections.push(section);
      currentZ += currentSection.height;
    }

    const topPanel = classifyPanel({
      id: `P${stack.length}`,
      z0: currentZ,
      z1: currentZ + boundaryPt,
      centerZ: currentZ + boundaryPt / 2,
      lowerType: stack.length > 0 ? stack[stack.length - 1].type : "bottomClearance",
      upperType: "topClearance",
      panelThickness: boundaryPt,
      panelThicknessRule: "boundary",
    });
    panels.push(topPanel);
    currentZ += boundaryPt;

    const topClearanceRegion = {
      z0: currentZ,
      z1: currentZ + topEndHeight,
    };
    currentZ += topEndHeight;

    return {
      bottomClearanceRegion,
      topClearanceRegion,
      sections,
      panels,
      boundaryPanelThicknessMm: boundaryPt,
      middlePanelThicknessMm: Pt,
      totalStackHeight: currentZ,
      cabinetHeight: ui.cabinet.height,
      displaySegments: buildDisplaySegments(
        bottomClearanceRegion,
        sections,
        panels,
        topClearanceRegion,
        boundaryPt,
        Pt,
      ),
    };
  }

  function buildDisplaySegments(bottomClearanceRegion, sections, panels, topClearanceRegion, boundaryPt, middlePt) {
    const out = [
      {
        id: "bottom-clearance",
        type: "bottomClearance",
        segmentKind: "endClearance",
        height: bottomClearanceRegion.z1 - bottomClearanceRegion.z0,
        z0: bottomClearanceRegion.z0,
        z1: bottomClearanceRegion.z1,
        locked: true,
      },
    ];
    for (let index = 0; index < sections.length; index += 1) {
      const panel = panels[index];
      const panelHeight = panel.panelThickness != null ? panel.panelThickness : middlePt;
      out.push({
        ...panel,
        type: "horizontalPanel",
        segmentKind: "panel",
        height: panelHeight,
        panelThickness: panelHeight,
        panelThicknessRule: panel.panelThicknessRule || (index === 0 ? "boundary" : "middle"),
        locked: true,
        generated: true,
      });
      out.push({
        ...sections[index],
        segmentKind: "functionZone",
      });
    }
    const topPanel = panels[sections.length];
    out.push({
      ...topPanel,
      type: "horizontalPanel",
      segmentKind: "panel",
      height: boundaryPt,
      panelThickness: boundaryPt,
      panelThicknessRule: "boundary",
      locked: true,
      generated: true,
    });
    out.push({
      id: "top-clearance",
      type: "topClearance",
      segmentKind: "endClearance",
      height: topClearanceRegion.z1 - topClearanceRegion.z0,
      z0: topClearanceRegion.z0,
      z1: topClearanceRegion.z1,
      locked: true,
    });
    return out;
  }

  function generateZi(panels) {
    const ziList = [];
    let index = 1;
    for (const panel of panels) {
      if (panel.shape !== "full" && panel.shape !== "half") continue;
      ziList.push({
        id: `Z${index}`,
        panelId: panel.id,
        centerZ: panel.centerZ,
        z0: panel.z0,
        z1: panel.z1,
        role: panel.role,
        shape: panel.shape,
        requiresHSet: panel.requiresHSet,
      });
      index += 1;
    }
    return ziList;
  }

  /** Cabinet +Z of the top face of the full Zi on the fridge_base panel (directly under the fridge cavity). */
  function findFridgeBaseFullZiTopZ(layout, base) {
    const pt = base && base.Pt != null && Number.isFinite(Number(base.Pt)) ? Number(base.Pt) : 15;
    const zi = (layout && layout.ziList ? layout.ziList : []).find(
      (z) => z && z.role === "fridge_base" && z.shape === "full",
    );
    if (!zi || !Number.isFinite(Number(zi.z0))) return null;
    return Number(zi.z0) + pt;
  }

  function findFridgeSectionHeight(layout, base) {
    const sections = layout && Array.isArray(layout.sections) ? layout.sections : [];
    const fridgeSection = sections.find((section) => section && section.type === "fridge");
    if (fridgeSection && Number.isFinite(Number(fridgeSection.height))) {
      return Number(fridgeSection.height);
    }
    return base && Number.isFinite(Number(base.fridgeH)) ? Number(base.fridgeH) : 0;
  }

  function getZiFullProfile(CW, CD) {
    return [
      [15, 0],
      [15, 105],
      [0, 105],
      [0, CD - 105],
      [15, CD - 105],
      [15, CD],
      [CW - 15, CD],
      [CW - 15, CD - 105],
      [CW, CD - 105],
      [CW, 105],
      [CW - 15, 105],
      [CW - 15, 0],
      [15, 0],
    ];
  }

  function getZiHalfProfile(CW) {
    return [
      [0, 0],
      [0, 45],
      [16, 45],
      [16, 150],
      [CW - 16, 150],
      [CW - 16, 45],
      [CW, 45],
      [CW, 0],
      [0, 0],
    ];
  }

  function getV5Profile(fridgeCutoutHeight) {
    return [
      [0, 0],
      [150, 0],
      [150, fridgeCutoutHeight],
      [0, fridgeCutoutHeight],
      [0, 0],
    ];
  }

  function resolvePanelGeometry(panels, base) {
    const wm = base && base.widthModel;
    const psw =
      wm && Number.isFinite(Number(wm.panelSystemWidth)) && Number(wm.panelSystemWidth) > 0
        ? Number(wm.panelSystemWidth)
        : base.Cw != null
        ? Number(base.Cw)
        : 0;
    return panels.map((panel) => {
      if (panel.shape === "full") {
        return {
          panelId: panel.id,
          profileName: "zi_full_profile",
          thickness: base.Pt,
          outerVector: getZiFullProfile(psw, base.Cd),
          holes: [],
          grooves: [],
        };
      }
      if (panel.shape === "half") {
        return {
          panelId: panel.id,
          profileName: "zi_half_profile",
          thickness: base.Pt,
          outerVector: getZiHalfProfile(psw),
          holes: [],
          grooves: [],
        };
      }
      return {
        panelId: panel.id,
        profileName: panel.shape,
        thickness: base.Pt,
        holes: [],
        grooves: [],
        handledBy: panel.shape === "top_system" ? "T-series" : "B-series",
      };
    });
  }

  function resolveAvoidance(ui, panels, Pt) {
    if (!ui.wheelAvoidance.enabled) {
      return {
        enabled: false,
        inputHeight: 0,
        inputDepth: 0,
        finalMode: "none",
        finalTopZ: 0,
        finalFrontBoardHeight: 0,
        finalDepth: 0,
        fridgeBaseBottomZ: 0,
        fridgeGap: 0,
      };
    }

    const fridgeBase = panels.find((panel) => panel.role === "fridge_base");
    if (!fridgeBase) {
      throw new Error("No fridge_base panel found.");
    }

    const fridgeBaseBottomZ = fridgeBase.z0;
    const inputHeight = ui.wheelAvoidance.height;
    const inputDepth = ui.wheelAvoidance.depth;
    const gap = fridgeBaseBottomZ - inputHeight;

    if (fridgeBaseBottomZ < inputHeight + Pt) {
      throw new Error("Fridge base panel bottom must be >= Avoidance Height + panel thickness.");
    }

    if (gap < 105) {
      return {
        enabled: true,
        inputHeight,
        inputDepth,
        finalMode: "raised",
        finalTopZ: fridgeBaseBottomZ,
        finalFrontBoardHeight: fridgeBaseBottomZ - Pt,
        finalDepth: inputDepth,
        fridgeBaseBottomZ,
        fridgeGap: gap,
      };
    }

    return {
      enabled: true,
      inputHeight,
      inputDepth,
      finalMode: "normal",
      finalTopZ: inputHeight,
      finalFrontBoardHeight: inputHeight - Pt,
      finalDepth: inputDepth,
      fridgeBaseBottomZ,
      fridgeGap: gap,
    };
  }

  function bottomStructureTopZ(panels, layout) {
    const pls = panels || [];
    const bot = pls.find((p) => p && p.role === "bottom_boundary");
    if (bot && Number.isFinite(Number(bot.z1))) return Number(bot.z1);
    const bcr = layout && layout.bottomClearanceRegion;
    if (bcr && Number.isFinite(Number(bcr.z1))) return Number(bcr.z1);
    return 0;
  }

  function hSetRoleForPanel(panel) {
    if (!panel) return "h_mid";
    if (panel.role === "fridge_base") return "fridge_base_support";
    return "h_mid";
  }

  function panelDerivedHPlane(panel, avoidance) {
    if (!panel || !panel.requiresHSet) return null;
    const isRaisedFridgeBase = panel.role === "fridge_base" && avoidance && avoidance.finalMode === "raised";
    const z0 = isRaisedFridgeBase ? panel.z1 : panel.z0 - HSET_HEIGHT;
    const z1 = isRaisedFridgeBase ? panel.z1 + HSET_HEIGHT : panel.z0;
    const role = hSetRoleForPanel(panel);
    const reasons = [String(panel.role || "requiresHSet"), isRaisedFridgeBase ? "raised_avoidance_above" : "below_panel_hset"].filter(
      (x, i, a) => a.indexOf(x) === i,
    );
    return {
      id: `HSet_${panel.id}`,
      sourcePanelId: panel.id,
      sourceRole: panel.role,
      z0,
      z1,
      mode: isRaisedFridgeBase ? "above_panel" : "below_panel",
      members: ["H13", "H24", "H34"],
      role,
      reasons,
    };
  }

  function insertMidGapCandidatesBetween(sortedPlanes, minGapMm) {
    const mids = [];
    let midSeq = 0;
    const minGap = minGapMm != null ? minGapMm : HSET_MIN_GAP_FOR_STRUCTURAL_MID_MM;
    for (let i = 0; i < sortedPlanes.length - 1; i += 1) {
      const a = sortedPlanes[i];
      const b = sortedPlanes[i + 1];
      const gapLow = Number(a.z1);
      const gapHigh = Number(b.z0);
      if (!Number.isFinite(gapLow) || !Number.isFinite(gapHigh)) continue;
      const span = gapHigh - gapLow;
      if (span < minGap) continue;
      midSeq += 1;
      const id = midSeq === 1 ? "HSet_mid" : `HSet_mid_${midSeq}`;
      let z0 = Math.round(gapLow + (span - HSET_HEIGHT) / 2);
      let z1 = z0 + HSET_HEIGHT;
      if (z1 > gapHigh) {
        z1 = Math.round(gapHigh);
        z0 = Math.max(gapLow, z1 - HSET_HEIGHT);
      }
      if (z0 < gapLow) {
        z0 = Math.ceil(gapLow);
        z1 = Math.min(gapHigh, z0 + HSET_HEIGHT);
      }
      if (z1 - z0 < HSET_HEIGHT - 1) continue;
      mids.push({
        id,
        sourcePanelId: null,
        sourceRole: "mid_gap",
        z0,
        z1,
        mode: "structural_mid_gap",
        members: ["H13", "H24", "H34"],
        role: "h_mid",
        reasons: ["structural_mid_gap"],
      });
    }
    return mids;
  }

  function canonicalMergedHSetId(ids) {
    const arr = [...new Set(ids)].filter(Boolean).map(String);
    const panelLinked = arr.filter((id) => /^HSet_P\d+$/.test(id)).sort();
    if (panelLinked.length) return panelLinked[0];
    if (arr.includes("HSet_mid")) return "HSet_mid";
    const midN = arr.filter((id) => /^HSet_mid_\d+$/.test(id)).sort();
    if (midN.length) return midN[0];
    if (arr.includes("HSet_bottom")) return "HSet_bottom";
    return arr.sort()[0] || "HSet_merged";
  }

  function mergeHPlanesCandidates(candidates, tolMm) {
    const tol = tolMm != null ? tolMm : HSET_Z_MERGE_TOL_MM;
    const list = (candidates || []).filter((c) => c && Number.isFinite(Number(c.z0)) && Number.isFinite(Number(c.z1)));
    const used = new Set();
    const out = [];
    for (let i = 0; i < list.length; i += 1) {
      if (used.has(i)) continue;
      const group = [list[i]];
      used.add(i);
      for (let j = i + 1; j < list.length; j += 1) {
        if (used.has(j)) continue;
        const a = group[0];
        const b = list[j];
        if (Math.abs(Number(a.z0) - Number(b.z0)) <= tol && Math.abs(Number(a.z1) - Number(b.z1)) <= tol) {
          group.push(b);
          used.add(j);
        }
      }
      if (group.length === 1) {
        out.push(group[0]);
        continue;
      }
      const ids = group.map((g) => g.id);
      const merged = { ...group[0] };
      merged.id = canonicalMergedHSetId(ids);
      const reasons = [];
      const seenR = new Set();
      for (const g of group) {
        for (const r of g.reasons || []) {
          const s = String(r);
          if (!seenR.has(s)) {
            seenR.add(s);
            reasons.push(s);
          }
        }
      }
      merged.reasons = reasons;
      merged.sourcePanelId = group.map((g) => g.sourcePanelId).find((x) => x != null) || null;
      merged.sourceRole = group.map((g) => g.sourceRole).find((x) => x != null && x !== "mid_gap") || group[0].sourceRole;
      const roles = group.map((g) => g.role).filter(Boolean);
      if (roles.includes("fridge_base_support")) merged.role = "fridge_base_support";
      else if (roles.includes("h_top")) merged.role = "h_top";
      else if (roles.includes("h_bottom")) merged.role = "h_bottom";
      else merged.role = roles[0] || "h_mid";
      merged.anchorType = "merged";
      merged.anchorDescription = group
        .map((g) => (g.anchorDescription != null ? String(g.anchorDescription) : ""))
        .filter(Boolean)
        .join(" | ");
      const refLows = group.map((g) => g.referenceLowZ).filter((x) => x != null && Number.isFinite(Number(x)));
      const refHighs = group.map((g) => g.referenceHighZ).filter((x) => x != null && Number.isFinite(Number(x)));
      if (refLows.length) merged.referenceLowZ = Math.min(...refLows.map(Number));
      if (refHighs.length) merged.referenceHighZ = Math.max(...refHighs.map(Number));
      out.push(merged);
    }
    out.sort((a, b) => Number(a.z0) - Number(b.z0) || String(a.id).localeCompare(String(b.id)));
    return out;
  }

  /**
   * HSet planes: H_bot (avoidance top or bottom boundary, omitted in raised wheel-avoidance mode),
   * panel-linked H_fridge / others, H_mid centered between fridge_base_support and H_top,
   * H_top: z1 always at cabinet top FCh (flush with V-profile top / V顶面). Merged only when z0/z1 match exactly (tol 0).
   *
   * Raised mode: fridge base sits on avoidance top; fridge HSet is above_panel at fridge_base z1
   * (directly above Z full). A separate H_bot band would overlap that stack, so it is not emitted.
   */
  function generateHPlanes(panels, avoidance, layout) {
    const warnings = [];
    const lay = layout || {};
    const pnl = panels || [];
    const av = avoidance || {};
    const fch = lay.cabinetHeight != null ? Number(lay.cabinetHeight) : NaN;
    const omitBottomForRaised = av.enabled === true && av.finalMode === "raised";

    let bottomPlane = null;
    if (!omitBottomForRaised) {
      let botZ0;
      let botZ1;
      let botAnchorType;
      let botAnchorDescription;
      let botRefLow;
      let botRefHigh;
      if (av.enabled === true) {
        let avoidTopZ = NaN;
        if (av.finalTopZ != null && Number.isFinite(Number(av.finalTopZ))) {
          avoidTopZ = Number(av.finalTopZ);
        } else if (av.inputHeight != null && Number.isFinite(Number(av.inputHeight))) {
          avoidTopZ = Number(av.inputHeight);
        }
        if (!Number.isFinite(avoidTopZ)) avoidTopZ = 0;
        botZ0 = avoidTopZ;
        botZ1 = botZ0 + HSET_HEIGHT;
        botAnchorType = "avoidance_top";
        botAnchorDescription = "H_bot starts at avoidance top height";
        botRefLow = avoidTopZ;
        botRefHigh = avoidTopZ;
      } else {
        const bottomTop = bottomStructureTopZ(pnl, lay);
        botZ0 = bottomTop;
        botZ1 = botZ0 + HSET_HEIGHT;
        botAnchorType = "bottom_boundary";
        botAnchorDescription = "Wheel avoidance disabled; H_bot above bottom boundary panel z1";
        botRefLow = bottomTop;
        botRefHigh = bottomTop;
      }
      bottomPlane = {
        id: "HSet_bottom",
        sourcePanelId: null,
        sourceRole: "bottom_structure",
        z0: botZ0,
        z1: botZ1,
        mode: "bottom_band",
        members: ["H13", "H24", "H34"],
        role: "h_bottom",
        reasons: ["bottom_support"],
        anchorType: botAnchorType,
        anchorDescription: botAnchorDescription,
        referenceLowZ: botRefLow,
        referenceHighZ: botRefHigh,
      };
    }

    const panelPlanes = [];
    for (const panel of pnl) {
      const hp = panelDerivedHPlane(panel, av);
      if (!hp) continue;
      if (hp.role === "fridge_base_support") {
        hp.anchorType = hp.mode === "above_panel" ? "fridge_base_above" : "fridge_base_below";
        hp.anchorDescription =
          hp.mode === "above_panel"
            ? "H_fridge: z0 = fridge base panel z1 (raised)"
            : "H_fridge: z1 = fridge base panel z0 (below)";
      } else {
        hp.anchorType = "panel_requires_hset";
        hp.anchorDescription = `HSet for panel ${panel.id} (${String(panel.role || "")})`;
      }
      hp.referenceLowZ = hp.z0;
      hp.referenceHighZ = hp.z1;
      panelPlanes.push(hp);
    }
    panelPlanes.sort((a, b) => Number(a.z0) - Number(b.z0));

    let topPlane = null;
    if (Number.isFinite(fch) && fch >= HSET_HEIGHT) {
      const z1t = fch;
      const z0t = z1t - HSET_HEIGHT;
      topPlane = {
        id: "HSet_top",
        sourcePanelId: null,
        sourceRole: "top_side_connectors",
        z0: z0t,
        z1: z1t,
        mode: "top_band",
        members: ["H13", "H24"],
        role: "h_top",
        reasons: ["top_side_connectors"],
        anchorType: "v_top_cabinet_top",
        anchorDescription: "H_top.z1 = FCh (upper face flush with V board top / cabinet +Z)",
        referenceLowZ: z0t,
        referenceHighZ: z1t,
      };
    }

    let midPlane = null;
    if (topPlane) {
      const fridgeHs = panelPlanes.filter((p) => p.role === "fridge_base_support");
      const gapLow = fridgeHs.length
        ? Math.max(...fridgeHs.map((p) => Number(p.z1)))
        : bottomPlane != null
          ? Number(bottomPlane.z1)
          : bottomStructureTopZ(pnl, lay);
      const gapHigh = Number(topPlane.z0);
      const gapHeight = gapHigh - gapLow;
      if (gapHeight >= HSET_HEIGHT) {
        const centerZ = (gapLow + gapHigh) / 2;
        let mz0 = centerZ - HSET_HEIGHT / 2;
        let mz1 = centerZ + HSET_HEIGHT / 2;
        if (mz0 < gapLow) {
          mz0 = gapLow;
          mz1 = mz0 + HSET_HEIGHT;
        }
        if (mz1 > gapHigh) {
          mz1 = gapHigh;
          mz0 = mz1 - HSET_HEIGHT;
        }
        midPlane = {
          id: "HSet_mid",
          sourcePanelId: null,
          sourceRole: "mid_gap",
          z0: mz0,
          z1: mz1,
          mode: "structural_mid_gap",
          members: ["H13", "H24", "H34"],
          role: "h_mid",
          reasons: ["structural_mid_gap"],
          anchorType: "largest_gap_between_fridge_hset_and_h_top",
          anchorDescription: "H_mid centered between fridge HSet and H_top",
          referenceLowZ: gapLow,
          referenceHighZ: gapHigh,
        };
      } else if (gapHeight > 0) {
        warnings.push("H_mid skipped: gap between fridge HSet and H_top is too small");
      }
    }

    const combined = [];
    if (bottomPlane != null) combined.push(bottomPlane);
    combined.push(...panelPlanes);
    if (midPlane) combined.push(midPlane);
    if (topPlane) combined.push(topPlane);
    combined.sort((a, b) => Number(a.z0) - Number(b.z0) || String(a.id).localeCompare(String(b.id)));

    const merged = mergeHPlanesCandidates(combined, 0);
    return { hPlanes: merged, warnings };
  }

  function validateAll(ui, layout, ziList, avoidance, avoidanceError) {
    const errors = [];
    const warnings = [];
    const infos = [];

    if (Math.abs(layout.totalStackHeight - ui.cabinet.height) > 0.001) {
      errors.push(`Total stack height differs from cabinet height by ${layout.totalStackHeight - ui.cabinet.height} mm.`);
    }
    if (avoidanceError) {
      errors.push(avoidanceError.message);
    }
    const frontSettings = normalizeFrontHardwareSettings(ui);
    const midDepth = Math.max(0, Number(ui.cabinet.depth) - Number(frontSettings.frontPanelThickness || 0));
    if (midDepth - Number(ui.cabinet.panelThickness) <= Number(ui.fridge.depth)) {
      errors.push("Cabinet midDepth minus panel thickness must be greater than fridge depth.");
    }
    for (const section of layout.sections) {
      if (section.type === "drawer" && section.height < 220) {
        errors.push("Drawer height must be >= 220 mm.");
      } else if (section.type === "drawer" && section.height < 250) {
        warnings.push("Drawer height below recommended 250 mm.");
      }
    }
    for (const zi of ziList) {
      if (zi.centerZ > ui.cabinet.height - 300) {
        warnings.push("No Zi should be generated within top keepout zone.");
        break;
      }
    }
    if (ui.wheelAvoidance.enabled && !avoidanceError) {
      if (avoidance.finalMode === "raised") {
        infos.push("Fridge/avoidance gap < 105 mm: raised avoidance mode and above-fridge HSet will be used.");
      } else if (avoidance.finalMode === "normal") {
        infos.push("Fridge/avoidance gap >= 105 mm: below-fridge HSet will be used.");
      }
    }

    return {
      errors,
      warnings,
      infos,
      ok: errors.length === 0,
    };
  }

  const BLANK_PANEL_THICKNESS_MM = 16;

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function getDefaultHingeSideDistance(longSide) {
    return clamp(75 + (Number(longSide) - 300) * (25 / 300), 75, 100);
  }

  function generatesFridgeFrontPanel(type) {
    return type === "drawer" || type === "flap" || type === "blankPanel" || type === "fixedPanel";
  }

  function resolveFridgeFlapDirection(section, allSections) {
    const openableFrontSections = (allSections || []).filter((s) => s && (s.type === "drawer" || s.type === "flap"));
    if (!openableFrontSections.length) return "down_flap";
    const topMostOpenable = openableFrontSections.reduce((top, s) => (Number(s.z1) > Number(top.z1) ? s : top));
    return section && section.id === topMostOpenable.id ? "up_flap" : "down_flap";
  }

  function resolveFridgeFrontType(section, allSections) {
    if (!section) return null;
    if (section.type === "drawer") return "drawer";
    if (section.type === "blankPanel" || section.type === "fixedPanel") return "fixed_panel";
    if (section.type === "flap") return resolveFridgeFlapDirection(section, allSections);
    return null;
  }

  function zoneFrontSettings(input, section, globalSettings) {
    const stack = (input && Array.isArray(input.stack) ? input.stack : []) || [];
    const zone = stack.find((item) => item && item.id === section.id) || {};
    const hinge = Object.assign({}, globalSettings.defaultHingeSettings || {}, zone.hingeSettings || {});
    return {
      frontPanelEnabled: boolDefault(zone.frontPanelEnabled, true),
      lockEnabled: boolDefault(zone.lockEnabled, globalSettings.locksEnabled !== false),
      hingeEnabled: boolDefault(zone.hingeEnabled, true),
      fixedPanelFrontMode: zone.fixedPanelFrontMode || "auto",
      hingeSettings: {
        cupDiameter: Number.isFinite(Number(hinge.cupDiameter)) ? Number(hinge.cupDiameter) : DEFAULT_HINGE_CUP_DIAMETER_MM,
        cupDepth: Number.isFinite(Number(hinge.cupDepth)) ? Number(hinge.cupDepth) : DEFAULT_HINGE_CUP_DEPTH_MM,
        cupCenterFromEdge: Number.isFinite(Number(hinge.cupCenterFromEdge))
          ? Number(hinge.cupCenterFromEdge)
          : DEFAULT_HINGE_CUP_CENTER_FROM_EDGE_MM,
        useThreeHinges: boolDefault(hinge.useThreeHinges, false),
        sideDistance: hinge.sideDistance === "auto" || hinge.sideDistance == null || hinge.sideDistance === "" ? "auto" : Number(hinge.sideDistance),
      },
    };
  }

  function boundaryRefForPanel(panel, confidence) {
    if (!panel) return null;
    return {
      panelId: panel.id,
      lowerType: panel.lowerType,
      upperType: panel.upperType,
      role: panel.role,
      centerZ: panel.centerZ,
      bottomFaceZ: panel.z0,
      topFaceZ: panel.z1,
      panelThickness: panel.panelThickness,
      confidence: confidence || "layout_panel",
    };
  }

  function adjacentPanelBetween(layout, lowerSection, upperSection) {
    const panels = (layout && layout.panels) || [];
    return panels.find(
      (panel) =>
        panel &&
        Number.isFinite(Number(panel.centerZ)) &&
        Number.isFinite(Number(lowerSection && lowerSection.z1)) &&
        Math.abs(Number(panel.centerZ) - (Number(lowerSection.z1) + Number(upperSection.z0)) / 2) <=
          Math.max(2, Number(panel.panelThickness || 0)),
    );
  }

  function findSectionBelow(section, sections) {
    return (sections || [])
      .filter((candidate) => candidate && Number(candidate.z1) <= Number(section.z0) + 0.001)
      .sort((a, b) => Number(b.z1) - Number(a.z1))[0] || null;
  }

  function findSectionAbove(section, sections) {
    return (sections || [])
      .filter((candidate) => candidate && Number(candidate.z0) >= Number(section.z1) - 0.001)
      .sort((a, b) => Number(a.z0) - Number(b.z0))[0] || null;
  }

  function findBoundaryRefBetween(layout, lowerSection, upperSection, warnings) {
    const panel = adjacentPanelBetween(layout, lowerSection, upperSection);
    if (panel) return boundaryRefForPanel(panel, "layout_panel");
    const cpt = Number(layout && layout.middlePanelThicknessMm) || 15;
    const centerZ = (Number(lowerSection.z1) + Number(upperSection.z0)) / 2;
    const ref = {
      panelId: null,
      lowerType: lowerSection.type,
      upperType: upperSection.type,
      role: "fallback_section_boundary",
      centerZ,
      bottomFaceZ: centerZ - cpt / 2,
      topFaceZ: centerZ + cpt / 2,
      panelThickness: cpt,
      confidence: "fallback",
    };
    warnings.push(`FrontPanel: fallback boundary ref between ${lowerSection.id} and ${upperSection.id}.`);
    return ref;
  }

  function buildFridgeFrontContext(pureParams, boardPlan, warnings) {
    const base = (pureParams && pureParams.base) || {};
    const layout = (pureParams && pureParams.layout) || {};
    const input = (pureParams && pureParams.input) || {};
    const globalSettings = base.frontHardwareSettings || normalizeFrontHardwareSettings(input);
    const wm = base.widthModel || deriveWidthModel(input);
    const panels = layout.panels || [];
    const bottomBoundary = panels.find((panel) => panel && panel.role === "bottom_boundary") || panels[0] || null;
    const topBoundary = panels.find((panel) => panel && panel.role === "top_boundary") || panels[panels.length - 1] || null;
    const cpt = Number(base.Pt) || Number(layout.middlePanelThicknessMm) || 15;
    const b3Board = boardPlan && Array.isArray(boardPlan.boards) ? boardPlan.boards.find((board) => board.id === "B3") : null;
    const t3Board = boardPlan && Array.isArray(boardPlan.boards) ? boardPlan.boards.find((board) => board.id === "T3") : null;
    const bottomRailHeight =
      layout.bottomClearanceRegion && Number.isFinite(Number(layout.bottomClearanceRegion.z1))
        ? Number(layout.bottomClearanceRegion.z1)
        : 0;
    const topClearanceZ0 =
      layout.topClearanceRegion && Number.isFinite(Number(layout.topClearanceRegion.z0))
        ? Number(layout.topClearanceRegion.z0)
        : Number(layout.cabinetHeight || base.FCh || 0);
    return {
      CPT: cpt,
      FPT: globalSettings.frontPanelThickness,
      FC: globalSettings.frontClearance,
      globalSettings,
      lockPreset: LOCK_PRESETS[globalSettings.lockPresetId] || LOCK_PRESETS.razor_long_rounded_1,
      cabinetWidth: Number(base.Cw) || Number(input.cabinet && input.cabinet.width) || 0,
      cabinetHeight: Number(layout.cabinetHeight) || Number(base.FCh) || 0,
      panelSystemX0: Number(wm.panelSystemOriginX) || 0,
      panelSystemX1: (Number(wm.panelSystemOriginX) || 0) + (Number(wm.panelSystemWidth) || Number(base.Cw) || 0),
      layout,
      input,
      B3Ref: {
        boardId: b3Board ? "B3" : null,
        sourcePanelId: bottomBoundary ? bottomBoundary.id : null,
        bottomFaceZ: bottomRailHeight,
        topFaceZ: bottomRailHeight + cpt,
        confidence: b3Board ? "board_plan" : "layout_fallback",
      },
      T3Ref: {
        boardId: t3Board ? "T3" : null,
        sourcePanelId: topBoundary ? topBoundary.id : null,
        bottomFaceZ: topClearanceZ0 - cpt,
        topFaceZ: topClearanceZ0,
        confidence: t3Board ? "board_plan" : "layout_fallback",
      },
      warnings,
    };
  }

  function findExistingFixedFrontBoard(boardPlan, section) {
    if (!boardPlan || !Array.isArray(boardPlan.boards) || !section) return null;
    return boardPlan.boards.find((board) => board && board.source && board.source.sectionId === section.id && board.type === "blank_panel") || null;
  }

  function addHingeMetadata(panel, settings, warnings) {
    if (panel.resolvedType !== "up_flap" && panel.resolvedType !== "down_flap") return;
    if (settings.hingeEnabled === false) return;
    const hinge = settings.hingeSettings || {};
    const sideDistance =
      hinge.sideDistance === "auto" || !Number.isFinite(Number(hinge.sideDistance))
        ? getDefaultHingeSideDistance(panel.width)
        : Number(hinge.sideDistance);
    const cupCenterFromEdge = Number(hinge.cupCenterFromEdge) || DEFAULT_HINGE_CUP_CENTER_FROM_EDGE_MM;
    const centerZ = panel.resolvedType === "up_flap" ? panel.z1 - cupCenterFromEdge : panel.z0 + cupCenterFromEdge;
    const centersX = [panel.x0 + sideDistance, panel.x1 - sideDistance];
    if (hinge.useThreeHinges === true) centersX.splice(1, 0, (panel.x0 + panel.x1) / 2);
    panel.hingeHoles = centersX.map((centerX, index) => ({
      id: `${panel.id}_hinge_${index + 1}`,
      diameter: Number(hinge.cupDiameter) || DEFAULT_HINGE_CUP_DIAMETER_MM,
      depth: Number(hinge.cupDepth) || DEFAULT_HINGE_CUP_DEPTH_MM,
      centerX,
      centerY: 0,
      centerZ,
      drillDirection: "-Y",
    }));
    const radius = (Number(hinge.cupDiameter) || DEFAULT_HINGE_CUP_DIAMETER_MM) / 2;
    for (const hole of panel.hingeHoles) {
      if (hole.centerX - radius < panel.x0 || hole.centerX + radius > panel.x1 || hole.centerZ - radius < panel.z0 || hole.centerZ + radius > panel.z1) {
        warnings.push(`FrontPanel ${panel.id}: hinge cup ${hole.id} may be outside panel bounds.`);
      }
    }
  }

  function addLockMetadata(panel, ctx, settings, boundaryRefs, warnings) {
    if (panel.resolvedType !== "drawer" && panel.resolvedType !== "up_flap" && panel.resolvedType !== "down_flap") return;
    if (settings.lockEnabled === false || ctx.globalSettings.locksEnabled === false) return;
    const preset = ctx.lockPreset;
    let ref = null;
    let centerZ = null;
    if (panel.resolvedType === "up_flap") {
      ref = boundaryRefs.lower;
      if (ref) centerZ = Number(ref.topFaceZ) + Number(preset.mountingSurfaceToSlotCenter);
    } else {
      ref = boundaryRefs.upper;
      if (ref) centerZ = Number(ref.bottomFaceZ) - Number(preset.mountingSurfaceToSlotCenter);
    }
    if (!ref || !Number.isFinite(centerZ)) {
      warnings.push(`FrontPanel ${panel.id}: missing divider reference for lock placement.`);
      return;
    }
    const centerX = (panel.x0 + panel.x1) / 2;
    const width = preset.cutoutWidth;
    const height = preset.cutoutHeight;
    panel.lockCutout = {
      presetId: preset.id,
      shape: preset.cutoutShape,
      centerX,
      centerY: 0,
      centerZ,
      width,
      height,
      radius: preset.cutoutRadius,
      x0: centerX - width / 2,
      x1: centerX + width / 2,
      z0: centerZ - height / 2,
      z1: centerZ + height / 2,
      cutDirection: "-Y",
      reference: ref,
    };
    if (panel.lockCutout.x0 < panel.x0 || panel.lockCutout.x1 > panel.x1 || panel.lockCutout.z0 < panel.z0 || panel.lockCutout.z1 > panel.z1) {
      warnings.push(`FrontPanel ${panel.id}: lock cutout may be outside panel bounds.`);
    }
  }

  function buildFridgeFrontPanels(pureParams, boardPlan) {
    const warnings = [];
    const layout = (pureParams && pureParams.layout) || {};
    const sections = [...(layout.sections || [])].sort((a, b) => Number(a.z0) - Number(b.z0));
    const frontSections = sections.filter((section) => section && generatesFridgeFrontPanel(section.type));
    const ctx = buildFridgeFrontContext(pureParams, boardPlan, warnings);
    if (ctx.globalSettings.frontPanelsEnabled === false) return { frontPanels: [], warnings, context: ctx };
    const panels = [];
    for (const section of frontSections) {
      const settings = zoneFrontSettings(ctx.input, section, ctx.globalSettings);
      if (settings.frontPanelEnabled === false) continue;
      const resolvedType = resolveFridgeFrontType(section, sections);
      if (!resolvedType) continue;
      const isFixed = resolvedType === "fixed_panel";
      const x0 = isFixed ? ctx.panelSystemX0 : ctx.panelSystemX0 + ctx.FC;
      const x1 = isFixed ? ctx.panelSystemX1 : ctx.panelSystemX1 - ctx.FC;
      const below = findSectionBelow(section, sections);
      const above = findSectionAbove(section, sections);
      const lowest = frontSections[0] && frontSections[0].id === section.id;
      const highest = frontSections[frontSections.length - 1] && frontSections[frontSections.length - 1].id === section.id;
      let lowerRef = null;
      let upperRef = null;
      let z0;
      let z1;
      let z0Source;
      let z1Source;
      if (below && generatesFridgeFrontPanel(below.type)) {
        lowerRef = findBoundaryRefBetween(layout, below, section, warnings);
        z0 = Number(lowerRef.centerZ) + ctx.FC / 2;
        z0Source = "front_front_boundary";
      } else if (below && below.type === "fridge") {
        lowerRef = findBoundaryRefBetween(layout, below, section, warnings);
        z0 = Number(lowerRef.bottomFaceZ) + ctx.FC;
        z0Source = "fridge_boundary";
      } else if (lowest) {
        z0 = ctx.B3Ref.bottomFaceZ;
        z0Source = "B3";
      } else {
        z0 = Number(section.z0) + ctx.FC / 2;
        z0Source = "fallback_section";
        warnings.push(`FrontPanel ${section.id}: bottom edge used section fallback.`);
      }
      if (above && generatesFridgeFrontPanel(above.type)) {
        upperRef = findBoundaryRefBetween(layout, section, above, warnings);
        z1 = Number(upperRef.centerZ) - ctx.FC / 2;
        z1Source = "front_front_boundary";
      } else if (above && above.type === "fridge") {
        upperRef = findBoundaryRefBetween(layout, section, above, warnings);
        z1 = Number(upperRef.topFaceZ) - ctx.FC;
        z1Source = "fridge_boundary";
      } else if (highest) {
        z1 = ctx.T3Ref.topFaceZ;
        z1Source = "T3";
      } else {
        z1 = Number(section.z1) - ctx.FC / 2;
        z1Source = "fallback_section";
        warnings.push(`FrontPanel ${section.id}: top edge used section fallback.`);
      }
      if (!lowerRef && below) lowerRef = findBoundaryRefBetween(layout, below, section, warnings);
      if (!upperRef && above) upperRef = findBoundaryRefBetween(layout, section, above, warnings);
      const existing = isFixed ? findExistingFixedFrontBoard(boardPlan, section) : null;
      const mode = settings.fixedPanelFrontMode || "auto";
      const generatedAsNewBody = isFixed && mode !== "generate_new" && existing ? false : true;
      const panel = {
        id: `FP_${section.id}`,
        sectionId: section.id,
        sourceZoneType: section.type,
        resolvedType,
        x0,
        x1,
        y0: -ctx.FPT,
        y1: 0,
        z0,
        z1,
        width: x1 - x0,
        height: z1 - z0,
        thickness: ctx.FPT,
        generatedAsNewBody,
        reusedExistingBoardId: generatedAsNewBody ? undefined : existing.id,
        z0Source,
        z1Source,
        lowerBoundaryRef: lowerRef,
        upperBoundaryRef: upperRef,
        B3Ref: lowest ? ctx.B3Ref : undefined,
        T3Ref: highest ? ctx.T3Ref : undefined,
        warnings: [],
      };
      if (panel.width <= 0) panel.warnings.push("front panel width <= 0");
      if (panel.height <= 0) panel.warnings.push("front panel height <= 0");
      addHingeMetadata(panel, settings, warnings);
      addLockMetadata(panel, ctx, settings, { lower: lowerRef, upper: upperRef }, warnings);
      panels.push(panel);
    }
    return { frontPanels: panels, warnings, context: ctx };
  }

  function cloneValidation(validation) {
    const v = validation || {};
    return {
      errors: [...(v.errors || [])],
      warnings: [...(v.warnings || [])],
      infos: [...(v.infos || [])],
      ok: v.ok === true,
    };
  }

  function t3B3OuterVector(CW) {
    return [
      [16, 0],
      [16, 75],
      [0, 75],
      [0, 150],
      [CW, 150],
      [CW, 75],
      [CW - 16, 75],
      [CW - 16, 0],
      [16, 0],
    ];
  }

  /** Local YZ: Y+ front→rear, Z+ bottom→top; depthY 150; rear Zi slots at Y 100–150. */
  function getV12Profile(FCh, ziList, bottomEndHeight, topEndHeight, boundaryPt) {
    const bottomH = Number.isFinite(Number(bottomEndHeight)) ? Number(bottomEndHeight) : DEFAULT_BOTTOM_CLEARANCE_MM;
    const topH = Number.isFinite(Number(topEndHeight)) ? Number(topEndHeight) : DEFAULT_TOP_CLEARANCE_MM;
    const bpt = Number.isFinite(Number(boundaryPt)) ? Number(boundaryPt) : boundaryPanelThickness(15);
    const bottomPanelTopZ = bottomH + bpt;
    const topPanelTopZ = FCh - topH;
    const topPanelBottomZ = topPanelTopZ - bpt;
    const sorted = [...(ziList || [])].sort((a, b) => a.centerZ - b.centerZ);
    const pts = [
      [70, 0],
      [150, 0],
    ];
    for (let i = 0; i < sorted.length; i += 1) {
      const zc = sorted[i].centerZ;
      pts.push([150, zc - 8], [100, zc - 8], [100, zc + 8], [150, zc + 8]);
    }
    pts.push(
      [150, FCh],
      [70, FCh],
      [70, topPanelTopZ],
      [80, topPanelTopZ],
      [80, topPanelBottomZ],
      [0, topPanelBottomZ],
      [0, bottomPanelTopZ],
      [80, bottomPanelTopZ],
      [80, bottomH],
      [70, bottomH],
      [70, 0],
    );
    return pts;
  }

  /**
   * Rear vertical member in local YZ; Z origin at global finalAvoidanceTopZ.
   * Slots only for full Zi; front-cut at Y 0–50; top-right T4/T5 L slot.
   */
  function getV34Profile(FCh, finalAvoidanceTopZ, ziList) {
    const top = finalAvoidanceTopZ != null ? finalAvoidanceTopZ : 0;
    const V34h = FCh - top;
    const hh = Math.max(V34h, 0);
    const fullLocals = (ziList || [])
      .filter((z) => z.shape === "full")
      .map((z) => ({
        ...z,
        localZi: z.centerZ - top,
      }))
      .sort((a, b) => b.localZi - a.localZi);

    const pts = [[0, 0], [150, 0]];
    if (hh >= 121) {
      pts.push([150, hh - 121]);
      pts.push(
        [134, hh - 121],
        [134, hh - 16],
        [45, hh - 16],
        [45, hh],
        [0, hh],
      );
    } else {
      pts.push([150, hh], [0, hh]);
    }

    let currentZ = hh;
    for (let i = 0; i < fullLocals.length; i += 1) {
      let zTop = fullLocals[i].localZi + 8;
      let zBot = fullLocals[i].localZi - 8;
      zBot = Math.max(0, zBot);
      zTop = Math.min(hh, Math.max(zTop, zBot));
      if (zTop <= zBot) continue;
      if (currentZ > zTop) {
        pts.push([0, zTop]);
      }
      pts.push([50, zTop], [50, zBot], [0, zBot]);
      currentZ = zBot;
    }
    const last = pts[pts.length - 1];
    if (last[0] !== 0 || last[1] !== 0) {
      pts.push([0, 0]);
    }
    return pts;
  }

  function copyZiListForSource(ziList) {
    return (ziList || []).map((z) => ({
      id: z.id,
      panelId: z.panelId,
      centerZ: z.centerZ,
      z0: z.z0,
      z1: z.z1,
      role: z.role,
      shape: z.shape,
      requiresHSet: z.requiresHSet,
    }));
  }

  function getBoardById(boardPlan, boardId) {
    if (!boardPlan || !boardPlan.boards || boardId == null || boardId === "") return null;
    for (let i = 0; i < boardPlan.boards.length; i += 1) {
      if (boardPlan.boards[i].id === boardId) return boardPlan.boards[i];
    }
    return null;
  }

  function getVectorBBox(outerVector) {
    if (!outerVector || !outerVector.length) {
      return { minX: 0, maxX: 0, minY: 0, maxY: 0, width: 0, height: 0 };
    }
    let minX = outerVector[0][0];
    let maxX = minX;
    let minY = outerVector[0][1];
    let maxY = minY;
    for (let i = 1; i < outerVector.length; i += 1) {
      const x = outerVector[i][0];
      const y = outerVector[i][1];
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
    }
    return {
      minX,
      maxX,
      minY,
      maxY,
      width: maxX - minX,
      height: maxY - minY,
    };
  }

  function isVectorClosed(outerVector) {
    if (!outerVector || outerVector.length < 2) return false;
    const a = outerVector[0];
    const b = outerVector[outerVector.length - 1];
    return a[0] === b[0] && a[1] === b[1];
  }

  function pointExists(outerVector, point) {
    if (!outerVector || !point || point.length < 2) return false;
    const px = point[0];
    const py = point[1];
    for (let i = 0; i < outerVector.length; i += 1) {
      const p = outerVector[i];
      if (p[0] === px && p[1] === py) return true;
    }
    return false;
  }

  function dumpBoardVector(boardPlan, boardId) {
    const board = getBoardById(boardPlan, boardId);
    if (!board) {
      return {
        id: boardId,
        name: null,
        series: null,
        type: null,
        profilePlane: null,
        thickness: null,
        outerVector: null,
        bbox: null,
        pointCount: 0,
        isClosed: false,
      };
    }
    const ov = board.outerVector;
    const bbox = ov ? getVectorBBox(ov) : null;
    return {
      id: board.id,
      name: board.name,
      series: board.series,
      type: board.type,
      profilePlane: board.profilePlane,
      thickness: board.thickness,
      outerVector: ov,
      bbox,
      pointCount: ov ? ov.length : 0,
      isClosed: ov ? isVectorClosed(ov) : false,
    };
  }

  /**
   * Validates V1–V4 board outerVectors against BoardPlan / PureParams (debug only).
   */
  function verifyVSeriesVectors(pureParams, boardPlan) {
    const errors = [];
    const warnings = [];
    const infos = [];
    const checks = [];

    function addCheck(id, status, message) {
      checks.push({ id, status, message });
      if (status === "fail") errors.push(message);
      else if (status === "warn") warnings.push(message);
      else if (status === "info") infos.push(message);
    }

    if (!pureParams || !boardPlan) {
      addCheck("input", "fail", "Missing pureParams or boardPlan.");
      return { errors, warnings, infos, ok: false, checks };
    }

    const layout = pureParams.layout || {};
    const base = pureParams.base || {};
    const ziList = layout.ziList || [];
    const FCh =
      layout.cabinetHeight != null ? layout.cabinetHeight : base.FCh != null ? base.FCh : 0;
    const avoid = pureParams.avoidance || {};
    const finalAvoidanceTopZ =
      avoid.enabled === true && avoid.finalTopZ != null ? avoid.finalTopZ : 0;
    const V34h = FCh - finalAvoidanceTopZ;
    const bottomEndHeight =
      layout.bottomClearanceRegion && Number.isFinite(Number(layout.bottomClearanceRegion.z1 - layout.bottomClearanceRegion.z0))
        ? Number(layout.bottomClearanceRegion.z1 - layout.bottomClearanceRegion.z0)
        : DEFAULT_BOTTOM_CLEARANCE_MM;
    const topEndHeight =
      layout.topClearanceRegion && Number.isFinite(Number(layout.topClearanceRegion.z1 - layout.topClearanceRegion.z0))
        ? Number(layout.topClearanceRegion.z1 - layout.topClearanceRegion.z0)
        : DEFAULT_TOP_CLEARANCE_MM;
    const boundaryPt = Number.isFinite(Number(layout.boundaryPanelThicknessMm))
      ? Number(layout.boundaryPanelThicknessMm)
      : boundaryPanelThickness(base.Pt);
    const bottomPanelTopZ = bottomEndHeight + boundaryPt;
    const topPanelTopZ = FCh - topEndHeight;
    const topPanelBottomZ = topPanelTopZ - boundaryPt;

    const v12TopPoints = [
      [150, FCh],
      [70, FCh],
      [70, topPanelTopZ],
      [80, topPanelTopZ],
      [80, topPanelBottomZ],
      [0, topPanelBottomZ],
    ];
    const v12BottomPoints = [
      [0, bottomPanelTopZ],
      [80, bottomPanelTopZ],
      [80, bottomEndHeight],
      [70, bottomEndHeight],
      [70, 0],
    ];

    for (let vi = 0; vi < 2; vi += 1) {
      const vid = vi === 0 ? "V1" : "V2";
      const board = getBoardById(boardPlan, vid);
      if (!board) {
        addCheck(`${vid}_exists`, "fail", `${vid}: board missing from boardPlan.`);
        continue;
      }
      addCheck(`${vid}_exists`, "pass", `${vid}: board present.`);
      if (board.profilePlane !== "YZ") {
        addCheck(`${vid}_profilePlane`, "fail", `${vid}: profilePlane must be YZ, got ${board.profilePlane}.`);
      } else {
        addCheck(`${vid}_profilePlane`, "pass", `${vid}: profilePlane is YZ.`);
      }
      const ov = board.outerVector;
      if (!ov || !ov.length) {
        addCheck(`${vid}_outerVector`, "fail", `${vid}: outerVector missing or empty.`);
        continue;
      }
      if (!isVectorClosed(ov)) {
        addCheck(`${vid}_closed`, "fail", `${vid}: outerVector is not closed.`);
      } else {
        addCheck(`${vid}_closed`, "pass", `${vid}: outerVector is closed.`);
      }
      const bbox = getVectorBBox(ov);
      if (bbox.maxX !== 150) {
        addCheck(`${vid}_bbox_maxY_local`, "fail", `${vid}: bbox max of point[0] (local Y) must be 150, got ${bbox.maxX}.`);
      } else {
        addCheck(`${vid}_bbox_maxY_local`, "pass", `${vid}: bbox max local Y (index 0) is 150.`);
      }
      if (bbox.maxY !== FCh) {
        addCheck(`${vid}_bbox_maxZ_local`, "fail", `${vid}: bbox max of point[1] (local Z) must be FCh (${FCh}), got ${bbox.maxY}.`);
      } else {
        addCheck(`${vid}_bbox_maxZ_local`, "pass", `${vid}: bbox max local Z (index 1) equals FCh.`);
      }
      for (let zi = 0; zi < ziList.length; zi += 1) {
        const z = ziList[zi];
        const slot = [
          [150, z.centerZ - 8],
          [100, z.centerZ - 8],
          [100, z.centerZ + 8],
          [150, z.centerZ + 8],
        ];
        let allSlot = true;
        for (let s = 0; s < slot.length; s += 1) {
          if (!pointExists(ov, slot[s])) allSlot = false;
        }
        if (!allSlot) {
          addCheck(
            `${vid}_zi_slot_${z.id}`,
            "fail",
            `${vid}: missing rear slot corners for Zi ${z.id} (centerZ=${z.centerZ}).`,
          );
        } else {
          addCheck(`${vid}_zi_slot_${z.id}`, "pass", `${vid}: rear slot for Zi ${z.id} present.`);
        }
      }
      for (let t = 0; t < v12TopPoints.length; t += 1) {
        if (!pointExists(ov, v12TopPoints[t])) {
          addCheck(`${vid}_top_point_${t}`, "fail", `${vid}: missing top profile point ${JSON.stringify(v12TopPoints[t])}.`);
        } else {
          addCheck(`${vid}_top_point_${t}`, "pass", `${vid}: top point ${JSON.stringify(v12TopPoints[t])} present.`);
        }
      }
      for (let b = 0; b < v12BottomPoints.length; b += 1) {
        if (!pointExists(ov, v12BottomPoints[b])) {
          addCheck(
            `${vid}_bottom_point_${b}`,
            "fail",
            `${vid}: missing bottom feature point ${JSON.stringify(v12BottomPoints[b])}.`,
          );
        } else {
          addCheck(`${vid}_bottom_point_${b}`, "pass", `${vid}: bottom point ${JSON.stringify(v12BottomPoints[b])} present.`);
        }
      }
    }

    const lSlotPoints = [
      [150, V34h - 121],
      [134, V34h - 121],
      [134, V34h - 16],
      [45, V34h - 16],
      [45, V34h],
    ];

    for (let vi = 0; vi < 2; vi += 1) {
      const vid = vi === 0 ? "V3" : "V4";
      const board = getBoardById(boardPlan, vid);
      if (!board) {
        addCheck(`${vid}_exists`, "fail", `${vid}: board missing from boardPlan.`);
        continue;
      }
      addCheck(`${vid}_exists`, "pass", `${vid}: board present.`);
      if (board.profilePlane !== "YZ") {
        addCheck(`${vid}_profilePlane`, "fail", `${vid}: profilePlane must be YZ, got ${board.profilePlane}.`);
      } else {
        addCheck(`${vid}_profilePlane`, "pass", `${vid}: profilePlane is YZ.`);
      }
      const ov = board.outerVector;
      if (!ov || !ov.length) {
        addCheck(`${vid}_outerVector`, "fail", `${vid}: outerVector missing or empty.`);
        continue;
      }
      if (!isVectorClosed(ov)) {
        addCheck(`${vid}_closed`, "fail", `${vid}: outerVector is not closed.`);
      } else {
        addCheck(`${vid}_closed`, "pass", `${vid}: outerVector is closed.`);
      }
      addCheck(
        "V34_finalAvoidanceTopZ",
        "info",
        `finalAvoidanceTopZ=${finalAvoidanceTopZ} (avoidance.enabled=${avoid.enabled === true}).`,
      );
      if (V34h <= 121) {
        addCheck("V34h_min", "fail", `V34h (${V34h}) must be > 121.`);
      } else {
        addCheck("V34h_min", "pass", `V34h (${V34h}) > 121.`);
      }
      const bbox = getVectorBBox(ov);
      if (bbox.maxX !== 150) {
        addCheck(`${vid}_bbox_maxY_local`, "fail", `${vid}: bbox max of point[0] must be 150, got ${bbox.maxX}.`);
      } else {
        addCheck(`${vid}_bbox_maxY_local`, "pass", `${vid}: bbox max local Y is 150.`);
      }
      if (bbox.maxY !== V34h) {
        addCheck(`${vid}_bbox_maxZ_local`, "fail", `${vid}: bbox max of point[1] must be V34h (${V34h}), got ${bbox.maxY}.`);
      } else {
        addCheck(`${vid}_bbox_maxZ_local`, "pass", `${vid}: bbox max local Z equals V34h.`);
      }
      for (let zi = 0; zi < ziList.length; zi += 1) {
        const z = ziList[zi];
        const localZi = z.centerZ - finalAvoidanceTopZ;
        const zBot = Math.max(0, localZi - 8);
        const zTop = Math.min(V34h, localZi + 8);
        const slot =
          zTop > zBot
            ? [
                [0, zBot],
                [50, zBot],
                [50, zTop],
                [0, zTop],
              ]
            : null;
        const allFour = slot && slot.length === 4 ? slot.every((pt) => pointExists(ov, pt)) : false;
        if (z.shape === "full") {
          if (!slot || zTop <= zBot) {
            addCheck(
              `${vid}_full_slot_${z.id}`,
              "warn",
              `${vid}: full Zi ${z.id} slot collapsed after clamp (localZi=${localZi}).`,
            );
          } else if (!allFour) {
            addCheck(
              `${vid}_full_slot_${z.id}`,
              "fail",
              `${vid}: full Zi ${z.id} front slot corners missing after clamp (localZi=${localZi}).`,
            );
          } else {
            addCheck(`${vid}_full_slot_${z.id}`, "pass", `${vid}: full Zi ${z.id} slot present.`);
          }
        } else if (z.shape === "half") {
          if (allFour) {
            addCheck(
              `${vid}_half_slot_${z.id}`,
              "fail",
              `${vid}: half Zi ${z.id} must not have all four front slot corners (localZi=${localZi}).`,
            );
          } else {
            addCheck(`${vid}_half_slot_${z.id}`, "pass", `${vid}: half Zi ${z.id} correctly has no full slot quad.`);
          }
        }
      }
      if (V34h > 121) {
        for (let l = 0; l < lSlotPoints.length; l += 1) {
          if (!pointExists(ov, lSlotPoints[l])) {
            addCheck(
              `${vid}_lslot_${l}`,
              "fail",
              `${vid}: missing T4/T5 L-slot point ${JSON.stringify(lSlotPoints[l])}.`,
            );
          } else {
            addCheck(`${vid}_lslot_${l}`, "pass", `${vid}: L-slot point ${JSON.stringify(lSlotPoints[l])} present.`);
          }
        }
      }
    }

    return {
      errors,
      warnings,
      infos,
      ok: errors.length === 0,
      checks,
    };
  }

  function formatBoardPlacementSummary(placement) {
    if (!placement || typeof placement !== "object") return "";
    if (placement.side != null && placement.fridgeH != null) {
      return `YZ side=${placement.side} fridgeH=${placement.fridgeH}`;
    }
    if (placement.avoidanceRole === "front") {
      return `XZ Cw×H ${placement.widthX}×${placement.heightZ}`;
    }
    if (placement.avoidanceRole === "top") {
      return `XY Cw×D ${placement.widthX}×${placement.depthY}`;
    }
    if (placement.series === "S") {
      return `S ${placement.id || "SidePanel"}`.trim();
    }
    if (placement.series === "T" || placement.series === "B") {
      return `${placement.series} ${placement.id || ""} ${placement.region || ""}`.trim();
    }
    if (placement.series === "V" && placement.height != null && placement.depthY != null) {
      return `YZ ${placement.id || ""} h=${placement.height} dY=${placement.depthY} ${placement.profile || ""}`.trim();
    }
    if (placement.heightZ != null && placement.mode != null && placement.hPlaneId != null) {
      return `H z0=${placement.z0}-z1=${placement.z1} h=${placement.heightZ} mode=${placement.mode} (${placement.hPlaneId})`;
    }
    if (placement.heightZ != null && placement.thicknessY != null) {
      return `XZ x0=${placement.x0} z0=${placement.z0} ${placement.widthX}x${placement.heightZ} tY=${placement.thicknessY}`;
    }
    return `XY z0=${placement.z0}-z1=${placement.z1} cZ=${placement.centerZ} ${placement.widthX}x${placement.depthY} tZ=${placement.thicknessZ}`;
  }

  function boardSortKey(board, cabinetHeight) {
    const p = board.placement;
    if (p && typeof p.sortZ === "number") return p.sortZ;
    if (p && p.z0 != null && !Number.isNaN(p.z0)) return p.z0;
    const id = String(board.id || "");
    if (id === "B1") return -300;
    if (id === "SidePanel") return -310;
    if (id === "B2") return -299;
    if (id === "B3") return -298;
    if (id === "V1") return -205;
    if (id === "V2") return -204;
    if (id === "V3") return -203;
    if (id === "V4") return -202;
    if (id === "V5") return -200;
    if (id === "AvoidanceFront") return -150;
    if (id === "AvoidanceTop") return -149;
    if (id.charAt(0) === "T") {
      const n = parseInt(id.slice(1), 10);
      return cabinetHeight + (Number.isFinite(n) ? n : 0);
    }
    return 0;
  }

  /**
   * Default manufacturing / CAM metadata envelope (reserved; not yet used for logic).
   * Top-level profilePlane, outerVector, thickness remain authoritative for CAD v0.x;
   * geometry.* mirrors them for forward-compatible pipelines.
   */
  function defaultManufacturingMetadata(board) {
    const th = board.thickness;
    const thicknessMm =
      th != null && th !== '' && Number.isFinite(Number(th)) ? Number(th) : null;
    return {
      geometry: {
        profilePlane: board.profilePlane != null ? board.profilePlane : null,
        outerVector: board.outerVector != null ? board.outerVector : null,
        thickness:
          board.thickness != null && board.thickness !== '' ? board.thickness : null,
        thicknessMm,
      },
      material: {
        species: null,
        grade: null,
        blankSku: null,
        core: null,
        veneer: null,
        supplier: null,
      },
      faces: {
        faceFinishFront: null,
        faceFinishBack: null,
        paintCode: null,
      },
      edges: {
        edgeBandingPreset: null,
        perEdge: null,
      },
      grain: {
        requestedDirection: null,
        flipAllowed: null,
        matchParentId: null,
      },
      machining: {
        operations: null,
        drillHelperPreset: null,
        constraints: null,
      },
      labeling: {
        cncLabel: null,
        customerLabel: null,
        barcode: null,
      },
      nesting: {
        sheetId: null,
        nestingJobId: null,
        rotationDeg: null,
        priority: null,
        kerfMm: null,
      },
      placement: {
        manufacturingNotes: null,
        workpieceId: null,
        stationHints: null,
      },
    };
  }

  function attachManufacturingMetadata(board) {
    if (!board || typeof board !== 'object') return board;
    const existing = board.metadata && typeof board.metadata === 'object' ? board.metadata : {};
    const base = defaultManufacturingMetadata(board);
    const keys = Object.keys(base);
    const merged = {};
    for (let i = 0; i < keys.length; i += 1) {
      const k = keys[i];
      const def = base[k];
      const ext = existing[k] && typeof existing[k] === 'object' ? existing[k] : {};
      merged[k] = Object.assign({}, def, ext);
    }
    return Object.assign({}, board, {
      geometry: merged.geometry,
      material: merged.material,
      faces: merged.faces,
      edges: merged.edges,
      grain: merged.grain,
      machining: merged.machining,
      labeling: merged.labeling,
      nesting: merged.nesting,
      metadata: merged,
    });
  }

  /**
   * Integrity audit: every board must carry metadata shells + legacy geometry mirror.
   * Does not validate optional null fields inside shells.
   */
  function auditBoardMetadata(boardPlan) {
    const summary = {
      missingGeometry: [],
      missingMaterial: [],
      missingFaces: [],
      missingEdges: [],
      missingGrain: [],
      missingMachining: [],
      missingLabeling: [],
      missingNesting: [],
      missingPlacement: [],
      legacyGeometryMismatch: [],
    };
    const errors = [];
    const warnings = [];
    const checkedBoardIds = [];

    function shellOk(v) {
      return v != null && typeof v === 'object' && !Array.isArray(v);
    }

    function pushMissing(key, id) {
      const arr = summary[key];
      if (arr && id != null && arr.indexOf(id) === -1) arr.push(id);
    }

    if (!boardPlan || typeof boardPlan !== 'object') {
      errors.push('auditBoardMetadata: boardPlan is missing or not an object.');
      return {
        ok: false,
        boardCount: 0,
        checkedBoardIds,
        errors,
        warnings,
        summary,
      };
    }

    const boards = boardPlan.boards;
    if (!Array.isArray(boards)) {
      errors.push('auditBoardMetadata: boardPlan.boards is not an array.');
      return {
        ok: false,
        boardCount: 0,
        checkedBoardIds,
        errors,
        warnings,
        summary,
      };
    }

    for (let i = 0; i < boards.length; i += 1) {
      const board = boards[i];
      const id = board && board.id != null ? String(board.id) : `(index ${i})`;
      checkedBoardIds.push(id);

      if (!board || typeof board !== 'object') {
        errors.push(`Board ${id}: not an object.`);
        pushMissing('missingGeometry', id);
        continue;
      }

      if (!shellOk(board.geometry)) pushMissing('missingGeometry', id);
      if (!shellOk(board.material)) pushMissing('missingMaterial', id);
      if (!shellOk(board.faces)) pushMissing('missingFaces', id);
      if (!shellOk(board.edges)) pushMissing('missingEdges', id);
      if (!shellOk(board.grain)) pushMissing('missingGrain', id);
      if (!shellOk(board.machining)) pushMissing('missingMachining', id);
      if (!shellOk(board.labeling)) pushMissing('missingLabeling', id);
      if (!shellOk(board.nesting)) pushMissing('missingNesting', id);
      if (!shellOk(board.placement)) pushMissing('missingPlacement', id);

      if (!shellOk(board.geometry)) {
        errors.push(`Board ${id}: geometry shell missing or invalid.`);
      } else {
        let mismatch = false;
        if (board.profilePlane !== board.geometry.profilePlane) {
          mismatch = true;
          errors.push(
            `Board ${id}: profilePlane mismatch (top ${String(board.profilePlane)} vs geometry ${String(board.geometry.profilePlane)}).`,
          );
        }
        if (board.outerVector !== board.geometry.outerVector) {
          mismatch = true;
          errors.push(`Board ${id}: outerVector reference mismatch vs geometry.outerVector.`);
        }
        if (board.thickness !== board.geometry.thickness) {
          mismatch = true;
          errors.push(
            `Board ${id}: thickness mismatch (top ${String(board.thickness)} vs geometry ${String(board.geometry.thickness)}).`,
          );
        }
        if (mismatch && summary.legacyGeometryMismatch.indexOf(id) === -1) {
          summary.legacyGeometryMismatch.push(id);
        }
      }

      if (!shellOk(board.material)) errors.push(`Board ${id}: material shell missing or invalid.`);
      if (!shellOk(board.faces)) errors.push(`Board ${id}: faces shell missing or invalid.`);
      if (!shellOk(board.edges)) errors.push(`Board ${id}: edges shell missing or invalid.`);
      if (!shellOk(board.grain)) errors.push(`Board ${id}: grain shell missing or invalid.`);
      if (!shellOk(board.machining)) errors.push(`Board ${id}: machining shell missing or invalid.`);
      if (!shellOk(board.labeling)) errors.push(`Board ${id}: labeling shell missing or invalid.`);
      if (!shellOk(board.nesting)) errors.push(`Board ${id}: nesting shell missing or invalid.`);
      if (!shellOk(board.placement)) errors.push(`Board ${id}: placement shell missing or invalid.`);
    }

    const ok = errors.length === 0;

    return {
      ok,
      boardCount: boards.length,
      checkedBoardIds,
      errors,
      warnings,
      summary,
      widthModel: boardPlan.widthModel != null ? boardPlan.widthModel : null,
    };
  }

  function profileSpanVMaxMm(outerVector) {
    if (!Array.isArray(outerVector)) return 0;
    let m = 0;
    for (let i = 0; i < outerVector.length; i += 1) {
      const p = outerVector[i];
      if (p && typeof p === "object" && p.length >= 2) {
        const v = Number(p[1]);
        if (Number.isFinite(v)) m = Math.max(m, v);
      }
    }
    return m;
  }

  /** Global axis-aligned extents (mm) from profile plane + outerVector bbox + thickness (same convention as Fusion assembly audit). */
  function expectedGlobalSizeMmFromBoard(board) {
    if (!board || typeof board !== "object") return null;
    const bb = getVectorBBox(board.outerVector);
    if (!bb || !(bb.width > 0) || !(bb.height > 0)) return null;
    const wu = bb.width;
    const hv = bb.height;
    const tRaw = board.thickness != null ? Number(board.thickness) : NaN;
    const t = Number.isFinite(tRaw) ? tRaw : 15;
    const p = String(board.profilePlane || "XY").toUpperCase();
    if (p === "XZ") return { sizeX: wu, sizeY: t, sizeZ: hv };
    if (p === "YZ") return { sizeX: t, sizeY: wu, sizeZ: hv };
    return { sizeX: wu, sizeY: hv, sizeZ: t };
  }

  function nominalBTPlacementAuditExpected(boardId, cabinetWidthMm, bottomRailHeightMm, topRailHeightMm) {
    const cw = Number(cabinetWidthMm);
    if (!Number.isFinite(cw)) return null;
    const bottomH = Number.isFinite(Number(bottomRailHeightMm)) ? Number(bottomRailHeightMm) : DEFAULT_BOTTOM_CLEARANCE_MM;
    const topH = Number.isFinite(Number(topRailHeightMm)) ? Number(topRailHeightMm) : DEFAULT_TOP_CLEARANCE_MM;
    const T = {
      B1: { sizeX: cw, sizeY: 16, sizeZ: bottomH },
      B2: { sizeX: cw, sizeY: 15, sizeZ: bottomH },
      B3: { sizeX: cw, sizeY: 150, sizeZ: 15 },
      T1: { sizeX: cw, sizeY: 16, sizeZ: topH },
      T2: { sizeX: cw, sizeY: 15, sizeZ: topH },
      T3: { sizeX: cw, sizeY: 150, sizeZ: 15 },
    };
    return T[boardId] || null;
  }

  function nearSameGlobalSizesMm(a, b, tolMm) {
    const tol = tolMm != null ? tolMm : 3;
    if (!a || !b) return false;
    return (
      Math.abs(Number(a.sizeX) - Number(b.sizeX)) <= tol &&
      Math.abs(Number(a.sizeY) - Number(b.sizeY)) <= tol &&
      Math.abs(Number(a.sizeZ) - Number(b.sizeZ)) <= tol
    );
  }

  function orientationFromBoard(board) {
    const pp = (board && board.profilePlane) || "XY";
    const map = {
      XY: { thicknessAxis: "+Z", profileAxisU: "+X", profileAxisV: "+Y" },
      XZ: { thicknessAxis: "+Y", profileAxisU: "+X", profileAxisV: "+Z" },
      YZ: { thicknessAxis: "+X", profileAxisU: "+Y", profileAxisV: "+Z" },
    };
    const ax = map[pp] || map.XY;
    return {
      profilePlane: pp,
      thicknessAxis: ax.thicknessAxis,
      profileAxisU: ax.profileAxisU,
      profileAxisV: ax.profileAxisV,
    };
  }

  function hSetGroupIdFromBoardId(boardId) {
    return String(boardId).replace(/_H(?:13|24|34)$/, "");
  }

  /** Resolve HSet vertical span (mm) from source / placement / outerVector fallback. */
  function getHSetZRange(board) {
    if (!board || typeof board !== "object") return null;
    const src = board.source || {};
    let z0 = src.z0 != null ? Number(src.z0) : NaN;
    let z1 = src.z1 != null ? Number(src.z1) : NaN;
    if (!Number.isFinite(z0) || !Number.isFinite(z1)) {
      const hp = src.hPlane;
      if (hp && typeof hp === "object") {
        if (!Number.isFinite(z0) && hp.z0 != null) z0 = Number(hp.z0);
        if (!Number.isFinite(z1) && hp.z1 != null) z1 = Number(hp.z1);
      }
    }
    const pl = board.placement || {};
    if (!Number.isFinite(z0) && pl.z0 != null) z0 = Number(pl.z0);
    if (!Number.isFinite(z1) && pl.z1 != null) z1 = Number(pl.z1);
    let warning = null;
    if (!Number.isFinite(z0) || !Number.isFinite(z1)) {
      const bb = getVectorBBox(board.outerVector);
      if (bb && (bb.height > 0 || bb.width > 0)) {
        const span = bb.height > 0 ? bb.height : bb.width;
        z0 = 0;
        z1 = span;
        warning = `buildAssemblyPlacementPlan: HSet ${board.id} Z range inferred from outerVector span only (fallback).`;
      } else {
        return null;
      }
    }
    return { z0, z1, warning };
  }

  function classifyHSetGroupRole(z0, pureParams, fch) {
    const layout = (pureParams && pureParams.layout) || {};
    const bcr = layout.bottomClearanceRegion;
    let bottomTop = 150;
    if (bcr && bcr.z1 != null && Number.isFinite(Number(bcr.z1))) bottomTop = Number(bcr.z1);
    const panels = layout.panels || [];
    let fridgeZ0 = Number(fch) * 0.35;
    for (let pi = 0; pi < panels.length; pi += 1) {
      const panel = panels[pi];
      if (panel && panel.role === "fridge_base" && panel.z0 != null) {
        fridgeZ0 = Number(panel.z0);
        break;
      }
    }
    const z = Number(z0);
    if (!Number.isFinite(z)) return "unknown";
    if (z <= bottomTop + 100) return "H bottom";
    if (z <= fridgeZ0 + 200) return "H mid";
    return "H upper";
  }

  /**
   * V3/V4 assembly origin Z (mm): translate +Z so board top (cabinet +Z) matches V1/V2 top at FCh.
   * Uses placement.height when set, else outerVector bbox height in profile (V) direction.
   */
  function v34AssemblyOriginZForTopAlign(board, fchMm) {
    const fch = Number(fchMm);
    if (!Number.isFinite(fch) || fch <= 0 || !board || typeof board !== "object") return 0;
    const p = board.placement || {};
    let span = null;
    if (p.height != null && Number.isFinite(Number(p.height))) {
      span = Number(p.height);
    }
    if (!Number.isFinite(span) || span <= 0) {
      const bb = getVectorBBox(board.outerVector);
      if (bb && Number.isFinite(bb.height) && bb.height > 0) span = Number(bb.height);
    }
    if (!Number.isFinite(span) || span <= 0) return 0;
    return Math.max(0, fch - span);
  }

  function assemblyPlacementRecord(board, originMm, notes, placementRuleUsed, extraFields) {
    const rec = {
      boardId: board.id,
      mode: "assembly_v0_1",
      originMm: { x: originMm.x, y: originMm.y, z: originMm.z },
      orientation: orientationFromBoard(board),
      notes: notes && notes.length ? notes.slice() : [],
    };
    if (placementRuleUsed != null && placementRuleUsed !== "") {
      rec.placementRuleUsed = String(placementRuleUsed);
    }
    if (extraFields && typeof extraFields === "object") {
      Object.assign(rec, extraFields);
    }
    return rec;
  }

  /** Boards that receive placement.assembly in assembly_3d (v0.2 adds HSet + Avoidance). */
  function boardIdInAssemblyScope(id) {
    if (id == null || id === "") return false;
    const s = String(id);
    if (/^V[1-5]$/.test(s)) return true;
    if (/^Z\d+$/.test(s)) return true;
    if (s === "B1" || s === "B2" || s === "B3") return true;
    if (s === "T1" || s === "T2" || s === "T3" || s === "T4" || s === "T5") return true;
    if (/^HSet_.+_H(?:13|24|34)$/.test(s)) return true;
    if (s === "AvoidanceFront" || s === "AvoidanceTop") return true;
    if (s === "SidePanel") return true;
    return false;
  }

  /**
   * Assembly placement metadata v0.1 (no Fusion bodies). Sets board.placement.assembly per board.
   */
  function buildAssemblyPlacementPlan(pureParams, boardPlan) {
    const coordinateSystem = {
      X: "cabinet width left-to-right",
      Y: "front-to-rear",
      Z: "bottom-to-top",
      unit: "mm",
    };
    const placements = {};
    const errors = [];
    const warnings = [];

    if (!pureParams || !boardPlan || typeof boardPlan !== "object") {
      errors.push("buildAssemblyPlacementPlan: missing pureParams or boardPlan.");
      return {
        ok: false,
        coordinateSystem,
        placements,
        errors,
        warnings,
        placementDimensionAudit: [],
        placementDimensionAuditOk: true,
      };
    }

    const boards = boardPlan.boards;
    if (!Array.isArray(boards)) {
      errors.push("buildAssemblyPlacementPlan: boardPlan.boards is not an array.");
      return {
        ok: false,
        coordinateSystem,
        placements,
        errors,
        warnings,
        placementDimensionAudit: [],
        placementDimensionAuditOk: true,
      };
    }

    const base = pureParams.base || {};
    const layout = pureParams.layout || {};
    const input = pureParams.input || {};
    const cabIn = input.cabinet || {};
    const cw = base.Cw != null ? base.Cw : cabIn.width;
    const cd = base.Cd != null ? base.Cd : cabIn.depth;
    const fptAsm = Number(base.frontHardwareSettings && base.frontHardwareSettings.frontPanelThickness) || DEFAULT_FRONT_PANEL_THICKNESS_MM;
    const FCh =
      layout.cabinetHeight != null ? layout.cabinetHeight : base.FCh != null ? base.FCh : cabIn.height;
    const fridgeIn = input.fridge || {};
    const fridgeH = base.fridgeH != null ? base.fridgeH : fridgeIn.height || 0;

    const wm =
      base.widthModel && typeof base.widthModel === "object"
        ? base.widthModel
        : deriveWidthModel(input);
    const pswAsm =
      Number.isFinite(Number(wm.panelSystemWidth)) && Number(wm.panelSystemWidth) > 0
        ? Number(wm.panelSystemWidth)
        : Number(cw);
    const psxAsm = Number.isFinite(Number(wm.panelSystemOriginX)) ? Number(wm.panelSystemOriginX) : 0;
    function ix(localX) {
      return psxAsm + Number(localX);
    }

    if (!Number.isFinite(Number(cw)) || !Number.isFinite(Number(cd)) || !Number.isFinite(Number(FCh))) {
      errors.push("buildAssemblyPlacementPlan: cabinet width, depth, or height is not a finite number.");
    }

    const vTh = 15;

    const byId = {};
    for (let i = 0; i < boards.length; i += 1) {
      const b = boards[i];
      if (b && b.id != null) byId[String(b.id)] = b;
    }

    const b1 = byId.B1;
    const b2 = byId.B2;
    const t1 = byId.T1;
    const t2 = byId.T2;

    const b1ThicknessY =
      b1 && b1.thickness != null && Number.isFinite(Number(b1.thickness)) ? Number(b1.thickness) : 16;
    const t1ThicknessY =
      t1 && t1.thickness != null && Number.isFinite(Number(t1.thickness)) ? Number(t1.thickness) : 16;
    const endClrAsm = endClearanceHeights(layout, base);
    const bottomRailZSpan = b1 ? profileSpanVMaxMm(b1.outerVector) : endClrAsm.bottomH;
    const topRailZSpan = t1 ? profileSpanVMaxMm(t1.outerVector) : endClrAsm.topH;
    const boundaryPtAsm = Number.isFinite(Number(layout.boundaryPanelThicknessMm))
      ? Number(layout.boundaryPanelThicknessMm)
      : boundaryPanelThickness(base.Pt);
    const fchNum = Number(FCh);
    const b3OriginZ = Number.isFinite(bottomRailZSpan) ? bottomRailZSpan : endClrAsm.bottomH;
    const t1OriginZ = Number.isFinite(fchNum) && Number.isFinite(topRailZSpan) ? fchNum - topRailZSpan : 0;
    const t3OriginZ =
      Number.isFinite(fchNum) && Number.isFinite(topRailZSpan)
        ? fchNum - topRailZSpan - boundaryPtAsm
        : 0;

    function attach(board, rec) {
      if (!board || typeof board !== "object") return;
      if (!board.placement || typeof board.placement !== "object") {
        errors.push(`buildAssemblyPlacementPlan: board ${board.id} has no placement object.`);
        return;
      }
      board.placement = Object.assign({}, board.placement, { assembly: rec });
    }

    function skipBoard(board, id) {
      if (!board || typeof board !== "object") return;
      if (!board.placement || typeof board.placement !== "object") {
        board.placement = { assembly: null };
      } else {
        board.placement = Object.assign({}, board.placement, { assembly: null });
      }
      warnings.push(`${id}: not placed in assembly v0.1`);
    }

    for (let i = 0; i < boards.length; i += 1) {
      const board = boards[i];
      const id = board && board.id != null ? String(board.id) : "";

      if (!boardIdInAssemblyScope(id)) {
        skipBoard(board, id || `(index ${i})`);
        continue;
      }

      let rec = null;
      if (id === "V1") {
        rec = assemblyPlacementRecord(board, { x: ix(0), y: 0, z: 0 }, [
          "Front-left vertical stile; X includes panelSystemOriginX; origin at interior left of panel system.",
        ]);
      } else if (id === "V2") {
        rec = assemblyPlacementRecord(
          board,
          { x: ix(Number(pswAsm) - vTh), y: 0, z: 0 },
          ["Front-right vertical stile; X = originX + panelSystemWidth − stile thickness."],
        );
      } else if (id === "V3" || id === "V4") {
        const p = board.placement || {};
        const depY = p.depthY != null ? Number(p.depthY) : 150;
        const rearY = Math.max(0, Number(cd) - depY);
        const x = id === "V3" ? ix(0) : ix(Number(pswAsm) - vTh);
        const zTopAlign = v34AssemblyOriginZForTopAlign(board, FCh);
        rec = assemblyPlacementRecord(
          board,
          { x, y: rearY, z: zTopAlign },
          [
            "Rear vertical stile; Y = Cd − depthY; Z = FCh − profile height so top aligns with V1/V2 (cabinet top FCh).",
          ],
        );
      } else if (id === "V5") {
        const sps = String((wm.sidePanelSide != null ? wm.sidePanelSide : base.sidePanelSide) || "none").toLowerCase();
        const v5OnLeft = sps !== "left";
        const v5Th = board.thickness != null && Number.isFinite(Number(board.thickness)) ? Number(board.thickness) : vTh;
        const psx = psxAsm;
        const psw = Number(pswAsm);
        const xV5 = v5OnLeft ? psx + v5Th : psx + psw - 2 * v5Th;
        const ziTopZ = findFridgeBaseFullZiTopZ(layout, base);
        if (!Number.isFinite(ziTopZ)) {
          warnings.push(
            "V5: could not resolve fridge_base full Zi top Z from layout; origin Z defaulted to 0 (check stack / Zi roles).",
          );
        }
        const z0 = Number.isFinite(ziTopZ) ? ziTopZ : 0;
        const eps = 0.01;
        const v5OppositeSideOk =
          (sps === "right" && v5OnLeft) || (sps === "left" && !v5OnLeft) || (sps === "none" && v5OnLeft);
        const v5BottomMatchesZiFullTop =
          Number.isFinite(ziTopZ) && Math.abs(z0 - ziTopZ) < eps;
        const xExpect = v5OnLeft ? psx + v5Th : psx + psw - 2 * v5Th;
        const v5InsetOneBoardThicknessOk = Math.abs(xV5 - xExpect) < eps;
        rec = assemblyPlacementRecord(
          board,
          { x: xV5, y: 0, z: z0 },
          [
            "V5 fridge clearance strip (YZ): opposite SidePanel side; bottom Z = top of fridge_base full Zi; X inset one board thickness toward cabinet center (left: psx+tv5, right: psx+psw−2·tv5); Y=0.",
          ],
          "v5_opposite_side_inset_v0_1",
          {
            v5OnLeft,
            v5OppositeSideOk,
            v5BottomMatchesZiFullTop,
            v5InsetOneBoardThicknessOk,
          },
        );
      } else if (/^Z\d+$/.test(id)) {
        const p = board.placement || {};
        const z0 = p.z0 != null ? Number(p.z0) : 0;
        rec = assemblyPlacementRecord(
          board,
          { x: ix(0), y: 0, z: z0 },
          ["Zi horizontal panel; Z from BoardPlan placement.z0; X includes panelSystemOriginX."],
        );
      } else if (id === "B1") {
        rec = assemblyPlacementRecord(board, { x: ix(0), y: T1_T2_ASSEMBLY_Y_OFFSET_MM, z: 0 }, [
          "Bottom front rail XZ; Y +" +
            String(T1_T2_ASSEMBLY_Y_OFFSET_MM) +
            " mm (align with T1/T2 front offset); shares bottom rail Z span 0–" +
            String(b3OriginZ) +
            " mm with B2.",
        ]);
      } else if (id === "B2") {
        rec = assemblyPlacementRecord(board, { x: ix(0), y: T1_T2_ASSEMBLY_Y_OFFSET_MM + b1ThicknessY, z: 0 }, [
          "Bottom second rail XZ; same Z as B1; Y = +" +
            String(T1_T2_ASSEMBLY_Y_OFFSET_MM) +
            " mm plus B1 thickness (" +
            String(b1ThicknessY) +
            " mm) toward rear.",
        ]);
      } else if (id === "B3") {
        rec = assemblyPlacementRecord(board, { x: ix(0), y: 0, z: b3OriginZ }, [
          "Bottom inserted board XY; Z at top of bottom rail profile (" + String(b3OriginZ) + " mm).",
        ]);
      } else if (id === "T1") {
        rec = assemblyPlacementRecord(board, { x: ix(0), y: T1_T2_ASSEMBLY_Y_OFFSET_MM, z: t1OriginZ }, [
          "Top front rail XZ; Z origin at FCh − top rail profile height (" + String(topRailZSpan) + " mm); Y +39 mm.",
        ]);
      } else if (id === "T2") {
        rec = assemblyPlacementRecord(
          board,
          { x: ix(0), y: T1_T2_ASSEMBLY_Y_OFFSET_MM + t1ThicknessY, z: t1OriginZ },
          [
            "Top second rail XZ; same Z as T1; Y offset by T1 thickness (" + String(t1ThicknessY) + " mm) toward rear; base Y +39 mm.",
          ],
        );
      } else if (id === "T3") {
        rec = assemblyPlacementRecord(board, { x: ix(0), y: 0, z: t3OriginZ }, [
          "Top inserted board XY; Z at FCh − top clearance − boundary panel thickness.",
        ]);
      } else if (id === "T4") {
        rec = assemblyPlacementRecord(
          board,
          { x: ix(0), y: Number(cd) - 100, z: Number(FCh) - 16 },
          ["T4 rear top horizontal XY; v0.3 placement (rear Y offset 100 mm)."],
          "t4_rear_top_v0_3",
        );
      } else if (id === "T5") {
        warnings.push(
          "T5 assembly placement uses temporary vertical interpretation; BoardPlan profile may need refinement later.",
        );
        rec = assemblyPlacementRecord(
          Object.assign({}, board, { profilePlane: "XZ" }),
          { x: ix(0), y: Number(cd) - 15, z: Number(FCh) - 121 },
          ["T5 rear top vertical; assembly record uses XZ axes (temporary)."],
          "t5_rear_top_vertical_v0_3",
        );
      } else if (id === "SidePanel") {
        const cabW = Number(wm.cabinetWidth) > 0 ? Number(wm.cabinetWidth) : Number(cw);
        const xSide =
          wm.sidePanelSide === "right" ? Math.max(0, cabW - SIDE_PANEL_THICKNESS_MM) : 0;
        rec = assemblyPlacementRecord(
          board,
          { x: xSide, y: -fptAsm, z: 0 },
          [
            "Main side panel YZ; absolute X by exteriorSide (not offset by panelSystemOriginX); Y extends to -frontPanelThickness.",
            "assembly_3d (Fusion): YZ remap, then +Y +90°, +Z +90°, +X +180°, +Z +180° (same as Fusion Z −180°).",
          ],
          "side_panel_v0_1",
          {
            assemblyWorldRotateDegSequence: [
              { axis: "Y", deg: 90, note: "CCW from +Y (RH +90°)" },
              { axis: "Z", deg: 90, note: "CCW from +Z (RH +90°)" },
              { axis: "X", deg: 180, note: "RH +180° about cabinet +X" },
              { axis: "Z", deg: 180, note: "Half turn about +Z (≡ Fusion −180°)" },
            ],
          },
        );
      } else if (/^HSet_.+_H(?:13|24|34)$/.test(id)) {
        const zr = getHSetZRange(board);
        if (!zr || !Number.isFinite(zr.z0) || !Number.isFinite(zr.z1)) {
          errors.push(`buildAssemblyPlacementPlan: cannot resolve HSet Z range for ${id}.`);
        } else {
          if (zr.warning) warnings.push(zr.warning);
          const member = (board.placement && board.placement.member != null && String(board.placement.member)) || "";
          const vTk = board.thickness != null && Number.isFinite(Number(board.thickness)) ? Number(board.thickness) : 15;
          const frontY = H_CONNECTOR_FRONT_V_DEPTH_MM;
          const rearOff = H_CONNECTOR_REAR_V_DEPTH_MM;
          const oz = zr.z0;
          let ox = NaN;
          let oy = NaN;
          if (member === "H13") {
            ox = ix(0);
            oy = frontY;
          } else if (member === "H24") {
            ox = ix(Number(pswAsm) - vTk);
            oy = frontY;
          } else if (member === "H34") {
            ox = ix(vTk);
            oy = Math.max(0, Number(cd) - rearOff) + H34_ASSEMBLY_Y_OFFSET_MM;
          } else {
            errors.push(`buildAssemblyPlacementPlan: unknown HSet member ${member} for ${id}.`);
          }
          if (Number.isFinite(ox) && Number.isFinite(oy)) {
            const gid = hSetGroupIdFromBoardId(id);
            const groupRole = classifyHSetGroupRole(zr.z0, pureParams, FCh);
            const hNotes = [
              `HSet v0.3 ${gid} member ${member}; H13/H24 YZ at frontVDepth; H34 XZ at rear Y=Cd−rearVDepth+${H34_ASSEMBLY_Y_OFFSET_MM} (+Y); z0=${zr.z0}, z1=${zr.z1}; role=${groupRole}.`,
            ];
            if (member === "H13" || member === "H24") {
              hNotes.push(
                "assembly_3d (Fusion): after profilePlane YZ remap, apply world +Z +90° then world +X +90° (RH, pivot world origin).",
              );
            }
            const hExtra = {
              hSetGroupId: gid,
              hSetMember: member,
              groupRole,
              z0: zr.z0,
              z1: zr.z1,
            };
            if (member === "H13" || member === "H24") {
              hExtra.assemblyWorldRotateDegSequence = [
                { axis: "Z", deg: 90, note: "RH +90° about cabinet +Z" },
                { axis: "X", deg: 90, note: "RH +90° about cabinet +X" },
              ];
            }
            rec = assemblyPlacementRecord(
              board,
              { x: ox, y: oy, z: oz },
              hNotes,
              "hset_all_groups_v0_3",
              hExtra,
            );
          }
        }
      } else if (id === "AvoidanceFront") {
        const av = pureParams.avoidance || {};
        const avoidD = av.finalDepth != null ? Number(av.finalDepth) : 0;
        rec = assemblyPlacementRecord(
          board,
          { x: ix(0), y: Math.max(0, Number(cd) - avoidD), z: 0 },
          ["Avoidance front vertical XZ; Y = Cd − avoidance finalDepth (wheel pocket rear face)."],
          "avoidance_front_v0_2",
        );
      } else if (id === "AvoidanceTop") {
        const av = pureParams.avoidance || {};
        const avoidD = av.finalDepth != null ? Number(av.finalDepth) : 0;
        const topZ = av.finalTopZ != null ? Number(av.finalTopZ) : 0;
        const th = board.thickness != null && Number.isFinite(Number(board.thickness)) ? Number(board.thickness) : 15;
        rec = assemblyPlacementRecord(
          board,
          { x: ix(0), y: Math.max(0, Number(cd) - avoidD), z: Math.max(0, topZ - th) },
          ["Avoidance top XY; Z = finalTopZ − thickness; Y = Cd − finalDepth."],
          "avoidance_top_v0_2",
        );
      }

      if (rec) {
        placements[id] = rec;
        attach(board, rec);
      } else {
        errors.push(`buildAssemblyPlacementPlan: in-scope board ${id} not handled.`);
        skipBoard(board, id);
      }
    }

    const hGroupSet = new Set();
    for (let hi = 0; hi < boards.length; hi += 1) {
      const hb = boards[hi];
      if (!hb || hb.id == null) continue;
      const hid = String(hb.id);
      if (/^HSet_.+_H(?:13|24|34)$/.test(hid)) {
        hGroupSet.add(hSetGroupIdFromBoardId(hid));
      }
    }
    if (hGroupSet.size === 1) {
      warnings.push(
        `Only one HSet group exists in BoardPlan (${[...hGroupSet].join(
          ", ",
        )}); expected H mid and H bottom require additional HSet generation.`,
      );
    }

    const placementDimensionAudit = [];
    if (Number.isFinite(Number(cw))) {
      const btIds = ["B1", "B2", "B3", "T1", "T2", "T3"];
      for (let bi = 0; bi < btIds.length; bi += 1) {
        const bid = btIds[bi];
        const brd = byId[bid];
        if (!brd) continue;
        const nominal = nominalBTPlacementAuditExpected(bid, pswAsm, endClrAsm.bottomH, endClrAsm.topH);
        const fromBoard = expectedGlobalSizeMmFromBoard(brd);
        const status =
          nominal && fromBoard && nearSameGlobalSizesMm(nominal, fromBoard, 3) ? "ok" : "mismatch";
        if (status === "mismatch") {
          errors.push(
            `buildAssemblyPlacementPlan: placement dimension audit mismatch for ${bid} (expected ${JSON.stringify(
              nominal,
            )} vs board geometry ${JSON.stringify(fromBoard)}).`,
          );
        }
        placementDimensionAudit.push({
          boardId: bid,
          expectedGlobalSizeMm: nominal,
          fromBoardGlobalSizeMm: fromBoard,
          status,
        });
      }
    }

    const placementDimensionAuditOk = placementDimensionAudit.length === 0 || placementDimensionAudit.every((r) => r.status === "ok");

    const ok = errors.length === 0;
    return {
      ok,
      coordinateSystem,
      placements,
      widthModel: wm,
      errors,
      warnings,
      placementDimensionAudit,
      placementDimensionAuditOk,
    };
  }

  /**
   * Includes Zi, BlankPanel, B1–B3, T1–T5, HSet, V1–V4 (YZ profiles), V5 (if hasV5), avoidance (if enabled).
   */
  function endClearanceHeights(layout, base) {
    const bottomH =
      layout && layout.bottomClearanceRegion
        ? layout.bottomClearanceRegion.z1 - layout.bottomClearanceRegion.z0
        : base && base.bottomClearance != null
          ? Number(base.bottomClearance)
          : DEFAULT_BOTTOM_CLEARANCE_MM;
    const topH =
      layout && layout.topClearanceRegion
        ? layout.topClearanceRegion.z1 - layout.topClearanceRegion.z0
        : base && base.topClearance != null
          ? Number(base.topClearance)
          : DEFAULT_TOP_CLEARANCE_MM;
    return {
      bottomH: Number.isFinite(bottomH) ? bottomH : DEFAULT_BOTTOM_CLEARANCE_MM,
      topH: Number.isFinite(topH) ? topH : DEFAULT_TOP_CLEARANCE_MM,
    };
  }

  function buildBoardPlan(pureParams) {
    const validation = cloneValidation(pureParams && pureParams.validation);
    const boards = [];

    if (!pureParams || !pureParams.layout) {
      validation.ok = false;
      validation.errors.push("BoardPlan: missing pureParams.layout.");
      return {
        boards,
        validation,
        hPlanes: [],
        hSetGroups: [],
        createdBoardIds: [],
        widthModel: pureParams.input ? deriveWidthModel(pureParams.input) : null,
      };
    }

    const base = pureParams.base || {};
    const layout = pureParams.layout;
    const input = pureParams.input || {};
    const fridgeIn = input.fridge || {};
    const cabIn = input.cabinet || {};
    const fridgeW = base.fridgeW != null ? base.fridgeW : fridgeIn.width || 0;
    const cw = base.Cw != null ? base.Cw : cabIn.width || 0;
    const cd = base.Cd != null ? base.Cd : cabIn.depth || 0;
    const totalDepth = base.cabinetDepth != null ? Number(base.cabinetDepth) : Number(cd);
    const fpt = Number(base.frontHardwareSettings && base.frontHardwareSettings.frontPanelThickness) || DEFAULT_FRONT_PANEL_THICKNESS_MM;
    const wm =
      base.widthModel && typeof base.widthModel === "object"
        ? base.widthModel
        : deriveWidthModel(input);
    const psw =
      Number.isFinite(Number(wm.panelSystemWidth)) && Number(wm.panelSystemWidth) > 0
        ? Number(wm.panelSystemWidth)
        : cw;

    const geomByPanelId = {};
    for (const g of layout.panelGeometries || []) {
      if (g && g.panelId) geomByPanelId[g.panelId] = g;
    }

    const FCh = layout.cabinetHeight != null ? layout.cabinetHeight : base.FCh != null ? base.FCh : 0;
    const fridgeH = base.fridgeH != null ? base.fridgeH : fridgeIn.height || 0;
    const avoidance = pureParams.avoidance || {};
    const endClearances = endClearanceHeights(layout, base);
    const bottomRailHeightMm = endClearances.bottomH;
    const topRailHeightMm = endClearances.topH;

    const t3Profile = t3B3OuterVector(psw);

    if (wm.hasSidePanel === true) {
      const avoidD = avoidance.enabled === true && avoidance.finalDepth != null ? Number(avoidance.finalDepth) : 0;
      const topZ =
        avoidance.enabled === true && avoidance.finalTopZ != null
          ? Number(avoidance.finalTopZ)
          : avoidance.enabled === true && avoidance.inputHeight != null
          ? Number(avoidance.inputHeight)
          : 0;
      let spOv;
      if (avoidance.enabled === true) {
        const y1 = Math.max(0, cd - avoidD) + fpt;
        spOv = [
          [0, 0],
          [y1, 0],
          [y1, topZ],
          [totalDepth, topZ],
          [totalDepth, FCh],
          [0, FCh],
          [0, 0],
        ];
      } else {
        spOv = [
          [0, 0],
          [totalDepth, 0],
          [totalDepth, FCh],
          [0, FCh],
          [0, 0],
        ];
      }
      boards.push({
        id: "SidePanel",
        name: "Main Side Panel",
        series: "S",
        type: "side_panel",
        thickness: SIDE_PANEL_THICKNESS_MM,
        profilePlane: "YZ",
        outerVector: spOv,
        holes: [],
        grooves: [],
        source: {
          exteriorSide: wm.sidePanelSide,
          sidePanelThickness: wm.sidePanelThickness,
          widthModel: wm,
          frontPanelThickness: fpt,
          midDepth: cd,
          totalDepth,
        },
        placement: { series: "S", id: "SidePanel", region: "side_exterior" },
        notes: "Main structural side panel; local U spans total depth (front extension + midDepth), V = height (Z); assembly origin Y = -frontPanelThickness.",
      });
    }

    boards.push({
      id: "B1",
      name: "B1 Bottom Front Rail",
      series: "B",
      type: "bottom_front_rail",
      thickness: 16,
      profilePlane: "XZ",
      outerVector: [
        [0, 0],
        [psw, 0],
        [psw, bottomRailHeightMm],
        [0, bottomRailHeightMm],
        [0, 0],
      ],
      holes: [],
      grooves: [],
      source: { series: "B", board: "B1" },
      placement: { series: "B", id: "B1", region: "cabinet_bottom" },
      notes: "B-series bottom front rail (BoardPlan v0.2).",
    });
    boards.push({
      id: "B2",
      name: "B2 Bottom Second Rail",
      series: "B",
      type: "bottom_second_rail",
      thickness: 15,
      profilePlane: "XZ",
      outerVector: [
        [0, 0],
        [psw, 0],
        [psw, bottomRailHeightMm],
        [0, bottomRailHeightMm],
        [0, 0],
      ],
      holes: [],
      grooves: [],
      source: { series: "B", board: "B2" },
      placement: { series: "B", id: "B2", region: "cabinet_bottom" },
      notes: "B-series bottom second rail (BoardPlan v0.2).",
    });
    boards.push({
      id: "B3",
      name: "B3 Bottom Inserted Board",
      series: "B",
      type: "bottom_inserted_board",
      thickness: 15,
      profilePlane: "XY",
      outerVector: t3Profile,
      holes: {
        diameter: 3,
        positions: [
          [8, 92.5],
          [8, 103],
          [8, 140],
          [psw - 8, 92.5],
          [psw - 8, 103],
          [psw - 8, 140],
        ],
      },
      grooves: [
        {
          type: "connected_bottom_groove",
          mainWidth: 14.5,
          depth: 6.5,
          branchLength: 20,
          note: "placeholder groove definition; exact path can be refined later",
        },
      ],
      source: { series: "B", board: "B3" },
      placement: { series: "B", id: "B3", region: "cabinet_bottom" },
      notes: "B3 shares T3/B3 inserted profile (BoardPlan v0.2).",
    });

    for (const zi of layout.ziList || []) {
      const g = geomByPanelId[zi.panelId];
      if (!g || !Array.isArray(g.outerVector)) {
        validation.warnings.push(`BoardPlan: missing outerVector for Zi ${zi.id} (panel ${zi.panelId}).`);
        continue;
      }
      const thickness = g.thickness != null ? g.thickness : base.Pt;
      boards.push({
        id: zi.id,
        name: `Zi ${zi.role} (${zi.shape})`,
        series: "Zi",
        type: zi.shape === "full" ? "zi_full" : "zi_half",
        thickness,
        profilePlane: "XY",
        outerVector: g.outerVector,
        holes: g.holes || [],
        grooves: g.grooves || [],
        source: {
          ziId: zi.id,
          panelId: zi.panelId,
          role: zi.role,
          shape: zi.shape,
        },
        placement: {
          x0: 0,
          y0: 0,
          z0: zi.z0,
          z1: zi.z1,
          centerZ: zi.centerZ,
          widthX: psw,
          depthY: cd,
          thicknessZ: thickness,
        },
        notes: "Horizontal auto panel from Zi; profile in cabinet XY (width x depth), thickness along +Z.",
      });
    }

    for (const section of layout.sections || []) {
      if (section.type !== "blankPanel") continue;
      const h = section.height;
      boards.push({
        id: `BlankPanel_${section.id}`,
        name: `Blank Panel ${section.id}`,
        series: "Section",
        type: "blank_panel",
        thickness: BLANK_PANEL_THICKNESS_MM,
        profilePlane: "XZ",
        outerVector: [
          [0, 0],
          [fridgeW, 0],
          [fridgeW, h],
          [0, h],
          [0, 0],
        ],
        holes: [],
        grooves: [],
        source: {
          sectionId: section.id,
          sectionType: "blankPanel",
        },
        placement: {
          x0: 0,
          z0: section.z0,
          widthX: fridgeW,
          heightZ: h,
          thicknessY: BLANK_PANEL_THICKNESS_MM,
        },
        notes: "Section infill blank; not a Zi; FridgeCutoutWidth = fridge width (v0.3).",
      });
    }

    const pt = base.Pt != null ? Number(base.Pt) : cabIn.panelThickness != null ? Number(cabIn.panelThickness) : 15;
    const hTh = Number.isFinite(pt) ? pt : 15;

    const h13h24Len = Math.max(
      0,
      Number(cd) - H_CONNECTOR_FRONT_V_DEPTH_MM - H_CONNECTOR_REAR_V_DEPTH_MM,
    );
    const h34Len = Math.max(0, Number(psw) - 2 * hTh);

    for (const hPlane of layout.hPlanes || []) {
      const heightZ = hPlane.z1 - hPlane.z0;
      const hSource = {
        ...hPlane,
        members: hPlane.members ? [...hPlane.members] : [],
        reasons: Array.isArray(hPlane.reasons) ? [...hPlane.reasons] : [],
        h13h24Length: h13h24Len,
        h34Length: h34Len,
        vThickness: hTh,
        frontVConnectorDepth: H_CONNECTOR_FRONT_V_DEPTH_MM,
        rearVConnectorDepth: H_CONNECTOR_REAR_V_DEPTH_MM,
        panelSystemWidth: psw,
      };
      const ovH1324 = [
        [0, 0],
        [h13h24Len, 0],
        [h13h24Len, heightZ],
        [0, heightZ],
        [0, 0],
      ];
      const ovH34 = [
        [0, 0],
        [h34Len, 0],
        [h34Len, heightZ],
        [0, heightZ],
        [0, 0],
      ];
      const memberList =
        Array.isArray(hPlane.members) && hPlane.members.length > 0
          ? hPlane.members.map((m) => String(m))
          : ["H13", "H24", "H34"];
      const hSuffixesAll = [
        { suffix: "H13", type: "h13", member: "H13", profilePlane: "YZ", outerVector: ovH1324 },
        { suffix: "H24", type: "h24", member: "H24", profilePlane: "YZ", outerVector: ovH1324 },
        { suffix: "H34", type: "h34", member: "H34", profilePlane: "XZ", outerVector: ovH34 },
      ];
      const hSuffixes = hSuffixesAll.filter((row) => memberList.indexOf(row.member) !== -1);
      for (const { suffix, type, member, profilePlane, outerVector } of hSuffixes) {
        boards.push({
          id: `${hPlane.id}_${suffix}`,
          name: `${suffix} (${hPlane.id})`,
          series: "H",
          type,
          thickness: hTh,
          profilePlane,
          outerVector,
          holes: [],
          grooves: [],
          source: hSource,
          placement: {
            z0: hPlane.z0,
            z1: hPlane.z1,
            mode: hPlane.mode,
            heightZ,
            hPlaneId: hPlane.id,
            member,
            role: hPlane.role,
            hSetRole: hPlane.role,
            h13h24Length: h13h24Len,
            h34Length: h34Len,
            vThickness: hTh,
            frontVConnectorDepth: H_CONNECTOR_FRONT_V_DEPTH_MM,
            rearVConnectorDepth: H_CONNECTOR_REAR_V_DEPTH_MM,
          },
          notes:
            member === "H34"
              ? "H34 rear width connector XZ; span U = panelSystemWidth − 2×V thickness; V along Z."
              : "H13/H24 front-rear connector YZ; span U = Cd − frontVDepth − rearVDepth; V along Z.",
        });
      }
    }

    const ziListForV = layout.ziList || [];
    const finalAvoidanceTopZ =
      avoidance.enabled === true && avoidance.finalTopZ != null ? avoidance.finalTopZ : 0;
    const boundaryPt = Number.isFinite(Number(layout.boundaryPanelThicknessMm))
      ? Number(layout.boundaryPanelThicknessMm)
      : boundaryPanelThickness(base.Pt);
    const v12Profile = getV12Profile(FCh, ziListForV, bottomRailHeightMm, topRailHeightMm, boundaryPt);
    const v34Profile = getV34Profile(FCh, finalAvoidanceTopZ, ziListForV);
    const vSource12 = {
      ziList: copyZiListForSource(ziListForV),
      FCh,
      bottomEndHeight: bottomRailHeightMm,
      topEndHeight: topRailHeightMm,
      boundaryPanelThicknessMm: boundaryPt,
    };
    const vSource34 = {
      ziList: copyZiListForSource(ziListForV),
      finalAvoidanceTopZ,
      FCh,
    };

    boards.push({
      id: "V1",
      name: "V1 Front Vertical Member",
      series: "V",
      type: "front_vertical_member",
      thickness: 15,
      profilePlane: "YZ",
      outerVector: v12Profile,
      holes: [],
      grooves: [],
      source: vSource12,
      placement: { series: "V", id: "V1", height: FCh, depthY: 150, profile: "V12" },
      notes: "Front vertical member; V1/V2 share getV12Profile (BoardPlan v0.3).",
    });
    boards.push({
      id: "V2",
      name: "V2 Front Vertical Member",
      series: "V",
      type: "front_vertical_member",
      thickness: 15,
      profilePlane: "YZ",
      outerVector: v12Profile,
      holes: [],
      grooves: [],
      source: vSource12,
      placement: { series: "V", id: "V2", height: FCh, depthY: 150, profile: "V12" },
      notes: "Front vertical member; same outerVector as V1 until placement differs in geometry stage.",
    });
    boards.push({
      id: "V3",
      name: "V3 Rear Vertical Member",
      series: "V",
      type: "rear_vertical_member",
      thickness: 15,
      profilePlane: "YZ",
      outerVector: v34Profile,
      holes: [],
      grooves: [],
      source: vSource34,
      placement: {
        series: "V",
        id: "V3",
        height: FCh - finalAvoidanceTopZ,
        depthY: 150,
        profile: "V34",
        finalAvoidanceTopZ,
      },
      notes: "Rear vertical member; local Z = global Z - finalAvoidanceTopZ (BoardPlan v0.3).",
    });
    boards.push({
      id: "V4",
      name: "V4 Rear Vertical Member",
      series: "V",
      type: "rear_vertical_member",
      thickness: 15,
      profilePlane: "YZ",
      outerVector: v34Profile,
      holes: [],
      grooves: [],
      source: vSource34,
      placement: {
        series: "V",
        id: "V4",
        height: FCh - finalAvoidanceTopZ,
        depthY: 150,
        profile: "V34",
        finalAvoidanceTopZ,
      },
      notes: "Rear vertical member; same outerVector as V3 until placement differs in geometry stage.",
    });

    if (base.hasV5 === true) {
      const fridgeBaseZiTopZ = findFridgeBaseFullZiTopZ(layout, base);
      const v5Height = findFridgeSectionHeight(layout, base);
      if (!Number.isFinite(fridgeBaseZiTopZ)) {
        validation.warnings.push(
          "BoardPlan: V5 requested but fridge_base full Zi top Z could not be resolved from layout.ziList.",
        );
      }
      boards.push({
        id: "V5",
        name: "V5 Fridge Clearance Strip",
        series: "V",
        type: "v5_clearance_strip",
        thickness: 15,
        profilePlane: "YZ",
        outerVector: getV5Profile(v5Height),
        holes: [],
        grooves: [],
        source: {
          v5Side: base.v5Side,
          fridgeBaseZiTopZ: Number.isFinite(fridgeBaseZiTopZ) ? fridgeBaseZiTopZ : null,
          fridgeSectionHeight: v5Height,
          fridgeInputHeight: fridgeH,
        },
        placement: {
          side: base.v5Side,
          fridgeH: v5Height,
          fridgeInputHeight: fridgeH,
          height: v5Height,
          z0: Number.isFinite(fridgeBaseZiTopZ) ? fridgeBaseZiTopZ : null,
          z1: Number.isFinite(fridgeBaseZiTopZ) ? fridgeBaseZiTopZ + v5Height : null,
        },
        notes:
          "V5 on side opposite side panel (or left if none); bottom flush with top of fridge_base full Zi; X aligns with V1/V2; height = fridge cutout (BoardPlan v0.3).",
      });
    }

    if (avoidance.enabled === true) {
      const fh = avoidance.finalFrontBoardHeight != null ? avoidance.finalFrontBoardHeight : 0;
      const dep = avoidance.finalDepth != null ? avoidance.finalDepth : 0;
      boards.push({
        id: "AvoidanceFront",
        name: "Avoidance Front Vertical Board",
        series: "Avoidance",
        type: "avoidance_front_vertical",
        thickness: 15,
        profilePlane: "XZ",
        outerVector: [
          [0, 0],
          [psw, 0],
          [psw, fh],
          [0, fh],
          [0, 0],
        ],
        holes: [],
        grooves: [],
        source: avoidance,
        placement: { avoidanceRole: "front", widthX: psw, heightZ: fh },
        notes: "Wheel avoidance front board (BoardPlan v0.2).",
      });
      boards.push({
        id: "AvoidanceTop",
        name: "Avoidance Top Horizontal Board",
        series: "Avoidance",
        type: "avoidance_top_horizontal",
        thickness: 15,
        profilePlane: "XY",
        outerVector: [
          [0, 0],
          [psw, 0],
          [psw, dep],
          [0, dep],
          [0, 0],
        ],
        holes: [],
        grooves: [],
        source: avoidance,
        placement: { avoidanceRole: "top", widthX: psw, depthY: dep },
        notes: "Wheel avoidance top board (BoardPlan v0.2).",
      });
    }

    boards.push({
      id: "T1",
      name: "T1 Top Front Rail",
      series: "T",
      type: "top_front_rail",
      thickness: 16,
      profilePlane: "XZ",
      outerVector: [
        [0, 0],
        [psw, 0],
        [psw, topRailHeightMm],
        [0, topRailHeightMm],
        [0, 0],
      ],
      holes: [],
      grooves: [],
      source: { series: "T", board: "T1" },
      placement: { series: "T", id: "T1", region: "cabinet_top" },
      notes: "T-series top front rail (BoardPlan v0.2).",
    });
    boards.push({
      id: "T2",
      name: "T2 Top Second Rail",
      series: "T",
      type: "top_second_rail",
      thickness: 15,
      profilePlane: "XZ",
      outerVector: [
        [0, 0],
        [psw, 0],
        [psw, topRailHeightMm],
        [0, topRailHeightMm],
        [0, 0],
      ],
      holes: [],
      grooves: [],
      source: { series: "T", board: "T2" },
      placement: { series: "T", id: "T2", region: "cabinet_top" },
      notes: "T-series top second rail (BoardPlan v0.2).",
    });
    boards.push({
      id: "T3",
      name: "T3 Top Inserted Board",
      series: "T",
      type: "top_inserted_board",
      thickness: 15,
      profilePlane: "XY",
      outerVector: t3Profile,
      holes: {
        diameter: 3,
        positions: [
          [8, 100],
          [8, 125],
          [psw - 8, 100],
          [psw - 8, 125],
        ],
      },
      grooves: [],
      source: { series: "T", board: "T3" },
      placement: { series: "T", id: "T3", region: "cabinet_top" },
      notes: "T3 inserted board profile shared with B3 (BoardPlan v0.2).",
    });
    boards.push({
      id: "T4",
      name: "T4 Rear Top Horizontal Board",
      series: "T",
      type: "rear_top_horizontal_board",
      thickness: 15,
      profilePlane: "XY",
      outerVector: [
        [0, 0],
        [psw, 0],
        [psw, 100],
        [0, 100],
        [0, 0],
      ],
      holes: {
        diameter: 3,
        positions: [
          [8, 33],
          [8, 66],
          [psw - 8, 33],
          [psw - 8, 66],
        ],
      },
      grooves: [],
      source: { series: "T", board: "T4" },
      placement: { series: "T", id: "T4", region: "cabinet_top" },
      notes: "T4 rear top horizontal (BoardPlan v0.2).",
    });
    boards.push({
      id: "T5",
      name: "T5 Rear Top Vertical Board",
      series: "T",
      type: "rear_top_vertical_board",
      thickness: 15,
      profilePlane: "XY",
      outerVector: [
        [0, 0],
        [psw, 0],
        [psw, 100],
        [0, 100],
        [0, 0],
      ],
      holes: {
        diameter: 3,
        positions: [
          [8, 33],
          [8, 66],
          [psw - 8, 33],
          [psw - 8, 66],
        ],
      },
      grooves: [],
      source: { series: "T", board: "T5" },
      placement: { series: "T", id: "T5", region: "cabinet_top" },
      notes: "T5 rear top vertical (BoardPlan v0.2).",
    });

    const frontLayer = buildFridgeFrontPanels(pureParams, { boards });
    for (const warning of frontLayer.warnings || []) {
      validation.warnings.push(warning);
    }

    boards.sort((a, b) => {
      const ka = boardSortKey(a, FCh);
      const kb = boardSortKey(b, FCh);
      if (ka !== kb) return ka - kb;
      return String(a.id).localeCompare(String(b.id));
    });

    for (let i = 0; i < boards.length; i += 1) {
      boards[i] = attachManufacturingMetadata(boards[i]);
    }

    const hPlanesLayout = layout.hPlanes || [];
    const hSetGroups = hPlanesLayout.map((hp) => {
      const members =
        Array.isArray(hp.members) && hp.members.length > 0
          ? hp.members.map((m) => String(m))
          : ["H13", "H24", "H34"];
      const generatedBoardIds = members.map((m) => `${hp.id}_${m}`);
      const z0n = Number(hp.z0);
      const z1n = Number(hp.z1);
      const height = Number.isFinite(z0n) && Number.isFinite(z1n) ? z1n - z0n : null;
      return {
        hSetId: hp.id,
        role: hp.role != null ? hp.role : null,
        z0: hp.z0,
        z1: hp.z1,
        height,
        anchorType: hp.anchorType != null ? hp.anchorType : null,
        anchorDescription: hp.anchorDescription != null ? hp.anchorDescription : null,
        referenceLowZ: hp.referenceLowZ != null ? hp.referenceLowZ : null,
        referenceHighZ: hp.referenceHighZ != null ? hp.referenceHighZ : null,
        generatedBoardIds,
        reasons: Array.isArray(hp.reasons) ? [...hp.reasons] : [],
        mode: hp.mode,
        sourcePanelId: hp.sourcePanelId != null ? hp.sourcePanelId : null,
        sourceRole: hp.sourceRole != null ? hp.sourceRole : null,
      };
    });

    const hGroupCount = hSetGroups.length;
    if (hGroupCount === 1) {
      validation.warnings.push("Only one HSet group generated; bottom/mid HSet may be missing.");
    }
    const hasFridgeBaseH = hSetGroups.some((g) => g.role === "fridge_base_support");
    const hasBottomH = hSetGroups.some((g) => g.role === "h_bottom");
    if (hasFridgeBaseH && hasBottomH && hGroupCount < 3) {
      validation.warnings.push(
        "BoardPlan HSet: expected at least 3 HSet groups when structural bottom and fridge support are present; gap mid may be missing or merged.",
      );
    }

    const hasSidePanelBoard = boards.some((b) => b && b.id === "SidePanel");
    if (wm.hasSidePanel) {
      if (Math.abs(Number(wm.cabinetWidth) - Number(wm.panelSystemWidth) - Number(wm.sidePanelThickness)) > 0.01) {
        validation.warnings.push(
          "BoardPlan widthModel: cabinetWidth should equal panelSystemWidth + sidePanelThickness.",
        );
      }
      if (!hasSidePanelBoard) {
        validation.warnings.push("BoardPlan widthModel: hasSidePanel but SidePanel board was not generated.");
      }
    } else if (hasSidePanelBoard) {
      validation.warnings.push("BoardPlan widthModel: SidePanel board present but exteriorSide is none.");
    }

    const createdBoardIds = boards.map((b) => b.id);

    return {
      boards,
      validation,
      hPlanes: hPlanesLayout.map((h) => Object.assign({}, h)),
      hSetGroups,
      createdBoardIds,
      widthModel: wm,
      frontPanels: frontLayer.frontPanels,
      frontPanelContext: frontLayer.context
        ? {
            CPT: frontLayer.context.CPT,
            FPT: frontLayer.context.FPT,
            FC: frontLayer.context.FC,
            panelSystemX0: frontLayer.context.panelSystemX0,
            panelSystemX1: frontLayer.context.panelSystemX1,
            B3Ref: frontLayer.context.B3Ref,
            T3Ref: frontLayer.context.T3Ref,
          }
        : null,
    };
  }

  function buildPureParams(ui) {
    const base = deriveBaseParams(ui);
    const layout = buildNormalizedLayout(ui);
    const ziList = generateZi(layout.panels);
    base.hasV5 = ziList.some((z) => z && z.role === "fridge_base" && z.shape === "full");
    const panelGeometries = resolvePanelGeometry(layout.panels, base);

    let avoidance;
    let avoidanceError = null;
    try {
      avoidance = resolveAvoidance(ui, layout.panels, ui.cabinet.panelThickness);
    } catch (error) {
      avoidanceError = error;
      avoidance = {
        enabled: ui.wheelAvoidance.enabled,
        inputHeight: ui.wheelAvoidance.height,
        inputDepth: ui.wheelAvoidance.depth,
        finalMode: "none",
        finalTopZ: 0,
        finalFrontBoardHeight: 0,
        finalDepth: 0,
        fridgeBaseBottomZ: 0,
        fridgeGap: 0,
      };
    }

    const gh = generateHPlanes(layout.panels, avoidance, layout);
    const hPlanes = gh.hPlanes;
    const validation = validateAll(ui, layout, ziList, avoidance, avoidanceError);
    const hw = gh.warnings;
    if (Array.isArray(hw)) {
      for (let hi = 0; hi < hw.length; hi += 1) validation.warnings.push(hw[hi]);
    }
    const fridgeHSetMode = avoidance.finalMode === "raised" ? "above" : "below";

    return {
      meta: { version: VERSION, unit: UNIT },
      input: ui,
      base,
      layout: {
        totalStackHeight: layout.totalStackHeight,
        cabinetHeight: ui.cabinet.height,
        difference: layout.totalStackHeight - ui.cabinet.height,
        bottomClearanceRegion: layout.bottomClearanceRegion,
        topClearanceRegion: layout.topClearanceRegion,
        boundaryPanelThicknessMm: layout.boundaryPanelThicknessMm,
        middlePanelThicknessMm: layout.middlePanelThicknessMm,
        sections: layout.sections,
        panels: layout.panels,
        ziList,
        panelGeometries,
        hPlanes,
        displaySegments: layout.displaySegments,
      },
      avoidance,
      structuralMode: {
        fridgeHSetMode,
        avoidanceRaised: avoidance.finalMode === "raised",
        sidePanelSide: base.sidePanelSide,
        v5Side: base.v5Side,
        hasSidePanel: base.hasSidePanel,
        hasV5: base.hasV5,
      },
      validation,
    };
  }

  return {
    VERSION,
    DEFAULT_TOP_CLEARANCE_MM,
    DEFAULT_BOTTOM_CLEARANCE_MM,
    boundaryPanelThickness,
    cabinetWidthFromFridge,
    fridgeWidthFromCabinet,
    normalizeSectionType,
    deriveBaseParams,
    deriveWidthModel,
    classifyPanel,
    buildNormalizedLayout,
    generateZi,
    getZiFullProfile,
    getZiHalfProfile,
    getV5Profile,
    resolvePanelGeometry,
    resolveAvoidance,
    generateHPlanes,
    validateAll,
    buildPureParams,
    buildBoardPlan,
    auditBoardMetadata,
    buildAssemblyPlacementPlan,
    formatBoardPlacementSummary,
    getV12Profile,
    getV34Profile,
    getBoardById,
    getVectorBBox,
    isVectorClosed,
    pointExists,
    dumpBoardVector,
    verifyVSeriesVectors,
  };
});
