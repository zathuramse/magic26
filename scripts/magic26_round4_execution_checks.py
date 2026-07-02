#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Round-4 sanity checks for Magic26 signals.

Reads signal rows emitted by magic26_signal_pilot.py and adds:
- benchmark-relative forward return vs TAIEX close-to-close;
- t+1 close entry forward return (already emitted by pilot after 2026-07-01 update);
- simple execution/risk flags available from daily data.

Research-only; not a trading system.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import magic26_signal_pilot as pilot  # noqa: E402
from magic26_paths import out_dir, source_root  # noqa: E402

ROOT = source_root()
OUT = out_dir()


def load_benchmark(start_date: str, end_date: str) -> pd.DataFrame:
    bench = pilot.finmind_get(
        "TaiwanStockPrice",
        f"benchmark_TAIEX_{start_date.replace('-', '')}_{end_date.replace('-', '')}.parquet",
        data_id="TAIEX",
        start_date=start_date,
        end_date=end_date,
        sleep_s=0,
    )
    if bench.empty:
        raise RuntimeError("No TAIEX benchmark rows returned")
    bench = bench.copy()
    bench["date"] = pd.to_datetime(bench["date"])
    bench["close"] = pd.to_numeric(bench["close"], errors="coerce")
    bench = bench.sort_values("date").reset_index(drop=True)
    bench["bench_ma20"] = bench["close"].rolling(20).mean()
    bench["bench_ma60"] = bench["close"].rolling(60).mean()
    bench["bench_ma120"] = bench["close"].rolling(120).mean()
    bench["regime_close_gt_ma60"] = bench["close"] > bench["bench_ma60"]
    bench["regime_ma20_gt_ma60"] = bench["bench_ma20"] > bench["bench_ma60"]
    bench["regime_close_gt_ma120"] = bench["close"] > bench["bench_ma120"]
    bench["regime_all3"] = bench["regime_close_gt_ma60"] & bench["regime_ma20_gt_ma60"] & bench["regime_close_gt_ma120"]
    bench["regime_any2"] = (
        bench[["regime_close_gt_ma60", "regime_ma20_gt_ma60", "regime_close_gt_ma120"]].sum(axis=1) >= 2
    )
    for h in [5, 20, 60]:
        bench[f"bench_fwd_{h}d"] = bench["close"].shift(-h) / bench["close"] - 1
        bench[f"bench_t1_close_fwd_{h}d"] = bench["close"].shift(-(h + 1)) / bench["close"].shift(-1) - 1
        bench[f"bench_t1_open_fwd_{h}d"] = bench["close"].shift(-(h + 1)) / bench["open"].shift(-1) - 1
    keep = [
        "date", "close", "bench_ma20", "bench_ma60", "bench_ma120",
        "regime_close_gt_ma60", "regime_ma20_gt_ma60", "regime_close_gt_ma120", "regime_all3", "regime_any2",
        "bench_fwd_5d", "bench_fwd_20d", "bench_fwd_60d",
        "bench_t1_close_fwd_5d", "bench_t1_close_fwd_20d", "bench_t1_close_fwd_60d",
        "bench_t1_open_fwd_5d", "bench_t1_open_fwd_20d", "bench_t1_open_fwd_60d",
    ]
    return bench[keep].rename(columns={"close": "bench_close"})


