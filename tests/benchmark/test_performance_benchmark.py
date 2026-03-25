"""
Requirements:
- pytest
- httpx
- fastapi
- uvicorn
- sqlalchemy

Pytest benchmark for DENTAI paper metrics:
1) API response time
2) Server uptime
3) Database throughput
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Tuple

import httpx
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.database import Base, ChatLog, SessionLocal, StudentSession, init_db  # noqa: E402

MOCK_SERVER_URL = "http://127.0.0.1:8001"
RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_FILE = RESULTS_DIR / "benchmark_results.json"
API_REQUEST_LOG_FILE = RESULTS_DIR / "api_request_log.jsonl"
UPTIME_CHECK_LOG_FILE = RESULTS_DIR / "uptime_check_log.jsonl"
DB_INSERT_LOG_FILE = RESULTS_DIR / "db_insert_log.jsonl"

API_REQUEST_COUNT = 50
UPTIME_DURATION_SECONDS = 60
UPTIME_INTERVAL_SECONDS = 2
DB_INSERT_COUNT = 100
DB_CONCURRENCY = 20


@dataclass
class DBContext:
    session_factory: Any
    backend: str


def _percentile(values: List[float], pct: float) -> float:
    """Return percentile with linear interpolation."""
    if not values:
        return math.nan
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (len(ordered) - 1) * (pct / 100.0)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return float(ordered[low])
    weight = rank - low
    return float(ordered[low] * (1 - weight) + ordered[high] * weight)


def _describe_ms(latencies_ms: List[float]) -> Dict[str, float]:
    """Compute summary statistics in milliseconds."""
    if not latencies_ms:
        return {"mean_ms": math.nan, "median_ms": math.nan, "p95_ms": math.nan, "std_ms": math.nan}
    return {
        "mean_ms": round(statistics.mean(latencies_ms), 2),
        "median_ms": round(statistics.median(latencies_ms), 2),
        "p95_ms": round(_percentile(latencies_ms, 95), 2),
        "std_ms": round(statistics.pstdev(latencies_ms), 2),
    }


def _start_mock_server() -> subprocess.Popen:
    """Start mock server in a child process."""
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "tests.benchmark.mock_gemini_server:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8001",
    ]
    return subprocess.Popen(
        command,
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


async def _wait_for_server_ready(url: str, timeout_seconds: float = 20.0) -> None:
    """Poll health endpoint until ready."""
    deadline = time.perf_counter() + timeout_seconds
    async with httpx.AsyncClient(timeout=3.0) as client:
        while time.perf_counter() < deadline:
            try:
                response = await client.get(f"{url}/health")
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            await asyncio.sleep(0.4)
    raise RuntimeError("Mock benchmark server did not become ready in time.")


@pytest.fixture(scope="module")
def benchmark_server() -> Generator[str, None, None]:
    """Fixture that runs mock server for all benchmarks."""
    process = _start_mock_server()
    try:
        asyncio.run(_wait_for_server_ready(MOCK_SERVER_URL))
        yield MOCK_SERVER_URL
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


async def _measure_endpoint_latency(
    base_url: str,
    endpoint: str,
    payload_factory,
    request_count: int,
    concurrency: int = 10,
) -> Tuple[List[float], int, List[Dict[str, Any]]]:
    """Send concurrent requests and return latencies in ms + success count."""
    semaphore = asyncio.Semaphore(concurrency)
    request_logs: List[Dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=20.0) as client:

        async def one_call(i: int) -> Dict[str, Any]:
            payload = payload_factory(i)
            async with semaphore:
                start = time.perf_counter()
                status_code = None
                error_text = None
                try:
                    response = await client.post(f"{base_url}{endpoint}", json=payload)
                    status_code = response.status_code
                except httpx.HTTPError as exc:
                    error_text = str(exc)
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                return {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "endpoint": endpoint,
                    "request_id": f"BENCHMARK_TEST_API_{i:04d}",
                    "input_preview": str(payload)[:180],
                    "status_code": status_code,
                    "ok": status_code == 200,
                    "latency_ms": round(elapsed_ms, 3),
                    "error": error_text,
                }

        request_logs = await asyncio.gather(*(one_call(i) for i in range(request_count)))

    latencies_ms = [entry["latency_ms"] for entry in request_logs]
    success_count = sum(1 for entry in request_logs if entry["ok"])
    return latencies_ms, success_count, request_logs


async def _measure_uptime(base_url: str, duration_seconds: int, interval_seconds: int) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Measure uptime by repeated health checks."""
    total_checks = 0
    successful_checks = 0
    start = time.perf_counter()
    check_logs: List[Dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=5.0) as client:
        while (time.perf_counter() - start) < duration_seconds:
            total_checks += 1
            status_code = None
            error_text = None
            try:
                response = await client.get(f"{base_url}/health")
                status_code = response.status_code
                if response.status_code == 200:
                    successful_checks += 1
            except httpx.HTTPError as exc:
                error_text = str(exc)

            check_logs.append(
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "check_id": f"BENCHMARK_TEST_HEALTH_{total_checks:04d}",
                    "status_code": status_code,
                    "ok": status_code == 200,
                    "error": error_text,
                }
            )
            await asyncio.sleep(interval_seconds)

    uptime_pct = (successful_checks / total_checks * 100.0) if total_checks else 0.0
    return (
        {
            "duration_seconds": duration_seconds,
            "interval_seconds": interval_seconds,
            "total_checks": total_checks,
            "successful_checks": successful_checks,
            "uptime_percentage": round(uptime_pct, 2),
        },
        check_logs,
    )


