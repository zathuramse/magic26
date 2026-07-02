from __future__ import annotations

from pathlib import Path
import argparse
import json

import numpy as np
import pandas as pd

ROOT = Path("C:/Users/abckf/research-brain")
BASE = ROOT / "sources/strategy-checks/magic26"
OUT = BASE / "out"
CACHE = BASE / "cache"
DEFAULT_SNAPSHOT_SUFFIX = "20210101_20260701"


def build_inputs(snapshot_suffix: str) -> dict[str, Path]:
    return {
        "raw": OUT / f"magic26_round4_checked_signals_round6_regime_all_liquid30000000_raw_{snapshot_suffix}.csv",
        "adj": OUT / f"magic26_round4_checked_signals_round6_regime_all_liquid30000000_adj_{snapshot_suffix}.csv",
    }

CANDIDATES = {
    "candidate_a_repo50_c440_c5gt5": {
        "repo_min": 0.50,
        "c4_cap": 0.40,
        "c5_days": 5,
    },
    "candidate_b_magic_c440_c5gt5": {
        "repo_min": None,
        "c4_cap": 0.40,
        "c5_days": 5,
    },
    "candidate_c_high_concentration_c425_c5gt5": {
        "repo_min": None,
        "c4_cap": 0.25,
        "c5_days": 5,
    },
}


def candidate_mask(df: pd.DataFrame, spec: dict) -> pd.Series:
    core = (
        df["regime_all3"].astype(bool)
        & df["c1_cross_confirm"].astype(bool)
        & df["c2_range_strength"].astype(bool)
        & df["c3_xq_exact_proxy"].astype(bool)
        & (df["ret_20d"] > 0)
        & (df["ret_20d"] < spec["c4_cap"])
        & (df["days_since_max_volume"] > spec["c5_days"])
        & (df["days_since_max_volume"] < 120)
    )
    if spec["repo_min"] is not None:
        core = core & df["top5_volume_ratio_120"].between(spec["repo_min"], 1.00, inclusive="both")
    return core


def load_price(mode: str, stock_id: str, snapshot_suffix: str) -> pd.DataFrame | None:
    path = CACHE / f"{mode}_{stock_id}_{snapshot_suffix}.parquet"
    if not path.exists():
        return None
    p = pd.read_parquet(path)
    p["date"] = pd.to_datetime(p["date"])
    for col in ["open", "max", "min", "close"]:
        p[col] = pd.to_numeric(p[col], errors="coerce")
    return p.sort_values("date").reset_index(drop=True)


