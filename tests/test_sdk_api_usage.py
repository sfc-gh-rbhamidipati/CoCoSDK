"""
Validation tests: SDK API usage correctness across all demo scripts.

These tests verify that each Python demo script:
- Is valid Python (parses without syntax errors)
- Imports the correct SDK symbols from cortex_code_agent_sdk
- Uses the correct SDK API patterns (query, CortexCodeSDKClient, etc.)
- References security-domain files (threat_report.py), not marketing (report.py)

Tests are expected to FAIL before implementation (TDD red phase).
"""

import ast
import os
import re
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(filename):
    path = os.path.join(PROJECT_ROOT, filename)
    with open(path) as f:
        return f.read()


def _parse(filename):
    """Parse a Python file and return the AST. Fails if file doesn't exist or has syntax errors."""
    source = _read(filename)
    return ast.parse(source, filename=filename)


def _get_imports(tree):
    """Extract all imported names from an AST."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module:
                for alias in node.names:
                    names.add(alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
    return names


# ── threat_report.py (replacement for report.py) ──────────────────────

class TestThreatReportPy:
    """Validate the security-domain data pipeline replaces the marketing one."""

    def test_threat_report_exists(self):
        """threat_report.py must exist as the replacement for report.py."""
        path = os.path.join(PROJECT_ROOT, "threat_report.py")
        assert os.path.isfile(path), "threat_report.py does not exist yet"

    def test_threat_report_parses(self):
        tree = _parse("threat_report.py")
        assert tree is not None

    def test_threat_report_has_security_data(self):
        """Must contain security-relevant field names, not marketing fields."""
        source = _read("threat_report.py")
        # Should have security domain terms
        assert "threat" in source.lower() or "detection" in source.lower() or "blocked" in source.lower(), \
            "threat_report.py should contain security-domain terminology"
        # Should NOT have marketing terms
        assert "campaign_name" not in source, "threat_report.py should not reference campaign_name"
        assert "impressions" not in source, "threat_report.py should not reference impressions"
        assert "clicks" not in source, "threat_report.py should not reference clicks"

    def test_threat_report_has_escalation_rate(self):
        """Plan specifies escalation rate as a key metric."""
        source = _read("threat_report.py")
        assert "escalat" in source.lower(), "threat_report.py should compute escalation-related metrics"


# ── demo_single_turn.py ───────────────────────────────────────────────

class TestDemoSingleTurn:
    """Validate single-turn demo targets the security pipeline."""

    def test_parses(self):
        tree = _parse("demo_single_turn.py")
        assert tree is not None

    def test_imports_sdk(self):
        tree = _parse("demo_single_turn.py")
        imports = _get_imports(tree)
        assert "query" in imports or "CortexCodeSDKClient" in imports, \
            "Must import query or CortexCodeSDKClient from SDK"

    def test_references_threat_report(self):
        """Prompt should reference threat_report.py, not report.py."""
        source = _read("demo_single_turn.py")
        assert "threat_report" in source, \
            "Single-turn demo should reference threat_report.py"

    def test_no_marketing_references(self):
        source = _read("demo_single_turn.py")
        assert "marketing" not in source.lower(), "Should not reference marketing"
        assert "campaign" not in source.lower(), "Should not reference campaigns"

    def test_security_prompt(self):
        """Prompt should mention security context."""
        source = _read("demo_single_turn.py")
        assert "security" in source.lower() or "threat" in source.lower(), \
            "Prompt should reference security domain"


# ── demo_multi_turn.py ────────────────────────────────────────────────

class TestDemoMultiTurn:
    """Validate multi-turn demo has security-focused turns."""

    def test_parses(self):
        tree = _parse("demo_multi_turn.py")
        assert tree is not None

    def test_imports_sdk_client(self):
        tree = _parse("demo_multi_turn.py")
        imports = _get_imports(tree)
        assert "CortexCodeSDKClient" in imports, \
            "Multi-turn demo must import CortexCodeSDKClient"

    def test_turn1_security_summarize(self):
        """Turn 1 should ask to summarize the security event pipeline."""
        source = _read("demo_multi_turn.py")
        assert "threat_report" in source, \
            "Turn 1 should reference threat_report.py"
        assert "security" in source.lower() or "threat" in source.lower(), \
            "Turn 1 should mention security context"

    def test_turn2_anomaly_detection(self):
        """Turn 2 should ask about anomalous campaigns / escalation rate."""
        source = _read("demo_multi_turn.py")
        assert "escalation" in source.lower() or "anomal" in source.lower(), \
            "Turn 2 should reference escalation rate or anomaly detection"

    def test_no_marketing_references(self):
        source = _read("demo_multi_turn.py")
        assert "campaign" not in source.lower() or "threat campaign" in source.lower(), \
            "Should not reference marketing campaigns (threat campaigns are OK)"
        assert "clicks" not in source.lower(), "Should not reference clicks"


# ── demo_structured_output.py ─────────────────────────────────────────

class TestDemoStructuredOutput:
    """Validate the structured output demo uses a threat assessment schema."""

    def test_parses(self):
        tree = _parse("demo_structured_output.py")
        assert tree is not None

    def test_imports_sdk(self):
        tree = _parse("demo_structured_output.py")
        imports = _get_imports(tree)
        assert "query" in imports or "CortexCodeSDKClient" in imports

    def test_schema_has_threats_found(self):
        """Schema must have threats_found array, not bugs_found."""
        source = _read("demo_structured_output.py")
        assert "threats_found" in source, \
            "Schema should have 'threats_found' field"
        assert "bugs_found" not in source, \
            "Schema should not have 'bugs_found' (old marketing schema)"

    def test_schema_has_overall_risk(self):
        """Schema must have overall_risk, not overall_quality."""
        source = _read("demo_structured_output.py")
        assert "overall_risk" in source, \
            "Schema should have 'overall_risk' field"
        assert "overall_quality" not in source, \
            "Schema should not have 'overall_quality' (old marketing schema)"

    def test_schema_has_critical_severity(self):
        """Severity enum must include 'critical' level."""
        source = _read("demo_structured_output.py")
        assert "critical" in source, \
            "Schema severity should include 'critical' level"

    def test_schema_has_remediation(self):
        """Each threat should have a remediation field."""
        source = _read("demo_structured_output.py")
        assert "remediation" in source, \
            "Schema should include 'remediation' field per threat"

    def test_references_threat_report(self):
        source = _read("demo_structured_output.py")
        assert "threat_report" in source, \
            "Structured output demo should review threat_report.py"


# ── demo_chat_embed.py ────────────────────────────────────────────────

class TestDemoChatEmbed:
    """Validate the chat embedding demo exists and uses correct SDK patterns."""

    def test_file_exists(self):
        path = os.path.join(PROJECT_ROOT, "demo_chat_embed.py")
        assert os.path.isfile(path), "demo_chat_embed.py must be created"

    def test_parses(self):
        tree = _parse("demo_chat_embed.py")
        assert tree is not None

    def test_imports_sdk(self):
        tree = _parse("demo_chat_embed.py")
        imports = _get_imports(tree)
        assert "CortexCodeSDKClient" in imports or "query" in imports, \
            "Chat embed demo must import SDK client"

    def test_has_streaming_pattern(self):
        """Must demonstrate streaming responses (the embedding story)."""
        source = _read("demo_chat_embed.py")
        assert "receive_response" in source or "async for" in source, \
            "Chat embed demo should stream responses"

    def test_has_sql_execute_tool(self):
        """Should include sql_execute in allowed_tools per the plan."""
        source = _read("demo_chat_embed.py")
        assert "sql_execute" in source, \
            "Chat embed demo should allow sql_execute tool for data queries"

    def test_simulates_chat_backend(self):
        """Should simulate a chat backend request/response loop."""
        source = _read("demo_chat_embed.py")
        assert "input" in source.lower() or "request" in source.lower() or "question" in source.lower(), \
            "Chat embed demo should simulate handling user questions"

    def test_mentions_embed_or_chat_backend(self):
        """Docstring or comments should reference embedding or chat backend use case."""
        source = _read("demo_chat_embed.py")
        assert "embed" in source.lower() or "chat backend" in source.lower(), \
            "Chat embed demo should reference embedding or chat backend use case"
