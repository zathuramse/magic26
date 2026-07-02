# Magic26 daily refresh probe

run_at: 2026-07-02T17:09:46
mode: dry-run

## Decision

- current_snapshot_suffix: `20210101_20260701`
- target_snapshot_suffix: `20210101_20260702`
- current_dashboard_data_through: `2026-06-30`
- complete_data_through: `2026-07-02`
- should_refresh: `True`
- can_auto_refresh_now: `False`

## Probe days

- `2026-07-02` complete=True raw_rows=40874 adj_rows=2449 bench_rows=1
- `2026-07-01` complete=True raw_rows=40779 adj_rows=2768 bench_rows=1

## Blockers

- Refresh needed, but full automatic regeneration is not enabled yet because round/cache regeneration scripts still contain snapshot-specific refs.
- Found 22 remaining snapshot/date refs in round/cache scripts; parameterize before unattended refresh.
- Dry-run mode: no cache/export/deploy side effects were executed.

## Next steps

- Parameterize round/cache regeneration scripts that still contain snapshot-specific refs.
- Replace one-off extend_magic26_cache_to_20260701.py with generic cache extension from current_snapshot_suffix to target_snapshot_suffix.
- Add guarded full-run mode: regenerate raw/adjusted base outputs, dependent rounds, export, verifier, commit/push/deploy only when complete_data_through advances.
- Only after a successful full-run manual test, schedule 08:00 and 16:00 weekday cron jobs.