def path_metrics(price: pd.DataFrame, signal_date: pd.Timestamp) -> dict:
    idxs = price.index[price["date"] == signal_date]
    if len(idxs) == 0:
        return {"path_error": "signal_date_not_found"}
    i = int(idxs[0])
    entry_i = i + 1
    exit_i = i + 21
    if exit_i >= len(price):
        return {"path_error": "insufficient_forward_bars"}
    entry = float(price.loc[entry_i, "open"])
    if not np.isfinite(entry) or entry <= 0:
        return {"path_error": "bad_entry_open"}
    path = price.loc[entry_i:exit_i].copy()
    fixed20 = float(price.loc[exit_i, "close"] / entry - 1)
    mfe20 = float(path["max"].max() / entry - 1)
    mae20 = float(path["min"].min() / entry - 1)

    def first_hit_return(tp: float | None, sl: float | None) -> tuple[float, str, int]:
        for n, (_, row) in enumerate(path.iterrows(), start=1):
            hit_sl = sl is not None and float(row["min"]) <= entry * (1 + sl)
            hit_tp = tp is not None and float(row["max"]) >= entry * (1 + tp)
            # Conservative ambiguity rule: if both are hit in the same daily bar, assume stop first.
            if hit_sl:
                return float(sl), f"sl{int(abs(sl)*100)}", n
            if hit_tp:
                return float(tp), f"tp{int(tp*100)}", n
        return fixed20, "fixed20", 20

    tp15_sl8_ret, tp15_sl8_reason, tp15_sl8_days = first_hit_return(0.15, -0.08)
    tp20_sl8_ret, tp20_sl8_reason, tp20_sl8_days = first_hit_return(0.20, -0.08)
    sl8_ret, sl8_reason, sl8_days = first_hit_return(None, -0.08)
    tp20_ret, tp20_reason, tp20_days = first_hit_return(0.20, None)

    return {
        "path_error": "",
        "entry_date": price.loc[entry_i, "date"],
        "exit20_date": price.loc[exit_i, "date"],
        "entry_open": entry,
        "fixed20_ret": fixed20,
        "mfe20": mfe20,
        "mae20": mae20,
        "hit_mae_le_minus8": mae20 <= -0.08,
        "hit_mfe_ge_15": mfe20 >= 0.15,
        "hit_mfe_ge_20": mfe20 >= 0.20,
        "tp15_sl8_ret": tp15_sl8_ret,
        "tp15_sl8_reason": tp15_sl8_reason,
        "tp15_sl8_days": tp15_sl8_days,
        "tp20_sl8_ret": tp20_sl8_ret,
        "tp20_sl8_reason": tp20_sl8_reason,
        "tp20_sl8_days": tp20_sl8_days,
        "sl8_ret": sl8_ret,
        "sl8_reason": sl8_reason,
        "sl8_days": sl8_days,
        "tp20_ret": tp20_ret,
        "tp20_reason": tp20_reason,
        "tp20_days": tp20_days,
    }


