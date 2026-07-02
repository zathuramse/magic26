from __future__ import annotations

from pathlib import Path
import argparse
import json

import numpy as np
import pandas as pd

from magic26_paths import cache_dir, out_dir, research_root, source_root  # noqa: E402

ROOT = research_root()
BASE = source_root()
OUT = out_dir()
CACHE = cache_dir()
DEFAULT_SNAPSHOT_SUFFIX = "20210101_20260701"


def build_inputs(snapshot_suffix: str, round4_raw: str | None = None, round4_adj: str | None = None) -> dict[str, Path]:
    return {
        "raw": Path(round4_raw) if round4_raw else OUT / f"magic26_round4_checked_signals_round6_regime_all_liquid30000000_raw_{snapshot_suffix}.csv",
        "adj": Path(round4_adj) if round4_adj else OUT / f"magic26_round4_checked_signals_round6_regime_all_liquid30000000_adj_{snapshot_suffix}.csv",
    }

CANDIDATES = {
    "candidate_a_repo50_c440_c5gt5": {"repo_min": 0.50, "c4_cap": 0.40, "c5_days": 5},
    "candidate_b_magic_c440_c5gt5": {"repo_min": None, "c4_cap": 0.40, "c5_days": 5},
    "candidate_c_high_concentration_c425_c5gt5": {"repo_min": None, "c4_cap": 0.25, "c5_days": 5},
}

EXIT_RULES = [
    "fixed20",
    "close_sl8",
    "delayed3_close_sl8",
    "close_below_ma5",
    "delayed3_close_below_ma5",
    "close_below_ma10",
    "delayed3_close_below_ma10",
    "delayed3_ma10_or_sl8",
]


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
    p = p.sort_values("date").reset_index(drop=True)
    p["ma5"] = p["close"].rolling(5).mean()
    p["ma10"] = p["close"].rolling(10).mean()
    return p


def load_benchmark(snapshot_suffix: str) -> pd.DataFrame:
    path = CACHE / f"benchmark_TAIEX_{snapshot_suffix}.parquet"
    b = pd.read_parquet(path)
    b["date"] = pd.to_datetime(b["date"])
    for col in ["open", "close"]:
        b[col] = pd.to_numeric(b[col], errors="coerce")
    return b.sort_values("date").reset_index(drop=True)


def benchmark_return(bench: pd.DataFrame, entry_date: pd.Timestamp, exit_date: pd.Timestamp) -> float:
    entry = bench.loc[bench["date"] == entry_date]
    exit_ = bench.loc[bench["date"] == exit_date]
    if entry.empty or exit_.empty:
        return np.nan
    entry_open = float(entry.iloc[0]["open"])
    exit_close = float(exit_.iloc[0]["close"])
    if entry_open <= 0:
        return np.nan
    return exit_close / entry_open - 1


