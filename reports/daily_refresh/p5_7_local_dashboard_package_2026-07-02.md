# P5-7 Magic26 local dashboard package refresh

Date: 2026-07-02

## Scope

P5-7 built and verified a local dashboard package for the target snapshot.

```text
snapshot_suffix = 20210101_20260702
data_through = 2026-07-02
```

Side effects intentionally excluded:

- no Git push
- no Cloudflare deploy
- no cron scheduling

This stage does update local dashboard package files under:

```text
data/processed/
public/data/
```

## Important blocker found and resolved

The first explicit verifier run failed because the target dashboard package expected:

```text
magic26_round17_b_retest_rearm_watch_20210101_20260702.csv
```

but P5-6 had not regenerated round15/16/17 yet. The old verifier was correct to block this; deploying with a missing round17 file would mix target data with stale dashboard dependencies.

Resolution:

1. Copied repo-external tools into Magic26 repo scripts:

```text
scripts/magic26_round15_priority_review_pack.py
scripts/magic26_round16_top10_manual_review.py
scripts/magic26_round17_b_retest_rearm_watch.py
```

2. Added `--snapshot-suffix` to each, defaulting to:

```text
20210101_20260701
```

3. Ran them for target suffix:

```text
python scripts/magic26_round15_priority_review_pack.py --snapshot-suffix 20210101_20260702
python scripts/magic26_round16_top10_manual_review.py --snapshot-suffix 20210101_20260702
python scripts/magic26_round17_b_retest_rearm_watch.py --snapshot-suffix 20210101_20260702
```

4. Re-ran dashboard export.

## Round15/16/17 target outputs

External research outputs under:

```text
C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/
```

```text
magic26_round15_priority_review_ranked_20210101_20260702.csv rows=17
magic26_round15_priority_review_watch_20210101_20260702.csv rows=9
magic26_round16_top10_manual_review_20210101_20260702.csv rows=10
magic26_round17_b_retest_rearm_watch_20210101_20260702.csv rows=3
```

Manifest suffix checks:

```text
round15 manifest snapshot_suffix = 20210101_20260702
round16 manifest snapshot_suffix = 20210101_20260702
round17 manifest snapshot_suffix = 20210101_20260702
```

Note: target round17 has 3 rows, not the old snapshot's 4 rows. This is valid because the target package changed the upstream review queue. The verifier was updated to check consistency dynamically:

```text
summary.watch_state.rows == len(public/data/watch_states.json) > 0
```

and still requires expected states:

```text
等待降溫
中性等待
```

## Export command

```text
python scripts/export_dashboard_data.py \
  --snapshot-suffix 20210101_20260702 \
  --data-through 2026-07-02
```

## Package verifier

```text
python scripts/verify_magic26_package.py \
  --snapshot-suffix 20210101_20260702 \
  --data-through 2026-07-02 \
  --app-cache-bust 20260702riskv2 \
  --css-cache-bust 20260701q
```

Result:

```text
ok magic26 package 2026-07-02 latest 2026-06-26
```

## Data checks

Summary:

```text
data_through = 2026-07-02
latest_signal_date = 2026-06-26
total_candidate_rows = 311
latest_signal_groups = 1
watch_state.rows = 3
watch_state.state_counts = {'中性等待': 2, '等待降溫': 1}
```

K-line representative stock 6213:

```text
public/data/kline/raw_6213.json last_date = 2026-07-02
public/data/kline/adj_6213.json last_date = 2026-07-02
```

6213 risk_v2 representative check:

```text
risk_v2_level = 2
risk_v2_label_zh = 高追高 / 只觀察
risk_v2_is_display_only = true
```

Round CSV package checks:

```text
public/data/magic26_round17_b_retest_rearm_watch_20210101_20260702.csv exists
public/data/magic26_round19_author_absorption_detail_20210101_20260702.csv exists
public/data/magic26_round21_volgap_rescue_summary_20210101_20260702.csv exists
```

## Browser QA

Local server:

```text
python -m http.server 8787 --directory public
```

URL:

```text
http://127.0.0.1:8787/?v=p5-7-20260702
```

Observed page text:

```text
資料日期正常。
資料算到 2026-07-02；最近一次找到候選是 2026-06-26。
今日主清單 1 檔
6213 聯茂
只觀察｜已偏追高｜97分
```

Detail panel:

```text
K 線圖: 原始價｜2024-05-10～2026-07-02｜收 358.50
risk text: 只觀察；已偏追高，不建議直接追價
```

Console check:

```text
console_messages = 0
js_errors = 0
```

Programmatic browser check:

```json
{
  "data_through": "2026-07-02",
  "latest_signal_date": "2026-06-26",
  "total_candidate_rows": 311,
  "rawLast": "2026-07-02",
  "adjLast": "2026-07-02",
  "latest6213": {
    "risk_v2_level": 2,
    "risk_v2_label_zh": "高追高 / 只觀察",
    "display": true
  }
}
```

## Result

P5-7 succeeded locally. The local dashboard package now represents:

```text
data_through = 2026-07-02
latest_signal_date = 2026-06-26
```

This distinction is important: the data/K-line has refreshed through 2026-07-02, but the strategy did not find a newer qualifying candidate than 2026-06-26.

## Recommended next step

P5-8 should be deploy preflight + push/deploy production QA, still with explicit checks:

1. Final local gates.
2. Push local commits.
3. Run Cloudflare deploy with:

```text
--data-through 2026-07-02
--snapshot-suffix 20210101_20260702
--app-cache-bust 20260702riskv2
```

4. Verify production HTTP and browser:

```text
data_through = 2026-07-02
latest_signal_date = 2026-06-26
6213 risk_v2 level 2
K-line last date = 2026-07-02
console errors = 0
```

5. Only after P5-8 should cron scheduling be considered.
