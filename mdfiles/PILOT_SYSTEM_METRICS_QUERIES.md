# Pilot System Metrics - SQL Queries

This file documents how to extract pilot metrics from database logs.

## Source Tables

- `system_metric_logs` (new)
- `student_sessions`
- `chat_logs`

## 1) API response time (ms)

Average, p95, and error count for a date window:

```sql
SELECT
  AVG(metric_value) AS avg_ms,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY metric_value) AS p95_ms,
  SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed_calls,
  COUNT(*) AS total_calls
FROM system_metric_logs
WHERE metric_name = 'api_response_time_ms'
  AND timestamp >= NOW() - INTERVAL '7 days';
```

## 2) Task completion rate

Completion rate by sessions with at least one completion event (`diagnose_*`):

```sql
WITH session_totals AS (
  SELECT COUNT(*) AS total_sessions
  FROM student_sessions
  WHERE start_time >= NOW() - INTERVAL '30 days'
),
completed AS (
  SELECT COUNT(DISTINCT session_id) AS completed_sessions
  FROM system_metric_logs
  WHERE metric_name = 'task_completion_event'
    AND status = 'completed'
    AND timestamp >= NOW() - INTERVAL '30 days'
)
SELECT
  completed.completed_sessions,
  session_totals.total_sessions,
  CASE
    WHEN session_totals.total_sessions = 0 THEN 0
    ELSE (completed.completed_sessions::float / session_totals.total_sessions) * 100
  END AS completion_rate_pct
FROM completed, session_totals;
```

## 3) Server uptime

This metric must come from hosting platform telemetry (Streamlit Cloud/Supabase/infra monitor).

## 4) Database throughput

Write throughput from DB write metric events:

```sql
SELECT
  DATE_TRUNC('minute', timestamp) AS minute_bucket,
  COUNT(*) AS write_count,
  COUNT(*) / 60.0 AS writes_per_second
FROM system_metric_logs
WHERE metric_name = 'db_write_latency_ms'
  AND status = 'success'
  AND timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY 1
ORDER BY 1;
```

And DB write latency summary:

```sql
SELECT
  AVG(metric_value) AS avg_write_ms,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY metric_value) AS p95_write_ms,
  COUNT(*) AS sample_count
FROM system_metric_logs
WHERE metric_name = 'db_write_latency_ms'
  AND status = 'success'
  AND timestamp >= NOW() - INTERVAL '24 hours';
```

## 5) Reasoning deviation frequency (Shadow Evaluator)

Deviation frequency from `reasoning_deviation` metric:

```sql
SELECT
  SUM(CASE WHEN metric_value = 1 THEN 1 ELSE 0 END) AS deviation_count,
  COUNT(*) AS total_evaluations,
  CASE
    WHEN COUNT(*) = 0 THEN 0
    ELSE (SUM(CASE WHEN metric_value = 1 THEN 1 ELSE 0 END)::float / COUNT(*)) * 100
  END AS deviation_frequency_pct
FROM system_metric_logs
WHERE metric_name = 'reasoning_deviation'
  AND timestamp >= NOW() - INTERVAL '7 days';
```

## Notes

- Table is created automatically by `init_db()` because `SystemMetricLog` model is part of SQLAlchemy metadata.
- Existing historical sessions will not have backfilled system metrics.
- For pilot reporting, start collecting from deployment time onward.
