import adsk.core
import traceback
import os
import sys

_plugin_app = None


def _get_ui():
    app = adsk.core.Application.get()
    return app.userInterface if app else None


def run(context):
    global _plugin_app
    ui = _get_ui()
    try:
        plugin_dir = os.path.dirname(__file__)
        if plugin_dir not in sys.path:
            sys.path.insert(0, plugin_dir)
        # Force refresh local modules between add-in runs.
        for mod in [
            "fusion.adapter",
            "core.models",
            "services.scan_service",
            "services.color_service",
            "services.select_service",
            "services.contact_service",
            "services.drill_service",
            "services.restore_service",
            "services.half_slot_service",
            "ui.palette_controller",
        ]:
            if mod in sys.modules:
                del sys.modules[mod]

        # Lazy imports so module-load failures become visible.
        from fusion.adapter import FusionAdapter
        from services.color_service import ColorService
        from services.scan_service import ScanService
        from services.select_service import SelectService
        from services.contact_service import ContactService
        from services.drill_service import DrillService
        from services.half_slot_service import HalfSlotService
        from services.restore_service import RestoreService
        from ui.palette_controller import PaletteController

        class PluginConfig:
            CMD_ID = "troysPluginCommand"
            CMD_NAME = "Troy's Plugin"
            CMD_DESC = "Open Troy's Plugin palette."
            CONTROL_ID = "troysPluginControl"
            PANEL_ID = "troysPluginPanel"
            PANEL_NAME = "Troy's Plugin"
            FALLBACK_PANEL_ID = "SolidScriptsAddinsPanel"
            PALETTE_ID = "troysPluginPalette"
            PALETTE_NAME = "Troy's Plugin"

        class PluginApp:
            def __init__(self):
                self.fusion = FusionAdapter()
                self.handlers = []
                self.command_definition = None
                self.control = None
                self.panel = None
                self.palette_controller = PaletteController(
                    fusion_adapter=self.fusion,
                    handlers_store=self.handlers,
                    palette_id=PluginConfig.PALETTE_ID,
                    palette_name=PluginConfig.PALETTE_NAME,
                )
                self.scan_service = ScanService(self.fusion)
                self.color_service = ColorService(self.fusion)
                self.select_service = SelectService(self.fusion)
                self.contact_service = ContactService(self.fusion)
                self.drill_service = DrillService(self.fusion)
                self.restore_service = RestoreService(self.fusion)
                self.half_slot_service = HalfSlotService(self.fusion)
                self.palette_controller.set_scan_service(self.scan_service)
                self.palette_controller.set_color_service(self.color_service)
                self.palette_controller.set_select_service(self.select_service)
                self.palette_controller.set_contact_service(self.contact_service)
                self.palette_controller.set_drill_service(self.drill_service)
                self.palette_controller.set_restore_service(self.restore_service)
                self.palette_controller.set_half_slot_service(self.half_slot_service)

            def start(self):
                app, ui2 = self.fusion.get_app_ui()
                if not app or not ui2:
                    return
                cmd_defs = ui2.commandDefinitions
                self.command_definition = cmd_defs.itemById(PluginConfig.CMD_ID)
                resource_dir = os.path.join(os.path.dirname(__file__), "resources")
                if not self.command_definition:
                    self.command_definition = cmd_defs.addButtonDefinition(
                        PluginConfig.CMD_ID,
                        PluginConfig.CMD_NAME,
                        PluginConfig.CMD_DESC,
                        resource_dir,
                    )

                on_created = _CommandCreatedHandler(self)
                self.command_definition.commandCreated.add(on_created)
                self.handlers.append(on_created)

                workspace = ui2.workspaces.itemById("FusionSolidEnvironment")
                panel = workspace.toolbarPanels.itemById(PluginConfig.PANEL_ID) if workspace else None
                if not panel and workspace:
                    panel = workspace.toolbarPanels.add(
                        PluginConfig.PANEL_ID,
                        PluginConfig.PANEL_NAME,
                        PluginConfig.FALLBACK_PANEL_ID,
                        False,
                    )
                self.panel = panel
                if panel:
                    old_control = panel.controls.itemById(PluginConfig.CONTROL_ID)
                    if old_control:
                        old_control.deleteMe()
                    self.control = panel.controls.addCommand(self.command_definition, PluginConfig.CONTROL_ID)
                    self.control.isVisible = True
                    self.control.isPromoted = True
                    self.control.isPromotedByDefault = True
                self.palette_controller.show()

            def shutdown(self):
                _, ui2 = self.fusion.get_app_ui()
                try:
                    if self.control:
                        self.control.deleteMe()
                        self.control = None
                    if self.panel:
                        self.panel.deleteMe()
                        self.panel = None
                    self.palette_controller.hide()
                    if self.command_definition:
                        self.command_definition.deleteMe()
                        self.command_definition = None
                    self.handlers.clear()
                except:
                    if ui2:
                        ui2.messageBox("Add-in stop failed:\n{}".format(traceback.format_exc()))

        class _CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
            def __init__(self, plugin_app):
                super().__init__()
                self.plugin_app = plugin_app

            def notify(self, args):
                try:
                    cmd = args.command
                    on_execute = _ShowPaletteExecuteHandler(self.plugin_app)
                    cmd.execute.add(on_execute)
                    self.plugin_app.handlers.append(on_execute)
                except:
                    _, ui2 = self.plugin_app.fusion.get_app_ui()
                    if ui2:
                        ui2.messageBox("Command creation failed:\n{}".format(traceback.format_exc()))

        class _ShowPaletteExecuteHandler(adsk.core.CommandEventHandler):
            def __init__(self, plugin_app):
                super().__init__()
                self.plugin_app = plugin_app

            def notify(self, args):
                self.plugin_app.palette_controller.show()

        _plugin_app = PluginApp()
        _plugin_app.start()
    except:
        if ui:
            ui.messageBox("Add-in start failed (import/runtime):\n{}".format(traceback.format_exc()))


def stop(context):
    global _plugin_app
    if _plugin_app:
        _plugin_app.shutdown()
        _plugin_app = None
