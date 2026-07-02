#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Magic26 v0 research-only signal checker/backtest pilot.

This is NOT a trading system. It converts the five Facebook/XQ conditions into
verifiable daily-data rules and reports signal counts + forward-return sanity checks.

Defaults intentionally run on a small stock list first. Use --stock-ids or --max-stocks
for wider probes after confirming the rule definitions.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import requests

BASE = "https://api.finmindtrade.com/api/v4/data"
from magic26_paths import cache_dir, out_dir, source_root  # noqa: E402

ROOT = source_root()
CACHE = cache_dir()
OUT = out_dir()
ENV_CANDIDATES = [
    *( [Path(os.getenv("MAGIC26_ENV_FILE", ""))] if os.getenv("MAGIC26_ENV_FILE") else [] ),
    Path("C:/Users/abckf/AppData/Local/hermes/profiles/jojo/.env"),
    Path("C:/Users/abckf/AppData/Local/hermes/.env"),
]


def read_token() -> str:
    if os.getenv("FINMIND_TOKEN"):
        return os.getenv("FINMIND_TOKEN", "").strip()
    for env_path in ENV_CANDIDATES:
        if not env_path.exists():
            continue
        text = env_path.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            if line.startswith("FINMIND_TOKEN="):
                return line.split("=", 1)[1].strip().strip("\"'")
    return ""


def finmind_get(dataset: str, cache_name: str, sleep_s: float = 0.2, **params) -> pd.DataFrame:
    CACHE.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE / cache_name
    if cache_path.exists():
        return pd.read_parquet(cache_path)
    token = read_token()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    resp = requests.get(BASE, headers=headers, params={"dataset": dataset, **params}, timeout=120)
    resp.raise_for_status()
    js = resp.json()
    if js.get("status") != 200:
        raise RuntimeError(f"FinMind {dataset} failed: status={js.get('status')} msg={js.get('msg')}")
    df = pd.DataFrame(js.get("data") or [])
    df.to_parquet(cache_path, index=False)
    time.sleep(sleep_s)
    return df


def get_common_stock_info() -> pd.DataFrame:
    info = finmind_get("TaiwanStockInfo", "stock_info.parquet")
    if info.empty:
        return info
    common = info[(info["type"].isin(["twse", "tpex"])) & info["stock_id"].astype(str).str.match(r"^\d{4}$")].copy()
    # Keep listed/OTC common stocks. FinMind StockInfo also contains ETFs/beneficiary securities
    # with 4-digit-like ids; those distort an equity momentum strategy pilot.
    exclude_pat = r"ETF|ETN|指數股票型基金|受益證券|存託憑證|權證|牛證|熊證|所有證券|Index"
    common = common[~common["industry_category"].astype(str).str.contains(exclude_pat, regex=True, na=False)]
    common = common.sort_values(["stock_id", "date"]).drop_duplicates("stock_id", keep="last")
    return common.sort_values("stock_id").reset_index(drop=True)


def select_universe(info: pd.DataFrame, universe: str, max_stocks: int | None = None) -> list[str]:
    if info.empty:
        return []
    selected = info.copy()
    if universe == "tech":
        tech_pat = r"半導體|電子|電腦|通信|通訊|資訊|光電|數位雲端"
        selected = selected[selected["industry_category"].astype(str).str.contains(tech_pat, regex=True, na=False)]
    elif universe != "all":
        raise ValueError(f"Unknown universe: {universe}")
    ids = selected.sort_values("stock_id")["stock_id"].astype(str).drop_duplicates().tolist()
    return ids[:max_stocks] if max_stocks else ids