def _build_db_context() -> DBContext:
    """Try configured DB first; fallback to SQLite on failure."""
    try:
        init_db()
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        return DBContext(session_factory=SessionLocal, backend="configured_database")
    except Exception:
        fallback_engine = create_engine(
            "sqlite:///./dentai_benchmark_fallback.db",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=fallback_engine)
        fallback_factory = sessionmaker(autocommit=False, autoflush=False, bind=fallback_engine)
        return DBContext(session_factory=fallback_factory, backend="sqlite_fallback")


def _insert_one_interaction(db_ctx: DBContext, session_id: int, idx: int) -> Dict[str, Any]:
    """Insert one benchmark chat log row."""
    marker = f"BENCHMARK_TEST_{idx:04d}"
    start = time.perf_counter()
    try:
        with db_ctx.session_factory() as session:
            row = ChatLog(
                session_id=session_id,
                role="user",
                content=f"{marker} benchmark interaction payload",
                metadata_json={"benchmark": True, "marker": marker},
            )
            session.add(row)
            session.commit()
            return {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "request_id": marker,
                "ok": True,
                "latency_ms": round((time.perf_counter() - start) * 1000.0, 3),
                "error": None,
            }
    except SQLAlchemyError as exc:
        return {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "request_id": marker,
            "ok": False,
            "latency_ms": round((time.perf_counter() - start) * 1000.0, 3),
            "error": str(exc),
        }


