"""Magic26 round 17: B-class retest/rearm watch rules.

Research-only. For Round-16 B-class names, define second-observation rules:
- cool down after over-extension;
- constructive MA20 retest;
- breakout re-arm after consolidation;
- broken/downshift.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from magic26_paths import cache_dir, out_dir, research_root, source_root  # noqa: E402

ROOT = research_root()
MAGIC = source_root()
OUT = out_dir()
CACHE = cache_dir()
DEFAULT_SNAPSHOT_SUFFIX = "20210101_20260701"
SNAPSHOT_SUFFIX = DEFAULT_SNAPSHOT_SUFFIX
ROUND16 = OUT / f"magic26_round16_top10_manual_review_{SNAPSHOT_SUFFIX}.csv"
REPORT = MAGIC / f"magic26_round17_b_retest_rearm_watch_{SNAPSHOT_SUFFIX}.md"
CSV = OUT / f"magic26_round17_b_retest_rearm_watch_{SNAPSHOT_SUFFIX}.csv"
MANIFEST = OUT / f"magic26_round17_b_retest_rearm_watch_manifest_{SNAPSHOT_SUFFIX}.json"


def configure_paths(snapshot_suffix: str) -> None:
    global SNAPSHOT_SUFFIX, ROUND16, REPORT, CSV, MANIFEST
    SNAPSHOT_SUFFIX = snapshot_suffix
    ROUND16 = OUT / f"magic26_round16_top10_manual_review_{SNAPSHOT_SUFFIX}.csv"
    REPORT = MAGIC / f"magic26_round17_b_retest_rearm_watch_{SNAPSHOT_SUFFIX}.md"
    CSV = OUT / f"magic26_round17_b_retest_rearm_watch_{SNAPSHOT_SUFFIX}.csv"
    MANIFEST = OUT / f"magic26_round17_b_retest_rearm_watch_manifest_{SNAPSHOT_SUFFIX}.json"


def pct(v: Any) -> str:
    if pd.isna(v):
        return "—"
    return f"{float(v) * 100:.1f}%"


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def read_ohlc(stock_id: str, price_mode: str) -> pd.DataFrame:
    mode = "adj" if price_mode == "adjusted" else "raw"
    path = CACHE / f"{mode}_{stock_id}_{SNAPSHOT_SUFFIX}.parquet"
    if not path.exists() and mode == "adj":
        path = CACHE / f"raw_{stock_id}_{SNAPSHOT_SUFFIX}.parquet"
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_parquet(path).copy()
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def classify(row: dict[str, Any]) -> tuple[str, str, str]:
    ma20_gap = row["ma20_gap"]
    ma60_gap = row["ma60_gap"]
    rsi14 = row["rsi14"]
    vol_ratio = row["volume_ratio20"]
    close_near_high20 = row["close_vs_prev20_high"]
    pullback_from_high = row["pullback_from_post_signal_high"]

    if ma60_gap < -0.03 or ma20_gap < -0.06:
        return (
            "降級-跌破結構",
            "暫停深挖",
            "跌破 MA20/MA60 結構，除非重新站回 MA20 並改善量價，否則不進人工 watchlist。",
        )
    if ma20_gap > 0.18 or rsi14 >= 72:
        return (
            "等待降溫",
            "只觀察不追",
            "MA20 乖離或 RSI 過熱，等回測 MA20、RSI 降至 45–65、量縮不破。",
        )
    if -0.03 <= ma20_gap <= 0.08 and 42 <= rsi14 <= 68 and vol_ratio <= 1.25:
        return (
            "回測觀察區",
            "可加入人工watch條件單",
            "接近 MA20 且量能未失控；下一步看是否量縮不破後轉強。",
        )
    if close_near_high20 >= 0.99 and vol_ratio >= 1.25 and ma20_gap >= 0:
        return (
            "再啟動突破候選",
            "可人工覆盤突破品質",
            "接近/突破近20日高且量能放大；需檢查是否假突破與題材催化。",
        )
    if pullback_from_high <= -0.18 and ma20_gap >= -0.03:
        return (
            "深回測但未破結構",
            "觀察，不急",
            "從高點回落較深但尚未明確破結構；等橫盤或重新站回 MA20。",
        )
    return (
        "中性等待",
        "觀察",
        "尚未達再啟動，也未明確破壞；等量縮整理或放量突破。",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-suffix", default=DEFAULT_SNAPSHOT_SUFFIX)
    args = parser.parse_args()
    configure_paths(args.snapshot_suffix)

    prev = pd.read_csv(ROUND16)
    b = prev[prev["manual_decision"].astype(str).str.startswith("B-")].copy()
    if b.empty:
        raise RuntimeError("No B-class rows found from round16")

    rows: list[dict[str, Any]] = []
    for _, r in b.iterrows():
        stock_id = str(int(r["stock_id"])) if isinstance(r["stock_id"], (float, int)) else str(r["stock_id"])
        ohlc = read_ohlc(stock_id, r["price_mode"])
        close = ohlc["close"]
        ohlc["ma20"] = close.rolling(20).mean()
        ohlc["ma60"] = close.rolling(60).mean()
        ohlc["rsi14"] = rsi(close)
        ohlc["vol20"] = ohlc["Trading_Volume"].rolling(20).mean()
        latest = ohlc.iloc[-1]
        prev20_high = ohlc.iloc[-21:-1]["max"].max()
        signal_date = pd.Timestamp(r["date"])
        after = ohlc[ohlc["date"] >= signal_date]
        signal_close = float(after.iloc[0]["close"])
        post_high = float(after["max"].max())
        last_close = float(latest["close"])
        ma20 = float(latest["ma20"])
        ma60 = float(latest["ma60"])
        row = {
            **r.to_dict(),
            "stock_id": stock_id,
            "latest_date": latest["date"].strftime("%Y-%m-%d"),
            "latest_close": last_close,
            "signal_close": signal_close,
            "post_signal_ret": last_close / signal_close - 1,
            "post_signal_high": post_high,
            "pullback_from_post_signal_high": last_close / post_high - 1,
            "ma20": ma20,
            "ma60": ma60,
            "ma20_gap": last_close / ma20 - 1,
            "ma60_gap": last_close / ma60 - 1,
            "rsi14": float(latest["rsi14"]),
            "volume_ratio20": float(latest["Trading_Volume"] / latest["vol20"]),
            "prev20_high": float(prev20_high),
            "close_vs_prev20_high": last_close / float(prev20_high),
        }
        state, action, reason = classify(row)
        row["rearm_state"] = state
        row["suggested_action"] = action
        row["rule_reason"] = reason
        row["trigger_condition_next"] = (
            "回測型：接近MA20±8%、RSI45–65、量縮不破；"
            "突破型：收盤接近/突破20日高、量比>1.25、仍站MA20。"
        )
        rows.append(row)

    out = pd.DataFrame(rows).sort_values(
        ["rearm_state", "post_signal_ret"], ascending=[True, False]
    )
    out.to_csv(CSV, index=False, encoding="utf-8-sig")

    counts = out["rearm_state"].value_counts().to_dict()
    md: list[str] = []
    md.append("# Magic26 第十七輪：B 類四檔二次觀察 / 再啟動條件（2026-07-01）\n")
    md.append("## 目的\n")
    md.append("承接 Round 16，只處理 B 類：題材可能成立但追價風險高。這輪不追價、不調參，而是建立二次觀察條件。\n")
    md.append("## 一眼結論\n")
    md.append(f"- B 類檢查檔數：**{len(out)}**\n")
    md.append(f"- 狀態統計：`{json.dumps(counts, ensure_ascii=False)}`\n")
    md.append("- 原則：過熱只觀察；回測 MA20 量縮不破才可升級；跌破結構就降級。\n")
    md.append("\n## 二次觀察規則\n")
    md.append("- **等待降溫**：MA20 乖離 >18% 或 RSI >=72。\n")
    md.append("- **回測觀察區**：MA20 gap 約 -3%~+8%，RSI 42~68，量比20 <=1.25。\n")
    md.append("- **再啟動突破候選**：接近/突破近20日高，量比20 >=1.25，且站上 MA20。\n")
    md.append("- **降級-跌破結構**：MA20 gap < -6% 或 MA60 gap < -3%。\n")
    md.append("\n## 四檔狀態\n")
    for i, (_, x) in enumerate(out.iterrows(), 1):
        md.append(
            f"{i}. **{x.stock_id} {x.stock_name}**｜{x.rearm_state}｜{x.suggested_action}\n"
            f"   - 題材：{x.theme_bucket}\n"
            f"   - 路徑：訊號後 {pct(x.post_signal_ret)}；距訊號後高點 {pct(x.pullback_from_post_signal_high)}\n"
            f"   - 結構：MA20 gap {pct(x.ma20_gap)}；MA60 gap {pct(x.ma60_gap)}；RSI14 {x.rsi14:.1f}；量比20 {x.volume_ratio20:.2f}\n"
            f"   - 近20高比較：收盤/前20日高 {x.close_vs_prev20_high:.2f}\n"
            f"   - 判斷：{x.rule_reason}\n"
            f"   - 下一觸發：{x.trigger_condition_next}\n"
        )
    md.append("\n## 決策\n")
    md.append("- 不新增買進訊號；只建立 watchlist 升降級條件。\n")
    md.append("- B 類若仍過熱，等待降溫；若轉成回測觀察區，下一輪才做題材/基本面驗證。\n")
    md.append("- 若跌破結構，從 Magic26 人工優先名單移出，等待新訊號。\n")
    md.append("\n## 輸出\n")
    md.append(f"- csv: `{CSV}`")
    md.append(f"- manifest: `{MANIFEST}`")
    REPORT.write_text("\n".join(md), encoding="utf-8")
    MANIFEST.write_text(json.dumps({
        "snapshot_suffix": SNAPSHOT_SUFFIX,
        "input": str(ROUND16),
        "outputs": {"csv": str(CSV), "report": str(REPORT)},
        "rows": int(len(out)),
        "state_counts": counts,
        "decision": "watchlist_rearm_rules_only_not_buy_signal",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {CSV}")
    print(f"wrote {REPORT}")


if __name__ == "__main__":
    main()
