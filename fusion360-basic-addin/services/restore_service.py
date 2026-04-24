class RestoreService:
    def __init__(self, fusion_adapter):
        self.fusion = fusion_adapter

    def restore_screw_holes(self):
        design = self.fusion.get_active_design()
        if not design:
            return ["No active Fusion design."]
        root = design.rootComponent
        if not root:
            return ["No root component found."]

        components = self._all_components(root)
        removed_holes = 0
        removed_half_slot_features = 0
        removed_sketches = 0

        for comp in components:
            try:
                bodies = comp.bRepBodies
                for i in range(bodies.count):
                    self._clear_joinery_attributes(bodies.item(i))
            except:
                pass

            try:
                holes = comp.features.holeFeatures
                for i in range(holes.count - 1, -1, -1):
                    feat = holes.item(i)
                    if feat.name.startswith("TroyPlugin_HoleFeature"):
                        feat.deleteMe()
                        removed_holes += 1
            except:
                pass

            try:
                combines = comp.features.combineFeatures
                for i in range(combines.count - 1, -1, -1):
                    feat = combines.item(i)
                    name = feat.name or ""
                    if name.startswith("TroyPlugin_HoleFeature"):
                        feat.deleteMe()
                        removed_holes += 1
                    elif name.startswith("TroyPlugin_Tongue"):
                        feat.deleteMe()
                        removed_half_slot_features += 1
            except:
                pass

            try:
                extrudes = comp.features.extrudeFeatures
                for i in range(extrudes.count - 1, -1, -1):
                    feat = extrudes.item(i)
                    name = feat.name or ""
                    if name.startswith("TroyPlugin_HoleFeature") or name.startswith("TroyPlugin_HoleToolFeature"):
                        feat.deleteMe()
                        removed_holes += 1
                    elif name.startswith("TroyPlugin_SlotCut") or name.startswith("TroyPlugin_Tongue"):
                        feat.deleteMe()
                        removed_half_slot_features += 1
            except:
                pass

            try:
                sketches = comp.sketches
                for i in range(sketches.count - 1, -1, -1):
                    sk = sketches.item(i)
                    name = sk.name or ""
                    if (
                        name.startswith("TroyPlugin_HoleSketch")
                        or name.startswith("TroyPlugin_SlotSketch_")
                        or name.startswith("TroyPlugin_TongueSketch_")
                    ):
                        sk.deleteMe()
                        removed_sketches += 1
            except:
                pass

        app, _ = self.fusion.get_app_ui()
        if app and app.activeViewport:
            app.activeViewport.refresh()

        return [
            "Restore generated features completed.",
            f"Removed hole features: {removed_holes}",
            f"Removed half-slot features: {removed_half_slot_features}",
            f"Removed sketches: {removed_sketches}",
        ]

    def _all_components(self, root):
        comps = []
        seen = set()
        comps.append(root)
        seen.add(root.entityToken)
        for i in range(root.allOccurrences.count):
            occ = root.allOccurrences.item(i)
            comp = occ.component
            if not comp:
                continue
            token = comp.entityToken
            if token in seen:
                continue
            seen.add(token)
            comps.append(comp)
        return comps

    def _clear_joinery_attributes(self, body):
        try:
            attrs = body.attributes
            for i in range(attrs.count - 1, -1, -1):
                attr = attrs.item(i)
                if not attr or attr.groupName != "FusionCabinetAutomation":
                    continue
                if attr.name.startswith("joinery_"):
                    attr.deleteMe()
        except:
            pass
