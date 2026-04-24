import adsk.core


class ColorService:
    def __init__(self, fusion_adapter):
        self.fusion = fusion_adapter

    def apply(self):
        design = self.fusion.get_active_design()
        if not design:
            return ["No active Fusion design."]

        selected = self.fusion.selected_bodies()
        if selected:
            bodies = selected
            scope = "selected bodies"
        else:
            bodies = self.fusion.all_project_bodies(design)
            scope = "all project bodies"

        if not bodies:
            return ["No bodies found."]

        painted = 0
        failed = 0
        lines = [f"Apply Color on {len(bodies)} bodies ({scope})", ""]
        for owner, body in bodies:
            thickness = self._thickness_mm(body)
            label, base_rgb = self._color_for_thickness(thickness)
            main = self._get_or_create_appearance(design, f"TroyPlugin_{label}", base_rgb)
            side = self._get_or_create_appearance(
                design, f"TroyPlugin_{label}_Side", self._lighten(base_rgb, 0.45)
            )
            if not main or not side:
                failed += 1
                lines.append(f"{owner} | {body.name} | {label} | appearance-failed")
                continue

            ok = self._apply_face_color(body, main, side)
            if ok:
                painted += 1
                lines.append(f"{owner} | {body.name} | {label} | painted")
            else:
                failed += 1
                lines.append(f"{owner} | {body.name} | {label} | paint-failed")

        app, _ = self.fusion.get_app_ui()
        if app and app.activeViewport:
            app.activeViewport.refresh()

        return [f"Painted: {painted}", f"Failed: {failed}", ""] + lines

    def _thickness_mm(self, body):
        l, w, h = self.fusion.dims_mm(body)
        return min(l, w, h)

    def _color_for_thickness(self, thickness_mm):
        t = int(round(thickness_mm))
        if t == 15:
            return "Green", (80, 220, 100)
        if t == 18:
            return "Brown", (205, 140, 80)
        return "Blue", (90, 160, 255)

    def _lighten(self, rgb, factor):
        r = int(rgb[0] + (255 - rgb[0]) * factor)
        g = int(rgb[1] + (255 - rgb[1]) * factor)
        b = int(rgb[2] + (255 - rgb[2]) * factor)
        return min(255, r), min(255, g), min(255, b)

    def _get_or_create_appearance(self, design, name, rgb):
        ap = design.appearances.itemByName(name)
        if not ap:
            seed = design.appearances.item(0) if design.appearances.count > 0 else None
            if not seed:
                return None
            ap = design.appearances.addByCopy(seed, name)
            if not ap:
                return None
        self._set_appearance_color(ap, rgb)
        return ap

    def _set_appearance_color(self, appearance, rgb):
        props = appearance.appearanceProperties
        color = adsk.core.Color.create(rgb[0], rgb[1], rgb[2], 255)
        for i in range(props.count):
            cp = adsk.core.ColorProperty.cast(props.item(i))
            if cp:
                cp.value = color

    def _apply_face_color(self, body, main_appearance, side_appearance):
        try:
            body.appearance = main_appearance
            axis = self._thickness_axis(body)
            faces = body.faces
            for i in range(faces.count):
                face = faces.item(i)
                plane = adsk.core.Plane.cast(face.geometry)
                if not plane:
                    continue
                normal = [abs(plane.normal.x), abs(plane.normal.y), abs(plane.normal.z)]
                normal_axis = normal.index(max(normal))
                face.appearance = main_appearance if normal_axis == axis else side_appearance
            return True
        except:
            return False

    def _thickness_axis(self, body):
        bbox = body.boundingBox
        min_pt = bbox.minPoint
        max_pt = bbox.maxPoint
        lengths = [
            abs(max_pt.x - min_pt.x),
            abs(max_pt.y - min_pt.y),
            abs(max_pt.z - min_pt.z),
        ]
        return lengths.index(min(lengths))
