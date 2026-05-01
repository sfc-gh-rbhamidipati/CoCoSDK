"""
Security event pipeline: process threat detections, blocked URLs, and policy violations.
Computes per-campaign metrics and generates a JSON threat report.
This script has intentional bugs for the Cortex Code Agent SDK demo.
"""

import json


def load_threat_events(events):
    """Load raw security events into a list of threat campaign dicts."""
    required_keys = {"threat_campaign", "detections", "blocked", "escalated", "false_positives"}
    results = []
    for i, ev in enumerate(events):
        missing = required_keys - ev.keys()
        if missing:
            raise ValueError(f"Event at index {i} is missing required keys: {sorted(missing)}")
        results.append({
            "campaign": ev["threat_campaign"],
            "detections": ev["detections"],
            "blocked": ev["blocked"],
            "escalated": ev["escalated"],
            "false_positives": ev["false_positives"],
        })
    return results


def compute_metrics(campaigns):
    """Add detection_rate, block_rate, escalation_rate, and false_positive_ratio."""
    results = []
    for c in campaigns:
        enriched = dict(c)
        det = enriched["detections"]
        for field in ("detections", "blocked", "escalated", "false_positives"):
            if enriched[field] < 0:
                raise ValueError(
                    f"Campaign '{enriched['campaign']}': {field} ({enriched[field]}) is negative"
                )
        if enriched["false_positives"] > det:
            raise ValueError(
                f"Campaign '{enriched['campaign']}': false_positives ({enriched['false_positives']}) "
                f"exceeds detections ({det})"
            )
        if enriched["blocked"] > det:
            raise ValueError(
                f"Campaign '{enriched['campaign']}': blocked ({enriched['blocked']}) "
                f"exceeds detections ({det})"
            )
        if enriched["escalated"] > det:
            raise ValueError(
                f"Campaign '{enriched['campaign']}': escalated ({enriched['escalated']}) "
                f"exceeds detections ({det})"
            )
        if enriched["blocked"] + enriched["escalated"] + enriched["false_positives"] > det:
            raise ValueError(
                f"Campaign '{enriched['campaign']}': blocked + escalated + false_positives "
                f"({enriched['blocked'] + enriched['escalated'] + enriched['false_positives']}) "
                f"exceeds detections ({det})"
            )
        acted_on = enriched["blocked"] + enriched["escalated"]
        enriched["detection_rate"] = acted_on / det if det else 0.0
        enriched["block_rate"] = enriched["blocked"] / det if det else 0.0
        enriched["escalation_rate"] = enriched["escalated"] / det if det else 0.0
        enriched["false_positive_ratio"] = enriched["false_positives"] / det if det else 0.0
        results.append(enriched)
    return results


def format_threat_report(campaigns):
    """Return a JSON summary with totals and the highest-risk campaign."""
    if not campaigns:
        return json.dumps({"total_detections": 0, "highest_risk_campaign": None})

    total_detections = sum(c["detections"] for c in campaigns)
    total_blocked = sum(c["blocked"] for c in campaigns)
    total_escalated = sum(c["escalated"] for c in campaigns)
    total_false_positives = sum(c["false_positives"] for c in campaigns)

    active = [c for c in campaigns if c["detections"] > 0]
    highest_risk = max(active, key=lambda c: c.get("escalation_rate", 0)) if active else None

    campaign_details = [
        {
            "campaign": c["campaign"],
            "detections": c["detections"],
            "blocked": c["blocked"],
            "escalated": c["escalated"],
            "false_positives": c["false_positives"],
            "detection_rate": c.get("detection_rate", 0.0),
            "block_rate": c.get("block_rate", 0.0),
            "escalation_rate": c.get("escalation_rate", 0.0),
            "false_positive_ratio": c.get("false_positive_ratio", 0.0),
        }
        for c in campaigns
    ]

    return json.dumps({
        "total_detections": total_detections,
        "total_blocked": total_blocked,
        "total_escalated": total_escalated,
        "total_false_positives": total_false_positives,
        "highest_risk_campaign": highest_risk["campaign"] if highest_risk else None,
        "overall_block_rate": total_blocked / total_detections if total_detections > 0 else 0.0,
        "overall_escalation_rate": total_escalated / total_detections if total_detections > 0 else 0.0,
        "overall_false_positive_ratio": total_false_positives / total_detections if total_detections > 0 else 0.0,
        "campaigns": campaign_details,
    })


def flag_anomalous_campaigns(campaigns):
    """Flag campaigns whose escalation_rate exceeds 2x the average escalation rate."""
    if not campaigns:
        return []

    active = [c for c in campaigns if c.get("detections", 0) > 0]
    if not active:
        return []

    rates = [c.get("escalation_rate", 0.0) for c in active]
    avg_rate = sum(rates) / len(rates)

    flagged = []
    for i, c in enumerate(active):
        rate = rates[i]
        if avg_rate == 0.0:
            if rate > 0.0:
                flagged.append({
                    "campaign": c["campaign"],
                    "escalation_rate": rate,
                    "average_escalation_rate": avg_rate,
                    "ratio_to_average": float("inf"),
                })
            continue
        if rate > 2.0 * avg_rate:
            flagged.append({
                "campaign": c["campaign"],
                "escalation_rate": rate,
                "average_escalation_rate": avg_rate,
                "ratio_to_average": rate / avg_rate,
            })
    return flagged


if __name__ == "__main__":
    sample_events = [
        {"threat_campaign": "APT-29 Phishing", "detections": 1200, "blocked": 1150, "escalated": 45, "false_positives": 5},
        {"threat_campaign": "Ransomware C2", "detections": 340, "blocked": 328, "escalated": 12, "false_positives": 0},
        {"threat_campaign": "DNS Tunneling", "detections": 0, "blocked": 0, "escalated": 0, "false_positives": 0},
        {"threat_campaign": "Credential Stuffing", "detections": 870, "blocked": 650, "escalated": 98, "false_positives": 15},
    ]

    data = load_threat_events(sample_events)
    data = compute_metrics(data)
    print(format_threat_report(data))

    anomalies = flag_anomalous_campaigns(data)
    if anomalies:
        print(json.dumps({"anomalous_campaigns": anomalies}))