def fetch_price(stock_id: str, start_date: str, end_date: str, adjusted: bool) -> pd.DataFrame:
    dataset = "TaiwanStockPriceAdj" if adjusted else "TaiwanStockPrice"
    tag = "adj" if adjusted else "raw"
    safe_start = start_date.replace("-", "")
    safe_end = end_date.replace("-", "")
    # FinMind's stock-specific query parameter is data_id. Using stock_id returns all stocks
    # for the date range and can hit API limits/cache an incomplete all-market frame.
    df = finmind_get(dataset, f"{tag}_{stock_id}_{safe_start}_{safe_end}.parquet", data_id=stock_id, start_date=start_date, end_date=end_date)
    if df.empty:
        return df
    df = df.copy()
    df["stock_id"] = df["stock_id"].astype(str)
    df["date"] = pd.to_datetime(df["date"])
    for col in ["open", "max", "min", "close", "Trading_Volume", "Trading_money"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values("date").reset_index(drop=True)


def rolling_days_since_max(values: pd.Series, window: int) -> pd.Series:
    arr = values.to_numpy(dtype=float)
    out = np.full(len(arr), np.nan)
    for i in range(window - 1, len(arr)):
        w = arr[i - window + 1 : i + 1]
        if np.all(np.isnan(w)):
            continue
        # If ties, use the most recent max-volume day; conservative for recent-blowoff exclusion.
        max_val = np.nanmax(w)
        idxs = np.where(w == max_val)[0]
        if len(idxs):
            out[i] = (window - 1) - idxs[-1]
    return pd.Series(out, index=values.index)


def rolling_nth_largest_ratio(values: pd.Series, window: int, nth: int) -> pd.Series:
    arr = values.to_numpy(dtype=float)
    out = np.full(len(arr), np.nan)
    for i in range(window - 1, len(arr)):
        w = arr[i - window + 1 : i + 1]
        w = w[~np.isnan(w)]
        if len(w) < nth:
            continue
        top = np.sort(w)[::-1]
        if top[0] > 0:
            out[i] = top[nth - 1] / top[0]
    return pd.Series(out, index=values.index)


def current_run_length(flag: pd.Series) -> pd.Series:
    out = []
    run = 0
    for v in flag.fillna(False).astype(bool):
        run = run + 1 if v else 0
        out.append(run)
    return pd.Series(out, index=flag.index, dtype="int64")


def add_magic26_columns(df: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    d = df.copy()
    d["ma5"] = d["close"].rolling(5).mean()
    d["ma10"] = d["close"].rolling(10).mean()
    d["ma20"] = d["close"].rolling(20).mean()

    cross_3_days_ago = (d["ma5"].shift(4) <= d["ma20"].shift(4)) & (d["ma5"].shift(3) > d["ma20"].shift(3))
    daily_strong = (d["close"] > d["close"].shift(1)) & (d["close"] > d["ma5"])
    d["c1_cross_confirm"] = cross_3_days_ago & (daily_strong.rolling(5).sum() == 5)

    range_window = args.range_weeks * 5
    rolling_high = d["close"].rolling(range_window).max()
    rolling_low = d["close"].rolling(range_window).min()
    denom = rolling_high - rolling_low
    d["range_pos"] = np.where(denom > 0, (d["close"] - rolling_low) / denom, np.nan)
    d["c2_range_strength"] = d["range_pos"] >= args.range_threshold

    d["gap1"] = d["ma5"] / d["ma10"] - 1
    d["gap2"] = d["ma5"] / d["ma20"] - 1
    d["gap_ok"] = (d["gap1"] >= args.gap1) & (d["gap2"] >= args.gap2)
    d["gap_run_length"] = current_run_length(d["gap_ok"])
    d["c3_ma_gap_run"] = d["gap_run_length"].between(args.gap_run_min, args.gap_run_max, inclusive="both")
    d["gap1_run_length"] = current_run_length(d["gap1"] >= args.gap1)
    d["gap2_run_length"] = current_run_length(d["gap2"] >= args.gap2)
    d["c3_xq_exact_proxy"] = (
        ((d["gap1"] >= args.gap1).rolling(args.gap_run_min).sum() == args.gap_run_min)
        & ((d["gap2"] >= args.gap2).rolling(args.gap_run_min).sum() == args.gap_run_min)
        & (d["gap1_run_length"] <= args.gap_run_max)
        & (d["gap2_run_length"] <= args.gap_run_max)
    )

    d["ret_20d"] = d["close"] / d["close"].shift(args.ret_window) - 1
    d["c4_ret_cap"] = (d["ret_20d"] > args.ret_min) & (d["ret_20d"] < args.ret_max)

    d["vol_max_120"] = d["Trading_Volume"].rolling(args.vol_window).max()
    d["days_since_max_volume"] = rolling_days_since_max(d["Trading_Volume"], args.vol_window)
    d["c5_max_volume_not_recent"] = (d["days_since_max_volume"] > args.vol_exclude_recent_days) & (d["days_since_max_volume"] < args.vol_window)
    d["top5_volume_ratio_120"] = rolling_nth_largest_ratio(d["Trading_Volume"], args.vol_window, 5)
    d["repo_top5_volume_ratio_ok"] = d["top5_volume_ratio_120"].between(0.50, 1.00, inclusive="both")

    d["avg_amount_20d"] = d["Trading_money"].rolling(20).mean()
    d["vol_ma5"] = d["Trading_Volume"].rolling(5).mean()
    d["vol_ma20"] = d["Trading_Volume"].rolling(20).mean()
    d["q1_liquid"] = d["avg_amount_20d"] >= args.min_avg_amount
    d["q2_warm_volume"] = (d["vol_ma5"] > d["vol_ma20"]) & (d["Trading_Volume"] < d["vol_max_120"])

    d["magic26_v0"] = d[[
        "c1_cross_confirm",
        "c2_range_strength",
        "c3_ma_gap_run",
        "c4_ret_cap",
        "c5_max_volume_not_recent",
    ]].all(axis=1)
    d["magic26_v0_quality"] = d["magic26_v0"] & d["q1_liquid"] & d["q2_warm_volume"]

    d["signal_day_ret_1d"] = d["close"] / d["close"].shift(1) - 1
    d["next_open"] = d["open"].shift(-1)
    d["next_open_gap"] = d["next_open"] / d["close"] - 1
    d["next_day_intraday_ret"] = d["close"].shift(-1) / d["next_open"] - 1
    d["next_close"] = d["close"].shift(-1)
    for horizon in [5, 20, 60]:
        d[f"fwd_{horizon}d"] = d["close"].shift(-horizon) / d["close"] - 1
        d[f"t1_close_fwd_{horizon}d"] = d["close"].shift(-(horizon + 1)) / d["next_close"] - 1
        d[f"t1_open_fwd_{horizon}d"] = d["close"].shift(-(horizon + 1)) / d["next_open"] - 1
    return d


def summarize_signal(df: pd.DataFrame, signal_col: str) -> dict:
    s = df[df[signal_col]].copy()
    row = {"signal": signal_col, "signals": int(len(s))}
    for h in [5, 20, 60]:
        col = f"fwd_{h}d"
        vals = s[col].dropna()
        row[f"n_{h}d"] = int(len(vals))
        row[f"avg_{h}d"] = float(vals.mean()) if len(vals) else np.nan
        row[f"median_{h}d"] = float(vals.median()) if len(vals) else np.nan
        row[f"win_rate_{h}d"] = float((vals > 0).mean()) if len(vals) else np.nan
    vals60 = s["fwd_60d"].dropna()
    row["big_winner_60d_gt50"] = float((vals60 > 0.50).mean()) if len(vals60) else np.nan
    row["big_loser_60d_lt20"] = float((vals60 < -0.20).mean()) if len(vals60) else np.nan
    return row


def summarize_by_group(df: pd.DataFrame, signal_cols: list[str], group_col: str) -> pd.DataFrame:
    rows = []
    for group_value, part in df.groupby(group_col, dropna=False, observed=False):
        for signal_col in signal_cols:
            row = summarize_signal(part, signal_col)
            row = {"group_col": group_col, "group": group_value, **row}
            rows.append(row)
    return pd.DataFrame(rows)


def add_liquidity_bucket(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    bins = [-np.inf, 10_000_000, 30_000_000, 100_000_000, 300_000_000, np.inf]
    labels = ["<1千萬", "1-3千萬", "3千萬-1億", "1-3億", ">=3億"]
    d["liquidity_bucket"] = pd.cut(d["avg_amount_20d"], bins=bins, labels=labels)
    return d


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", default="2021-01-01")
    parser.add_argument("--end-date", default=date.today().isoformat())
    parser.add_argument("--stock-ids", default="2330,2317,2454,3661,3037,2382,3231,3017,3324,3013")
    parser.add_argument("--universe", choices=["manual", "all", "tech"], default="manual", help="manual uses --stock-ids; all/tech use filtered FinMind common-stock universe.")
    parser.add_argument("--max-stocks", type=int, default=0, help="Cap selected universe size for pilot runs. Avoid treating capped runs as representative.")
    parser.add_argument("--liquid-universe", action="store_true", help="After indicators are computed, keep only stocks whose latest 20D average trading value is >= --min-avg-amount.")
    parser.add_argument("--adjusted", action="store_true", help="Use TaiwanStockPriceAdj. Default uses TaiwanStockPrice to match XQ-like raw OHLCV more closely.")
    parser.add_argument("--range-weeks", type=int, default=60)
    parser.add_argument("--range-threshold", type=float, default=0.85)
    parser.add_argument("--gap1", type=float, default=0.02)
    parser.add_argument("--gap2", type=float, default=0.05)
    parser.add_argument("--gap-run-min", type=int, default=2)
    parser.add_argument("--gap-run-max", type=int, default=11)
    parser.add_argument("--ret-window", type=int, default=20)
    parser.add_argument("--ret-min", type=float, default=0.0)
    parser.add_argument("--ret-max", type=float, default=0.40)
    parser.add_argument("--vol-window", type=int, default=120)
    parser.add_argument("--vol-exclude-recent-days", type=int, default=5)
    parser.add_argument("--min-avg-amount", type=float, default=30_000_000)
    args = parser.parse_args()

    ROOT.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    stock_info = get_common_stock_info()
    if args.universe == "manual":
        stock_ids = [x.strip() for x in args.stock_ids.split(",") if x.strip()]
        if args.max_stocks > 0:
            stock_ids = stock_ids[: args.max_stocks]
    else:
        stock_ids = select_universe(stock_info, args.universe, args.max_stocks if args.max_stocks > 0 else None)
    if not stock_ids:
        raise SystemExit("No stock ids selected")

    frames = []
    errors = []
    for sid in stock_ids:
        try:
            raw = fetch_price(sid, args.start_date, args.end_date, args.adjusted)
            if raw.empty:
                errors.append({"stock_id": sid, "error": "empty price data"})
                continue
            enriched = add_magic26_columns(raw, args)
            frames.append(enriched)
        except Exception as exc:  # keep a wider probe running; errors are reported in manifest.
            errors.append({"stock_id": sid, "error": repr(exc)})

    if not frames:
        raise SystemExit(f"No usable price frames. errors={errors[:3]}")
    all_df = pd.concat(frames, ignore_index=True).sort_values(["date", "stock_id"])
    all_df = all_df.merge(
        stock_info[["stock_id", "stock_name", "industry_category", "type"]],
        on="stock_id",
        how="left",
    )

    if args.liquid_universe:
        latest_liquidity = all_df.sort_values("date").groupby("stock_id")["avg_amount_20d"].last()
        liquid_ids = latest_liquidity[latest_liquidity >= args.min_avg_amount].index.astype(str)
        all_df = all_df[all_df["stock_id"].astype(str).isin(liquid_ids)].copy()
        if all_df.empty:
            raise SystemExit("No stocks remained after --liquid-universe filter")

    cumulative_cols = {
        "c1_only": ["c1_cross_confirm"],
        "c1_c2": ["c1_cross_confirm", "c2_range_strength"],
        "c1_c2_c3": ["c1_cross_confirm", "c2_range_strength", "c3_ma_gap_run"],
        "c1_c2_c3_xq": ["c1_cross_confirm", "c2_range_strength", "c3_xq_exact_proxy"],
        "c1_c2_c3_repo_vol5": ["c1_cross_confirm", "c2_range_strength", "c3_xq_exact_proxy", "repo_top5_volume_ratio_ok"],
        "c1_c2_c3_c4": ["c1_cross_confirm", "c2_range_strength", "c3_ma_gap_run", "c4_ret_cap"],
        "magic26_v0": ["c1_cross_confirm", "c2_range_strength", "c3_ma_gap_run", "c4_ret_cap", "c5_max_volume_not_recent"],
        "magic26_v0_quality": ["magic26_v0", "q1_liquid", "q2_warm_volume"],
    }
    for name, cols in cumulative_cols.items():
        all_df[name] = all_df[cols].all(axis=1)

    signal_names = list(cumulative_cols.keys())
    all_df = add_liquidity_bucket(all_df)
    all_df["year"] = all_df["date"].dt.year

    summaries = pd.DataFrame([summarize_signal(all_df, name) for name in signal_names])
    yearly = summarize_by_group(all_df, signal_names, "year")
    liquidity = summarize_by_group(all_df, signal_names, "liquidity_bucket")
    signals = all_df[all_df[signal_names].any(axis=1)].copy()
    universe_tag = args.universe
    if args.liquid_universe:
        universe_tag += f"_liquid{int(args.min_avg_amount)}"
    price_tag = "adj" if args.adjusted else "raw"
    run_id = f"{universe_tag}_{price_tag}_{args.start_date.replace('-', '')}_{args.end_date.replace('-', '')}_{len(stock_ids)}stocks"
    summary_path = OUT / f"magic26_v0_summary_{run_id}.csv"
    yearly_path = OUT / f"magic26_v0_yearly_{run_id}.csv"
    liquidity_path = OUT / f"magic26_v0_liquidity_{run_id}.csv"
    signals_path = OUT / f"magic26_v0_signals_{run_id}.csv"
    manifest_path = OUT / f"magic26_v0_manifest_{run_id}.json"
    summaries.to_csv(summary_path, index=False, encoding="utf-8-sig")
    yearly.to_csv(yearly_path, index=False, encoding="utf-8-sig")
    liquidity.to_csv(liquidity_path, index=False, encoding="utf-8-sig")
    signals.to_csv(signals_path, index=False, encoding="utf-8-sig")
    manifest = {
        "run_id": run_id,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "stock_ids": stock_ids,
        "universe": args.universe,
        "liquid_universe": args.liquid_universe,
        "min_avg_amount": args.min_avg_amount,
        "selected_stock_count": int(len(stock_ids)),
        "retained_stock_count": int(all_df["stock_id"].nunique()),
        "adjusted": args.adjusted,
        "rows": int(len(all_df)),
        "errors": errors,
        "outputs": {
            "summary": str(summary_path),
            "yearly": str(yearly_path),
            "liquidity": str(liquidity_path),
            "signals": str(signals_path),
        },
        "rule_note": "C2 uses 5 trading days per week proxy; C3 uses consecutive run-length proxy pending original XQ script verification.",
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(summaries.to_string(index=False))
    print(f"saved summary: {summary_path}")
    print(f"saved yearly: {yearly_path}")
    print(f"saved liquidity: {liquidity_path}")
    print(f"saved signals: {signals_path}")
    print(f"saved manifest: {manifest_path}")
    if errors:
        print(f"errors: {len(errors)}; first={errors[0]}")


if __name__ == "__main__":
    main()
