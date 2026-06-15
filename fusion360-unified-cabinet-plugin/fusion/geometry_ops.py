import adsk.core


ATTRIBUTE_GROUP = "UnifiedCabinetPlugin"
MODEL_Z_OFFSET_MM = 10000.0


def mm_to_cm(value_mm):
    return float(value_mm) / 10.0


def sanitize_token(value, fallback="item", limit=80):
    out = []
    for ch in str(value or fallback):
        if ch.isalnum() or ch in ("_", "-"):
            out.append(ch)
        else:
            out.append("_")
    return ("".join(out) or fallback)[:limit]


def move_body_by_mm(root_comp, body, dx_mm, dy_mm, dz_mm, feature_prefix="UCP_MOVE_"):
    if abs(dx_mm) < 0.001 and abs(dy_mm) < 0.001 and abs(dz_mm) < 0.001:
        return None
    bodies = adsk.core.ObjectCollection.create()
    bodies.add(body)
    transform = adsk.core.Matrix3D.create()
    transform.translation = adsk.core.Vector3D.create(mm_to_cm(dx_mm), mm_to_cm(dy_mm), mm_to_cm(dz_mm))
    move_input = root_comp.features.moveFeatures.createInput(bodies, transform)
    try:
        move_input.defineAsFreeMove(transform)
    except Exception:
        pass
    move_feature = root_comp.features.moveFeatures.add(move_input)
    move_feature.name = "{}{}".format(feature_prefix, sanitize_token(getattr(body, "name", "body"), limit=40))
    return move_feature


def body_min_mm(body):
    point = body.boundingBox.minPoint
    return point.x * 10.0, point.y * 10.0, point.z * 10.0


def move_body_min_corner_to(root_comp, body, target_x_mm, target_y_mm, target_z_mm, feature_prefix="UCP_MOVE_"):
    min_x, min_y, min_z = body_min_mm(body)
    return move_body_by_mm(
        root_comp,
        body,
        target_x_mm - min_x,
        target_y_mm - min_y,
        target_z_mm - min_z,
        feature_prefix=feature_prefix,
    )


def body_matches_module(body, name_prefixes=None, module=None, preview_mode=None):
    name = str(getattr(body, "name", "") or "")
    if name_prefixes:
        for prefix in name_prefixes:
            if name.startswith(str(prefix)):
                return True
    try:
        attrs = body.attributes
        if module is not None:
            attr = attrs.itemByName(ATTRIBUTE_GROUP, "module")
            if attr and str(attr.value) == str(module):
                if preview_mode is None:
                    return True
                mode_attr = attrs.itemByName(ATTRIBUTE_GROUP, "previewMode")
                return bool(mode_attr and str(mode_attr.value) == str(preview_mode))
    except Exception:
        pass
    return False


def offset_bodies_z_mm(root_comp, bodies, dz_mm=MODEL_Z_OFFSET_MM, feature_prefix="UCP_MODEL_Z_OFFSET_"):
    moved = 0
    failed = 0
    if not root_comp or not bodies or abs(dz_mm) < 0.001:
        return {"offsetMm": dz_mm, "movedBodies": 0, "failedBodies": 0}
    collection = adsk.core.ObjectCollection.create()
    for body in bodies:
        try:
            collection.add(body)
        except Exception:
            failed += 1
    if collection.count < 1:
        return {"offsetMm": dz_mm, "movedBodies": 0, "failedBodies": failed}
    transform = adsk.core.Matrix3D.create()
    transform.translation = adsk.core.Vector3D.create(0, 0, mm_to_cm(dz_mm))
    try:
        move_input = root_comp.features.moveFeatures.createInput(collection, transform)
        try:
            move_input.defineAsFreeMove(transform)
        except Exception:
            pass
        move_feature = root_comp.features.moveFeatures.add(move_input)
        move_feature.name = "{}{}mm".format(feature_prefix, int(dz_mm))
        moved = collection.count
    except Exception:
        failed += collection.count
    return {"offsetMm": dz_mm, "movedBodies": moved, "failedBodies": failed}


def offset_matching_bodies_z_mm(
    root_comp,
    name_prefixes=None,
    module=None,
    preview_mode=None,
    dz_mm=MODEL_Z_OFFSET_MM,
    feature_prefix="UCP_MODEL_Z_OFFSET_",
):
    bodies = []
    try:
        count = root_comp.bRepBodies.count
    except Exception:
        count = 0
    for idx in range(count):
        try:
            body = root_comp.bRepBodies.item(idx)
            if body_matches_module(body, name_prefixes=name_prefixes, module=module, preview_mode=preview_mode):
                bodies.append(body)
        except Exception:
            pass
    result = offset_bodies_z_mm(root_comp, bodies, dz_mm=dz_mm, feature_prefix=feature_prefix)
    result["matchedBodies"] = len(bodies)
    return result
