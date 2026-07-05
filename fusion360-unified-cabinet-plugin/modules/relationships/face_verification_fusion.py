"""Fusion helpers for M5 face verification."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    import adsk.core as adsk_core
except Exception:
    adsk_core = None

from face_verification import extract_axis_aligned_faces_from_panel


def _normalize_vector(vec) -> Optional[List[float]]:
    if vec is None:
        return None
    try:
        x, y, z = float(vec.x), float(vec.y), float(vec.z)
    except Exception:
        try:
            x, y, z = float(vec[0]), float(vec[1]), float(vec[2])
        except Exception:
            return None
    mag = (x * x + y * y + z * z) ** 0.5
    if mag <= 1e-9:
        return None
    return [x / mag, y / mag, z / mag]


def _face_world_point_mm(face) -> Optional[List[float]]:
    try:
        pt = face.pointOnFace
        return [pt.x * 10.0, pt.y * 10.0, pt.z * 10.0]
    except Exception:
        return None


def _face_world_normal(face) -> Optional[List[float]]:
    try:
        evaluator = face.evaluator
        pt = face.pointOnFace
        result = evaluator.getNormalAtPoint(pt)
        normal = result[1] if isinstance(result, (tuple, list)) and len(result) == 2 else result
        return _normalize_vector(normal)
    except Exception:
        return None


def _face_area_mm2(face) -> float:
    try:
        props = face.areaProperties(adsk_core.CalculationAccuracy.MediumCalculationAccuracy)
        return float(props.area) * 100.0
    except Exception:
        return 0.0


def _classify_brep_face(normal: List[float], thickness_axis: str) -> str:
    comps = [("X", abs(normal[0])), ("Y", abs(normal[1])), ("Z", abs(normal[2]))]
    axis = max(comps, key=lambda item: item[1])[0]
    if thickness_axis in ("X", "Y", "Z") and axis == thickness_axis:
        return "SURFACE"
    return "EDGE"


def extract_brep_faces_from_body(body, panel: Dict[str, Any]) -> List[Dict[str, Any]]:
    if body is None or adsk_core is None:
        return []
    panel_id = str(panel.get("panelId") or getattr(body, "name", "") or "panel")
    thickness_axis = (panel.get("inferred") or {}).get("thicknessAxis") or "UNKNOWN"
    faces: List[Dict[str, Any]] = []
    try:
        for index in range(body.faces.count):
            face = body.faces.item(index)
            normal = _face_world_normal(face)
            origin = _face_world_point_mm(face)
            if not normal or not origin:
                continue
            face_id = "{}::BREP_{}".format(panel_id, index)
            faces.append(
                {
                    "faceId": face_id,
                    "panelId": panel_id,
                    "faceClass": _classify_brep_face(normal, thickness_axis),
                    "normal": normal,
                    "planeOriginMm": origin,
                    "boundsMm": dict(panel.get("bbox") or {}),
                    "areaMm2": round(_face_area_mm2(face), 4),
                    "source": "fusion_brep",
                }
            )
    except Exception:
        return []
    return faces


def extract_faces_for_panel(body, panel: Dict[str, Any]) -> List[Dict[str, Any]]:
    brep_faces = extract_brep_faces_from_body(body, panel)
    if brep_faces:
        return brep_faces
    return extract_axis_aligned_faces_from_panel(panel)
