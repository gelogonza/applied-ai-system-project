"""
Reliability check for the Mood Music RAG pipeline.

Runs 6 predefined queries against Claude, measures pass/fail and confidence
per query, and saves a full report to reliability_report.json.

Usage:
    python scripts/reliability_check.py

Requires ANTHROPIC_API_KEY to be set (or a .env file in the project root).
"""

import json
import os
import sys
from pathlib import Path

# Make src/ and the project root importable from scripts/
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

import anthropic

from rag import retrieve_songs, run_rag, score_response, validate_output
from recommender import load_songs

# ---------------------------------------------------------------------------
# Test cases
# Each entry has a query and a brief note explaining what it's testing.
# ---------------------------------------------------------------------------
TEST_CASES = [
    {
        "query": "something chill to study to",
        "note": "core use case — low-energy lofi query",
    },
    {
        "query": "intense workout gym music",
        "note": "high-energy query with strong keyword signals",
    },
    {
        "query": "romantic dinner jazz",
        "note": "genre-specific query with mood context",
    },
    {
        "query": "angry aggressive heavy music",
        "note": "edge case — tests angry/metal retrieval",
    },
    {
        "query": "upbeat pop songs to dance to",
        "note": "happy/energetic pop query",
    },
    {
        "query": "music",
        "note": "degraded input — near-empty context, tests fallback behavior",
    },
]

PASS_MARK = 0.40  # minimum confidence to count as a quality pass


def run_checks() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    songs = load_songs(str(ROOT / "data" / "songs.csv"))

    print(f"\nMood Music — Reliability Check ({len(TEST_CASES)} queries)\n")
    print(f"{'#':<3} {'Query':<40} {'Guardrail':<12} {'Confidence'}")
    print("-" * 70)

    results = []
    for i, case in enumerate(TEST_CASES, 1):
        query = case["query"]

        # Retrieve (deterministic — called separately so we can score later)
        retrieved = retrieve_songs(query, songs, k=5)

        # Generate (calls Claude)
        response = run_rag(query, songs, client)

        # Measure
        guardrail_ok, _ = validate_output(response, retrieved)
        confidence = score_response(response, retrieved)
        quality_pass = guardrail_ok and confidence >= PASS_MARK

        status = "✓ PASS" if quality_pass else "✗ FAIL"
        print(f"{i:<3} {query:<40} {status:<12} {confidence:.2f}")

        results.append({
            "query": query,
            "note": case["note"],
            "retrieved_titles": [s["title"] for s in retrieved],
            "response": response,
            "guardrail_passed": guardrail_ok,
            "confidence_score": confidence,
            "quality_pass": quality_pass,
        })

    # Summary
    passed = sum(1 for r in results if r["quality_pass"])
    avg_conf = sum(r["confidence_score"] for r in results) / len(results)
    avg_conf_passed = (
        sum(r["confidence_score"] for r in results if r["quality_pass"]) / passed
        if passed else 0.0
    )

    print("-" * 70)
    print(
        f"\nResults: {passed} / {len(results)} passed  |  "
        f"Avg confidence: {avg_conf:.2f}  |  "
        f"Avg confidence (passed only): {avg_conf_passed:.2f}"
    )

    if passed < len(results):
        failed = [r["query"] for r in results if not r["quality_pass"]]
        print(f"Failed queries: {failed}")

    # Save report
    report_path = ROOT / "reliability_report.json"
    report = {
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "pass_rate": round(passed / len(results), 2),
            "avg_confidence": round(avg_conf, 2),
            "avg_confidence_passed": round(avg_conf_passed, 2),
            "pass_mark": PASS_MARK,
        },
        "results": results,
    }
    with report_path.open("w") as f:
        json.dump(report, f, indent=2)
    print(f"\nFull report saved to {report_path.name}")


if __name__ == "__main__":
    run_checks()
