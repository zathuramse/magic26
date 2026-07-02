# P5-6 Magic26 downstream risk rounds regeneration

Date: 2026-07-02

## Scope

P5-6 parameterized and regenerated the downstream summary/risk rounds that depend on round8/round19 outputs.

Target suffix:

```text
20210101_20260702
```

Side effects intentionally excluded:

- no dashboard export
- no `public/data` overwrite
- no Cloudflare deploy
- no cron scheduling
- no Git push

## Source scripts

The original generators were found outside the Magic26 repo under:

```text
C:/Users/abckf/research-brain/tools/
```

They were copied into the Magic26 repo and parameterized so the refresh pipeline does not depend on scattered external tools:

```text
scripts/magic26_round14_bootstrap_path_review.py
scripts/magic26_round19_author_absorption.py
scripts/magic26_round20_60d_validation.py
scripts/magic26_round21_volgap_rescue_review.py
```

Each script now accepts:

```text
--snapshot-suffix
```

Default remains:

```text
20210101_20260701
```

## Commands run

```text
python scripts/magic26_round14_bootstrap_path_review.py \
  --snapshot-suffix 20210101_20260702

python scripts/magic26_round19_author_absorption.py \
  --snapshot-suffix 20210101_20260702

python scripts/magic26_round20_60d_validation.py \
  --snapshot-suffix 20210101_20260702

python scripts/magic26_round21_volgap_rescue_review.py \
  --snapshot-suffix 20210101_20260702
```

## Generated external research outputs

These files are under:

```text
C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/
```

### Round14

```text
magic26_round14_bootstrap_summary_20210101_20260702.csv
magic26_round14_excluded_weak_momentum_path_review_20210101_20260702.csv
magic26_round14_baseline_vs_floor15_yearly_20210101_20260702.csv
magic26_round14_bootstrap_path_manifest_20210101_20260702.json
```

### Round19

```text
magic26_round19_author_absorption_detail_20210101_20260702.csv
magic26_round19_ret60_cap_summary_20210101_20260702.csv
magic26_round19_volume_gap_summary_20210101_20260702.csv
magic26_round19_risk_badge_summary_20210101_20260702.csv
magic26_round19_author_absorption_manifest_20210101_20260702.json
```

### Round20

```text
magic26_round20_60d_validation_summary_20210101_20260702.csv
magic26_round20_60d_flagged_cases_20210101_20260702.csv
magic26_round20_60d_validation_manifest_20210101_20260702.json
```

### Round21

```text
magic26_round21_volgap_rescue_summary_20210101_20260702.csv
magic26_round21_volgap_rescue_cases_20210101_20260702.csv
magic26_round21_volgap_rescue_review_manifest_20210101_20260702.json
```

## Validation summary

### Old suffix `20210101_20260701`

```text
round14 bootstrap rows: 2
round19 detail rows: 96, date_max=2026-06-26, 6213_rows=2
round19 ret60 summary rows: 16, contains ret60 <= 150%
round19 volume gap summary rows: 42, contains top1/top10 < 2
round19 risk badge summary rows: 24
round20 summary rows: 84, contains ret60 <= 150% and top1/top10 < 2
round20 flagged cases rows: 96, date_max=2026-06-26, 6213_rows=2
round21 summary rows: 24, contains rescue candidate and danger candidate
round21 cases rows: 96, date_max=2026-06-26, 6213_rows=2
```

### New suffix `20210101_20260702`

```text
round14 bootstrap rows: 2
round19 detail rows: 96, date_max=2026-06-26, 6213_rows=2
round19 ret60 summary rows: 16, contains ret60 <= 150%
round19 volume gap summary rows: 42, contains top1/top10 < 2
round19 risk badge summary rows: 24
round20 summary rows: 84, contains ret60 <= 150% and top1/top10 < 2
round20 flagged cases rows: 96, date_max=2026-06-26, 6213_rows=2
round21 summary rows: 24, contains rescue candidate and danger candidate
round21 cases rows: 96, date_max=2026-06-26, 6213_rows=2
```

## Field checks

Round19 detail:

```text
ret_60d_signal non-null: 96
top1_to_top10_volume_ratio non-null: 96
risk_long_ma_score non-null: 96
6213 rows: 2
```

Round20 flagged cases:

```text
ret_60d_signal non-null: 96
top1_to_top10_volume_ratio non-null: 96
risk_long_ma_score non-null: 96
flag_ret60_gt150 non-null: 96
flag_volgap_top10_ge2 non-null: 96
6213 rows: 2
```

Round21 cases:

```text
ret_60d_signal non-null: 96
top1_to_top10_volume_ratio non-null: 96
risk_long_ma_score non-null: 96
case_class_60d non-null: 96
6213 rows: 2
```

## Interpretation

- Downstream risk rounds regenerated cleanly for `20210101_20260702`.
- Row counts are stable versus the old suffix because these rounds depend on Candidate-A rows whose latest signal date is still `2026-06-26`.
- 6213 remains present through round19/20/21.
- The expected risk/summary concepts remain present:
  - `ret60 <= 150%`
  - `top1/top10 < 2`
  - `rescue candidate`
  - `danger candidate`

## Result

P5-6 succeeded locally. The target suffix now has regenerated round14/19/20/21 outputs.

The dashboard still remains on the previous production package until a later stage copies/exports these target-suffix outputs into dashboard data and runs local/browser verification.

## Recommended next step

P5-7 should perform a dashboard export dry-run / local package build for `20210101_20260702` and `data_through=2026-07-02`, still without deploy:

1. Run `export_dashboard_data.py` with explicit target suffix/data-through.
2. Verify all expected round files are copied into `data/processed` and `public/data` only when intentionally in scope.
3. Run package verifier with explicit suffix/date.
4. Browser QA locally if verifier passes.
5. Commit; still no push/deploy until P5-8.
