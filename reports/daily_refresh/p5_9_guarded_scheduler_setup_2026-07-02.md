# P5-9 Magic26 guarded scheduler setup

Date: 2026-07-02

## Scope

P5-9 adds a guarded daily refresh/deploy runner and prepares Hermes cron scheduling.

The key rule is: do not schedule a deploy-only command. The scheduled job must first prove that a newer complete trading day exists.

## Added scripts

Project runner:

```text
scripts/magic26_guarded_refresh_deploy.py
```

Hermes cron wrapper:

```text
C:/Users/abckf/AppData/Local/hermes/profiles/jojo/scripts/magic26_guarded_refresh_cron.py
```

The cron wrapper calls the project runner and is intentionally silent when the dashboard is already up to date.

## Guard logic

The project runner:

1. Probes FinMind raw + adjusted + TAIEX benchmark completeness.
2. Reads current dashboard state from `public/data/summary.json` and `data/processed/export_manifest.json`.
3. Derives:

```text
current_dashboard_data_through
target complete_data_through
current_snapshot_suffix
target_snapshot_suffix
```

4. If no newer complete day exists:

```text
status = skipped_up_to_date
exit code = 0
stdout = empty in cron wrapper
```

5. If a newer complete day exists, it runs the full pipeline:

```text
extend_magic26_cache.py --refresh-daily
magic26_signal_pilot.py raw
magic26_signal_pilot.py adjusted
magic26_round4_execution_checks.py raw
magic26_round4_execution_checks.py adjusted
magic26_round7_param_grid.py
magic26_round8_tradeability_checks.py
magic26_round9_close_exit_checks.py
magic26_round14_bootstrap_path_review.py
magic26_round19_author_absorption.py
magic26_round20_60d_validation.py
magic26_round21_volgap_rescue_review.py
export_dashboard_data.py interim
magic26_round15_priority_review_pack.py
magic26_round16_top10_manual_review.py
magic26_round17_b_retest_rearm_watch.py
export_dashboard_data.py final
verify_magic26_package.py
git add / commit / push
deploy_cloudflare.py
```

Round15/16/17 are intentionally after an interim export because round15 consumes the dashboard candidate history CSV.

## Runtime reports

Cron/runtime reports are written under:

```text
reports/daily_refresh/runtime/
```

This path is ignored in git:

```text
reports/daily_refresh/runtime/
```

Reason: if every skip run writes a tracked/untracked report into the repo, the worktree becomes dirty and the next real refresh would correctly refuse to run. Runtime reports must not dirty the repo.

## Current dry-run / skip verification

Current production state:

```text
current_dashboard_data_through = 2026-07-02
complete_data_through = 2026-07-02
current_snapshot_suffix = 20210101_20260702
target_snapshot_suffix = 20210101_20260702
should_refresh = false
```

Manual verbose dry-run result:

```json
{
  "status": "skipped_up_to_date",
  "current_dashboard_data_through": "2026-07-02",
  "complete_data_through": "2026-07-02",
  "target_snapshot_suffix": "20210101_20260702",
  "message": "Dashboard already matches latest complete data."
}
```

Cron wrapper skip test:

```text
cron_stdout_bytes = 0
```

This is intended: no Telegram noise when the dashboard is already current.

Worktree after wrapper skip test did not gain runtime report files because `reports/daily_refresh/runtime/` is ignored.

## Validation commands

Passed:

```text
python -m py_compile scripts/magic26_guarded_refresh_deploy.py C:/Users/abckf/AppData/Local/hermes/profiles/jojo/scripts/magic26_guarded_refresh_cron.py
python scripts/magic26_guarded_refresh_deploy.py --dry-run --verbose --lookback-days 10 --stop-after-complete 2
python C:/Users/abckf/AppData/Local/hermes/profiles/jojo/scripts/magic26_guarded_refresh_cron.py > reports/daily_refresh/runtime/cron_stdout_test.txt
```

## Scheduling plan

Create two Hermes no-agent cron jobs:

```text
08:00 Monday-Friday
16:00 Monday-Friday
```

Both call:

```text
magic26_guarded_refresh_cron.py
```

Recommended delivery:

```text
origin
```

Because no-agent cron with empty stdout is silent, QQ receives a message only when:

- a real refresh/deploy happened, or
- the script failed and Hermes reports the non-zero exit.

## Known limitation

The full refresh path has been implemented and syntax-tested, but it has not yet been exercised against a newer trading day because production is already current through 2026-07-02. The safe behaviour for the current state is verified: skip silently.

The first real post-2026-07-02 refresh should be monitored via cron output and production QA.
