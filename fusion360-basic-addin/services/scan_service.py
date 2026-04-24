import adsk.core

from core.models import BodyModel
from config import ATTRIBUTE_GROUP


class ScanService:
    def __init__(self, fusion_adapter):
        self.fusion = fusion_adapter

    def scan(self):
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

        lines = [f"Bodies found: {len(bodies)} ({scope})", ""]
        for owner, body in bodies:
            body_model = BodyModel.from_brep_body(owner, body)
            self._write_body_attributes(body, body_model)
            self._write_face_roles(body, body_model.thickness_axis)
            lines.append(
                "{} | {} | LxWxH: {:.2f} x {:.2f} x {:.2f} mm".format(
                    body_model.owner,
                    body_model.name,
                    body_model.length_mm,
                    body_model.width_mm,
                    body_model.height_mm,
                )
            )
        return lines

    def _write_body_attributes(self, body, model):
        attrs = body.attributes
        attrs.add(ATTRIBUTE_GROUP, "length_mm", "{:.3f}".format(model.length_mm))
        attrs.add(ATTRIBUTE_GROUP, "width_mm", "{:.3f}".format(model.width_mm))
        attrs.add(ATTRIBUTE_GROUP, "height_mm", "{:.3f}".format(model.height_mm))
        attrs.add(ATTRIBUTE_GROUP, "thickness_mm", "{:.3f}".format(model.thickness_mm))
        attrs.add(ATTRIBUTE_GROUP, "thickness_axis", str(model.thickness_axis))
        attrs.add(ATTRIBUTE_GROUP, "material", model.material)

    def _write_face_roles(self, body, thickness_axis):
        for i in range(body.faces.count):
            face = body.faces.item(i)
            plane = face.geometry
            # Only planar faces get deterministic role; others are null.
            plane_geo = adsk.core.Plane.cast(plane)

            role = "null"
            if plane_geo:
                normal = [abs(plane_geo.normal.x), abs(plane_geo.normal.y), abs(plane_geo.normal.z)]
                normal_axis = normal.index(max(normal))
                role = "front_back" if normal_axis == thickness_axis else "side"
            face.attributes.add(ATTRIBUTE_GROUP, "role", role)
