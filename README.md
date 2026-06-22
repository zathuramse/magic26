# Magic26

Magic26 is a reproducible Taiwan stock-screen research package and pull-only dashboard.

## What this is

- Research reconstruction of the Magic26/XQ screening logic.
- Backtest summaries and tradeability checks through 2026-06-22.
- A static Cloudflare Pages dashboard for candidate-list review.

## What this is not

- Not investment advice.
- Not an auto-trading system.
- Not a promise that historical results will persist.

## Current main observation spec

```text
regime_all3=True
C1+C2+C3
repo_vol5 >= 50%
0 < 20D return < 40%
days_since_max_volume > 5
t+1 open entry
fixed 20D close exit for research evaluation
```

## Layout

- `public/` — Cloudflare Pages static site.
- `public/data/` — dashboard JSON/CSV data bundle.
- `data/processed/` — packaged processed research outputs.
- `docs/reports/` — round-by-round research reports.
- `scripts/` — reproducible research scripts used to generate the outputs.

## Local preview

```bash
python -m http.server 8788 -d public
```

Then open `http://127.0.0.1:8788`.
