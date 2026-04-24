import adsk.fusion

from core.models import BodyModel


class SelectService:
    def __init__(self, fusion_adapter):
        self.fusion = fusion_adapter

    def select_15(self):
        return self._select_by_target(15)

    def select_18(self):
        return self._select_by_target(18)

    def select_other(self):
        return self._select_by_target("other")

    def _select_by_target(self, target):
        app, ui = self.fusion.get_app_ui()
        design = self.fusion.get_active_design()
        if not app or not ui or not design:
            return ["No active Fusion design."]

        body_pairs = self.fusion.all_project_bodies(design)
        if not body_pairs:
            return ["No bodies found."]
        bodies = [BodyModel.from_brep_body(owner, body) for owner, body in body_pairs]

        sels = ui.activeSelections
        if sels is None:
            return ["Selection API unavailable."]
        try:
            sels.clear()
        except Exception as ex:
            return [f"Selection clear failed: {ex}"]

        matched = 0
        failed = 0
        details = []
        for model in bodies:
            t = self._thickness_tag(model)
            if isinstance(target, int):
                is_match = t == target
                target_label = f"{target}mm"
            else:
                is_match = t not in (15, 18)
                target_label = "Other"
            if not is_match:
                continue

            ok = self._add_selectable(sels, model.source_body)
            l, w, h = model.length_mm, model.width_mm, model.height_mm
            if ok:
                matched += 1
                details.append(
                    f"{model.owner} | {model.name} | LxWxH: {l:.2f} x {w:.2f} x {h:.2f} mm | T:{t}"
                )
            else:
                failed += 1
                details.append(f"{model.owner} | {model.name} | T:{t} | select-failed")

        if app and app.activeViewport:
            app.activeViewport.refresh()

        lines = [f"Selected ({target_label}): {matched}", f"Failed: {failed}", ""]
        lines.extend(details if details else ["No matching bodies found."])
        return lines

    def _thickness_tag(self, model):
        return int(round(model.thickness_mm))

    def _add_selectable(self, selections, body):
        try:
            if selections.add(body):
                return True
        except:
            pass
        try:
            native = getattr(body, "nativeObject", None)
            if native and selections.add(native):
                return True
        except:
            pass
        try:
            faces = body.faces
            if faces and faces.count > 0 and selections.add(faces.item(0)):
                return True
        except:
            pass
        return False
