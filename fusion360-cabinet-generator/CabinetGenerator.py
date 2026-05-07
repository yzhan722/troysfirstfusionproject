import adsk.core
import os
import sys
import traceback


_app = None


class CabinetGeneratorApp:
    CMD_ID = "cabinetGeneratorCommand"
    CMD_NAME = "Cabinet Generator"
    CMD_DESC = "Generate cabinet debug sketches from pure geometry calculations."
    CONTROL_ID = "cabinetGeneratorControl"
    PANEL_ID = "cabinetGeneratorPanel"
    PANEL_NAME = "Cabinet Generator"
    FALLBACK_PANEL_ID = "SolidScriptsAddinsPanel"
    PALETTE_ID = "cabinetGeneratorPalette"
    PALETTE_NAME = "Cabinet Generator"

    def __init__(self):
        from fusion.adapter import FusionAdapter
        from services.debug_sketch_service import DebugSketchService
        from services.solid_extrude_service import SolidExtrudeService

        self.fusion = FusionAdapter()
        self.handlers = []
        self.command_definition = None
        self.control = None
        self.panel = None
        self.palette = None
        self.debug_sketch_service = DebugSketchService(self.fusion)
        self.solid_extrude_service = SolidExtrudeService(self.fusion)

    def start(self):
        _, ui = self.fusion.get_app_ui()
        if not ui:
            return

        cmd_defs = ui.commandDefinitions
        self.command_definition = cmd_defs.itemById(self.CMD_ID)
        if not self.command_definition:
            self.command_definition = cmd_defs.addButtonDefinition(
                self.CMD_ID,
                self.CMD_NAME,
                self.CMD_DESC,
                "",
            )

        on_created = _CommandCreatedHandler(self)
        self.command_definition.commandCreated.add(on_created)
        self.handlers.append(on_created)

        workspace = ui.workspaces.itemById("FusionSolidEnvironment")
        self.panel = workspace.toolbarPanels.itemById(self.PANEL_ID) if workspace else None
        if not self.panel and workspace:
            self.panel = workspace.toolbarPanels.add(
                self.PANEL_ID,
                self.PANEL_NAME,
                self.FALLBACK_PANEL_ID,
                False,
            )
        if self.panel:
            old_control = self.panel.controls.itemById(self.CONTROL_ID)
            if old_control:
                old_control.deleteMe()
            self.control = self.panel.controls.addCommand(self.command_definition, self.CONTROL_ID)
            self.control.isVisible = True
            self.control.isPromoted = True
            self.control.isPromotedByDefault = True

        self.show_palette()

    def stop(self):
        _, ui = self.fusion.get_app_ui()
        try:
            if self.control:
                self.control.deleteMe()
                self.control = None
            if self.panel:
                self.panel.deleteMe()
                self.panel = None
            if self.palette:
                self.palette.deleteMe()
                self.palette = None
            if self.command_definition:
                self.command_definition.deleteMe()
                self.command_definition = None
            self.handlers.clear()
        except:
            if ui:
                ui.messageBox("Cabinet Generator stop failed:\n{}".format(traceback.format_exc()))

    def show_palette(self):
        _, ui = self.fusion.get_app_ui()
        if not ui:
            return
        palettes = ui.palettes
        self.palette = palettes.itemById(self.PALETTE_ID)
        if not self.palette:
            html_path = os.path.join(os.path.dirname(__file__), "palette.html")
            self.palette = palettes.add(
                self.PALETTE_ID,
                self.PALETTE_NAME,
                "file:///" + os.path.abspath(html_path).replace("\\", "/"),
                True,
                True,
                True,
                420,
                620,
                False,
            )
            incoming = _PaletteIncomingHandler(self)
            self.palette.incomingFromHTML.add(incoming)
            self.handlers.append(incoming)
        self.palette.isVisible = True

    def handle_html_event(self, html_args):
        action, params = self._parse_html_args(html_args)
        if not action:
            html_args.returnData = ""
            return
        if action == "generateDebugSketches":
            lines = self.debug_sketch_service.generate(params)
        elif action == "generateBodies":
            lines = self.solid_extrude_service.generate(params)
        elif action == "clearGenerated":
            lines = self.solid_extrude_service.clear_generated()
        else:
            lines = ["Unknown action: {}".format(action or "")]

        html_args.returnData = ""
        if self.palette:
            self.palette.sendInfoToHTML("cabinetResult", self._json_text(lines))

    def _parse_html_args(self, html_args):
        import json

        raw = html_args.data or ""
        if not raw:
            return html_args.action, {}
        try:
            payload = json.loads(raw)
            if isinstance(payload, dict):
                action = payload.get("action")
                params = payload.get("params") or {}
                nested = payload.get("data")
                if isinstance(nested, str) and nested:
                    try:
                        nested_payload = json.loads(nested)
                        if isinstance(nested_payload, dict):
                            action = nested_payload.get("action") or action
                            params = nested_payload.get("params") or params
                    except:
                        pass
                if action and action != "response":
                    return action, params
        except:
            pass
        return html_args.action if html_args.action != "response" else None, {}

    def _json_text(self, lines):
        import json

        return json.dumps({"text": "\n".join(lines)})


class _CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self, app):
        super().__init__()
        self.app = app

    def notify(self, args):
        try:
            command = args.command
            on_execute = _ShowPaletteExecuteHandler(self.app)
            command.execute.add(on_execute)
            self.app.handlers.append(on_execute)
        except:
            _, ui = self.app.fusion.get_app_ui()
            if ui:
                ui.messageBox("Cabinet Generator command failed:\n{}".format(traceback.format_exc()))


class _ShowPaletteExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self, app):
        super().__init__()
        self.app = app

    def notify(self, args):
        self.app.show_palette()


class _PaletteIncomingHandler(adsk.core.HTMLEventHandler):
    def __init__(self, app):
        super().__init__()
        self.app = app

    def notify(self, args):
        try:
            html_args = adsk.core.HTMLEventArgs.cast(args)
            if html_args:
                self.app.handle_html_event(html_args)
        except:
            _, ui = self.app.fusion.get_app_ui()
            if ui:
                ui.messageBox("Cabinet Generator action failed:\n{}".format(traceback.format_exc()))


def run(context):
    global _app
    ui = adsk.core.Application.get().userInterface if adsk.core.Application.get() else None
    try:
        plugin_dir = os.path.dirname(__file__)
        if plugin_dir not in sys.path:
            sys.path.insert(0, plugin_dir)
        for mod in [
            "fusion.adapter",
            "core.overhead_geometry",
            "services.debug_sketch_service",
            "services.solid_extrude_service",
        ]:
            if mod in sys.modules:
                del sys.modules[mod]
        _app = CabinetGeneratorApp()
        _app.start()
    except:
        if ui:
            ui.messageBox("Cabinet Generator start failed:\n{}".format(traceback.format_exc()))


def stop(context):
    global _app
    if _app:
        _app.stop()
        _app = None
