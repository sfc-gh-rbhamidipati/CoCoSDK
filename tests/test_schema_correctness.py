"""
Validation tests: JSON Schema correctness for the threat assessment output.

Verifies the structured output schema in demo_structured_output.py is a valid
JSON Schema that matches the planned threat assessment format from the plan.

Tests are expected to FAIL before implementation (TDD red phase).
"""

import ast
import json
import os
import re
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(filename):
    path = os.path.join(PROJECT_ROOT, filename)
    with open(path) as f:
        return f.read()


def _extract_schema_dict(filename):
    """
    Extract the schema dictionary from the structured output demo.
    Looks for a top-level variable assignment whose name contains 'SCHEMA'.
    """
    source = _read(filename)
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and "SCHEMA" in target.id.upper():
                    # Evaluate the literal value
                    return ast.literal_eval(node.value)
    raise ValueError(f"No *SCHEMA* variable found in {filename}")


class TestThreatAssessmentSchema:
    """Validate the threat assessment JSON schema structure."""

    def test_schema_is_extractable(self):
        """A SCHEMA variable must exist and be a valid dict literal."""
        schema = _extract_schema_dict("demo_structured_output.py")
        assert isinstance(schema, dict)

    def test_schema_is_object_type(self):
        schema = _extract_schema_dict("demo_structured_output.py")
        assert schema.get("type") == "object"

    def test_schema_has_file_property(self):
        schema = _extract_schema_dict("demo_structured_output.py")
        props = schema.get("properties", {})
        assert "file" in props, "Schema must have 'file' property"
        assert props["file"].get("type") == "string"

    def test_schema_has_threats_found_array(self):
        schema = _extract_schema_dict("demo_structured_output.py")
        props = schema.get("properties", {})
        assert "threats_found" in props, "Schema must have 'threats_found' property"
        assert props["threats_found"].get("type") == "array"

    def test_threat_item_has_line(self):
        schema = _extract_schema_dict("demo_structured_output.py")
        items = schema["properties"]["threats_found"]["items"]
        item_props = items.get("properties", {})
        assert "line" in item_props, "Each threat must have a 'line' property"
        assert item_props["line"].get("type") == "integer"

    def test_threat_item_has_severity_with_critical(self):
        schema = _extract_schema_dict("demo_structured_output.py")
        items = schema["properties"]["threats_found"]["items"]
        item_props = items.get("properties", {})
        assert "severity" in item_props
        severity_enum = item_props["severity"].get("enum", [])
        assert "critical" in severity_enum, \
            "Severity enum must include 'critical'"
        assert "low" in severity_enum
        assert "medium" in severity_enum
        assert "high" in severity_enum

    def test_threat_item_has_description(self):
        schema = _extract_schema_dict("demo_structured_output.py")
        items = schema["properties"]["threats_found"]["items"]
        item_props = items.get("properties", {})
        assert "description" in item_props
        assert item_props["description"].get("type") == "string"

    def test_threat_item_has_remediation(self):
        schema = _extract_schema_dict("demo_structured_output.py")
        items = schema["properties"]["threats_found"]["items"]
        item_props = items.get("properties", {})
        assert "remediation" in item_props, \
            "Each threat must have 'remediation', not 'fix'"
        assert item_props["remediation"].get("type") == "string"

    def test_threat_item_required_fields(self):
        schema = _extract_schema_dict("demo_structured_output.py")
        items = schema["properties"]["threats_found"]["items"]
        required = items.get("required", [])
        for field in ["line", "severity", "description", "remediation"]:
            assert field in required, f"'{field}' must be required in threat items"

    def test_schema_has_overall_risk(self):
        schema = _extract_schema_dict("demo_structured_output.py")
        props = schema.get("properties", {})
        assert "overall_risk" in props, "Schema must have 'overall_risk'"
        risk_enum = props["overall_risk"].get("enum", [])
        assert "critical" in risk_enum
        assert "low" in risk_enum

    def test_schema_has_summary(self):
        schema = _extract_schema_dict("demo_structured_output.py")
        props = schema.get("properties", {})
        assert "summary" in props
        assert props["summary"].get("type") == "string"

    def test_schema_required_top_level_fields(self):
        schema = _extract_schema_dict("demo_structured_output.py")
        required = schema.get("required", [])
        for field in ["file", "threats_found", "overall_risk", "summary"]:
            assert field in required, f"'{field}' must be a required top-level field"

    def test_no_old_schema_fields(self):
        """Old marketing schema fields must be completely gone."""
        schema = _extract_schema_dict("demo_structured_output.py")
        props = schema.get("properties", {})
        assert "bugs_found" not in props, "Old 'bugs_found' field must be removed"
        assert "overall_quality" not in props, "Old 'overall_quality' field must be removed"
        # Check nested items too
        if "threats_found" in props:
            items = props["threats_found"].get("items", {})
            item_props = items.get("properties", {})
            assert "fix" not in item_props, "Old 'fix' field must be replaced with 'remediation'"