def find_exit(price: pd.DataFrame, signal_date: pd.Timestamp, rule: str) -> dict:
    idxs = price.index[price["date"] == signal_date]
    if len(idxs) == 0:
        return {"path_error": "signal_date_not_found"}
    i = int(idxs[0])
    entry_i = i + 1
    fixed_exit_i = i + 21
    if fixed_exit_i >= len(price):
        return {"path_error": "insufficient_forward_bars"}
    entry_open = float(price.loc[entry_i, "open"])
    if not np.isfinite(entry_open) or entry_open <= 0:
        return {"path_error": "bad_entry_open"}

    exit_i = fixed_exit_i
    reason = "fixed20"
    for j in range(entry_i, fixed_exit_i + 1):
        day_n = j - entry_i + 1
        close = float(price.loc[j, "close"])
        ma5 = float(price.loc[j, "ma5"])
        ma10 = float(price.loc[j, "ma10"])
        delayed_ok = day_n >= 4  # enter day is day1; hold 3 bars before activating delayed exits.
        hit = False
        if rule == "close_sl8":
            hit = close <= entry_open * 0.92
            reason = "close_sl8" if hit else reason
        elif rule == "delayed3_close_sl8":
            hit = delayed_ok and close <= entry_open * 0.92
            reason = "delayed3_close_sl8" if hit else reason
        elif rule == "close_below_ma5":
            hit = np.isfinite(ma5) and close < ma5
            reason = "close_below_ma5" if hit else reason
        elif rule == "delayed3_close_below_ma5":
            hit = delayed_ok and np.isfinite(ma5) and close < ma5
            reason = "delayed3_close_below_ma5" if hit else reason
        elif rule == "close_below_ma10":
            hit = np.isfinite(ma10) and close < ma10
            reason = "close_below_ma10" if hit else reason
        elif rule == "delayed3_close_below_ma10":
            hit = delayed_ok and np.isfinite(ma10) and close < ma10
            reason = "delayed3_close_below_ma10" if hit else reason
        elif rule == "delayed3_ma10_or_sl8":
            hit_ma10 = delayed_ok and np.isfinite(ma10) and close < ma10
            hit_sl8 = delayed_ok and close <= entry_open * 0.92
            hit = hit_ma10 or hit_sl8
            if hit:
                reason = "delayed3_close_sl8" if hit_sl8 else "delayed3_close_below_ma10"
        elif rule == "fixed20":
            hit = False
        else:
            raise ValueError(f"unknown rule: {rule}")
        if hit:
            exit_i = j
            break

    exit_close = float(price.loc[exit_i, "close"])
    ret = exit_close / entry_open - 1
    return {
        "path_error": "",
        "entry_date": price.loc[entry_i, "date"],
        "exit_date": price.loc[exit_i, "date"],
        "entry_open": entry_open,
        "exit_close": exit_close,
        "hold_days": int(exit_i - entry_i + 1),
        "exit_reason": reason,
        "return": float(ret),
    }


