import importlib

import adsk.core
import adsk.fusion

import panel_body_resolver

panel_body_resolver = importlib.reload(panel_body_resolver)

import metadata_inspector
import tag_metadata_editor
import work_zones
from panel_search_service import collect_all_tags, collect_defined_panels, resolve_panel_targets, search_panels


metadata_inspector = importlib.reload(metadata_inspector)
tag_metadata_editor = importlib.reload(tag_metadata_editor)
work_zones = importlib.reload(work_zones)

body_matches_record = panel_body_resolver.body_matches_record
find_body_in_design = panel_body_resolver.find_body_in_design
list_solid_bodies = panel_body_resolver.list_solid_bodies
resolve_main_body = panel_body_resolver.resolve_main_body


class PanelAttributesController:
    def __init__(self, fusion_adapter):
        self.fusion = fusion_adapter

    def _selected_entities(self):
        getter = getattr(self.fusion, "get_selected_entities", None)
        if callable(getter):
            return getter()

        selection = self._active_selection_collection()
        if selection is None:
            return []

        entities = []
        try:
            count = selection.count
        except Exception:
            count = 0
        for index in range(count):
            try:
                item = selection.item(index)
                entity = getattr(item, "entity", item)
                if entity:
                    entities.append(entity)
            except Exception:
                continue
        return entities

    def _active_selection_collection(self):
        app = adsk.core.Application.get()
        ui = app.userInterface if app else None
        for owner, attr_name in ((ui, "activeSelections"), (ui, "activeSelection"), (app, "activeSelections")):
            if not owner:
                continue
            try:
                selection = getattr(owner, attr_name)
            except Exception:
                selection = None
            if selection is not None:
                return selection
        return None

    def _select_bodies_and_fit(self, bodies):
        valid_bodies = [body for body in (bodies or []) if body]
        if not valid_bodies:
            return 0

        selection = self._active_selection_collection()
        if selection is None:
            selector = getattr(self.fusion, "select_bodies_and_fit", None)
            if callable(selector):
                return selector(valid_bodies)
            return 0

        try:
            selection.clear()
            for body in valid_bodies:
                selection.add(body)
        except Exception:
            selector = getattr(self.fusion, "select_bodies_and_fit", None)
            if callable(selector):
                return selector(valid_bodies)
            return 0

        try:
            app = adsk.core.Application.get()
            viewport = app.activeViewport if app else None
            if viewport:
                viewport.fit()
                viewport.refresh()
        except Exception:
            refresh = getattr(self.fusion, "refresh_viewport", None)
            if callable(refresh):
                refresh()
        return len(valid_bodies)

    def _component_by_path(self, root, occurrence_path):
        component = root
        for index in occurrence_path or []:
            try:
                if not component.occurrences or index >= component.occurrences.count:
                    return None
                component = component.occurrences.item(index).component
            except Exception:
                return None
        return component

    def _entity_from_token(self, entity_token):
        if not entity_token:
            return None
        design = self.fusion.get_active_design()
        if not design:
            return None
        try:
            entity = design.findEntityByToken(str(entity_token))
        except Exception:
            return None
        if isinstance(entity, list):
            entity = entity[0] if entity else None
        return entity

    def _body_from_token(self, entity_token):
        entity = self._entity_from_token(entity_token)
        if not entity:
            return None
        object_type = str(getattr(entity, "objectType", "") or "")
        if "BRepBody" in object_type:
            return entity
        for attr_name in ("body", "parentBody"):
            try:
                body = getattr(entity, attr_name)
            except Exception:
                body = None
            if body:
                return body
        return None

    def _resolve_tag_scan_entity(self, entity_token, kind, result, selected_bodies=None):
        body_record = result.get("body") or {}
        selection = result.get("selection") or {}
        root = self.fusion.get_root_component()

        if kind == "body":
            for token in (
                entity_token,
                body_record.get("entityToken"),
                selection.get("selectionEntityToken"),
            ):
                body = self._body_from_token(token)
                if body:
                    return body

            if root:
                body = find_body_in_design(root, body_record)
                if body:
                    return body
                body, _warnings = self._body_from_metadata_record(root, body_record)
                if body:
                    return body

            for candidate in selected_bodies or []:
                if body_matches_record(candidate, body_record):
                    return candidate
            return None

        entity = self._entity_from_token(entity_token)
        if entity:
            object_type = str(getattr(entity, "objectType", "") or "")
            if "BRepFace" in object_type or "BRepEdge" in object_type:
                return entity

        selection_token = selection.get("selectionEntityToken")
        entity = self._entity_from_token(selection_token)
        if entity:
            object_type = str(getattr(entity, "objectType", "") or "")
            if "BRepFace" in object_type or "BRepEdge" in object_type:
                return entity
        return None

    def _selected_bodies(self):
        bodies = []
        seen = set()
        for entity in self._selected_entities():
            body, source_kind = metadata_inspector._selection_owner_body(entity)
            if not body:
                continue
            key = metadata_inspector._body_key(body)
            if key in seen:
                continue
            seen.add(key)
            bodies.append(body)
        return bodies

    def _body_by_name(self, component, body_name):
        target_name = str(body_name or "").strip()
        if not component or not target_name:
            return None
        for body in list_solid_bodies(component):
            if str(getattr(body, "name", "") or "") == target_name:
                return body
        return None

    def _body_from_metadata_record(self, root, record):
        body = self._body_from_token(record.get("entityToken"))
        if body:
            return body, []

        warnings = []
        component = self._component_by_path(root, record.get("occurrencePath") or [])
        if component:
            body = self._body_by_name(component, record.get("bodyName"))
            if body:
                return body, warnings
            body, warning = resolve_main_body(component)
            if warning:
                warnings.append(warning)
            return body, warnings
        return None, warnings

    def search_panels(self, payload, _palette):
        root = self.fusion.get_root_component()
        if not root:
            return "panelAttributesResult", {
                "ok": False,
                "action": "searchPanels",
                "errors": ["No active Fusion design."],
            }

        query = str((payload or {}).get("query") or "").strip()
        panels = search_panels(root, query)
        serializable = []
        for panel in panels:
            item = dict(panel)
            item.pop("entityToken", None)
            serializable.append(item)

        return "panelAttributesResult", {
            "ok": True,
            "action": "searchPanels",
            "query": query,
            "panels": serializable,
            "tags": collect_all_tags(root),
            "count": len(serializable),
        }

    def select_by_tag(self, payload, palette):
        root = self.fusion.get_root_component()
        if not root:
            return "panelAttributesResult", {
                "ok": False,
                "action": "selectByTag",
                "errors": ["No active Fusion design."],
            }

        query = str((payload or {}).get("query") or "").strip()
        if not query:
            return "panelAttributesResult", {
                "ok": False,
                "action": "selectByTag",
                "errors": ["Enter at least one tag or keyword."],
            }

        panels = search_panels(root, query)
        if not panels:
            return "panelAttributesResult", {
                "ok": True,
                "action": "selectByTag",
                "query": query,
                "selectedCount": 0,
                "panels": [],
                "warnings": ["No matching panels found."],
            }

        targets, warnings = resolve_panel_targets(root, panels)
        bodies = [target["body"] for target in targets if target.get("body")]
        selected_count = self.fusion.select_bodies_and_fit(bodies)

        serializable = []
        for panel in panels:
            item = dict(panel)
            item.pop("entityToken", None)
            serializable.append(item)

        if palette:
            palette.send(
                "panelAttributesSelectionChanged",
                {
                    "query": query,
                    "selectedCount": selected_count,
                    "panels": serializable,
                },
            )

        return "panelAttributesResult", {
            "ok": True,
            "action": "selectByTag",
            "query": query,
            "selectedCount": selected_count,
            "panels": serializable,
            "warnings": warnings,
        }

    def select_panel(self, payload, _palette):
        root = self.fusion.get_root_component()
        if not root:
            return "panelAttributesResult", {
                "ok": False,
                "action": "selectPanel",
                "errors": ["No active Fusion design."],
            }

        occurrence_path = (payload or {}).get("occurrencePath") or []
        panels = collect_defined_panels(root)
        panel = None
        for candidate in panels:
            if list(candidate.get("occurrencePath") or []) == list(occurrence_path):
                panel = candidate
                break
        if not panel:
            return "panelAttributesResult", {
                "ok": False,
                "action": "selectPanel",
                "errors": ["Panel not found in current search results."],
            }

        targets, warnings = resolve_panel_targets(root, [panel])
        bodies = [target["body"] for target in targets if target.get("body")]
        selected_count = self.fusion.select_bodies_and_fit(bodies)
        item = dict(panel)
        item.pop("entityToken", None)

        return "panelAttributesResult", {
            "ok": True,
            "action": "selectPanel",
            "selectedCount": selected_count,
            "panel": item,
            "warnings": warnings,
        }

    def select_metadata_record(self, payload, _palette):
        root = self.fusion.get_root_component()
        if not root:
            return "panelAttributesResult", {
                "ok": False,
                "action": "selectMetadataRecord",
                "errors": ["No active Fusion design."],
            }

        body, warnings = self._body_from_metadata_record(root, payload or {})
        if not body:
            return "panelAttributesResult", {
                "ok": False,
                "action": "selectMetadataRecord",
                "errors": ["Could not resolve scanned metadata record to a Fusion body."],
            }

        selected_count = self._select_bodies_and_fit([body])
        return "panelAttributesResult", {
            "ok": True,
            "action": "selectMetadataRecord",
            "selectedCount": selected_count,
            "panel": {
                "panelId": (payload or {}).get("panelId"),
                "bodyName": str(getattr(body, "name", "") or ""),
                "componentName": (payload or {}).get("componentName") or "",
            },
            "warnings": warnings,
        }

    def select_metadata_records(self, payload, _palette):
        root = self.fusion.get_root_component()
        if not root:
            return "panelAttributesResult", {
                "ok": False,
                "action": "selectMetadataRecords",
                "errors": ["No active Fusion design."],
            }

        records = (payload or {}).get("records") or []
        bodies = []
        warnings = []
        seen = set()
        for record in records:
            body, record_warnings = self._body_from_metadata_record(root, record)
            for warning in record_warnings:
                warnings.append("{}: {}".format(record.get("panelId") or record.get("bodyName") or "metadata record", warning))
            if not body:
                warnings.append("Could not resolve {}".format(record.get("panelId") or "metadata record"))
                continue
            key = str(getattr(body, "entityToken", "") or id(body))
            if key in seen:
                continue
            seen.add(key)
            bodies.append(body)

        selected_count = self._select_bodies_and_fit(bodies)
        return "panelAttributesResult", {
            "ok": True,
            "action": "selectMetadataRecords",
            "selectedCount": selected_count,
            "query": (payload or {}).get("query") or "typed tags",
            "panels": [
                {
                    "panelId": record.get("panelId"),
                    "bodyName": record.get("bodyName"),
                    "componentName": record.get("componentName"),
                    "occurrencePath": record.get("occurrencePath") or [],
                    "entityToken": record.get("entityToken") or "",
                }
                for record in records
            ],
            "warnings": warnings[:20],
        }

    def scan_metadata(self, payload, _palette):
        root = self.fusion.get_root_component()
        if not root:
            return "panelAttributesResult", {
                "ok": False,
                "action": "scanMetadata",
                "errors": ["No active Fusion design."],
            }

        zone_filter = str((payload or {}).get("zoneFilter") or "").strip().lower() or None
        records, counts = metadata_inspector.scan_panel_metadata(root, zone_filter=zone_filter)
        return "panelAttributesResult", {
            "ok": True,
            "action": "scanMetadata",
            "records": records,
            "counts": counts,
            "count": len(records),
            "zoneFilter": zone_filter or "all",
        }

    def scan_selected_metadata(self, _payload, _palette):
        root = self.fusion.get_root_component()
        if not root:
            return "panelAttributesResult", {
                "ok": False,
                "action": "scanSelectedMetadata",
                "errors": ["No active Fusion design."],
            }

        selected_entities = self._selected_entities()
        if not selected_entities:
            return "panelAttributesResult", {
                "ok": True,
                "action": "scanSelectedMetadata",
                "records": [],
                "counts": {"Valid": 0, "Warning": 0, "Invalid": 0, "Missing": 0},
                "count": 0,
                "warnings": ["No bodies or faces selected."],
            }

        records, counts, skipped = metadata_inspector.scan_selected_panel_metadata(selected_entities)
        warnings = skipped[:20]
        if not records and not warnings:
            warnings.append("No supported body or face selections found.")
        return "panelAttributesResult", {
            "ok": True,
            "action": "scanSelectedMetadata",
            "records": records,
            "counts": counts,
            "count": len(records),
            "warnings": warnings,
        }

    ZONE_OPACITY = 0.5
    ZONE_SPECS = {
        "assembly": {"bodyName": "AssemblyZone", "label": "Assembly Zone", "rgb": (45, 110, 225)},
        "generation": {"bodyName": "GenerationZone", "label": "Generation Zone", "rgb": (60, 170, 90)},
        "nesting": {"bodyName": "NestingZone", "label": "Nesting Zone", "rgb": (235, 150, 50)},
    }
    ZONE_SKETCH_NAMES = (
        "AssemblyZoneSketch", "AssemblyZoneTextSketch",  # legacy single-zone names
        "WorkZoneSketch_assembly", "WorkZoneSketch_generation", "WorkZoneSketch_nesting",
        "WorkZoneText_assembly", "WorkZoneText_generation", "WorkZoneText_nesting",
    )

    def get_work_zones(self, _payload, _palette):
        """Return the work-zone layout saved in the active design (if any)."""
        root = self.fusion.get_root_component()
        if not root:
            return "panelAttributesResult", {
                "ok": False,
                "action": "getWorkZones",
                "errors": ["No active Fusion design."],
            }
        layout = work_zones.load_zone_layout(root)
        return "panelAttributesResult", {
            "ok": True,
            "action": "getWorkZones",
            "found": bool(layout),
            "layout": layout,
        }

    def set_work_zones(self, payload, _palette):
        app = adsk.core.Application.get()
        design = app.activeProduct if app else None
        root = self.fusion.get_root_component()
        if not root or design is None:
            return "panelAttributesResult", {
                "ok": False,
                "action": "setWorkZones",
                "errors": ["No active Fusion design."],
            }

        data = payload or {}
        width_mm = max(float(data.get("widthMm") or 10000.0), 1.0)
        depth_mm = max(float(data.get("depthMm") or 10000.0), 1.0)

        def _optional_mm(key):
            try:
                value = float(data.get(key) or 0.0)
                return value if value > 0 else None
            except Exception:
                return None

        generation_w = _optional_mm("generationWidthMm")
        generation_d = _optional_mm("generationDepthMm")
        nesting_w = _optional_mm("nestingWidthMm")
        nesting_d = _optional_mm("nestingDepthMm")

        # Without explicit nesting sizes, preserve a previously grown nesting
        # zone; everything is repositioned around the new assembly size.
        if nesting_w is None and nesting_d is None:
            previous = work_zones.load_zone_layout(root) or {}
            nesting_w, nesting_d = work_zones.rect_size(previous.get(work_zones.ZONE_NESTING))

        layout = work_zones.compute_zone_layout(
            width_mm, depth_mm, nesting_w, nesting_d,
            generation_width_mm=generation_w, generation_depth_mm=generation_d,
        )
        if work_zones.zones_overlap(layout):
            return "panelAttributesResult", {
                "ok": False,
                "action": "setWorkZones",
                "errors": ["Zone layout would overlap; adjust sizes."],
            }

        self._remove_existing_work_zones(root)

        colour_notes = []
        try:
            for zone_id in (work_zones.ZONE_ASSEMBLY, work_zones.ZONE_GENERATION, work_zones.ZONE_NESTING):
                rect = layout[zone_id]
                spec = self.ZONE_SPECS[zone_id]
                body = self._create_zone_plane(root, zone_id, rect)
                if body is None:
                    colour_notes.append("{}: create failed".format(zone_id))
                    continue
                body.name = spec["bodyName"]
                self._mark_zone_body(body, zone_id)
                status = self._apply_zone_appearance(app, design, body, zone_id, spec["rgb"])
                colour_notes.append("{}: {}".format(zone_id, status))
                try:
                    body.opacity = self.ZONE_OPACITY
                except Exception:
                    pass
                self._add_zone_labels(root, zone_id, spec["label"], rect)

            work_zones.save_zone_layout(root, layout)
            try:
                viewport = app.activeViewport
                if viewport:
                    viewport.fit()
                    viewport.refresh()
            except Exception:
                pass
        except Exception as ex:
            return "panelAttributesResult", {
                "ok": False,
                "action": "setWorkZones",
                "errors": ["Could not create work zones: {}".format(ex)],
            }

        return "panelAttributesResult", {
            "ok": True,
            "action": "setWorkZones",
            "widthMm": round(width_mm, 1),
            "depthMm": round(depth_mm, 1),
            "layout": layout,
            "message": "Work zones set (assembly {:.0f}×{:.0f} mm; generation +X; nesting +Y; gap {:.0f} mm).".format(
                width_mm, depth_mm, layout.get("gapMm", 0.0)
            ),
        }

    def _create_zone_plane(self, root, zone_id, rect):
        try:
            sketch = root.sketches.add(root.xYConstructionPlane)
            sketch.name = "WorkZoneSketch_{}".format(zone_id)
            point = adsk.core.Point3D
            sketch.sketchCurves.sketchLines.addTwoPointRectangle(
                point.create(rect["x0"] / 10.0, rect["y0"] / 10.0, 0.0),
                point.create(rect["x1"] / 10.0, rect["y1"] / 10.0, 0.0),
            )
            profile = sketch.profiles.item(0)
            # Zero-thickness surface patch (a plane region, not a slab).
            patches = root.features.patchFeatures
            patch_input = patches.createInput(
                profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation
            )
            patch = patches.add(patch_input)
            return patch.bodies.item(0)
        except Exception:
            return None

    def _mark_zone_body(self, body, zone_id):
        try:
            body.attributes.add(
                work_zones.WORK_ZONE_MARKER_GROUP,
                work_zones.WORK_ZONE_MARKER_NAME,
                work_zones.WORK_ZONE_MARKER_VALUE,
            )
            body.attributes.add(work_zones.WORK_ZONE_MARKER_GROUP, "zoneId", str(zone_id))
        except Exception:
            pass

    def _add_zone_labels(self, root, zone_id, label, rect):
        try:
            text_plane = self._work_zone_text_plane(root)
            if text_plane is None:
                return
            sketch = root.sketches.add(text_plane)
            sketch.name = "WorkZoneText_{}".format(zone_id)
            texts = sketch.sketchTexts
            w_cm = (rect["x1"] - rect["x0"]) / 10.0
            d_cm = (rect["y1"] - rect["y0"]) / 10.0
            cx = (rect["x0"] + rect["x1"]) / 2.0 / 10.0
            height_cm = max(min(w_cm, d_cm) * 0.05, 0.5)
            box_half_w = w_cm * 0.4
            margin = height_cm * 1.5
            for y_center in (rect["y0"] / 10.0 + margin, rect["y1"] / 10.0 - margin):
                self._add_zone_text_box(texts, label, height_cm, box_half_w, y_center, cx)
        except Exception:
            pass

    def _work_zone_text_plane(self, root):
        try:
            planes = root.constructionPlanes
            for index in range(planes.count):
                plane = planes.item(index)
                if plane and plane.name == "WorkZoneTextPlane":
                    return plane
            plane_input = planes.createInput()
            # Sit the text 0.1 mm above the surfaces so it is not z-fighting.
            plane_input.setByOffset(root.xYConstructionPlane, adsk.core.ValueInput.createByReal(0.01))
            plane = planes.add(plane_input)
            plane.name = "WorkZoneTextPlane"
            return plane
        except Exception:
            return None

    def _add_zone_text_box(self, texts, content, height_cm, box_half_w, y_center, cx=0.0):
        point = adsk.core.Point3D
        corner = point.create(cx - box_half_w, y_center - height_cm / 2.0, 0.0)
        diagonal = point.create(cx + box_half_w, y_center + height_cm / 2.0, 0.0)
        try:
            text_input = texts.createInput2(content, height_cm)
            text_input.setAsMultiLine(
                corner,
                diagonal,
                adsk.core.HorizontalAlignments.CenterHorizontalAlignment,
                adsk.core.VerticalAlignments.MiddleVerticalAlignment,
                0,
            )
            texts.add(text_input)
        except Exception:
            try:
                text_input = texts.createInput(content, height_cm)
                try:
                    text_input.position = point.create(cx - box_half_w * 0.5, y_center, 0.0)
                except Exception:
                    pass
                texts.add(text_input)
            except Exception:
                pass

    def _remove_existing_work_zones(self, root):
        zone_body_names = {spec["bodyName"] for spec in self.ZONE_SPECS.values()}
        try:
            bodies = root.bRepBodies
            for index in range(bodies.count - 1, -1, -1):
                body = bodies.item(index)
                if body and body.name in zone_body_names:
                    body.deleteMe()
        except Exception:
            pass
        try:
            sketches = root.sketches
            for index in range(sketches.count - 1, -1, -1):
                sketch = sketches.item(index)
                if sketch and sketch.name in self.ZONE_SKETCH_NAMES:
                    sketch.deleteMe()
        except Exception:
            pass
        try:
            planes = root.constructionPlanes
            for index in range(planes.count - 1, -1, -1):
                plane = planes.item(index)
                if plane and plane.name in ("AssemblyZoneTextPlane", "WorkZoneTextPlane"):
                    plane.deleteMe()
        except Exception:
            pass

    def _find_appearance_library(self, app):
        try:
            libraries = app.materialLibraries
        except Exception:
            return None
        try:
            lib = libraries.itemByName("Fusion 360 Appearance Library")
            if lib is not None and getattr(lib, "appearances", None) and lib.appearances.count:
                return lib
        except Exception:
            pass
        try:
            for index in range(libraries.count):
                library = libraries.item(index)
                lib_appearances = getattr(library, "appearances", None)
                if lib_appearances and lib_appearances.count:
                    return library
        except Exception:
            pass
        return None

    def _pick_base_appearance(self, library):
        appearances = library.appearances
        preferred = [
            "Paint - Enamel Glossy (Blue)",
            "Plastic - Matte (Blue)",
            "Plastic - Glossy (Blue)",
            "Paint - Enamel Glossy (Generic)",
            "Plastic - Matte (Generic)",
            "Powder Coat (Blue)",
        ]
        for name in preferred:
            try:
                appearance = appearances.itemByName(name)
                if appearance is not None:
                    return appearance
            except Exception:
                continue
        # Fall back to the first appearance that exposes a colour property.
        try:
            for index in range(appearances.count):
                candidate = appearances.item(index)
                if self._appearance_has_color(candidate):
                    return candidate
        except Exception:
            pass
        try:
            return appearances.item(0)
        except Exception:
            return None

    def _appearance_has_color(self, appearance):
        try:
            props = appearance.appearanceProperties
            for index in range(props.count):
                if isinstance(props.item(index), adsk.core.ColorProperty):
                    return True
        except Exception:
            pass
        return False

    def _apply_zone_appearance(self, app, design, body, zone_id, rgb):
        try:
            appearances = design.appearances
            name = "UC Work Zone {}".format(zone_id)
            appearance = None
            try:
                appearance = appearances.itemByName(name)
            except Exception:
                appearance = None
            if appearance is None:
                library = self._find_appearance_library(app)
                if library is None:
                    return "no appearance library found"
                base = self._pick_base_appearance(library)
                if base is None:
                    return "no base appearance found"
                appearance = appearances.addByCopy(base, name)
            if appearance is None:
                return "could not create appearance"
            colored = self._set_appearance_color(appearance, rgb[0], rgb[1], rgb[2])
            self._set_appearance_opacity(appearance, self.ZONE_OPACITY)
            body.appearance = appearance
            return "applied '{}', colorSet={}".format(appearance.name, colored)
        except Exception as ex:
            return "failed: {}".format(ex)

    def _set_appearance_color(self, appearance, red, green, blue):
        color = adsk.core.Color.create(red, green, blue, 0)
        properties = None
        try:
            properties = appearance.appearanceProperties
        except Exception:
            return False
        set_any = False
        for prop_id in ("opaque_albedo", "surface_albedo", "generic_diffuse", "metal_f0"):
            try:
                prop = properties.itemById(prop_id)
            except Exception:
                prop = None
            if isinstance(prop, adsk.core.ColorProperty):
                try:
                    prop.value = color
                    set_any = True
                except Exception:
                    pass
        if not set_any:
            try:
                for index in range(properties.count):
                    prop = properties.item(index)
                    if isinstance(prop, adsk.core.ColorProperty):
                        try:
                            prop.value = color
                            set_any = True
                        except Exception:
                            continue
            except Exception:
                pass
        return set_any

    def _set_appearance_opacity(self, appearance, opacity):
        try:
            properties = appearance.appearanceProperties
            for index in range(properties.count):
                prop = properties.item(index)
                name = ""
                try:
                    name = "{} {}".format(getattr(prop, "id", "") or "", getattr(prop, "name", "") or "").lower()
                except Exception:
                    name = ""
                if isinstance(prop, adsk.core.FloatProperty) and ("opacity" in name or "transparen" in name):
                    try:
                        prop.value = float(opacity)
                    except Exception:
                        continue
        except Exception:
            pass

    def tag_scan_selected(self, _payload, _palette):
        root = self.fusion.get_root_component()
        if not root:
            return "panelAttributesResult", {
                "ok": False,
                "action": "tagScanSelected",
                "errors": ["No active Fusion design."],
            }

        selected_entities = self._selected_entities()
        if not selected_entities:
            return "panelAttributesResult", {
                "ok": True,
                "action": "tagScanSelected",
                "results": [],
                "warnings": ["No body, face, or edge selected."],
            }

        results, warnings = metadata_inspector.tag_scan_selected(selected_entities, root)
        return "panelAttributesResult", {
            "ok": True,
            "action": "tagScanSelected",
            "results": results,
            "count": len(results),
            "warnings": warnings[:20],
        }

    def apply_tag_scan_drafts(self, payload, _palette):
        root = self.fusion.get_root_component()
        if not root:
            return "panelAttributesResult", {
                "ok": False,
                "action": "applyTagScanDrafts",
                "errors": ["No active Fusion design."],
            }

        drafts = (payload or {}).get("drafts") or []
        results = (payload or {}).get("results") or []
        if not drafts:
            return "panelAttributesResult", {
                "ok": False,
                "action": "applyTagScanDrafts",
                "errors": ["No pending tag edits to apply."],
            }
        if not results:
            return "panelAttributesResult", {
                "ok": False,
                "action": "applyTagScanDrafts",
                "errors": ["Tag scan context is missing. Scan selected entities again, then apply."],
            }

        applied, failed = tag_metadata_editor.apply_tag_scan_drafts(
            results,
            drafts,
            lambda token, kind, result: self._resolve_tag_scan_entity(
                token,
                kind,
                result,
                selected_bodies=self._selected_bodies(),
            ),
        )

        refreshed_results = results
        refreshed_warnings = []
        selected_entities = self._selected_entities()
        if selected_entities:
            refreshed_results, refreshed_warnings = metadata_inspector.tag_scan_selected(selected_entities, root)

        return "panelAttributesResult", {
            "ok": len(applied) > 0 and len(failed) == 0,
            "action": "applyTagScanDrafts",
            "applied": applied,
            "failed": failed,
            "appliedCount": len(applied),
            "failedCount": len(failed),
            "results": refreshed_results,
            "warnings": refreshed_warnings[:20],
            "errors": [item.get("error") for item in failed if item.get("error")][:20] if failed and not applied else [],
        }
