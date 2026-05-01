"""
Tests for threat_report.flag_anomalous_campaigns.
"""

import os
import sys
import pytest

# Ensure the project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from threat_report import load_threat_events, compute_metrics, flag_anomalous_campaigns


# -- Helpers -----------------------------------------------------------------

def _make_enriched_campaigns(raw_events):
    """Run the full pipeline: load -> compute_metrics."""
    return compute_metrics(load_threat_events(raw_events))


SAMPLE_EVENTS = [
    {"threat_campaign": "APT-29 Phishing", "detections": 1200, "blocked": 1120, "escalated": 45, "false_positives": 30},
    {"threat_campaign": "Ransomware C2", "detections": 340, "blocked": 320, "escalated": 12, "false_positives": 5},
    {"threat_campaign": "DNS Tunneling", "detections": 0, "blocked": 0, "escalated": 0, "false_positives": 0},
    {"threat_campaign": "Credential Stuffing", "detections": 870, "blocked": 650, "escalated": 98, "false_positives": 120},
]


# -- Empty / single-element edge cases --------------------------------------

class TestFlagAnomalousEdgeCases:

    def test_empty_list(self):
        assert flag_anomalous_campaigns([]) == []

    def test_single_campaign_not_flagged(self):
        """A lone campaign can't exceed 2x its own average."""
        campaigns = _make_enriched_campaigns([
            {"threat_campaign": "Solo", "detections": 100, "blocked": 50, "escalated": 10, "false_positives": 5},
        ])
        assert flag_anomalous_campaigns(campaigns) == []

    def test_all_identical_rates(self):
        """When every campaign has the same rate, none exceed 2x average."""
        campaigns = _make_enriched_campaigns([
            {"threat_campaign": "A", "detections": 100, "blocked": 50, "escalated": 10, "false_positives": 0},
            {"threat_campaign": "B", "detections": 200, "blocked": 100, "escalated": 20, "false_positives": 0},
        ])
        assert flag_anomalous_campaigns(campaigns) == []

    def test_all_zero_detections(self):
        """All-zero campaigns should produce no flags (0 is not > 0)."""
        campaigns = _make_enriched_campaigns([
            {"threat_campaign": "A", "detections": 0, "blocked": 0, "escalated": 0, "false_positives": 0},
            {"threat_campaign": "B", "detections": 0, "blocked": 0, "escalated": 0, "false_positives": 0},
        ])
        assert flag_anomalous_campaigns(campaigns) == []


# -- Core anomaly detection --------------------------------------------------

class TestFlagAnomalousDetection:

    def test_sample_data_no_outlier_above_2x_average(self):
        """No campaign in the sample data exceeds 2x the average escalation rate."""
        campaigns = _make_enriched_campaigns(SAMPLE_EVENTS)
        flagged = flag_anomalous_campaigns(campaigns)
        assert flagged == []

    def test_sample_data_does_not_flag_low_rate(self):
        """Ransomware C2 and DNS Tunneling should not be flagged."""
        campaigns = _make_enriched_campaigns(SAMPLE_EVENTS)
        flagged_names = [f["campaign"] for f in flag_anomalous_campaigns(campaigns)]
        assert "Ransomware C2" not in flagged_names
        assert "DNS Tunneling" not in flagged_names

    def test_clear_outlier_is_flagged(self):
        """One extreme outlier among low-rate campaigns must be flagged."""
        campaigns = _make_enriched_campaigns([
            {"threat_campaign": "Low-A", "detections": 1000, "blocked": 900, "escalated": 10, "false_positives": 0},
            {"threat_campaign": "Low-B", "detections": 1000, "blocked": 900, "escalated": 10, "false_positives": 0},
            {"threat_campaign": "Outlier", "detections": 1000, "blocked": 100, "escalated": 500, "false_positives": 0},
        ])
        flagged = flag_anomalous_campaigns(campaigns)
        assert len(flagged) == 1
        assert flagged[0]["campaign"] == "Outlier"

    def test_boundary_exactly_2x_not_flagged(self):
        """A campaign at exactly 2x the average should NOT be flagged (strict >)."""
        campaigns = [
            {"campaign": "Zero", "escalation_rate": 0.0, "detections": 100},
            {"campaign": "Exact2x", "escalation_rate": 0.1, "detections": 100},
        ]
        flagged = flag_anomalous_campaigns(campaigns)
        assert len(flagged) == 0


# -- Output structure --------------------------------------------------------

class TestFlagAnomalousOutput:

    def test_output_contains_required_keys(self):
        campaigns = _make_enriched_campaigns([
            {"threat_campaign": "Low-1", "detections": 1000, "blocked": 900, "escalated": 10, "false_positives": 0},
            {"threat_campaign": "Low-2", "detections": 1000, "blocked": 900, "escalated": 10, "false_positives": 0},
            {"threat_campaign": "High", "detections": 100, "blocked": 10, "escalated": 90, "false_positives": 0},
        ])
        flagged = flag_anomalous_campaigns(campaigns)
        assert len(flagged) >= 1
        entry = flagged[0]
        assert "campaign" in entry
        assert "escalation_rate" in entry
        assert "average_escalation_rate" in entry
        assert "ratio_to_average" in entry

    def test_ratio_to_average_is_correct(self):
        campaigns = _make_enriched_campaigns([
            {"threat_campaign": "Low", "detections": 1000, "blocked": 900, "escalated": 10, "false_positives": 0},
            {"threat_campaign": "High", "detections": 100, "blocked": 10, "escalated": 90, "false_positives": 0},
        ])
        flagged = flag_anomalous_campaigns(campaigns)
        for entry in flagged:
            expected_ratio = entry["escalation_rate"] / entry["average_escalation_rate"]
            assert abs(entry["ratio_to_average"] - expected_ratio) < 1e-9
