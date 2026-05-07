import adsk.core
import adsk.fusion


class FusionAdapter:
    def get_app_ui(self):
        app = adsk.core.Application.get()
        if not app:
            return None, None
        return app, app.userInterface

    def get_active_design(self):
        app, _ = self.get_app_ui()
        return adsk.fusion.Design.cast(app.activeProduct) if app else None

    def refresh_viewport(self):
        app, _ = self.get_app_ui()
        if app and app.activeViewport:
            app.activeViewport.refresh()

    def cm(self, value_mm):
        return float(value_mm) / 10.0
