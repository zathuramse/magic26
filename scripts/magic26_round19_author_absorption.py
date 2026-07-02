"""Magic26 round 19: absorb author updates.

Research-only. Tests three source-derived ideas:
1) ret60 upper cap (0-150% primary)
2) top-1 volume gap versus top-3/5/10 volume
3) daily/weekly long MA bearish risk badges
"""
from __future__ import annotations

import argparse
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from magic26_paths import cache_dir, out_dir, research_root, source_root  # noqa: E402

ROOT = research_root()
BASE = source_root()
CACHE = cache_dir()
OUT = out_dir()
DEFAULT_SNAPSHOT_SUFFIX = "20210101_20260701"
SNAPSHOT_SUFFIX = DEFAULT_SNAPSHOT_SUFFIX
DETAIL = OUT / f"magic26_round8_tradeability_detail_{SNAPSHOT_SUFFIX}.csv"
REPORT = BASE / f"magic26_round19_author_absorption_report_{SNAPSHOT_SUFFIX}.md"
ENRICHED_CSV = OUT / f"magic26_round19_author_absorption_detail_{SNAPSHOT_SUFFIX}.csv"
RET60_CSV = OUT / f"magic26_round19_ret60_cap_summary_{SNAPSHOT_SUFFIX}.csv"
VOLGAP_CSV = OUT / f"magic26_round19_volume_gap_summary_{SNAPSHOT_SUFFIX}.csv"
RISK_CSV = OUT / f"magic26_round19_risk_badge_summary_{SNAPSHOT_SUFFIX}.csv"
MANIFEST = OUT / f"magic26_round19_author_absorption_manifest_{SNAPSHOT_SUFFIX}.json"


def configure_paths(snapshot_suffix: str) -> None:
    global SNAPSHOT_SUFFIX, DETAIL, REPORT, ENRICHED_CSV, RET60_CSV, VOLGAP_CSV, RISK_CSV, MANIFEST
    SNAPSHOT_SUFFIX = snapshot_suffix
    DETAIL = OUT / f"magic26_round8_tradeability_detail_{SNAPSHOT_SUFFIX}.csv"
    REPORT = BASE / f"magic26_round19_author_absorption_report_{SNAPSHOT_SUFFIX}.md"
    ENRICHED_CSV = OUT / f"magic26_round19_author_absorption_detail_{SNAPSHOT_SUFFIX}.csv"
    RET60_CSV = OUT / f"magic26_round19_ret60_cap_summary_{SNAPSHOT_SUFFIX}.csv"
    VOLGAP_CSV = OUT / f"magic26_round19_volume_gap_summary_{SNAPSHOT_SUFFIX}.csv"
    RISK_CSV = OUT / f"magic26_round19_risk_badge_summary_{SNAPSHOT_SUFFIX}.csv"
    MANIFEST = OUT / f"magic26_round19_author_absorption_manifest_{SNAPSHOT_SUFFIX}.json"
    load_px.cache_clear()
MAIN = "candidate_a_repo50_c440_c5gt5"


