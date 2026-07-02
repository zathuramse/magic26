"""Magic26 round 16: Top-10 manual technical/theme review.

Research-only. Uses local Magic26 cache OHLC data and Round-15 priority queue.
No trading, no parameter optimization, no external scraping dependency.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path("C:/Users/abckf/research-brain")
MAGIC = ROOT / "sources" / "strategy-checks" / "magic26"
OUT = MAGIC / "out"
CACHE = MAGIC / "cache"
DEFAULT_SNAPSHOT_SUFFIX = "20210101_20260701"
SNAPSHOT_SUFFIX = DEFAULT_SNAPSHOT_SUFFIX
ROUND15 = OUT / f"magic26_round15_priority_review_ranked_{SNAPSHOT_SUFFIX}.csv"
REPORT = MAGIC / f"magic26_round16_top10_manual_review_{SNAPSHOT_SUFFIX}.md"
CSV = OUT / f"magic26_round16_top10_manual_review_{SNAPSHOT_SUFFIX}.csv"
MANIFEST = OUT / f"magic26_round16_top10_manual_review_manifest_{SNAPSHOT_SUFFIX}.json"


def configure_paths(snapshot_suffix: str) -> None:
    global SNAPSHOT_SUFFIX, ROUND15, REPORT, CSV, MANIFEST
    SNAPSHOT_SUFFIX = snapshot_suffix
    ROUND15 = OUT / f"magic26_round15_priority_review_ranked_{SNAPSHOT_SUFFIX}.csv"
    REPORT = MAGIC / f"magic26_round16_top10_manual_review_{SNAPSHOT_SUFFIX}.md"
    CSV = OUT / f"magic26_round16_top10_manual_review_{SNAPSHOT_SUFFIX}.csv"
    MANIFEST = OUT / f"magic26_round16_top10_manual_review_manifest_{SNAPSHOT_SUFFIX}.json"

THEMES = {
    "2327": ("被動元件 / MLCC / AI伺服器電源鏈", "題材可追，但要確認 AI server 高階料號與毛利，不可只看漲價循環。"),
    "4979": ("光通訊 / CPO / 光收發模組", "題材密度高，但波動也高；要確認營收與毛利是否跟上 CPO/800G 期待。"),
    "2887": ("金融股 / 併購整合 / 資金輪動", "不屬 AI 題材；看合併綜效、金融股輪動、殖利率與淨值評價。"),
    "3450": ("光通訊 / 光學元件 / AI網通", "與光通訊鏈相關；要確認是否為實質訂單/規格升級，不只跟隨族群。"),
    "3163": ("光通訊 / CPO / 資料中心網通", "題材與華星光同族群，需比較營收彈性與估值擁擠度。"),
    "6488": ("半導體矽晶圓 / 景氣循環", "偏半導體循環復甦，不是純 AI 高成長；重點是價格、稼動率與庫存去化。"),
    "3036": ("IC通路 / AI伺服器供應鏈", "通路股要看庫存週轉與毛利率，營收放大不等於估值重估。"),
    "6173": ("被動元件 / MLCC / 電子零組件", "可放入被動元件族群觀察，但需確認高階產品占比。"),
    "6584": ("伺服器滑軌 / 機構件 / AI server", "若 AI server 滑軌訂單成立，題材較直接；需驗證客戶與出貨延續性。"),
    "6291": ("電源管理IC / 半導體", "小型半導體題材彈性高，但要看營收與 EPS 是否兌現。"),
}


def pct(v: Any) -> str:
    if pd.isna(v):
        return "—"
    return f"{float(v) * 100:.1f}%"


def money(v: Any) -> str:
    if pd.isna(v):
        return "—"
    return f"{float(v) / 1e8:.1f}億"


def read_ohlc(stock_id: str, price_mode: str) -> pd.DataFrame:
    mode = "adj" if price_mode == "adjusted" else "raw"
    path = CACHE / f"{mode}_{stock_id}_{SNAPSHOT_SUFFIX}.parquet"
    if not path.exists() and mode == "adj":
        path = CACHE / f"raw_{stock_id}_{SNAPSHOT_SUFFIX}.parquet"
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_parquet(path).copy()
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date")


def rsi(close: pd.Series, period: int = 14) -> float:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    val = 100 - (100 / (1 + rs))
    return float(val.iloc[-1]) if not val.dropna().empty else np.nan


def classify(row: dict[str, Any]) -> tuple[str, str]:
    ret = row["post_signal_ret"]
    above20 = row["latest_close"] >= row["ma20"] if not pd.isna(row["ma20"]) else False
    above60 = row["latest_close"] >= row["ma60"] if not pd.isna(row["ma60"]) else False
    ma20_gap = row["ma20_gap"]
    dd = row["max_drawdown_after_signal"]
    if row["stock_id"] == "2887":
        return "A-可放人工watchlist", "金融股框架不同；若仍站上MA20/60且回撤可控，可作資金輪動觀察。"
    if ret < -0.05 or not above20:
        return "C-技術型反彈/先降級", "訊號後動能不足或跌回MA20下，先不要深挖題材。"
    if ma20_gap > 0.18 or ret > 0.55:
        return "B-題材成立但追價風險高", "訊號後漲幅/MA20乖離偏大，等整理或回測再看。"
    if dd < -0.22:
        return "B-題材成立但波動過大", "最大回撤偏深，適合watch，不適合直接追。"
    if above20 and above60 and ret > 0:
        return "A-可放人工watchlist", "訊號後仍維持正報酬且站上MA20/60，可進入人工圖形與題材覆盤。"
    return "C-技術型反彈/先降級", "條件未明顯轉強，先保留觀察。"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-suffix", default=DEFAULT_SNAPSHOT_SUFFIX)
    args = parser.parse_args()
    configure_paths(args.snapshot_suffix)

    q = pd.read_csv(ROUND15).head(10).copy()
    rows: list[dict[str, Any]] = []
    for _, r in q.iterrows():
        stock_id = str(int(r["stock_id"])) if isinstance(r["stock_id"], (int, float)) else str(r["stock_id"])
        ohlc = read_ohlc(stock_id, r["price_mode"])
        signal_date = pd.Timestamp(r["date"])
        after = ohlc[ohlc["date"] >= signal_date].copy()
        if after.empty:
            raise RuntimeError(f"No OHLC after signal for {stock_id} {signal_date}")
        latest = ohlc.iloc[-1]
        signal = after.iloc[0]
        close = ohlc["close"]
        ma20 = close.rolling(20).mean().iloc[-1]
        ma60 = close.rolling(60).mean().iloc[-1]
        latest_close = float(latest["close"])
        signal_close = float(signal["close"])
        post_ret = latest_close / signal_close - 1
        max_runup = float(after["max"].max() / signal_close - 1)
        max_dd = float(after["min"].min() / signal_close - 1)
        avg_vol20 = ohlc["Trading_Volume"].rolling(20).mean().iloc[-1]
        latest_vol_ratio = float(latest["Trading_Volume"] / avg_vol20) if avg_vol20 else np.nan
        theme, theme_note = THEMES.get(stock_id, ("待分類", "需人工補題材與公司資料。"))
        row = {
            **r.to_dict(),
            "stock_id": stock_id,
            "latest_date": latest["date"].strftime("%Y-%m-%d"),
            "signal_close": signal_close,
            "latest_close": latest_close,
            "post_signal_ret": post_ret,
            "max_runup_after_signal": max_runup,
            "max_drawdown_after_signal": max_dd,
            "ma20": float(ma20),
            "ma60": float(ma60),
            "ma20_gap": latest_close / float(ma20) - 1 if ma20 else np.nan,
            "ma60_gap": latest_close / float(ma60) - 1 if ma60 else np.nan,
            "rsi14": rsi(close),
            "latest_volume_ratio20": latest_vol_ratio,
            "theme_bucket": theme,
            "theme_note": theme_note,
        }
        decision, reason = classify(row)
        row["manual_decision"] = decision
        row["decision_reason"] = reason
        rows.append(row)

    out = pd.DataFrame(rows)
    out.to_csv(CSV, index=False, encoding="utf-8-sig")

    def item(i: int, x: pd.Series) -> str:
        return (
            f"{i}. **{x.stock_id} {x.stock_name}**｜{x.manual_decision}\n"
            f"   - 題材：{x.theme_bucket}\n"
            f"   - 路徑：訊號 {x.date} close {x.signal_close:.2f} → 最新 {x.latest_date} close {x.latest_close:.2f}，訊號後 {pct(x.post_signal_ret)}；最大上行 {pct(x.max_runup_after_signal)}；最大回撤 {pct(x.max_drawdown_after_signal)}\n"
            f"   - 均線：MA20 gap {pct(x.ma20_gap)}；MA60 gap {pct(x.ma60_gap)}；RSI14 {x.rsi14:.1f}；量比20 {x.latest_volume_ratio20:.2f}\n"
            f"   - 研究判斷：{x.decision_reason}\n"
            f"   - 題材盲點：{x.theme_note}\n"
        )

    counts = out["manual_decision"].value_counts().to_dict()
    md: list[str] = []
    md.append("# Magic26 第十六輪：Top 10 圖形 / 題材 / 產業脈絡覆盤（2026-07-01）\n")
    md.append("## 目的\n")
    md.append("承接 Round 15，只覆盤第一優先前 10 檔；用本地 OHLC cache 看訊號後路徑，再加上產業/題材脈絡。這不是交易建議。\n")
    md.append("## 一眼結論\n")
    md.append(f"- 分類統計：{json.dumps(counts, ensure_ascii=False)}\n")
    md.append("- 優先看 A 類；B 類若題材成立也先等整理；C 類先降級，不急著深挖。\n")
    md.append("- 這輪仍不回頭調參數；重點是把候選變成可人工研究的 watchlist。\n")
    md.append("\n## Top 10 覆盤\n")
    for i, (_, x) in enumerate(out.iterrows(), 1):
        md.append(item(i, x))
    md.append("\n## 決策\n")
    md.append("- **A-可放人工watchlist**：進入下一輪較深入基本面/題材驗證。\n")
    md.append("- **B-題材成立但追價/波動風險高**：不淘汰，但等整理或回測後再看。\n")
    md.append("- **C-技術型反彈/先降級**：不要投入深度研究時間，除非後續重新轉強。\n")
    md.append("\n## 輸出\n")
    md.append(f"- csv: `{CSV}`")
    md.append(f"- manifest: `{MANIFEST}`")
    REPORT.write_text("\n".join(md), encoding="utf-8")
    MANIFEST.write_text(json.dumps({
        "snapshot_suffix": SNAPSHOT_SUFFIX,
        "input": str(ROUND15),
        "outputs": {"csv": str(CSV), "report": str(REPORT)},
        "rows": int(len(out)),
        "decision_counts": counts,
        "data_source": "local Magic26 parquet cache",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {CSV}")
    print(f"wrote {REPORT}")


if __name__ == "__main__":
    main()
