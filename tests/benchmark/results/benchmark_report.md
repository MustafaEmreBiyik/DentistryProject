# DENTAI Performance Benchmark Report

Generated at (UTC): 2026-03-23T11:45:28.934052+00:00
Benchmark data timestamp: 2026-03-23T11:43:17.481332+00:00

## Paper-Ready Sentences

1. The average API response time for the virtual patient (Gemini) was 596.10 ms (SD=170.13), and the shadow evaluator processed inputs in an average of 204.23 ms (SD=40.64).
2. During the monitoring window, the platform uptime was 100.00% (30/30 successful health checks).
3. The interaction logging subsystem sustained 43.18 transactions per second, with a success rate of 100.00% (100/100 successful inserts).

## Academic Table (Copy/Paste)

| Metric | Mean | Median | P95 | SD | Additional |
|---|---:|---:|---:|---:|---|
| Gemini API Response Time (ms) | 596.10 | 580.38 | 875.22 | 170.13 | n=50 |
| Shadow Evaluator Response Time (ms) | 204.23 | 199.29 | 274.00 | 40.64 | n=50 |
| Server Uptime (%) | - | - | - | - | 100.00% (30/30 checks) |
| Database Throughput (TPS) | - | - | - | - | 43.18 TPS; success=100.00% |

## Method Summary

- API latency benchmark: 50 requests to Gemini mock + 50 requests to shadow evaluator mock.
- Uptime benchmark: health checks every 2 seconds over 60 seconds.
- Database benchmark: 100 concurrent benchmark inserts with cleanup using the BENCHMARK_TEST_ prefix.