def summarize(df: pd.DataFrame) -> dict:
    row = {"trades": int(len(df))}
    if df.empty:
        return row
    for col in ["return", "excess"]:
        vals = df[col].replace([np.inf, -np.inf], np.nan).dropna()
        row[f"avg_{col}"] = float(vals.mean()) if len(vals) else np.nan
        row[f"median_{col}"] = float(vals.median()) if len(vals) else np.nan
        row[f"win_{col}"] = float((vals > 0).mean()) if len(vals) else np.nan
    row["avg_hold_days"] = float(df["hold_days"].mean())
    row["median_hold_days"] = float(df["hold_days"].median())
    row["pct_exit_before_20d"] = float((df["hold_days"] < 21).mean())
    reason_counts = df["exit_reason"].value_counts(normalize=True).to_dict()
    for reason, pct in reason_counts.items():
        row[f"pct_reason_{reason}"] = float(pct)
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-suffix", default=DEFAULT_SNAPSHOT_SUFFIX)
    parser.add_argument("--round4-raw", default=None, help="Override raw round4 checked-signal CSV path. Keeps default full-run naming when omitted.")
    parser.add_argument("--round4-adj", default=None, help="Override adjusted round4 checked-signal CSV path. Keeps default full-run naming when omitted.")
    args = parser.parse_args()
    inputs = build_inputs(args.snapshot_suffix, args.round4_raw, args.round4_adj)

    bench = load_benchmark(args.snapshot_suffix)
    price_cache: dict[tuple[str, str], pd.DataFrame | None] = {}
    detail_rows = []
    summary_rows = []
    year_rows = []

    for mode, input_path in inputs.items():
        df = pd.read_csv(input_path)
        df["date"] = pd.to_datetime(df["date"])
        df["stock_id"] = df["stock_id"].astype(str).str.replace(r"\.0$", "", regex=True)
        for cand_name, spec in CANDIDATES.items():
            signals = df.loc[candidate_mask(df, spec)].copy()
            for _, sig in signals.iterrows():
                stock_id = str(sig["stock_id"])
                key = (mode, stock_id)
                if key not in price_cache:
                    price_cache[key] = load_price(mode, stock_id, args.snapshot_suffix)
                price = price_cache[key]
                for rule in EXIT_RULES:
                    row = {
                        "price_mode": mode,
                        "candidate": cand_name,
                        "exit_rule": rule,
                        "signal_date": sig["date"],
                        "year": int(sig["year"]),
                        "stock_id": stock_id,
                        "stock_name": sig.get("stock_name", ""),
                        "industry_category": sig.get("industry_category", ""),
                    }
                    if price is None:
                        row["path_error"] = "missing_price_cache"
                    else:
                        row.update(find_exit(price, sig["date"], rule))
                        if row.get("path_error", "") == "":
                            brow = benchmark_return(bench, row["entry_date"], row["exit_date"])
                            row["bench_return"] = brow
                            row["excess"] = row["return"] - brow if np.isfinite(brow) else np.nan
                    detail_rows.append(row)

    detail = pd.DataFrame(detail_rows)
    if detail.empty or "path_error" not in detail.columns:
        valid = pd.DataFrame()
    else:
        valid = detail[detail["path_error"] == ""].copy()
    if not valid.empty and {"price_mode", "candidate", "exit_rule"}.issubset(valid.columns):
        for (mode, cand, rule), part in valid.groupby(["price_mode", "candidate", "exit_rule"]):
            summary_rows.append({"price_mode": mode, "candidate": cand, "exit_rule": rule, **summarize(part)})
    if not valid.empty and {"price_mode", "candidate", "exit_rule", "year"}.issubset(valid.columns):
        for (mode, cand, rule, year), part in valid.groupby(["price_mode", "candidate", "exit_rule", "year"]):
            year_rows.append({"price_mode": mode, "candidate": cand, "exit_rule": rule, "year": int(year), **summarize(part)})

    summary = pd.DataFrame(summary_rows)
    if not summary.empty:
        summary = summary.sort_values(["price_mode", "candidate", "median_excess"], ascending=[True, True, False])
    yearly = pd.DataFrame(year_rows)
    if not yearly.empty:
        yearly = yearly.sort_values(["price_mode", "candidate", "exit_rule", "year"])

    detail_path = OUT / f"magic26_round9_close_exit_detail_{args.snapshot_suffix}.csv"
    summary_path = OUT / f"magic26_round9_close_exit_summary_{args.snapshot_suffix}.csv"
    yearly_path = OUT / f"magic26_round9_close_exit_yearly_{args.snapshot_suffix}.csv"
    manifest_path = OUT / f"magic26_round9_close_exit_manifest_{args.snapshot_suffix}.json"
    detail.to_csv(detail_path, index=False, encoding="utf-8-sig")
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    yearly.to_csv(yearly_path, index=False, encoding="utf-8-sig")
    manifest = {
        "snapshot_suffix": args.snapshot_suffix,
        "inputs": {k: str(v) for k, v in inputs.items()},
        "candidates": CANDIDATES,
        "exit_rules": EXIT_RULES,
        "assumptions": [
            "Entry is next trading day's open.",
            "Variable exits use close-confirmed rules and exit at that day's close.",
            "Delayed3 exits start checking after holding 3 entry bars; first possible exit is day4 close.",
            "Excess return subtracts TAIEX open-to-close return over the same entry/exit dates.",
        ],
        "outputs": {"detail": str(detail_path), "summary": str(summary_path), "yearly": str(yearly_path)},
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    pd.set_option("display.max_columns", 80)
    print(summary.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print(f"saved detail: {detail_path}")
    print(f"saved summary: {summary_path}")
    print(f"saved yearly: {yearly_path}")
    print(f"saved manifest: {manifest_path}")


if __name__ == "__main__":
    main()
