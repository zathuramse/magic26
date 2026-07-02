# P5-3 Magic26 generic cache extension verification

Date: 2026-07-02

## Scope

P5-3 only extends local Magic26 parquet caches from the current snapshot suffix to the next target suffix.

- Source suffix: `20210101_20260701`
- Target suffix: `20210101_20260702`
- Tail fetch range: `2026-07-01` to `2026-07-02`
- Target data date: `2026-07-02`
- Side effects intentionally excluded:
  - no round7/8/9/14/19/20/21 regeneration
  - no dashboard export
  - no `public/data` overwrite
  - no Cloudflare deploy
  - no cron scheduling

## Implementation

Added reusable script:

```text
scripts/extend_magic26_cache.py
```

Important options:

```text
--source-suffix
--target-suffix
--tail-start
--target-date
--dry-run
--refresh-daily
--overwrite
--sample-stock-id
```

`--refresh-daily` is required when a cached daily FinMind parquet is stale or empty.

## Stale daily cache issue found and fixed

During the first P5-3 run, `daily_adj_20260701.parquet` was found to be a stale empty cache:

```text
daily_adj_20260701.parquet rows=0
```

That would have produced target adjusted caches that jump from `2026-06-30` directly to `2026-07-02` for some stocks.

The script was updated with `--refresh-daily`, then P5-3 was rerun with:

```text
python scripts/extend_magic26_cache.py \
  --dry-run \
  --refresh-daily \
  --overwrite \
  --source-suffix 20210101_20260701 \
  --target-suffix 20210101_20260702 \
  --tail-start 2026-07-01 \
  --target-date 2026-07-02

python scripts/extend_magic26_cache.py \
  --refresh-daily \
  --overwrite \
  --source-suffix 20210101_20260701 \
  --target-suffix 20210101_20260702 \
  --tail-start 2026-07-01 \
  --target-date 2026-07-02
```

After refresh:

```text
daily_adj_20260701.parquet rows=2768 date=2026-07-01 6213_rows=1
daily_adj_20260702.parquet rows=2449 date=2026-07-02 6213_rows=1
```

## Final cache counts

```text
raw_*_20210101_20260701.parquet: 2144
raw_*_20210101_20260702.parquet: 2144

adj_*_20210101_20260701.parquet: 2130
adj_*_20210101_20260702.parquet: 2130

benchmark_TAIEX_20210101_20260701.parquet: 1
benchmark_TAIEX_20210101_20260702.parquet: 1

total *_20210101_20260701.parquet: 4275
total *_20210101_20260702.parquet: 4275
missing target counterparts: 0
```

## Representative validation

### 6213 raw

```text
raw_6213_20210101_20260702.parquet
rows: 1331
min date: 2021-01-04
max date: 2026-07-02
duplicate date/stock rows: 0
```

Latest rows:

```text
2026-06-30 close=370.5
2026-07-01 close=360.0
2026-07-02 close=358.5
```

### 6213 adjusted

```text
adj_6213_20210101_20260702.parquet
rows: 1331
min date: 2021-01-04
max date: 2026-07-02
duplicate date/stock rows: 0
```

Latest rows:

```text
2026-06-30 close=370.5
2026-07-01 close=357.0
2026-07-02 close=358.5
```

### TAIEX benchmark

```text
benchmark_TAIEX_20210101_20260702.parquet
rows: 1331
min date: 2021-01-04
max date: 2026-07-02
duplicate date/stock rows: 0
```

Latest rows:

```text
2026-06-30 close=46125.91
2026-07-01 close=47018.99
2026-07-02 close=46744.16
```

## Generated reports

Final refreshed dry-run:

```text
reports/daily_refresh/p5_3_extend_magic26_cache_dry_run_20260702_174042.json
reports/daily_refresh/p5_3_extend_magic26_cache_dry_run_20260702_174042.md
```

Final refreshed local write:

```text
reports/daily_refresh/p5_3_extend_magic26_cache_local_write_20260702_174258.json
reports/daily_refresh/p5_3_extend_magic26_cache_local_write_20260702_174258.md
```

## Result

P5-3 succeeded locally: the next cache suffix `20210101_20260702` exists and is internally complete for raw, adjusted, and TAIEX benchmark cache coverage.

The dashboard still shows the previous production package until the later P5 stages regenerate rounds, export dashboard data, verify, push, and deploy.

## Recommended next step

P5-4 should parameterize and run the base signal regeneration against `20210101_20260702`:

1. raw `magic26_signal_pilot.py`
2. adjusted `magic26_signal_pilot.py`
3. raw/adjusted `magic26_round4_execution_checks.py`

Do this locally first, then verify row counts and latest dates before touching dependent rounds or dashboard export.
