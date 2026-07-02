# P5-8 Magic26 production deploy QA

Date: 2026-07-02

## Scope

P5-8 pushed the completed daily-refresh local package and deployed Magic26 production.

No cron scheduling was performed in this phase.

## GitHub push

Pre-push local state:

```text
main...origin/main [ahead 7]
```

Pushed commits through:

```text
a8d8dd3 Refresh Magic26 local dashboard package
```

GitHub read-back:

```json
{
  "sha": "a8d8dd36a2d90e62165b3c83e2d38e1df465edf4",
  "message": "Refresh Magic26 local dashboard package",
  "date": "2026-07-02T10:55:40Z"
}
```

Post-push sync:

```text
origin/main...HEAD = 0 0
```

## Preflight checks

Passed:

```text
python -m py_compile scripts/deploy_cloudflare.py scripts/verify_magic26_package.py scripts/export_dashboard_data.py scripts/daily_refresh_magic26.py scripts/extend_magic26_cache.py scripts/magic26_signal_pilot.py scripts/magic26_round4_execution_checks.py scripts/magic26_round7_param_grid.py scripts/magic26_round8_tradeability_checks.py scripts/magic26_round9_close_exit_checks.py scripts/magic26_round14_bootstrap_path_review.py scripts/magic26_round15_priority_review_pack.py scripts/magic26_round16_top10_manual_review.py scripts/magic26_round17_b_retest_rearm_watch.py scripts/magic26_round19_author_absorption.py scripts/magic26_round20_60d_validation.py scripts/magic26_round21_volgap_rescue_review.py

python scripts/verify_magic26_package.py \
  --snapshot-suffix 20210101_20260702 \
  --data-through 2026-07-02 \
  --app-cache-bust 20260702riskv2 \
  --css-cache-bust 20260701q

node --check public/app.js
git diff --check
```

Verifier result:

```text
ok magic26 package 2026-07-02 latest 2026-06-26
```

Secret/large-file scan summary:

```text
changed_files = 346
large_files = []
forbidden_files = []
```

Keyword hits were inspected manually; they were code constants / documentation strings / masked examples, not real credentials.

## Cloudflare deploy

Command:

```text
python scripts/deploy_cloudflare.py \
  --project-name magic26 \
  --data-through 2026-07-02 \
  --snapshot-suffix 20210101_20260702 \
  --app-cache-bust 20260702riskv2 \
  --css-cache-bust 20260701q
```

Deployment result:

```text
Deployment complete
Production deployment: https://c724a86b.magic26.pages.dev
Source commit: a8d8dd3
```

Canonical URL:

```text
https://magic26.pages.dev/?v=20260702riskv2
```

Per-deployment URL:

```text
https://c724a86b.magic26.pages.dev
```

## Deploy-script production verification

Deploy script verified canonical production:

```json
{
  "url": "https://magic26.pages.dev/?v=20260702riskv2",
  "data_through": "2026-07-02",
  "latest_signal_date": "2026-06-26",
  "total_candidate_rows": 311,
  "latest_signal_groups": 1
}
```

## Independent HTTP QA

Checked both:

```text
https://magic26.pages.dev
https://c724a86b.magic26.pages.dev
```

Both passed:

```text
HTML status 200
app.js?v=20260702riskv2 present
styles.css?v=20260701q present
summary.data_through = 2026-07-02
summary.latest_signal_date = 2026-06-26
summary.total_candidate_rows = 311
summary.watch_state.rows = 3
raw_6213 last date = 2026-07-02
adj_6213 last date = 2026-07-02
latest_signal_groups 6213 risk_v2_level = 2
latest_signal_groups 6213 risk_v2_label_zh = 高追高 / 只觀察
latest_signal_groups 6213 risk_v2_is_display_only = true
```

CSV availability checks:

```text
magic26_round17_b_retest_rearm_watch_20210101_20260702.csv rows incl header = 4
magic26_round19_author_absorption_detail_20210101_20260702.csv rows incl header = 97
magic26_round21_volgap_rescue_summary_20210101_20260702.csv rows incl header = 25
```

## Production browser QA

URL:

```text
https://magic26.pages.dev/?v=20260702riskv2-p58
```

Observed page:

```text
資料日期正常。
資料算到 2026-07-02；最近一次找到候選是 2026-06-26。
今日主清單 1 檔
6213 聯茂
只觀察｜已偏追高｜97分
```

Browser probe result:

```json
{
  "pageTextOk": true,
  "detailTextOk": true,
  "summary": {
    "data_through": "2026-07-02",
    "latest_signal_date": "2026-06-26",
    "total_candidate_rows": 311,
    "watch_state": {
      "rows": 3,
      "state_counts": {
        "中性等待": 2,
        "等待降溫": 1
      }
    }
  },
  "rawLast": "2026-07-02",
  "adjLast": "2026-07-02",
  "latest6213": {
    "date": "2026-06-26",
    "risk_v2_level": 2,
    "risk_v2_label_zh": "高追高 / 只觀察",
    "display": true
  }
}
```

Console:

```text
console_messages = 0
js_errors = 0
```

## Result

P5-8 succeeded. Production Magic26 now serves the 2026-07-02 data package.

Important interpretation:

```text
Data/K-line through: 2026-07-02
Latest qualifying Magic26 candidate signal: 2026-06-26
```

This is expected: the refresh found no newer qualifying candidate after 2026-06-26.

## Recommended next step

P5-9 should add guarded scheduling, but not as a blind deploy cron. It should run the full pipeline with completeness checks:

1. Probe raw + adjusted + benchmark completeness.
2. If `complete_data_through <= current dashboard data_through`, skip quietly.
3. If data is complete and newer, run cache extension, signal regeneration, downstream rounds, export, verifier, deploy.
4. Keep 8:00 and 16:00 schedules, but require completeness guards before deployment.
5. Record logs/report artifacts for every run.
