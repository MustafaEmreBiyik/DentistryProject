"""
Requirements:
- Python standard library only

Generate markdown benchmark report from benchmark_results.json.
Run:
    python tests/benchmark/generate_report.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

BASE_DIR = Path(__file__).resolve().parent
RESULTS_FILE = BASE_DIR / "results" / "benchmark_results.json"
REPORT_FILE = BASE_DIR / "results" / "benchmark_report.md"


def _format_float(value: Any, digits: int = 2) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "N/A"


def _paper_sentences(data: Dict[str, Any]) -> Dict[str, str]:
    gemini = data["metric_1_api_response_time"]["gemini_mock"]
    shadow = data["metric_1_api_response_time"]["shadow_evaluator_mock"]
    uptime = data["metric_2_server_uptime"]
    db = data["metric_3_database_throughput"]

    sentence_api = (
        "The average API response time for the virtual patient (Gemini) was "
        f"{_format_float(gemini.get('mean_ms'))} ms (SD={_format_float(gemini.get('std_ms'))}), "
        "and the shadow evaluator processed inputs in an average of "
        f"{_format_float(shadow.get('mean_ms'))} ms (SD={_format_float(shadow.get('std_ms'))})."
    )

    sentence_uptime = (
        "During the monitoring window, the platform uptime was "
        f"{_format_float(uptime.get('uptime_percentage'))}% "
        f"({uptime.get('successful_checks', 0)}/{uptime.get('total_checks', 0)} successful health checks)."
    )

    sentence_db = (
        "The interaction logging subsystem sustained "
        f"{_format_float(db.get('transactions_per_second'))} transactions per second, "
        f"with a success rate of {_format_float(db.get('success_rate_percentage'))}% "
        f"({db.get('insert_successful', 0)}/{db.get('insert_attempted', 0)} successful inserts)."
    )

    return {
        "api": sentence_api,
        "uptime": sentence_uptime,
        "db": sentence_db,
    }


def generate_markdown_report(data: Dict[str, Any]) -> str:
    gemini = data["metric_1_api_response_time"]["gemini_mock"]
    shadow = data["metric_1_api_response_time"]["shadow_evaluator_mock"]
    uptime = data["metric_2_server_uptime"]
    db = data["metric_3_database_throughput"]
    meta = data.get("benchmark_meta", {})

    sentences = _paper_sentences(data)

    lines = [
        "# DENTAI Performance Benchmark Report",
        "",
        f"Generated at (UTC): {datetime.now(timezone.utc).isoformat()}",
        f"Benchmark data timestamp: {meta.get('generated_at_utc', 'N/A')}",
        "",
        "## Paper-Ready Sentences",
        "",
        f"1. {sentences['api']}",
        f"2. {sentences['uptime']}",
        f"3. {sentences['db']}",
        "",
        "## Academic Table (Copy/Paste)",
        "",
        "| Metric | Mean | Median | P95 | SD | Additional |",
        "|---|---:|---:|---:|---:|---|",
        (
            "| Gemini API Response Time (ms) "
            f"| {_format_float(gemini.get('mean_ms'))} "
            f"| {_format_float(gemini.get('median_ms'))} "
            f"| {_format_float(gemini.get('p95_ms'))} "
            f"| {_format_float(gemini.get('std_ms'))} "
            f"| n={gemini.get('success_count', 0)} |"
        ),
        (
            "| Shadow Evaluator Response Time (ms) "
            f"| {_format_float(shadow.get('mean_ms'))} "
            f"| {_format_float(shadow.get('median_ms'))} "
            f"| {_format_float(shadow.get('p95_ms'))} "
            f"| {_format_float(shadow.get('std_ms'))} "
            f"| n={shadow.get('success_count', 0)} |"
        ),
        (
            "| Server Uptime (%) "
            "| - | - | - | - "
            f"| {_format_float(uptime.get('uptime_percentage'))}% "
            f"({uptime.get('successful_checks', 0)}/{uptime.get('total_checks', 0)} checks) |"
        ),
        (
            "| Database Throughput (TPS) "
            "| - | - | - | - "
            f"| {_format_float(db.get('transactions_per_second'))} TPS; "
            f"success={_format_float(db.get('success_rate_percentage'))}% |"
        ),
        "",
        "## Method Summary",
        "",
        "- API latency benchmark: 50 requests to Gemini mock + 50 requests to shadow evaluator mock.",
        "- Uptime benchmark: health checks every 2 seconds over 60 seconds.",
        (
            "- Database benchmark: 100 concurrent benchmark inserts with cleanup using "
            "the BENCHMARK_TEST_ prefix."
        ),
        "",
    ]

    return "\n".join(lines)


def main() -> None:
    if not RESULTS_FILE.exists():
        raise FileNotFoundError(
            f"Benchmark results file not found: {RESULTS_FILE}. Run test_performance_benchmark.py first."
        )

    data = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
    markdown = generate_markdown_report(data)
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(markdown, encoding="utf-8")

    print(f"Benchmark report generated: {REPORT_FILE}")


def _self_test() -> None:
    """Small sanity check for local development."""
    if RESULTS_FILE.exists():
        main()


if __name__ == "__main__":
    main()
