"""Load and reconcile generator-declared relationships."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from generator_declared_relationships import build_reconcile_report, reconcile_declarations_with_geometry
from overhead_declared_relationships import (
    GENERATOR_NAME,
    detect_overhead_generator,
    resolve_declarations_for_panels,
)
from relationship_models import PanelSnapshot
from relationship_service import dedupe_panel_snapshots, scan_relationships


def panel_ids_from_snapshots(panels: List[PanelSnapshot]) -> Set[str]:
    return {panel.panelId for panel in panels if panel.panelId}


def load_declarations_for_panels(
    panels: List[PanelSnapshot],
    *,
    generator: Optional[str] = None,
    preferred_run_token: Optional[str] = None,
    embedded_declarations: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    panel_ids = panel_ids_from_snapshots(panels)
    if not panel_ids:
        return []
    if generator:
        return resolve_declarations_for_panels(
            panel_ids,
            generator,
            preferred_run_token=preferred_run_token,
            embedded_declarations=embedded_declarations,
        )
    if detect_overhead_generator(panel_ids):
        return resolve_declarations_for_panels(
            panel_ids,
            GENERATOR_NAME,
            preferred_run_token=preferred_run_token,
            embedded_declarations=embedded_declarations,
        )
    return []


def _scope_panels_to_run(
    panels: List[PanelSnapshot],
    preferred_run_token: Optional[str],
) -> List[PanelSnapshot]:
    token = str(preferred_run_token or "").strip()
    if not token:
        return dedupe_panel_snapshots(panels)
    prefix = "ohc.{}.".format(token)
    scoped = [panel for panel in panels if str(panel.panelId or "").startswith(prefix)]
    if not scoped:
        scoped = [panel for panel in panels if token in panel.panelId]
    if scoped:
        return dedupe_panel_snapshots(scoped)
    return dedupe_panel_snapshots(panels)


def reconcile_generator_declarations(
    panels: List[PanelSnapshot],
    *,
    generator: Optional[str] = None,
    tolerance_mm: float = 0.5,
    include_none: bool = False,
    preferred_run_token: Optional[str] = None,
    embedded_declarations: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    panels = _scope_panels_to_run(panels, preferred_run_token)
    declarations = load_declarations_for_panels(
        panels,
        generator=generator,
        preferred_run_token=preferred_run_token,
        embedded_declarations=embedded_declarations,
    )
    if not declarations:
        return build_reconcile_report(
            generator=generator or "unknown",
            panels=panels,
            reconcile_result={
                "ok": False,
                "declarationCount": 0,
                "geometryOkCount": 0,
                "reconciled": [],
                "relationships": [],
                "errors": ["No generator declarations matched the current panel set."],
                "warnings": [],
            },
            geometry_relationships=[],
        )

    _, geometry_relationships = scan_relationships(
        panels,
        tolerance_mm=tolerance_mm,
        include_none=include_none,
    )
    resolved_generator = str(declarations[0].get("generator") or generator or GENERATOR_NAME)
    reconcile_result = reconcile_declarations_with_geometry(declarations, geometry_relationships)
    return build_reconcile_report(
        generator=resolved_generator,
        panels=panels,
        reconcile_result=reconcile_result,
        geometry_relationships=geometry_relationships,
    )
