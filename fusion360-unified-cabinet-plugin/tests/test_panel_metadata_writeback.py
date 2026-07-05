import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HW_DIR = ROOT / "modules" / "hardware"
PANEL_ATTR_DIR = ROOT / "panel_attributes"
REL_DIR = ROOT / "modules" / "relationships"
for path in (ROOT, HW_DIR, PANEL_ATTR_DIR, REL_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from connect_demo_pack import find_first_screw_eligible  # noqa: E402
from hardware_rule_engine import (  # noqa: E402
    HARDWARE_TYPE_DRAWER_RUNNER_HOLE,
    HARDWARE_TYPE_SCREW_HOLE,
    HARDWARE_TYPE_TONGUE_GROOVE,
    dispatch_hardware_cut_plan,
    dispatch_hardware_preview,
    evaluate_hardware_rule,
    list_hardware_types,
)
from panel_metadata_writeback import (  # noqa: E402
    OPERATION_TYPE,
    append_hardware_feature,
    build_panel_feature_record,
    find_hardware_features,
)
from relationship_fixtures import build_fixture_snapshots, expected_fixture_cases  # noqa: E402
from relationship_report import build_scan_report  # noqa: E402
from relationship_service import scan_relationships  # noqa: E402
from screw_hole_from_relationship import build_cut_feature_metadata  # noqa: E402


def _fixture_scan():
    panels = build_fixture_snapshots()
    _, relationships = scan_relationships(panels, tolerance_mm=0.5, include_none=True)
    return build_scan_report(
        action="relationships.scan",
        panels=panels,
        relationships=relationships,
        scope="fixture",
        tolerance_mm=0.5,
        expected_fixtures=expected_fixture_cases(),
    )


class PanelMetadataWritebackTests(unittest.TestCase):
    def test_build_panel_feature_record_from_screw_hole_intent(self):
        feature = {
            "featureId": "rel.test::screw_hole",
            "geometry": {
                "axis": "Y",
                "diameterMm": 4,
                "depthMm": 15,
                "positions": [{"x": 10, "y": 0, "z": 20}, {"x": 90, "y": 0, "z": 20}],
            },
            "sourceRelationshipId": "rel.test",
            "hostPanelId": "HOST",
            "targetPanelId": "TARGET",
            "source": {"ruleId": "screw_hole_from_edge_to_surface_v1"},
        }
        cut_meta = build_cut_feature_metadata(
            feature,
            relationship_id="rel.test",
            host_panel_id="HOST",
            target_panel_id="TARGET",
        )
        record = build_panel_feature_record(feature, cut_metadata=cut_meta, cut_feature_name="HW_REL_SCREW_HOLE_1")
        self.assertEqual(record["kind"], "hole")
        self.assertEqual(record["operationType"], OPERATION_TYPE)
        self.assertEqual(record["sourceRelationshipId"], "rel.test")
        self.assertEqual(record["holeCount"], 2)
        self.assertEqual(record["center2d"], [10.0, 20.0])

    def test_append_hardware_feature_deduplicates(self):
        base = {"schemaVersion": 1, "features": []}
        record = {
            "featureId": "rel.test::screw_hole",
            "operationType": OPERATION_TYPE,
            "sourceRelationshipId": "rel.test",
        }
        updated, appended, _ = append_hardware_feature(base, record)
        self.assertTrue(appended)
        updated2, appended2, reason = append_hardware_feature(updated, record)
        self.assertFalse(appended2)
        self.assertEqual(reason, "duplicate_feature")
        self.assertEqual(len(updated2["features"]), 1)

    def test_find_hardware_features_by_relationship(self):
        metadata = {
            "features": [
                {"featureId": "a", "sourceRelationshipId": "rel.one", "operationType": OPERATION_TYPE},
                {"featureId": "b", "sourceRelationshipId": "rel.two", "operationType": OPERATION_TYPE},
            ]
        }
        found = find_hardware_features(metadata, source_relationship_id="rel.one")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["featureId"], "a")


class HardwareRuleEngineTests(unittest.TestCase):
    def test_list_hardware_types_includes_scaffold_types(self):
        rows = list_hardware_types()
        types = {row["type"] for row in rows}
        self.assertIn(HARDWARE_TYPE_SCREW_HOLE, types)
        self.assertIn(HARDWARE_TYPE_TONGUE_GROOVE, types)
        self.assertIn(HARDWARE_TYPE_DRAWER_RUNNER_HOLE, types)
        screw = next(row for row in rows if row["type"] == HARDWARE_TYPE_SCREW_HOLE)
        tongue = next(row for row in rows if row["type"] == HARDWARE_TYPE_TONGUE_GROOVE)
        self.assertTrue(screw["implemented"])
        self.assertTrue(tongue["previewOnly"])

    def test_screw_hole_preview_dispatch_fixture(self):
        scan = _fixture_scan()
        rel = find_first_screw_eligible(scan.get("relationships") or [])
        panel_map = {panel.panelId: panel.to_dict() for panel in build_fixture_snapshots()}
        host_id = rel["roles"]["hostPanelId"]
        target_id = rel["roles"]["targetPanelId"]
        report = dispatch_hardware_preview(
            rel,
            rule={"type": HARDWARE_TYPE_SCREW_HOLE},
            panel_snapshots={host_id: panel_map[host_id], target_id: panel_map[target_id]},
        )
        self.assertEqual(report.get("hardwareType"), HARDWARE_TYPE_SCREW_HOLE)
        self.assertTrue(report.get("ok"))
        self.assertGreaterEqual(int(report.get("holeCount") or 0), 1)

    def test_tongue_groove_cut_blocked_scaffold(self):
        scan = _fixture_scan()
        rel = find_first_screw_eligible(scan.get("relationships") or [])
        gate = evaluate_hardware_rule(HARDWARE_TYPE_TONGUE_GROOVE, rel, action="cut")
        self.assertFalse(gate.get("ok"))
        self.assertTrue(gate.get("previewOnly"))

    def test_screw_hole_cut_plan_requires_verification(self):
        scan = _fixture_scan()
        rel = find_first_screw_eligible(scan.get("relationships") or [])
        blocked = dispatch_hardware_cut_plan(rel, rule={"type": HARDWARE_TYPE_SCREW_HOLE})
        self.assertFalse(blocked.get("ok"))


if __name__ == "__main__":
    unittest.main()
