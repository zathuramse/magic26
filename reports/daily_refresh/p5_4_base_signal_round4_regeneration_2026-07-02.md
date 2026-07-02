# P5-4 Magic26 base signal + round4 regeneration

Date: 2026-07-02

## Scope

P5-4 regenerated only the base Magic26 signal outputs and round4 execution-check outputs against the new local cache suffix.

- Source cache suffix: `20210101_20260702`
- Start date: `2021-01-01`
- End date: `2026-07-02`
- Universe: `all`
- Liquidity filter: `--liquid-universe --min-avg-amount 30000000`
- Price modes: raw and adjusted

Side effects intentionally excluded:

- no round7/8/9/14/19/20/21 regeneration
- no dashboard export
- no `public/data` overwrite
- no Cloudflare deploy
- no cron scheduling
- no Git push

## Commands run

### Raw base signal

```text
python scripts/magic26_signal_pilot.py \
  --start-date 2021-01-01 \
  --end-date 2026-07-02 \
  --universe all \
  --liquid-universe \
  --min-avg-amount 30000000
```

### Adjusted base signal

```text
python scripts/magic26_signal_pilot.py \
  --start-date 2021-01-01 \
  --end-date 2026-07-02 \
  --universe all \
  --liquid-universe \
  --min-avg-amount 30000000 \
  --adjusted
```

### Raw round4 execution checks

```text
python scripts/magic26_round4_execution_checks.py \
  --signals C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_v0_signals_all_liquid30000000_raw_20210101_20260702_2130stocks.csv \
  --start-date 2021-01-01 \
  --end-date 2026-07-02 \
  --run-label round6_regime_all_liquid30000000_raw_20210101_20260702
```

### Adjusted round4 execution checks

```text
python scripts/magic26_round4_execution_checks.py \
  --signals C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_v0_signals_all_liquid30000000_adj_20210101_20260702_2130stocks.csv \
  --start-date 2021-01-01 \
  --end-date 2026-07-02 \
  --run-label round6_regime_all_liquid30000000_adj_20210101_20260702
```

## Generated external research outputs

These files are under:

```text
C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/
```

### Base signal outputs

```text
magic26_v0_signals_all_liquid30000000_raw_20210101_20260702_2130stocks.csv
magic26_v0_signals_all_liquid30000000_adj_20210101_20260702_2130stocks.csv
magic26_v0_manifest_all_liquid30000000_raw_20210101_20260702_2130stocks.json
magic26_v0_manifest_all_liquid30000000_adj_20210101_20260702_2130stocks.json
```

### Round4 outputs

```text
magic26_round4_checked_signals_round6_regime_all_liquid30000000_raw_20210101_20260702.csv
magic26_round4_summary_round6_regime_all_liquid30000000_raw_20210101_20260702.csv
magic26_round4_yearly_round6_regime_all_liquid30000000_raw_20210101_20260702.csv
magic26_round4_regime_round6_regime_all_liquid30000000_raw_20210101_20260702.csv
magic26_round4_manifest_round6_regime_all_liquid30000000_raw_20210101_20260702.json

magic26_round4_checked_signals_round6_regime_all_liquid30000000_adj_20210101_20260702.csv
magic26_round4_summary_round6_regime_all_liquid30000000_adj_20210101_20260702.csv
magic26_round4_yearly_round6_regime_all_liquid30000000_adj_20210101_20260702.csv
magic26_round4_regime_round6_regime_all_liquid30000000_adj_20210101_20260702.csv
magic26_round4_manifest_round6_regime_all_liquid30000000_adj_20210101_20260702.json
```

## Baseline comparison

Previous suffix `20210101_20260701`:

```text
raw base signals: rows=1425 date_max=2026-06-29 stocks=742
adj base signals: rows=1458 date_max=2026-06-29 stocks=748
raw round4: rows=1425 date_max=2026-06-29 stocks=742
adj round4: rows=1458 date_max=2026-06-29 stocks=748
6213 latest signal date: 2026-06-26 in both raw/adj
```

New suffix `20210101_20260702`:

```text
raw base signals: rows=1412 date_max=2026-06-29 stocks=733
adj base signals: rows=1445 date_max=2026-06-29 stocks=738
raw round4: rows=1412 date_max=2026-06-29 stocks=733
adj round4: rows=1445 date_max=2026-06-29 stocks=738
6213 latest signal date: 2026-06-26 in both raw/adj
```

Interpretation:

- The price cache now extends to `2026-07-02`, but no newer base Magic26 signal was generated after `2026-06-29`.
- 6213 remains present and its latest signal date remains `2026-06-26`.
- Lower signal row counts versus the previous suffix are possible because the liquid-universe filter is based on latest 20-day average trading value at the new end date.

## Round4 validation

Raw round4:

```text
rows=1412
date_min=2021-02-18
date_max=2026-06-29
stocks=733
6213 rows=2
6213 date_max=2026-06-26
bench_close_missing=0
risk_next_gap_gt3 exists=True
regime_all3 exists=True
```

Adjusted round4:

```text
rows=1445
date_min=2021-02-18
date_max=2026-06-29
stocks=738
6213 rows=2
6213 date_max=2026-06-26
bench_close_missing=0
risk_next_gap_gt3 exists=True
regime_all3 exists=True
```

Forward-return columns have expected tail NaNs because signals near the end date do not yet have 20D/60D future data.

## Result

P5-4 succeeded locally: base signal and round4 execution-check outputs now exist for `20210101_20260702`.

The dashboard remains on the previous production package until later P5 stages regenerate dependent rounds, export dashboard data, verify, push, and deploy.

## Recommended next step

P5-5 should parameterize and run the dependent early rounds that consume round4:

1. `magic26_round7_param_grid.py`
2. `magic26_round8_tradeability_checks.py`
3. `magic26_round9_close_exit_checks.py`

This should still be local-only first. After those exist for `20210101_20260702`, later stages can regenerate round14/19/20/21 and then dashboard export.
