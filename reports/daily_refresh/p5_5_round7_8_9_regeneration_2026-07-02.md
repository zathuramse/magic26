# P5-5 Magic26 round7/8/9 regeneration

Date: 2026-07-02

## Scope

P5-5 parameterized and regenerated the dependent early rounds that consume round4 checked signals.

- Target suffix: `20210101_20260702`
- Default script suffix remains: `20210101_20260701`
- Inputs: round4 checked signals generated in P5-4
- Cache: per-stock raw/adjusted/benchmark parquet generated in P5-3

Side effects intentionally excluded:

- no round14/19/20/21 regeneration
- no dashboard export
- no `public/data` overwrite
- no Cloudflare deploy
- no cron scheduling
- no Git push

## Scripts changed

Parameterized:

```text
scripts/magic26_round7_param_grid.py
scripts/magic26_round8_tradeability_checks.py
scripts/magic26_round9_close_exit_checks.py
```

Each now accepts:

```text
--snapshot-suffix
```

Default remains:

```text
20210101_20260701
```

This keeps the current production-oriented behavior unchanged unless a target suffix is explicitly passed.

## Commands run

```text
python scripts/magic26_round7_param_grid.py \
  --snapshot-suffix 20210101_20260702

python scripts/magic26_round8_tradeability_checks.py \
  --snapshot-suffix 20210101_20260702

python scripts/magic26_round9_close_exit_checks.py \
  --snapshot-suffix 20210101_20260702
```

## Generated external research outputs

These files are under:

```text
C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/
```

### Round7

```text
magic26_round7_param_grid_summary_20210101_20260702.csv
magic26_round7_param_grid_yearly_20210101_20260702.csv
magic26_round7_param_grid_top_20210101_20260702.csv
magic26_round7_param_grid_manifest_20210101_20260702.json
```

### Round8

```text
magic26_round8_tradeability_detail_20210101_20260702.csv
magic26_round8_tradeability_summary_20210101_20260702.csv
magic26_round8_tradeability_2024_failures_by_industry_20210101_20260702.csv
magic26_round8_tradeability_manifest_20210101_20260702.json
```

### Round9

```text
magic26_round9_close_exit_detail_20210101_20260702.csv
magic26_round9_close_exit_summary_20210101_20260702.csv
magic26_round9_close_exit_yearly_20210101_20260702.csv
magic26_round9_close_exit_manifest_20210101_20260702.json
```

## Validation summary

### Baseline suffix `20210101_20260701`

```text
round7 top rows: 40
round8 detail rows: 312
round8 detail date_max: 2026-06-26
round8 6213 rows: 4
round8 path_errors: 13
round8 summary rows: 6
round9 detail rows: 2496
round9 signal_date_max: 2026-06-26
round9 6213 rows: 32
round9 path_errors: 104
round9 summary rows: 48
```

### New suffix `20210101_20260702`

```text
round7 top rows: 40
round8 detail rows: 311
round8 detail date_max: 2026-06-26
round8 6213 rows: 4
round8 path_errors: 12
round8 summary rows: 6
round9 detail rows: 2488
round9 signal_date_max: 2026-06-26
round9 6213 rows: 32
round9 path_errors: 96
round9 summary rows: 48
```

Interpretation:

- Round7/8/9 were regenerated successfully for `20210101_20260702`.
- Latest candidate signal date remains `2026-06-26` in round8/9 because P5-4 base signals did not produce newer qualifying candidate rows.
- 6213 remains present in round8 and round9.
- `insufficient_forward_bars` counts are lower in the new suffix because the cache now includes more forward bars through `2026-07-02`.
- Row counts differ slightly because P5-4 recomputed the liquid universe at the later end date.

## Manifest verification

The new manifests record:

```text
snapshot_suffix = 20210101_20260702
```

and point to the matching round4/cache-based outputs.

## Result

P5-5 succeeded locally: round7/8/9 outputs now exist for `20210101_20260702`.

The dashboard remains on the previous production package until later stages regenerate round14/19/20/21, export dashboard data, verify, push, and deploy.

## Recommended next step

P5-6 should parameterize and regenerate downstream summary/risk rounds:

1. `magic26_round14_*`
2. `magic26_round19_*`
3. `magic26_round20_*`
4. `magic26_round21_*`

Still local-only first. Only after these are complete should dashboard export be attempted.
