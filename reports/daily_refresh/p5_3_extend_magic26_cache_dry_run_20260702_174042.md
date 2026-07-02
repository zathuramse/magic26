# P5-3 Magic26 cache extension report

- mode: dry-run
- refresh_daily: `True`
- overwrite: `True`
- source_suffix: `20210101_20260701`
- target_suffix: `20210101_20260702`
- tail_start: `2026-07-01`
- target_date: `2026-07-02`
- trading_days: 2026-07-01, 2026-07-02
- scope: cache parquet only; no round regeneration, no dashboard export, no deploy, no cron

## Daily feed rows
- raw: rows=4672 date_min=2026-07-01 date_max=2026-07-02
- adj: rows=4349 date_min=2026-07-01 date_max=2026-07-02

## Cache extension summary
- raw: source_files=2144 planned_or_written=2144 exists_skipped=0
  - sample 6213: old_max=2026-07-01 add_rows=2 out_max=2026-07-02 status=planned
- adj: source_files=2130 planned_or_written=2130 exists_skipped=0
  - sample 6213: old_max=2026-06-30 add_rows=2 out_max=2026-07-02 status=planned
- benchmark_TAIEX: status=planned old_max=2026-07-01 add_rows=2 out_max=2026-07-02

## Validation notes

- raw sample 6213 extends to target date 2026-07-02.
- adj sample 6213 extends to target date 2026-07-02.
- benchmark_TAIEX extends to target date 2026-07-02.