async def _measure_db_throughput(insert_count: int, concurrency: int) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Insert N benchmark records concurrently and compute throughput metrics."""
    db_ctx = _build_db_context()

    with db_ctx.session_factory() as session:
        benchmark_session = StudentSession(
            student_id="BENCHMARK_TEST_STUDENT",
            case_id="BENCHMARK_TEST_CASE",
            current_score=0.0,
        )
        session.add(benchmark_session)
        session.commit()
        session.refresh(benchmark_session)
        benchmark_session_id = benchmark_session.id

    semaphore = asyncio.Semaphore(concurrency)

    async def insert_task(i: int) -> Dict[str, Any]:
        async with semaphore:
            return await asyncio.to_thread(_insert_one_interaction, db_ctx, benchmark_session_id, i)

    start = time.perf_counter()
    insert_logs = await asyncio.gather(*(insert_task(i) for i in range(insert_count)))
    elapsed = time.perf_counter() - start

    success_count = sum(1 for entry in insert_logs if entry["ok"])
    fail_count = insert_count - success_count
    tps = success_count / elapsed if elapsed > 0 else 0.0

    with db_ctx.session_factory() as session:
        session.query(ChatLog).filter(ChatLog.content.like("BENCHMARK_TEST_%")).delete(synchronize_session=False)
        session.query(StudentSession).filter(StudentSession.student_id == "BENCHMARK_TEST_STUDENT").delete(
            synchronize_session=False
        )
        session.commit()

    return (
        {
            "database_backend": db_ctx.backend,
            "insert_attempted": insert_count,
            "insert_successful": success_count,
            "insert_failed": fail_count,
            "success_rate_percentage": round((success_count / insert_count) * 100.0, 2),
            "elapsed_seconds": round(elapsed, 4),
            "transactions_per_second": round(tps, 2),
            "cleanup_prefix": "BENCHMARK_TEST_",
        },
        insert_logs,
    )


def _write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    """Write records as JSONL for request-level tracing."""
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _print_summary_table(results: Dict[str, Any]) -> None:
    """Print a compact console summary."""
    gemini = results["metric_1_api_response_time"]["gemini_mock"]
    shadow = results["metric_1_api_response_time"]["shadow_evaluator_mock"]
    uptime = results["metric_2_server_uptime"]
    db = results["metric_3_database_throughput"]

    print("\n" + "=" * 92)
    print("DENTAI PERFORMANCE BENCHMARK SUMMARY")
    print("=" * 92)
    print(f"{'Metric':<34} {'Mean':>10} {'Median':>10} {'P95':>10} {'Std':>10} {'Extra':>16}")
    print("-" * 92)
    print(
        f"{'Gemini API Latency (ms)':<34} "
        f"{gemini['mean_ms']:>10.2f} {gemini['median_ms']:>10.2f} {gemini['p95_ms']:>10.2f} "
        f"{gemini['std_ms']:>10.2f} {gemini['success_count']:>16}"
    )
    print(
        f"{'Shadow Evaluator Latency (ms)':<34} "
        f"{shadow['mean_ms']:>10.2f} {shadow['median_ms']:>10.2f} {shadow['p95_ms']:>10.2f} "
        f"{shadow['std_ms']:>10.2f} {shadow['success_count']:>16}"
    )
    print(f"{'Server Uptime (%)':<34} {'-':>10} {'-':>10} {'-':>10} {'-':>10} {uptime['uptime_percentage']:>16.2f}")
    print(
        f"{'DB Throughput (TPS)':<34} {'-':>10} {'-':>10} {'-':>10} {'-':>10} "
        f"{db['transactions_per_second']:>16.2f}"
    )
    print("=" * 92)


async def _run_benchmark(benchmark_server: str) -> Dict[str, Any]:
    """Async benchmark workflow."""
    gemini_latencies, gemini_success, gemini_logs = await _measure_endpoint_latency(
        base_url=benchmark_server,
        endpoint="/v1/models/gemini-pro:generateContent",
        payload_factory=lambda i: {
            "contents": [{"parts": [{"text": f"BENCHMARK_TEST_prompt_{i}"}]}],
            "generationConfig": {"temperature": 0.2},
        },
        request_count=API_REQUEST_COUNT,
        concurrency=10,
    )

    shadow_latencies, shadow_success, shadow_logs = await _measure_endpoint_latency(
        base_url=benchmark_server,
        endpoint="/v1/shadow-evaluator",
        payload_factory=lambda i: {
            "student_text": f"BENCHMARK_TEST_action_{i}",
            "rules": {"critical_safety_rules": ["no_allergy_conflict"]},
            "context_summary": "BENCHMARK_TEST_context",
        },
        request_count=API_REQUEST_COUNT,
        concurrency=10,
    )

    uptime_result, uptime_logs = await _measure_uptime(
        base_url=benchmark_server,
        duration_seconds=UPTIME_DURATION_SECONDS,
        interval_seconds=UPTIME_INTERVAL_SECONDS,
    )

    db_result, db_insert_logs = await _measure_db_throughput(
        insert_count=DB_INSERT_COUNT,
        concurrency=DB_CONCURRENCY,
    )

    api_request_logs = gemini_logs + shadow_logs

    results = {
        "benchmark_meta": {
            "project": "DENTAI",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "request_counts": {
                "api_requests_per_endpoint": API_REQUEST_COUNT,
                "db_insert_attempts": DB_INSERT_COUNT,
            },
            "uptime_window_seconds": UPTIME_DURATION_SECONDS,
            "uptime_interval_seconds": UPTIME_INTERVAL_SECONDS,
            "marker_prefix": "BENCHMARK_TEST_",
        },
        "metric_1_api_response_time": {
            "gemini_mock": {
                **_describe_ms(gemini_latencies),
                "success_count": gemini_success,
                "request_count": API_REQUEST_COUNT,
            },
            "shadow_evaluator_mock": {
                **_describe_ms(shadow_latencies),
                "success_count": shadow_success,
                "request_count": API_REQUEST_COUNT,
            },
        },
        "metric_2_server_uptime": uptime_result,
        "metric_3_database_throughput": db_result,
        "request_level_logs": {
            "api_requests_jsonl": str(API_REQUEST_LOG_FILE.name),
            "uptime_checks_jsonl": str(UPTIME_CHECK_LOG_FILE.name),
            "db_inserts_jsonl": str(DB_INSERT_LOG_FILE.name),
            "api_request_count": len(api_request_logs),
            "uptime_check_count": len(uptime_logs),
            "db_insert_count": len(db_insert_logs),
        },
    }

    _write_jsonl(API_REQUEST_LOG_FILE, api_request_logs)
    _write_jsonl(UPTIME_CHECK_LOG_FILE, uptime_logs)
    _write_jsonl(DB_INSERT_LOG_FILE, db_insert_logs)

    return results


def test_performance_benchmark(benchmark_server: str) -> None:
    """End-to-end benchmark runner that writes JSON output."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results = asyncio.run(_run_benchmark(benchmark_server))

    RESULTS_FILE.write_text(json.dumps(results, indent=2), encoding="utf-8")

    _print_summary_table(results)

    assert results["metric_1_api_response_time"]["gemini_mock"]["success_count"] == API_REQUEST_COUNT
    assert results["metric_1_api_response_time"]["shadow_evaluator_mock"]["success_count"] == API_REQUEST_COUNT
    assert results["metric_2_server_uptime"]["total_checks"] > 0
    assert results["metric_3_database_throughput"]["insert_attempted"] == DB_INSERT_COUNT
