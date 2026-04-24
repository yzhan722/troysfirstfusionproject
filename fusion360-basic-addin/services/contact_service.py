import adsk.core

from core.models import BodyModel
from config import ATTRIBUTE_GROUP


class ContactService:
    def __init__(self, fusion_adapter):
        self.fusion = fusion_adapter

    def detect(self):
        selected = self.fusion.selected_bodies()
        if len(selected) < 2:
            return ["Select at least 2 bodies first."]

        body_models = [BodyModel.from_brep_body(owner, body) for owner, body in selected]
        confirmed = 0
        review = 0
        none = 0
        lines = [f"Selected bodies: {len(body_models)}", ""]

        for i in range(len(body_models)):
            for j in range(i + 1, len(body_models)):
                a_model = body_models[i]
                b_model = body_models[j]
                a = a_model.source_body
                b = b_model.source_body
                status, area_mm2, axis, gap_mm, plane_coord = self._contact_area_by_bbox(a, b)
                a_face = self._nearest_planar_face(a, axis, plane_coord)
                b_face = self._nearest_planar_face(b, axis, plane_coord)
                a_role = self._face_role(a_face)
                b_role = self._face_role(b_face)
                if status == "confirmed":
                    confirmed += 1
                elif status == "review":
                    review += 1
                else:
                    none += 1
                lines.append(
                    "{} <-> {} | status:{} | area:{:.2f} mm^2 | axis:{} | gap:{:.3f} mm | contact:{} -> {}".format(
                        a_model.name, b_model.name, status, area_mm2, axis, gap_mm, a_role, b_role
                    )
                )

        total = (len(body_models) * (len(body_models) - 1)) // 2
        return [
            f"Total pairs: {total}",
            f"Confirmed: {confirmed}",
            f"Review: {review}",
            f"None: {none}",
            "",
        ] + lines

    def _contact_area_by_bbox(self, body_a, body_b):
        a = body_a.boundingBox
        b = body_b.boundingBox
        a_min = [a.minPoint.x * 10.0, a.minPoint.y * 10.0, a.minPoint.z * 10.0]
        a_max = [a.maxPoint.x * 10.0, a.maxPoint.y * 10.0, a.maxPoint.z * 10.0]
        b_min = [b.minPoint.x * 10.0, b.minPoint.y * 10.0, b.minPoint.z * 10.0]
        b_max = [b.maxPoint.x * 10.0, b.maxPoint.y * 10.0, b.maxPoint.z * 10.0]

        best_axis = 0
        best_gap = float("inf")
        best_area = 0.0
        best_plane_coord = 0.0
        for axis in range(3):
            if a_max[axis] < b_min[axis]:
                gap = b_min[axis] - a_max[axis]
                plane_coord = (a_max[axis] + b_min[axis]) * 0.5
            elif b_max[axis] < a_min[axis]:
                gap = a_min[axis] - b_max[axis]
                plane_coord = (a_min[axis] + b_max[axis]) * 0.5
            else:
                gap = 0.0
                plane_coord = (max(a_min[axis], b_min[axis]) + min(a_max[axis], b_max[axis])) * 0.5

            if gap < best_gap:
                best_gap = gap
                best_axis = axis
                best_plane_coord = plane_coord

            if gap > 1.0:
                continue

            plane_axes = [idx for idx in (0, 1, 2) if idx != axis]
            ov1 = min(a_max[plane_axes[0]], b_max[plane_axes[0]]) - max(a_min[plane_axes[0]], b_min[plane_axes[0]])
            ov2 = min(a_max[plane_axes[1]], b_max[plane_axes[1]]) - max(a_min[plane_axes[1]], b_min[plane_axes[1]])
            if ov1 <= 0 or ov2 <= 0:
                continue
            area = ov1 * ov2
            if area > best_area:
                best_area = area
                best_gap = gap
                best_axis = axis
                best_plane_coord = plane_coord

        if best_area <= 0:
            return "none", 0.0, best_axis, best_gap, best_plane_coord
        if best_gap <= 0.5:
            return "confirmed", best_area, best_axis, best_gap, best_plane_coord
        return "review", best_area, best_axis, best_gap, best_plane_coord

    def _nearest_planar_face(self, body, axis, plane_coord_mm):
        best = None
        best_dist = float("inf")
        for i in range(body.faces.count):
            face = body.faces.item(i)
            plane = adsk.core.Plane.cast(face.geometry)
            if not plane:
                continue
            normal = [abs(plane.normal.x), abs(plane.normal.y), abs(plane.normal.z)]
            n_axis = normal.index(max(normal))
            if n_axis != axis:
                continue
            coord = [plane.origin.x * 10.0, plane.origin.y * 10.0, plane.origin.z * 10.0][axis]
            dist = abs(coord - plane_coord_mm)
            if dist < best_dist:
                best_dist = dist
                best = face
        return best

    def _face_role(self, face):
        if not face:
            return "unknown"
        attr = face.attributes.itemByName(ATTRIBUTE_GROUP, "role")
        if not attr or not attr.value:
            return "unknown"
        return attr.value
