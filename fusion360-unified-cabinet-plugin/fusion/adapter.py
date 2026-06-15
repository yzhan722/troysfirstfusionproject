import adsk.core
import adsk.fusion


class FusionAdapter:
    """Small Fusion API wrapper shared by unified plugin modules."""

    @staticmethod
    def mm_to_cm(value_mm):
        return float(value_mm) / 10.0

    def get_app_ui(self):
        app = adsk.core.Application.get()
        return app, app.userInterface if app else None

    def get_active_design(self):
        app, _ui = self.get_app_ui()
        if not app or not app.activeProduct:
            return None
        return adsk.fusion.Design.cast(app.activeProduct)

    def get_root_component(self):
        design = self.get_active_design()
        return design.rootComponent if design else None

    def refresh_viewport(self):
        app, _ui = self.get_app_ui()
        try:
            if app and app.activeViewport:
                app.activeViewport.refresh()
        except Exception:
            pass

    def log(self, tag, message):
        app, _ui = self.get_app_ui()
        try:
            log_fn = getattr(app, "log", None) if app else None
            if callable(log_fn):
                log_fn(str(tag), str(message)[:3500])
        except Exception:
            pass
