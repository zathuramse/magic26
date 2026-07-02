# Magic26 P5-1 daily refresh probe

run_at: 2026-07-02T16:44:33
mode: dry-run

## Decision

- current_dashboard_data_through: `2026-06-30`
- complete_data_through: `2026-07-02`
- should_refresh: `True`
- can_auto_refresh_now: `False`

## Probe days

- `2026-07-02` complete=True raw_rows=40874 adj_rows=1818 bench_rows=1
- `2026-07-01` complete=True raw_rows=40779 adj_rows=2768 bench_rows=1

## Blockers

- Refresh needed, but full automatic regeneration is not enabled yet because scripts still contain hard-coded snapshot suffix/date refs.
- Found 75 hard-coded snapshot/date refs in scripts; parameterize before unattended refresh.
- Dry-run mode: no cache/export/deploy side effects were executed.

## Next steps

- Parameterize snapshot suffix/date in export, verifier, deploy, kline cache paths, and round scripts.
- Replace one-off extend_magic26_cache_to_20260701.py with generic cache extension from current suffix to complete_data_through.
- Add guarded full-run mode: regenerate raw/adjusted base outputs, dependent rounds, export, verifier, commit/push/deploy only when complete_data_through advances.
- Only after a successful full-run manual test, schedule 08:00 and 16:00 weekday cron jobs.
