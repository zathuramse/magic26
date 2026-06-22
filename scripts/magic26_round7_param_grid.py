from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd

ROOT = Path("C:/Users/abckf/research-brain")
OUT = ROOT / "sources/strategy-checks/magic26/out"

INPUTS = {
    "raw": OUT / "magic26_round4_checked_signals_round6_regime_all_liquid30000000_raw_20210101_20260622.csv",
    "adj": OUT / "magic26_round4_checked_signals_round6_regime_all_liquid30000000_adj_20210101_20260622.csv",
}

REPO_THRESHOLDS = [0.40, 0.50, 0.60]
C4_CAPS = [0.25, 0.40, 0.60]
C5_EXCLUDE_DAYS = [3, 5, 8]


def summarize(frame: pd.DataFrame, signal: pd.Series) -> dict:
    s = frame.loc[signal].copy()
    row: dict[str, object] = {"signals": int(len(s))}
    for h in [20, 60]:
        col = f"t1_open_excess_{h}d"
        vals = s[col].replace([np.inf, -np.inf], np.nan).dropna()
        row[f"n_{h}d"] = int(len(vals))
        row[f"avg_{h}d"] = float(vals.mean()) if len(vals) else np.nan
        row[f"median_{h}d"] = float(vals.median()) if len(vals) else np.nan
        row[f"win_{h}d"] = float((vals > 0).mean()) if len(vals) else np.nan
    row["pct_signal_day_gt9"] = float(s["risk_signal_day_gt9"].mean()) if len(s) else np.nan
    row["pct_next_gap_gt3"] = float(s["risk_next_gap_gt3"].mean()) if len(s) else np.nan
    return row


def make_signals(df: pd.DataFrame) -> dict[str, pd.Series]:
    core = df["c1_cross_confirm"] & df["c2_range_strength"] & df["c3_xq_exact_proxy"]
    regime = df["regime_all3"].astype(bool)
    signals: dict[str, pd.Series] = {}

    signals["core_c1c2c3_regime"] = regime & core

    for repo_th in REPO_THRESHOLDS:
        repo_ok = df["top5_volume_ratio_120"].between(repo_th, 1.00, inclusive="both")
        name = f"core_repo{int(repo_th * 100)}_regime"
        signals[name] = regime & core & repo_ok

    for c4_cap in C4_CAPS:
        c4_ok = (df["ret_20d"] > 0) & (df["ret_20d"] < c4_cap)
        for c5_days in C5_EXCLUDE_DAYS:
            c5_ok = (df["days_since_max_volume"] > c5_days) & (df["days_since_max_volume"] < 120)
            name = f"magic_c4{int(c4_cap * 100)}_c5gt{c5_days}_regime"
            signals[name] = regime & core & c4_ok & c5_ok
            for repo_th in REPO_THRESHOLDS:
                repo_ok = df["top5_volume_ratio_120"].between(repo_th, 1.00, inclusive="both")
                rname = f"magic_repo{int(repo_th * 100)}_c4{int(c4_cap * 100)}_c5gt{c5_days}_regime"
                signals[rname] = regime & core & repo_ok & c4_ok & c5_ok
    return signals


def main() -> None:
    all_summary = []
    all_yearly = []
    for price_mode, path in INPUTS.items():
        df = pd.read_csv(path)
        for col in ["date"]:
            df[col] = pd.to_datetime(df[col])
        for col in [
            "c1_cross_confirm", "c2_range_strength", "c3_xq_exact_proxy", "regime_all3",
            "risk_signal_day_gt9", "risk_next_gap_gt3",
        ]:
            df[col] = df[col].astype(bool)
        signals = make_signals(df)
        for name, mask in signals.items():
            row = {"price_mode": price_mode, "signal": name, **summarize(df, mask)}
            all_summary.append(row)
            for year, part in df.groupby("year"):
                ymask = mask.loc[part.index]
                yrow = {"price_mode": price_mode, "year": int(year), "signal": name, **summarize(part, ymask)}
                all_yearly.append(yrow)

    summary = pd.DataFrame(all_summary)
    yearly = pd.DataFrame(all_yearly)

    # Robustness score is intentionally simple and conservative: reward median/win, penalize tiny samples.
    summary["score_20d"] = (
        summary["median_20d"].fillna(-999)
        + (summary["win_20d"].fillna(0) - 0.5) * 0.20
        + np.minimum(summary["signals"], 80) / 80 * 0.02
    )

    summary_path = OUT / "magic26_round7_param_grid_summary_20210101_20260622.csv"
    yearly_path = OUT / "magic26_round7_param_grid_yearly_20210101_20260622.csv"
    top_path = OUT / "magic26_round7_param_grid_top_20210101_20260622.csv"
    manifest_path = OUT / "magic26_round7_param_grid_manifest_20210101_20260622.json"

    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    yearly.to_csv(yearly_path, index=False, encoding="utf-8-sig")

    # Keep only variants that exist in both raw and adjusted; rank by average of raw/adj 20D median and win.
    pivot = summary.pivot(index="signal", columns="price_mode", values=["signals", "avg_20d", "median_20d", "win_20d", "avg_60d", "median_60d", "win_60d", "pct_signal_day_gt9", "pct_next_gap_gt3"])
    flat = []
    for signal in pivot.index:
        item = {"signal": signal}
        for metric in ["signals", "avg_20d", "median_20d", "win_20d", "avg_60d", "median_60d", "win_60d", "pct_signal_day_gt9", "pct_next_gap_gt3"]:
            for mode in ["raw", "adj"]:
                item[f"{mode}_{metric}"] = pivot.loc[signal, (metric, mode)] if (metric, mode) in pivot.columns else np.nan
        item["avg_raw_adj_median_20d"] = np.nanmean([item["raw_median_20d"], item["adj_median_20d"]])
        item["avg_raw_adj_win_20d"] = np.nanmean([item["raw_win_20d"], item["adj_win_20d"]])
        item["min_raw_adj_signals"] = np.nanmin([item["raw_signals"], item["adj_signals"]])
        item["rank_score"] = item["avg_raw_adj_median_20d"] + (item["avg_raw_adj_win_20d"] - 0.5) * 0.20 + min(item["min_raw_adj_signals"], 80) / 80 * 0.02
        flat.append(item)
    top = pd.DataFrame(flat).sort_values("rank_score", ascending=False)
    top.to_csv(top_path, index=False, encoding="utf-8-sig")

    manifest = {
        "inputs": {k: str(v) for k, v in INPUTS.items()},
        "assumptions": [
            "All variants require regime_all3=True.",
            "Entry metric is t+1 open excess vs TAIEX.",
            "Main horizon is 20D; 60D is secondary.",
            "This is a small robustness grid, not best-parameter optimization.",
        ],
        "repo_thresholds": REPO_THRESHOLDS,
        "c4_caps": C4_CAPS,
        "c5_exclude_days": C5_EXCLUDE_DAYS,
        "outputs": {
            "summary": str(summary_path),
            "yearly": str(yearly_path),
            "top": str(top_path),
        },
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    pd.set_option("display.max_columns", 50)
    print(top.head(15).to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print(f"saved summary: {summary_path}")
    print(f"saved yearly: {yearly_path}")
    print(f"saved top: {top_path}")
    print(f"saved manifest: {manifest_path}")


if __name__ == "__main__":
    main()