def profit_factor(x: pd.Series) -> float:
    x = pd.to_numeric(x, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    gains = x[x > 0].sum()
    losses = -x[x < 0].sum()
    if losses == 0:
        return float("inf") if gains > 0 else float("nan")
    return float(gains / losses)


def pct(x: Any) -> str:
    return "—" if pd.isna(x) else f"{float(x)*100:.1f}%"


def num(x: Any) -> str:
    return "—" if pd.isna(x) else f"{float(x):.2f}"


@lru_cache(maxsize=None)
def load_px(mode: str, stock_id: str) -> pd.DataFrame | None:
    p = CACHE / f"{mode}_{stock_id}_{SNAPSHOT_SUFFIX}.parquet"
    if not p.exists():
        return None
    df = pd.read_parquet(p).copy()
    if "date" not in df.columns:
        return None
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def asof_index(px: pd.DataFrame, dt: pd.Timestamp) -> int | None:
    idx = px[px["date"] <= dt].index
    if len(idx) == 0:
        return None
    return int(idx[-1])


def barslast_cross_under(a: pd.Series, b: pd.Series, idx: int) -> float:
    if idx <= 0:
        return np.nan
    cross = (a.shift(1) >= b.shift(1)) & (a < b)
    hits = np.flatnonzero(cross.iloc[: idx + 1].fillna(False).to_numpy())
    if len(hits) == 0:
        return np.nan
    return float(idx - hits[-1])


def enrich_row(row: pd.Series) -> dict[str, Any]:
    mode = str(row["price_mode"])
    stock_id = str(row["stock_id"])
    dt = pd.to_datetime(row["date"])
    px = load_px(mode, stock_id)
    out: dict[str, Any] = {}
    if px is None:
        out["enrich_error"] = "missing_px"
        return out
    idx = asof_index(px, dt)
    if idx is None:
        out["enrich_error"] = "no_asof_date"
        return out
    close = pd.to_numeric(px["close"], errors="coerce")
    volume = pd.to_numeric(px["Trading_Volume"], errors="coerce") if "Trading_Volume" in px.columns else pd.to_numeric(px.get("volume"), errors="coerce")

    if idx >= 60 and close.iloc[idx - 60] not in (0, np.nan):
        out["ret_60d_signal"] = float(close.iloc[idx] / close.iloc[idx - 60] - 1)
    else:
        out["ret_60d_signal"] = np.nan

    # Top volume gap in the past 120 trading bars including signal day.
    start = max(0, idx - 119)
    vols = volume.iloc[start : idx + 1].dropna().sort_values(ascending=False).to_numpy()
    out["top_volume_window_n"] = int(len(vols))
    if len(vols) >= 10 and vols[0] > 0:
        out["top1_volume"] = float(vols[0])
        for n in (3, 5, 10):
            out[f"top{n}_volume"] = float(vols[n - 1])
            out[f"top1_to_top{n}_volume_ratio"] = float(vols[0] / vols[n - 1]) if vols[n - 1] > 0 else np.nan
    else:
        for n in (3, 5, 10):
            out[f"top1_to_top{n}_volume_ratio"] = np.nan

    ma60 = close.rolling(60).mean()
    ma120 = close.rolling(120).mean()
    ma240 = close.rolling(240).mean()
    d60, d120, d240 = ma60.iloc[idx], ma120.iloc[idx], ma240.iloc[idx]
    daily_simple = bool(pd.notna(d240) and d240 > d120 and d120 > d60)
    daily_strong = bool(pd.notna(d240) and pd.notna(d120) and pd.notna(d60) and (d240 >= max(d60, d120) * 1.03 or (d240 >= max(d60, d120) and d240 >= min(d60, d120) * 1.05)))
    daily_right_shoulder = bool(pd.notna(d120) and pd.notna(d60) and pd.notna(d240) and d120 > max(d60, d240) * 1.001 and (barslast_cross_under(ma60, ma120, idx) >= 10))
    out["risk_daily_long_ma_bear"] = daily_simple or daily_strong
    out["risk_daily_long_ma_simple_bear"] = daily_simple
    out["risk_daily_long_ma_strong_bear"] = daily_strong
    out["risk_daily_right_shoulder"] = daily_right_shoulder

    # Weekly risk badge: resample to week ending Friday, using last close.
    w = px.set_index("date")["close"].resample("W-FRI").last().dropna().reset_index()
    widx = asof_index(w, dt)
    if widx is not None:
        wc = pd.to_numeric(w["close"], errors="coerce")
        w60 = wc.rolling(60).mean(); w120 = wc.rolling(120).mean(); w240 = wc.rolling(240).mean()
        x60, x120, x240 = w60.iloc[widx], w120.iloc[widx], w240.iloc[widx]
        weekly_simple = bool(pd.notna(x240) and x240 > x120 and x120 > x60)
        weekly_strong = bool(pd.notna(x240) and pd.notna(x120) and pd.notna(x60) and x240 > max(x120, x60) * 1.05)
        weekly_right_shoulder = bool(pd.notna(x120) and pd.notna(x60) and pd.notna(x240) and x120 > max(x60, x240) * 1.001 and (barslast_cross_under(w60, w120, widx) >= 10))
    else:
        weekly_simple = weekly_strong = weekly_right_shoulder = False
    out["risk_weekly_long_ma_bear"] = weekly_simple or weekly_strong
    out["risk_weekly_long_ma_simple_bear"] = weekly_simple
    out["risk_weekly_long_ma_strong_bear"] = weekly_strong
    out["risk_weekly_right_shoulder"] = weekly_right_shoulder
    out["risk_any_long_ma_bear"] = bool(out["risk_daily_long_ma_bear"] or out["risk_weekly_long_ma_bear"])
    out["risk_long_ma_score"] = -int(out["risk_daily_long_ma_bear"]) - int(out["risk_weekly_long_ma_bear"])
    return out


def summarize(g: pd.DataFrame, group: str, label: str, baseline_n: int | None = None) -> dict[str, Any]:
    v = g.dropna(subset=["fixed20_ret", "t1_open_excess_20d"]).copy()
    row: dict[str, Any] = {"group": group, "label": label, "trades": int(len(v))}
    if baseline_n:
        row["retention"] = len(v) / baseline_n
    if v.empty:
        return row
    row.update({
        "avg_return": float(v["fixed20_ret"].mean()),
        "median_return": float(v["fixed20_ret"].median()),
        "win_return": float((v["fixed20_ret"] > 0).mean()),
        "pf_return": profit_factor(v["fixed20_ret"]),
        "avg_excess": float(v["t1_open_excess_20d"].mean()),
        "median_excess": float(v["t1_open_excess_20d"].median()),
        "win_excess": float((v["t1_open_excess_20d"] > 0).mean()),
        "pf_excess": profit_factor(v["t1_open_excess_20d"]),
        "right_tail_20pct": float((v["fixed20_ret"] >= 0.20).mean()),
        "right_tail_50pct": float((v["fixed20_ret"] >= 0.50).mean()),
        "bad_loss_minus10pct": float((v["fixed20_ret"] <= -0.10).mean()),
        "avg_ret60_signal": float(v["ret_60d_signal"].mean()) if "ret_60d_signal" in v else np.nan,
        "median_ret60_signal": float(v["ret_60d_signal"].median()) if "ret_60d_signal" in v else np.nan,
    })
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-suffix", default=DEFAULT_SNAPSHOT_SUFFIX)
    args = parser.parse_args()
    configure_paths(args.snapshot_suffix)

    df = pd.read_csv(DETAIL)
    df = df[df["candidate"].eq(MAIN)].copy()
    df["date"] = pd.to_datetime(df["date"])
    enrich = pd.DataFrame([enrich_row(r) for _, r in df.iterrows()])
    edf = pd.concat([df.reset_index(drop=True), enrich], axis=1)
    edf.to_csv(ENRICHED_CSV, index=False, encoding="utf-8-sig")

    ret_rows: list[dict[str, Any]] = []
    vol_rows: list[dict[str, Any]] = []
    risk_rows: list[dict[str, Any]] = []

    for mode, mdf in edf.groupby("price_mode"):
        # Retention should be based on valid evaluable trades, not raw rows with missing forward path.
        base_n = int(mdf.dropna(subset=["fixed20_ret", "t1_open_excess_20d"]).shape[0])
        base = summarize(mdf, "ret60_cap", f"{mode}: baseline", base_n)
        ret_rows.append(base)
        for cap in (1.20, 1.50, 2.00):
            g = mdf[mdf["ret_60d_signal"].le(cap)]
            ret_rows.append(summarize(g, "ret60_cap", f"{mode}: ret60 <= {cap:.0%}", base_n))
        for lo, hi, name in [(0, 1.2, "ret60 <=120% only"), (1.2, 1.5, "120%<ret60<=150%"), (1.5, 2.0, "150%<ret60<=200%"), (2.0, np.inf, "ret60>200%")]:
            g = mdf[mdf["ret_60d_signal"].gt(lo) & mdf["ret_60d_signal"].le(hi)] if np.isfinite(hi) else mdf[mdf["ret_60d_signal"].gt(lo)]
            ret_rows.append(summarize(g, "ret60_bucket", f"{mode}: {name}", base_n))

        for n in (3, 5, 10):
            col = f"top1_to_top{n}_volume_ratio"
            vol_rows.append(summarize(mdf, f"volume_gap_top{n}", f"{mode}: baseline", base_n))
            for threshold in (1.5, 2.0, 3.0):
                g = mdf[mdf[col].lt(threshold)]
                vol_rows.append(summarize(g, f"volume_gap_top{n}", f"{mode}: top1/top{n} < {threshold:g}", base_n))
                bad = mdf[mdf[col].ge(threshold)]
                vol_rows.append(summarize(bad, f"volume_gap_top{n}_flagged", f"{mode}: flagged top1/top{n} >= {threshold:g}", base_n))

        for col in ["risk_daily_long_ma_bear", "risk_weekly_long_ma_bear", "risk_any_long_ma_bear", "risk_daily_right_shoulder", "risk_weekly_right_shoulder"]:
            risk_rows.append(summarize(mdf[mdf[col].eq(False)], "risk_badge", f"{mode}: {col}=False", base_n))
            risk_rows.append(summarize(mdf[mdf[col].eq(True)], "risk_badge", f"{mode}: {col}=True", base_n))
        for score, g in mdf.groupby("risk_long_ma_score"):
            risk_rows.append(summarize(g, "risk_score", f"{mode}: risk_long_ma_score={int(score)}", base_n))

    ret = pd.DataFrame(ret_rows)
    vol = pd.DataFrame(vol_rows)
    risk = pd.DataFrame(risk_rows)
    # add deltas versus per-mode baseline inside each group where applicable
    for table in (ret, vol, risk):
        table["mode"] = table["label"].str.split(":").str[0]
        for mode in table["mode"].dropna().unique():
            mb = table[(table["mode"].eq(mode)) & (table["label"].eq(f"{mode}: baseline"))]
            if len(mb):
                b = mb.iloc[0]
                idx = table["mode"].eq(mode)
                for c in ["median_excess", "win_excess", "right_tail_50pct"]:
                    if c in table.columns:
                        table.loc[idx, f"delta_{c}"] = table.loc[idx, c] - b.get(c, np.nan)
    ret.to_csv(RET60_CSV, index=False, encoding="utf-8-sig")
    vol.to_csv(VOLGAP_CSV, index=False, encoding="utf-8-sig")
    risk.to_csv(RISK_CSV, index=False, encoding="utf-8-sig")

    adj_ret = ret[ret["mode"].eq("adj")].copy()
    adj_vol = vol[vol["mode"].eq("adj")].copy()
    adj_risk = risk[risk["mode"].eq("adj")].copy()

    md: list[str] = []
    md.append("# Magic26 Round 19：原作者更新吸收測試（2026-06-30）\n")
    md.append("## 目的\n")
    md.append("把 2026-06-30 檢閱原作者 Facebook / xq-xs repo 後最值得吸收的三件事，先用既有 Magic26 Round 8 detail + OHLC cache 做 research-only 驗證：\n")
    md.append("1. 60日漲幅上限，主測 `ret60 <= 150%`。\n")
    md.append("2. 第一大量斷層風險：`top1/top3`, `top1/top5`, `top1/top10`。\n")
    md.append("3. 評分系統負分化：日/周長均空頭作為 risk badge。\n")
    md.append("\n## 重要限制\n")
    md.append("- 使用既有樣本 `candidate_a_repo50_c440_c5gt5`，不是全市場重新掃描。\n")
    md.append("- 主要績效仍是既有 `fixed20_ret` / `t1_open_excess_20d`，不是 60 天持有績效；本輪先看條件方向。\n")
    md.append("- 周線 240MA 對早期樣本需要長歷史；資料不足時 badge 會是 False，因此周線負分可能低估。\n")

    md.append("\n## A. 60日漲幅上限\n")
    for _, r in adj_ret[adj_ret.group.eq("ret60_cap")].iterrows():
        md.append(f"- `{r.label}`：n={int(r.trades)}，保留 {pct(r.get('retention'))}，excess中位 {pct(r.get('median_excess'))}，勝率 {pct(r.get('win_excess'))}，50%右尾 {pct(r.get('right_tail_50pct'))}，Δ中位 {pct(r.get('delta_median_excess'))}")
    md.append("\nret60 分桶：\n")
    for _, r in adj_ret[adj_ret.group.eq("ret60_bucket")].iterrows():
        md.append(f"- `{r.label}`：n={int(r.trades)}，excess中位 {pct(r.get('median_excess'))}，勝率 {pct(r.get('win_excess'))}，50%右尾 {pct(r.get('right_tail_50pct'))}")

    md.append("\n## B. 第一大量斷層風險\n")
    for group in ["volume_gap_top3", "volume_gap_top5", "volume_gap_top10"]:
        focus = adj_vol[(adj_vol.group.eq(group)) & (adj_vol.label.str.contains("< 2"))]
        flagged = adj_vol[(adj_vol.group.eq(group + "_flagged")) & (adj_vol.label.str.contains(">= 2"))]
        if len(focus):
            r = focus.iloc[0]
            md.append(f"- `{r.label}`：n={int(r.trades)}，保留 {pct(r.get('retention'))}，excess中位 {pct(r.get('median_excess'))}，勝率 {pct(r.get('win_excess'))}，50%右尾 {pct(r.get('right_tail_50pct'))}，Δ中位 {pct(r.get('delta_median_excess'))}")
        if len(flagged):
            r = flagged.iloc[0]
            md.append(f"  - flagged `{r.label}`：n={int(r.trades)}，excess中位 {pct(r.get('median_excess'))}，勝率 {pct(r.get('win_excess'))}，50%右尾 {pct(r.get('right_tail_50pct'))}")

    md.append("\n## C. 日/周長均空頭 risk badge\n")
    for _, r in adj_risk[adj_risk.group.isin(["risk_badge", "risk_score"])].iterrows():
        if any(key in str(r.label) for key in ["risk_daily_long_ma_bear", "risk_weekly_long_ma_bear", "risk_any_long_ma_bear", "risk_long_ma_score"]):
            md.append(f"- `{r.label}`：n={int(r.trades)}，保留 {pct(r.get('retention'))}，excess中位 {pct(r.get('median_excess'))}，勝率 {pct(r.get('win_excess'))}，50%右尾 {pct(r.get('right_tail_50pct'))}")

    md.append("\n## D. 右尾指標與 event log 檢查\n")
    md.append("本輪 summary 已加入 `right_tail_20pct`、`right_tail_50pct`、`bad_loss_minus10pct`，先把原作者『飆股比率比平均報酬率重要』落成欄位。下一輪若要完全貼近作者框架，應改用 60日持有報酬做 `pnl60 >= 50%` / `pnl60 >= 100%`。\n")
    md.append("已檢查 dashboard event log：`magic26_candidates_history.csv` 目前 329 rows / 30 columns，已有日期、股票、候選、price_mode、ret20、20/60日 excess、research_tags；但尚未有明確 `source=live_scan/backtest_export/reconstructed` 欄位。\n")

    md.append("\n## 初步決策\n")
    md.append("1. `ret60 <= 150%` 可升為正式候選條件，但本輪只能說它是風報比濾網候選；是否改主規格要看 60天績效與誤刪右尾。本輪 adjusted 只排除 1 檔：`2024-05-06 天良`，ret60 約 +186%，20日 excess 約 +5.4%，不是右尾大贏家。\n")
    md.append("2. 第一大量斷層先做 risk badge，不做硬排除。`top1/top10 >= 2` 的 flagged 組中位 excess 較弱，但 `top1/top3 >= 1.5` flagged 組反而較強；代表斷層量不是單調負面，必須分 top3/top5/top10 與位置/K線脈絡。\n")
    md.append("3. 日/周長均空頭 risk badge 建議保留為評分欄位；本輪 True 樣本太少。weekly long bear 只有 2 檔：`5351 鈺創` 很差、`6488 環球晶` 很好，因此只能當風險提示，不能當 veto。\n")
    md.append("4. 下一個實作方向：把 Round 19 的三組欄位接進 dashboard data export，但先標記為『研究中 risk badge』，不改主規格、不自動排除。\n")
    md.append("\n## 輸出\n")
    for p in [ENRICHED_CSV, RET60_CSV, VOLGAP_CSV, RISK_CSV, MANIFEST]:
        md.append(f"- `{p}`")
    REPORT.write_text("\n".join(md), encoding="utf-8")

    MANIFEST.write_text(json.dumps({
        "snapshot_suffix": SNAPSHOT_SUFFIX,
        "source_detail": str(DETAIL),
        "candidate": MAIN,
        "outputs": {
            "detail": str(ENRICHED_CSV),
            "ret60": str(RET60_CSV),
            "volume_gap": str(VOLGAP_CSV),
            "risk_badge": str(RISK_CSV),
            "report": str(REPORT),
        },
        "rows_detail": int(len(edf)),
        "rows_ret60": int(len(ret)),
        "rows_volume_gap": int(len(vol)),
        "rows_risk": int(len(risk)),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {ENRICHED_CSV}")
    print(f"wrote {RET60_CSV}")
    print(f"wrote {VOLGAP_CSV}")
    print(f"wrote {RISK_CSV}")
    print(f"wrote {REPORT}")


if __name__ == "__main__":
    main()