def summarize(df: pd.DataFrame) -> dict:
    row = {"signals": int(len(df))}
    if df.empty:
        return row
    for col in ["t1_open_excess_20d", "fixed20_ret", "mfe20", "mae20", "tp15_sl8_ret", "tp20_sl8_ret", "sl8_ret", "tp20_ret"]:
        vals = df[col].replace([np.inf, -np.inf], np.nan).dropna()
        row[f"avg_{col}"] = float(vals.mean()) if len(vals) else np.nan
        row[f"median_{col}"] = float(vals.median()) if len(vals) else np.nan
        row[f"win_{col}"] = float((vals > 0).mean()) if len(vals) else np.nan
    risk_cols = [
        "risk_signal_day_gt9", "risk_next_gap_gt3", "next_gap_gt5", "next_gap_gt7",
        "hit_mae_le_minus8", "hit_mfe_ge_15", "hit_mfe_ge_20",
    ]
    for col in risk_cols:
        row[f"pct_{col}"] = float(df[col].mean()) if col in df else np.nan
    for reason_col in ["tp15_sl8_reason", "tp20_sl8_reason"]:
        counts = df[reason_col].value_counts(normalize=True).to_dict() if reason_col in df else {}
        for key, value in counts.items():
            row[f"pct_{reason_col}_{key}"] = float(value)
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-suffix", default=DEFAULT_SNAPSHOT_SUFFIX)
    args = parser.parse_args()
    inputs = build_inputs(args.snapshot_suffix)

    detail_rows = []
    summary_rows = []
    failure_rows = []
    price_cache: dict[tuple[str, str], pd.DataFrame | None] = {}

    for mode, input_path in inputs.items():
        df = pd.read_csv(input_path)
        df["date"] = pd.to_datetime(df["date"])
        df["stock_id"] = df["stock_id"].astype(str).str.replace(r"\.0$", "", regex=True)
        df["next_gap_gt5"] = df["next_open_gap"] >= 0.05
        df["next_gap_gt7"] = df["next_open_gap"] >= 0.07

        for cand_name, spec in CANDIDATES.items():
            mask = candidate_mask(df, spec)
            cand = df.loc[mask].copy()
            rows = []
            for _, sig in cand.iterrows():
                stock_id = str(sig["stock_id"])
                key = (mode, stock_id)
                if key not in price_cache:
                    price_cache[key] = load_price(mode, stock_id, args.snapshot_suffix)
                price = price_cache[key]
                base = sig.to_dict()
                base["price_mode"] = mode
                base["candidate"] = cand_name
                if price is None:
                    base["path_error"] = "missing_price_cache"
                else:
                    base.update(path_metrics(price, sig["date"]))
                rows.append(base)
            cdf = pd.DataFrame(rows)
            if not cdf.empty:
                for col in ["hit_mae_le_minus8", "hit_mfe_ge_15", "hit_mfe_ge_20"]:
                    cdf[col] = cdf[col].map(lambda x: bool(x) if pd.notna(x) else False)
            detail_rows.append(cdf)
            valid = cdf[cdf.get("path_error", "") == ""] if not cdf.empty else cdf
            summary_rows.append({"price_mode": mode, "candidate": cand_name, **summarize(valid)})

            if not valid.empty:
                fail2024 = valid[(valid["year"] == 2024) & (valid["t1_open_excess_20d"] < 0)].copy()
                for industry, part in fail2024.groupby("industry_category", dropna=False):
                    failure_rows.append({
                        "price_mode": mode,
                        "candidate": cand_name,
                        "industry_category": industry,
                        "failures": int(len(part)),
                        "avg_t1_open_excess_20d": float(part["t1_open_excess_20d"].mean()),
                        "median_t1_open_excess_20d": float(part["t1_open_excess_20d"].median()),
                        "avg_next_open_gap": float(part["next_open_gap"].mean()),
                        "avg_signal_day_ret_1d": float(part["signal_day_ret_1d"].mean()),
                        "pct_signal_day_gt9": float(part["risk_signal_day_gt9"].mean()),
                        "pct_next_gap_gt3": float(part["risk_next_gap_gt3"].mean()),
                    })

    detail = pd.concat(detail_rows, ignore_index=True) if detail_rows else pd.DataFrame()
    summary = pd.DataFrame(summary_rows)
    failures = pd.DataFrame(failure_rows).sort_values(["price_mode", "candidate", "failures"], ascending=[True, True, False]) if failure_rows else pd.DataFrame()

    detail_path = OUT / f"magic26_round8_tradeability_detail_{args.snapshot_suffix}.csv"
    summary_path = OUT / f"magic26_round8_tradeability_summary_{args.snapshot_suffix}.csv"
    failures_path = OUT / f"magic26_round8_tradeability_2024_failures_by_industry_{args.snapshot_suffix}.csv"
    manifest_path = OUT / f"magic26_round8_tradeability_manifest_{args.snapshot_suffix}.json"

    detail.to_csv(detail_path, index=False, encoding="utf-8-sig")
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    failures.to_csv(failures_path, index=False, encoding="utf-8-sig")
    manifest = {
        "snapshot_suffix": args.snapshot_suffix,
        "inputs": {k: str(v) for k, v in inputs.items()},
        "candidates": CANDIDATES,
        "assumptions": [
            "Entry uses next trading day's open.",
            "Fixed20 uses close after 20 trading days from entry day.",
            "TP/SL simulations use daily high/low only; if take-profit and stop-loss are both touched in the same day, stop-loss is assumed first as a conservative ambiguity rule.",
            "Limit-up tradability is approximated from signal-day return and next-open gap; official intraday limit-up lock data is not available here.",
        ],
        "outputs": {
            "detail": str(detail_path),
            "summary": str(summary_path),
            "failures_by_industry": str(failures_path),
        },
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    pd.set_option("display.max_columns", 80)
    print(summary.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print(f"saved detail: {detail_path}")
    print(f"saved summary: {summary_path}")
    print(f"saved failures: {failures_path}")
    print(f"saved manifest: {manifest_path}")


if __name__ == "__main__":
    main()
