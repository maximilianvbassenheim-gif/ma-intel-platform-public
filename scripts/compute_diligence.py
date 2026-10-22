#!/usr/bin/env python3
"""Generate a deterministic, evidence-linked report for the fictional diligence demo."""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO_ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = REPO_ROOT / "data" / "internal" / "DEMO_diligence_case.json"
REPORTS_DIR = REPO_ROOT / "reports"


def score_case(case: dict, source_sha256: str, generated_at: str) -> dict:
    """Score available evidence while retaining uncertainty and conflicting findings."""
    criteria = case.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        raise ValueError("Case must contain a non-empty criteria list")

    total_weight = 0
    scored_weight = 0
    overall_weighted_score = 0.0
    confidence_coverage = 0.0
    results = []
    seen_ids = set()

    for criterion in criteria:
        criterion_id = criterion["id"]
        weight = criterion["weight"]
        evidence = criterion.get("evidence", [])
        if not isinstance(weight, (int, float)) or weight <= 0:
            raise ValueError(f"Criterion {criterion_id} must have a positive weight")
        total_weight += weight

        weighted_score = 0.0
        total_confidence = 0.0
        for item in evidence:
            evidence_id = item["id"]
            confidence = item["confidence"]
            score = item["score"]
            if evidence_id in seen_ids:
                raise ValueError(f"Evidence IDs must be unique: {evidence_id}")
            seen_ids.add(evidence_id)
            if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
                raise ValueError(f"Evidence {evidence_id} confidence must be between 0 and 1")
            if not isinstance(score, (int, float)) or not 0 <= score <= 100:
                raise ValueError(f"Evidence {evidence_id} score must be between 0 and 100")
            if item.get("stance") not in {"supports", "concerns"}:
                raise ValueError(f"Evidence {evidence_id} stance must be supports or concerns")
            if not item.get("observed_at") or not item.get("source"):
                raise ValueError(f"Evidence {evidence_id} needs a source and observed_at timestamp")
            weighted_score += score * confidence
            total_confidence += confidence

        criterion_score = (
            weighted_score / total_confidence if total_confidence else None
        )
        criterion_confidence = (
            total_confidence / len(evidence) if evidence else 0.0
        )
        if criterion_score is not None:
            scored_weight += weight
            overall_weighted_score += criterion_score * weight
        confidence_coverage += weight * criterion_confidence

        stances = {item["stance"] for item in evidence}
        results.append(
            {
                "id": criterion_id,
                "name": criterion["name"],
                "weight": weight,
                "score": round(criterion_score, 2) if criterion_score is not None else None,
                "confidence": round(criterion_confidence, 3),
                "has_conflicting_evidence": stances == {"supports", "concerns"},
                "evidence": evidence,
                "open_questions": criterion.get("open_questions", []),
            }
        )

    overall_score = (
        overall_weighted_score / scored_weight if scored_weight else None
    )
    overall_confidence = confidence_coverage / total_weight
    return {
        "case_id": case["case_id"],
        "company": case["company"],
        "notice": case["notice"],
        "generated_at": generated_at,
        "provenance": {
            "input_file": str(INPUT_PATH.relative_to(REPO_ROOT)),
            "input_sha256": source_sha256,
            "scoring_method": (
                "Each criterion is the confidence-weighted mean of its evidence scores "
                "(0-100); the overall score is weighted by criterion weight. "
                "Confidence coverage includes all criteria, including those without evidence."
            ),
        },
        "overall_score": round(overall_score, 2) if overall_score is not None else None,
        "confidence_coverage": round(overall_confidence, 3),
        "status": "preliminary" if overall_confidence < 0.7 else "evidence-supported",
        "criteria": results,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "> **Fictional demo case only. This is not an investment recommendation or a real diligence finding.**",
        "",
        f"# Diligence assessment: {report['company']}",
        "",
        f"- **Case:** `{report['case_id']}`",
        f"- **Generated:** {report['generated_at']}",
        f"- **Overall score:** {report['overall_score']}/100",
        f"- **Evidence confidence coverage:** {report['confidence_coverage']:.1%}",
        f"- **Status:** {report['status']}",
        "",
        "Scores summarize the supplied fictional evidence and do not replace professional diligence.",
        "",
        "## Criterion summary",
        "",
        "| Criterion | Weight | Score | Confidence | Conflicting evidence |",
        "| :--- | ---: | ---: | ---: | :---: |",
    ]
    for criterion in report["criteria"]:
        score = f"{criterion['score']:.2f}" if criterion["score"] is not None else "N/A"
        lines.append(
            f"| {criterion['name']} | {criterion['weight']}% | {score} | "
            f"{criterion['confidence']:.1%} | "
            f"{'Yes' if criterion['has_conflicting_evidence'] else 'No'} |"
        )

    lines.extend(["", "## Evidence, counter-evidence, and open questions", ""])
    for criterion in report["criteria"]:
        lines.extend([f"### {criterion['name']}", ""])
        if criterion["evidence"]:
            for item in criterion["evidence"]:
                stance = "Supporting evidence" if item["stance"] == "supports" else "Counter-evidence / concern"
                lines.extend(
                    [
                        f"- **{stance} — {item['id']}** (score {item['score']}/100; "
                        f"confidence {item['confidence']:.0%})",
                        f"  - Finding: {item['finding']}",
                        f"  - Source: {item['source']} ({item['source_type']})",
                        f"  - Observed at: {item['observed_at']}",
                    ]
                )
        else:
            lines.append("- No evidence supplied.")
        if criterion["open_questions"]:
            lines.append("- **Open questions:**")
            lines.extend(f"  - {question}" for question in criterion["open_questions"])
        lines.append("")

    lines.extend(
        [
            "## Provenance",
            "",
            f"- Input: `{report['provenance']['input_file']}`",
            f"- SHA-256: `{report['provenance']['input_sha256']}`",
            f"- Scoring: {report['provenance']['scoring_method']}",
            "",
            report["notice"],
            "",
        ]
    )
    return "\n".join(lines)


def run_pipeline() -> int:
    try:
        input_bytes = INPUT_PATH.read_bytes()
        case = json.loads(input_bytes)
        report = score_case(
            case,
            hashlib.sha256(input_bytes).hexdigest(),
            datetime.now(timezone.utc).isoformat(),
        )
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"❌ Could not generate diligence report: {exc}")
        return 1

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "DEMO_diligence.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (REPORTS_DIR / "DEMO_diligence.md").write_text(
        render_markdown(report), encoding="utf-8"
    )
    print("✔ Fictional diligence reports generated: DEMO_diligence.md and DEMO_diligence.json")
    return 0


if __name__ == "__main__":
    sys.exit(run_pipeline())
