"""Magic26 round 15: manual priority review pack.

Research-only. Turns the Round-14 dashboard labels into a compact manual review
queue: main-spec A, non-weak, non-chase, liquid, floor15 observation first;
then separate weak/high-open/low-liquidity watch queues.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from magic26_paths import dash_root, out_dir, research_root, source_root  # noqa: E402

ROOT = research_root()
DASH = dash_root()
SOURCE = source_root()
OUT = out_dir()
DEFAULT_SNAPSHOT_SUFFIX = "20210101_20260701"
SNAPSHOT_SUFFIX = DEFAULT_SNAPSHOT_SUFFIX
INPUT = DASH / "public" / "data" / "magic26_candidates_history.csv"
REPORT = SOURCE / f"magic26_round15_priority_review_pack_{SNAPSHOT_SUFFIX}.md"
RANKED_CSV = OUT / f"magic26_round15_priority_review_ranked_{SNAPSHOT_SUFFIX}.csv"
WATCH_CSV = OUT / f"magic26_round15_priority_review_watch_{SNAPSHOT_SUFFIX}.csv"
MANIFEST = OUT / f"magic26_round15_priority_review_manifest_{SNAPSHOT_SUFFIX}.json"


def configure_paths(snapshot_suffix: str) -> None:
    global SNAPSHOT_SUFFIX, REPORT, RANKED_CSV, WATCH_CSV, MANIFEST
    SNAPSHOT_SUFFIX = snapshot_suffix
    REPORT = SOURCE / f"magic26_round15_priority_review_pack_{SNAPSHOT_SUFFIX}.md"
    RANKED_CSV = OUT / f"magic26_round15_priority_review_ranked_{SNAPSHOT_SUFFIX}.csv"
    WATCH_CSV = OUT / f"magic26_round15_priority_review_watch_{SNAPSHOT_SUFFIX}.csv"
    MANIFEST = OUT / f"magic26_round15_priority_review_manifest_{SNAPSHOT_SUFFIX}.json"


def is_true(v: Any) -> bool:
    return str(v).lower() in {"true", "1", "yes"}


def pct(v: Any) -> str:
    if pd.isna(v):
        return "—"
    return f"{float(v) * 100:.1f}%"


def money(v: Any) -> str:
    if pd.isna(v):
        return "—"
    return f"{float(v) / 1e8:.1f}億"


def stock_links(stock_id: Any) -> str:
    sid = str(stock_id).replace(".0", "")
    return (
        f"[YahooTW](https://tw.stock.yahoo.com/quote/{sid}.TW) / "
        f"[YahooTWO](https://tw.stock.yahoo.com/quote/{sid}.TWO) / "
        f"[Goodinfo](https://goodinfo.tw/tw/StockDetail.asp?STOCK_ID={sid}) / "
        f"[Wantgoo](https://www.wantgoo.com/stock/{sid})"
    )


def priority_score(r: pd.Series) -> int:
    score = 0
    if r["candidate"] == "A_repo50_c4_40_fixed20":
        score += 45
    if not is_true(r.get("is_high_open_risk", False)):
        score += 18
    if not is_true(r.get("is_low_liquidity_risk", False)):
        score += 15
    score += min(14, max(0, float(r.get("top5_volume_ratio_120") or 0) * 14))
    score += min(8, max(0, float(r.get("avg_amount_20d") or 0) / 1_000_000_000 * 2))
    if is_true(r.get("is_weak_momentum", False)):
        score -= 18
    return int(round(score))


def dedupe_prefer_adjusted(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    x["_mode_rank"] = x["price_mode"].map({"adjusted": 0, "raw": 1}).fillna(2)
    x = x.sort_values(["date", "stock_id", "_mode_rank"], ascending=[False, True, True])
    return x.drop_duplicates(["date", "stock_id", "candidate"], keep="first").drop(columns=["_mode_rank"])


def review_questions(r: pd.Series) -> str:
    checks = [
        "日K是否已貼近前高/創高後爆量長黑？",
        "訊號後是否仍有量縮不破或轉強K？",
        "產業/題材是否有近一季可驗證催化？",
    ]
    if r["industry_category"] in {"半導體業", "電子零組件業", "通信網路業", "電子工業"}:
        checks.append("是否屬 AI/高速傳輸/先進封裝/電源散熱鏈，且非純題材？")
    if r["industry_category"] == "金融保險":
        checks.append("金融股要看資金輪動與殖利率/併購重估，不要用科技股同一套題材框架。")
    return "；".join(checks)


def line(r: pd.Series, idx: int) -> str:
    return (
        f"{idx}. **{r.stock_id} {r.stock_name}**（{r.industry_category}｜{r.date}｜{r.price_mode}）\n"
        f"   - 分數/優先：{int(r.review_score)}｜{r.research_priority_zh}\n"
        f"   - 標籤：{r.research_tags}｜{r.momentum_bucket_zh}\n"
        f"   - 20D漲幅 {pct(r.ret_20d)}；repo量比 {pct(r.top5_volume_ratio_120)}；20D金額 {money(r.avg_amount_20d)}；隔日開盤 {pct(r.next_open_gap)}\n"
        f"   - 外部：{stock_links(r.stock_id)}\n"
        f"   - 覆盤問題：{r.review_questions}\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-suffix", default=DEFAULT_SNAPSHOT_SUFFIX)
    args = parser.parse_args()
    configure_paths(args.snapshot_suffix)

    df = pd.read_csv(INPUT)
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    a = df[df["candidate"].eq("A_repo50_c4_40_fixed20")].copy()
    recent = a[a["date"] >= "2026-01-01"].copy()
    recent = dedupe_prefer_adjusted(recent)
    recent["review_score"] = recent.apply(priority_score, axis=1)
    recent["review_questions"] = recent.apply(review_questions, axis=1)

    clean = recent[
        recent["is_floor15_observation"].map(is_true)
        & ~recent["is_weak_momentum"].map(is_true)
        & ~recent["is_high_open_risk"].map(is_true)
        & ~recent["is_low_liquidity_risk"].map(is_true)
    ].copy()
    clean = clean.sort_values(["review_score", "date", "avg_amount_20d"], ascending=[False, False, False])

    watch = recent[
        recent["is_weak_momentum"].map(is_true)
        | recent["is_high_open_risk"].map(is_true)
        | recent["is_low_liquidity_risk"].map(is_true)
    ].copy()
    watch = watch.sort_values(["date", "review_score"], ascending=[False, False])

    columns = [
        "date", "stock_id", "stock_name", "industry_category", "price_mode", "review_score",
        "research_priority_zh", "research_tags", "momentum_bucket_zh", "ret_20d",
        "top5_volume_ratio_120", "avg_amount_20d", "next_open_gap", "range_pos",
        "days_since_max_volume", "review_questions",
    ]
    clean[columns].to_csv(RANKED_CSV, index=False, encoding="utf-8-sig")
    watch[columns].to_csv(WATCH_CSV, index=False, encoding="utf-8-sig")

    md: list[str] = []
    md.append("# Magic26 第十五輪：主規格 A 人工覆盤優先清單（2026-07-01）\n")
    md.append("## 目的\n")
    md.append("承接 Round 14，不再微調 ret20 參數，而是把 dashboard 標籤轉成可人工覆盤的清單：主規格 A、非弱動能、非高開、非低流動、floor15觀察優先。\n")
    md.append("## 一眼結論\n")
    md.append(f"1. 2026 近期主規格 A 去重後共 **{len(recent)}** 檔/次；其中乾淨優先清單 **{len(clean)}** 檔/次，風險觀察 **{len(watch)}** 檔/次。\n")
    md.append("2. 這不是買進名單，是人工覆盤 queue：先看圖形/題材/產業脈絡，再決定是否放進 watchlist。\n")
    md.append("3. 弱動能、高開、低流動仍保留在 watch CSV，但不要混進第一優先清單。\n")
    md.append("\n## 第一優先：主規格 A / floor15 / 非高開 / 非低流動 / 非弱動能\n")
    for i, (_, r) in enumerate(clean.head(15).iterrows(), 1):
        md.append(line(r, i))
    md.append("\n## 風險觀察：弱動能 / 高開 / 低流動\n")
    for i, (_, r) in enumerate(watch.head(12).iterrows(), 1):
        md.append(line(r, i))
    md.append("\n## 覆盤規則\n")
    md.append("- **先看日K path**：訊號後是量縮不破、箱型整理、還是直接長黑破線。\n")
    md.append("- **再看題材脈絡**：只接受可驗證催化，避免純社群題材。\n")
    md.append("- **最後看交易條件**：高開、低流動、弱動能只降優先，不直接刪。\n")
    md.append("- **不要回頭改參數**：Round 14 已證明 floor15 改善不夠強，這輪目標是人工研究排序。\n")
    md.append("\n## 輸出\n")
    md.append(f"- ranked: `{RANKED_CSV}`")
    md.append(f"- watch: `{WATCH_CSV}`")
    md.append(f"- manifest: `{MANIFEST}`")
    REPORT.write_text("\n".join(md), encoding="utf-8")

    MANIFEST.write_text(json.dumps({
        "snapshot_suffix": SNAPSHOT_SUFFIX,
        "input": str(INPUT),
        "outputs": {"ranked": str(RANKED_CSV), "watch": str(WATCH_CSV), "report": str(REPORT)},
        "rows_recent_a_deduped": int(len(recent)),
        "rows_ranked": int(len(clean)),
        "rows_watch": int(len(watch)),
        "decision": "manual_review_queue_only_not_trading_signal",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {RANKED_CSV}")
    print(f"wrote {WATCH_CSV}")
    print(f"wrote {REPORT}")


if __name__ == "__main__":
    main()
