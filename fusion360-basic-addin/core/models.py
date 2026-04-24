from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from config import ATTRIBUTE_GROUP


Vec3 = Tuple[float, float, float]


@dataclass
class BodyModel:
    owner: str
    name: str
    token: str
    length_mm: float
    width_mm: float
    height_mm: float
    thickness_mm: float
    thickness_axis: int
    bbox_min_mm: Vec3
    bbox_max_mm: Vec3
    material: str = "null"
    body_attrs: Dict[str, str] = field(default_factory=dict)
    face_roles: Dict[str, str] = field(default_factory=dict)
    source_body: Optional[object] = None

    @classmethod
    def from_brep_body(cls, owner, body):
        bbox = body.boundingBox
        min_pt = bbox.minPoint
        max_pt = bbox.maxPoint
        x_mm = abs(max_pt.x - min_pt.x) * 10.0
        y_mm = abs(max_pt.y - min_pt.y) * 10.0
        z_mm = abs(max_pt.z - min_pt.z) * 10.0
        dims_sorted = sorted([x_mm, y_mm, z_mm], reverse=True)
        axis_lengths = [x_mm, y_mm, z_mm]
        thickness_mm = min(axis_lengths)
        thickness_axis = axis_lengths.index(thickness_mm)
        body_attrs = cls._read_body_attrs(body)
        face_roles = cls._read_face_roles(body)

        return cls(
            owner=owner,
            name=body.name,
            token=body.entityToken,
            length_mm=dims_sorted[0],
            width_mm=dims_sorted[1],
            height_mm=dims_sorted[2],
            thickness_mm=thickness_mm,
            thickness_axis=thickness_axis,
            bbox_min_mm=(min_pt.x * 10.0, min_pt.y * 10.0, min_pt.z * 10.0),
            bbox_max_mm=(max_pt.x * 10.0, max_pt.y * 10.0, max_pt.z * 10.0),
            material=body_attrs.get("material", "null"),
            body_attrs=body_attrs,
            face_roles=face_roles,
            source_body=body,
        )

    @staticmethod
    def _read_body_attrs(body):
        out = {}
        attrs = body.attributes
        for i in range(attrs.count):
            attr = attrs.item(i)
            if attr and attr.groupName == ATTRIBUTE_GROUP:
                out[attr.name] = attr.value
        return out

    @staticmethod
    def _read_face_roles(body):
        out = {}
        for i in range(body.faces.count):
            face = body.faces.item(i)
            token = face.entityToken
            role_attr = face.attributes.itemByName(ATTRIBUTE_GROUP, "role")
            if role_attr and role_attr.value:
                out[token] = role_attr.value
        return out


@dataclass
class BodyInfo:
    owner: str
    name: str
    length_mm: float
    width_mm: float
    height_mm: float
