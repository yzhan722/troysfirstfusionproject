import adsk.core
import json
import os
import traceback


class PaletteController:
    def __init__(self, fusion_adapter, handlers_store, palette_id, palette_name):
        self.fusion = fusion_adapter
        self.handlers_store = handlers_store
        self.palette_id = palette_id
        self.palette_name = palette_name
        self.palette = None
        self.scan_service = None
        self.color_service = None
        self.select_service = None
        self.contact_service = None
        self.drill_service = None
        self.restore_service = None
        self.half_slot_service = None

    def set_scan_service(self, scan_service):
        self.scan_service = scan_service

    def set_color_service(self, color_service):
        self.color_service = color_service

    def set_select_service(self, select_service):
        self.select_service = select_service

    def set_contact_service(self, contact_service):
        self.contact_service = contact_service

    def set_drill_service(self, drill_service):
        self.drill_service = drill_service

    def set_restore_service(self, restore_service):
        self.restore_service = restore_service

    def set_half_slot_service(self, half_slot_service):
        self.half_slot_service = half_slot_service

    def show(self):
        _, ui = self.fusion.get_app_ui()
        if not ui:
            return
        palettes = ui.palettes
        self.palette = palettes.itemById(self.palette_id)
        if not self.palette:
            html_path = os.path.join(os.path.dirname(__file__), "..", "palette.html")
            self.palette = palettes.add(
                self.palette_id,
                self.palette_name,
                "file:///" + os.path.abspath(html_path).replace("\\", "/"),
                True,
                True,
                True,
                420,
                540,
                False,
            )
            incoming = _PaletteIncomingHandler(self)
            self.palette.incomingFromHTML.add(incoming)
            self.handlers_store.append(incoming)
        self.palette.isVisible = True

    def hide(self):
        if self.palette:
            self.palette.deleteMe()
            self.palette = None

    def handle_action(self, html_args):
        action = self._resolve_action(html_args)
        if not action:
            return
        if action == "scan" and self.scan_service:
            lines = self.scan_service.scan()
        elif action == "applyColor" and self.color_service:
            lines = self.color_service.apply()
        elif action == "select15" and self.select_service:
            lines = self.select_service.select_15()
        elif action == "select18" and self.select_service:
            lines = self.select_service.select_18()
        elif action == "selectOther" and self.select_service:
            lines = self.select_service.select_other()
        elif action == "detectContacts" and self.contact_service:
            lines = self.contact_service.detect()
        elif action == "drillScrewHoles" and self.drill_service:
            lines = self.drill_service.drill()
        elif action == "restoreGenerated" and self.restore_service:
            lines = self.restore_service.restore_screw_holes()
        elif action == "halfSlot" and self.half_slot_service:
            lines = self.half_slot_service.create()
        elif action == "fullSlot" and self.half_slot_service:
            lines = self.half_slot_service.create_full_slot()
        else:
            lines = [f"Coming soon: {action}"]

        payload = json.dumps({"text": "\n".join(lines)})
        # Avoid response echo loops: update HTML via sendInfo only.
        html_args.returnData = ""
        if self.palette:
            self.palette.sendInfoToHTML("scanResult", payload)

    def _resolve_action(self, html_args):
        action = html_args.action
        if action and action not in ("response",):
            return action
        if html_args.data:
            parsed = self._extract_action_from_data(html_args.data)
            if parsed:
                return parsed
        return None

    def _extract_action_from_data(self, raw_data):
        try:
            parsed = json.loads(raw_data)
            if isinstance(parsed, dict):
                action = parsed.get("action")
                if isinstance(action, str):
                    return action
                nested = parsed.get("data")
                if isinstance(nested, str) and nested:
                    nested_obj = json.loads(nested)
                    if isinstance(nested_obj, dict):
                        nested_action = nested_obj.get("action")
                        if isinstance(nested_action, str):
                            return nested_action
        except:
            pass
        if isinstance(raw_data, str):
            text = raw_data.strip()
            if text and ("{" not in text and "}" not in text):
                return text
        return None


class _PaletteIncomingHandler(adsk.core.HTMLEventHandler):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller

    def notify(self, args):
        try:
            html_args = adsk.core.HTMLEventArgs.cast(args)
            if not html_args:
                return
            self.controller.handle_action(html_args)
        except:
            _, ui = self.controller.fusion.get_app_ui()
            if ui:
                ui.messageBox("Palette action failed:\n{}".format(traceback.format_exc()))