def summarize(df: pd.DataFrame, signal_col: str) -> dict:
    s = df[df[signal_col]].copy()
    row = {"signal": signal_col, "signals": int(len(s))}
    for h in [20, 60]:
        raw_col = f"fwd_{h}d"
        rel_col = f"excess_{h}d"
        t1_col = f"t1_close_fwd_{h}d"
        t1_rel_col = f"t1_excess_{h}d"
        t1_open_col = f"t1_open_fwd_{h}d"
        t1_open_rel_col = f"t1_open_excess_{h}d"
        for prefix, col in [("raw", raw_col), ("excess", rel_col), ("t1", t1_col), ("t1_excess", t1_rel_col), ("t1_open", t1_open_col), ("t1_open_excess", t1_open_rel_col)]:
            vals = s[col].dropna()
            row[f"n_{prefix}_{h}d"] = int(len(vals))
            row[f"avg_{prefix}_{h}d"] = float(vals.mean()) if len(vals) else np.nan
            row[f"median_{prefix}_{h}d"] = float(vals.median()) if len(vals) else np.nan
            row[f"win_{prefix}_{h}d"] = float((vals > 0).mean()) if len(vals) else np.nan
    row["avg_signal_day_ret_1d"] = float(s["signal_day_ret_1d"].mean()) if len(s) else np.nan
    row["pct_signal_day_gt9"] = float((s["signal_day_ret_1d"] >= 0.09).mean()) if len(s) else np.nan
    row["pct_next_gap_gt3"] = float((s["next_open_gap"] >= 0.03).mean()) if len(s) else np.nan
    row["pct_next_gap_lt_minus3"] = float((s["next_open_gap"] <= -0.03).mean()) if len(s) else np.nan
    row["pct_low_liquidity_lt100m"] = float((s["avg_amount_20d"] < 100_000_000).mean()) if len(s) else np.nan
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--signals", required=True)
    parser.add_argument("--start-date", default="2021-01-01")
    parser.add_argument("--end-date", default="2026-07-01")
    parser.add_argument("--run-label", required=True)
    parser.add_argument("--signals-to-check", default="c1_c2,c1_c2_c3,magic26_v0,magic26_v0_quality")
    args = parser.parse_args()

    path = Path(args.signals)
    sig = pd.read_csv(path)
    if sig.empty:
        raise SystemExit("Empty signals file")
    sig["date"] = pd.to_datetime(sig["date"])
    bench = load_benchmark(args.start_date, args.end_date)
    merged = sig.merge(bench, on="date", how="left")

    for h in [5, 20, 60]:
        merged[f"excess_{h}d"] = merged[f"fwd_{h}d"] - merged[f"bench_fwd_{h}d"]
        merged[f"t1_excess_{h}d"] = merged[f"t1_close_fwd_{h}d"] - merged[f"bench_t1_close_fwd_{h}d"]
        merged[f"t1_open_excess_{h}d"] = merged[f"t1_open_fwd_{h}d"] - merged[f"bench_t1_open_fwd_{h}d"]
    merged = merged.replace([np.inf, -np.inf], np.nan)

    merged["risk_signal_day_gt9"] = merged["signal_day_ret_1d"] >= 0.09
    merged["risk_next_gap_gt3"] = merged["next_open_gap"] >= 0.03
    merged["risk_next_gap_lt_minus3"] = merged["next_open_gap"] <= -0.03
    merged["risk_liquidity_lt100m"] = merged["avg_amount_20d"] < 100_000_000

    signal_cols = [x.strip() for x in args.signals_to_check.split(",") if x.strip()]
    summary = pd.DataFrame([summarize(merged, col) for col in signal_cols])
    yearly_rows = []
    for year, part in merged.groupby(merged["date"].dt.year):
        for col in signal_cols:
            r = summarize(part, col)
            r = {"year": int(year), **r}
            yearly_rows.append(r)
    yearly = pd.DataFrame(yearly_rows)

    regime_rows = []
    regime_cols = ["regime_close_gt_ma60", "regime_ma20_gt_ma60", "regime_close_gt_ma120", "regime_any2", "regime_all3"]
    for regime_col in regime_cols:
        for regime_value, part in merged.groupby(regime_col, dropna=False):
            for col in signal_cols:
                r = summarize(part, col)
                r = {"regime": regime_col, "regime_value": bool(regime_value), **r}
                regime_rows.append(r)
    regime = pd.DataFrame(regime_rows)

    checked_path = OUT / f"magic26_round4_checked_signals_{args.run_label}.csv"
    summary_path = OUT / f"magic26_round4_summary_{args.run_label}.csv"
    yearly_path = OUT / f"magic26_round4_yearly_{args.run_label}.csv"
    regime_path = OUT / f"magic26_round4_regime_{args.run_label}.csv"
    manifest_path = OUT / f"magic26_round4_manifest_{args.run_label}.json"
    merged.to_csv(checked_path, index=False, encoding="utf-8-sig")
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    yearly.to_csv(yearly_path, index=False, encoding="utf-8-sig")
    regime.to_csv(regime_path, index=False, encoding="utf-8-sig")
    manifest = {
        "run_label": args.run_label,
        "source_signals": str(path),
        "rows": int(len(merged)),
        "benchmark": "TAIEX via FinMind TaiwanStockPrice data_id=TAIEX",
        "outputs": {
            "checked_signals": str(checked_path),
            "summary": str(summary_path),
            "yearly": str(yearly_path),
            "regime": str(regime_path),
        },
        "notes": [
            "t1_close_fwd_* uses next trading day's close as entry proxy, not next open.",
            "Risk flags are daily-data proxies only: signal-day >=9%, next-open gap +/-3%, and 20D average amount <100m.",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(summary.to_string(index=False))
    print(f"saved checked signals: {checked_path}")
    print(f"saved summary: {summary_path}")
    print(f"saved yearly: {yearly_path}")
    print(f"saved regime: {regime_path}")
    print(f"saved manifest: {manifest_path}")


if __name__ == "__main__":
    main()
