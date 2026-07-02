"""Magic26 Round 21: volume-gap right-tail / false-kill case review.

Research-only. Reviews cases where top1/top10 volume gap is flagged (>=2)
but 60D outcome still becomes a right-tail winner, then looks for simple
conditions that separate recoverable volume gaps from dangerous gaps.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path("C:/Users/abckf/research-brain")
BASE = ROOT / "sources" / "strategy-checks" / "magic26"
OUT = BASE / "out"
DEFAULT_SNAPSHOT_SUFFIX = "20210101_20260701"
SNAPSHOT_SUFFIX = DEFAULT_SNAPSHOT_SUFFIX
DETAIL = OUT / f"magic26_round19_author_absorption_detail_{SNAPSHOT_SUFFIX}.csv"
CASES_CSV = OUT / f"magic26_round21_volgap_rescue_cases_{SNAPSHOT_SUFFIX}.csv"
SUMMARY_CSV = OUT / f"magic26_round21_volgap_rescue_summary_{SNAPSHOT_SUFFIX}.csv"
REPORT = BASE / f"magic26_round21_volgap_rescue_review_report_{SNAPSHOT_SUFFIX}.md"
MANIFEST = OUT / f"magic26_round21_volgap_rescue_review_manifest_{SNAPSHOT_SUFFIX}.json"


def configure_paths(snapshot_suffix: str) -> None:
    global SNAPSHOT_SUFFIX, DETAIL, CASES_CSV, SUMMARY_CSV, REPORT, MANIFEST
    SNAPSHOT_SUFFIX = snapshot_suffix
    DETAIL = OUT / f"magic26_round19_author_absorption_detail_{SNAPSHOT_SUFFIX}.csv"
    CASES_CSV = OUT / f"magic26_round21_volgap_rescue_cases_{SNAPSHOT_SUFFIX}.csv"
    SUMMARY_CSV = OUT / f"magic26_round21_volgap_rescue_summary_{SNAPSHOT_SUFFIX}.csv"
    REPORT = BASE / f"magic26_round21_volgap_rescue_review_report_{SNAPSHOT_SUFFIX}.md"
    MANIFEST = OUT / f"magic26_round21_volgap_rescue_review_manifest_{SNAPSHOT_SUFFIX}.json"


def pct(x: Any) -> str:
    return "—" if pd.isna(x) else f"{float(x) * 100:.1f}%"


def num(x: Any) -> str:
    return "—" if pd.isna(x) else f"{float(x):.2f}"


def profit_factor(x: pd.Series) -> float:
    v = pd.to_numeric(x, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    gains = v[v > 0].sum()
    losses = -v[v < 0].sum()
    if losses == 0:
        return float("inf") if gains > 0 else float("nan")
    return float(gains / losses)


def summarize(g: pd.DataFrame, group: str, label: str, baseline_n: int | None = None) -> dict[str, Any]:
    v = g.dropna(subset=["t1_open_fwd_60d", "t1_open_excess_60d"]).copy()
    row: dict[str, Any] = {"group": group, "label": label, "trades": int(len(v))}
    if baseline_n:
        row["retention"] = len(v) / baseline_n
    if v.empty:
        return row
    ret = pd.to_numeric(v["t1_open_fwd_60d"], errors="coerce")
    excess = pd.to_numeric(v["t1_open_excess_60d"], errors="coerce")
    row.update(
        {
            "median_return_60d": float(ret.median()),
            "median_excess_60d": float(excess.median()),
            "win_excess_60d": float((excess > 0).mean()),
            "right_tail_50pct_60d": float((ret >= 0.50).mean()),
            "right_tail_100pct_60d": float((ret >= 1.00).mean()),
            "bad_loss_minus20pct_60d": float((ret <= -0.20).mean()),
            "pf_excess_60d": profit_factor(excess),
            "median_ret20": float(pd.to_numeric(v["ret_20d"], errors="coerce").median()),
            "median_ret60_signal": float(pd.to_numeric(v["ret_60d_signal"], errors="coerce").median()),
            "median_top1_top3": float(pd.to_numeric(v["top1_to_top3_volume_ratio"], errors="coerce").median()),
            "median_top1_top5": float(pd.to_numeric(v["top1_to_top5_volume_ratio"], errors="coerce").median()),
            "median_top1_top10": float(pd.to_numeric(v["top1_to_top10_volume_ratio"], errors="coerce").median()),
            "median_days_since_max_volume": float(pd.to_numeric(v["days_since_max_volume"], errors="coerce").median()),
            "median_range_pos": float(pd.to_numeric(v["range_pos"], errors="coerce").median()),
            "median_avg_amount_20d": float(pd.to_numeric(v["avg_amount_20d"], errors="coerce").median()),
        }
    )
    return row


def classify_case(row: pd.Series) -> str:
    ret = row.get("t1_open_fwd_60d")
    if pd.isna(ret):
        return "未成熟"
    if ret >= 1.0:
        return "超級右尾>=100%"
    if ret >= 0.5:
        return "右尾>=50%"
    if ret >= 0.2:
        return "小右尾20-50%"
    if ret <= -0.2:
        return "大虧<=-20%"
    if ret < 0:
        return "失敗<0%"
    return "普通0-20%"


def rescue_pattern(row: pd.Series) -> str:
    tags: list[str] = []
    t3 = row.get("top1_to_top3_volume_ratio")
    t5 = row.get("top1_to_top5_volume_ratio")
    t10 = row.get("top1_to_top10_volume_ratio")
    ret20 = row.get("ret_20d")
    ret60 = row.get("ret_60d_signal")
    days = row.get("days_since_max_volume")
    rng = row.get("range_pos")
    amount = row.get("avg_amount_20d")

    if pd.notna(t10) and t10 >= 3:
        tags.append("top10極端斷層")
    elif pd.notna(t10) and t10 >= 2:
        tags.append("top10斷層")
    if pd.notna(t3) and t3 < 1.5:
        tags.append("top3不斷層")
    if pd.notna(t5) and t5 < 2:
        tags.append("top5可接受")
    if pd.notna(ret20) and ret20 < 0.25:
        tags.append("ret20未過熱")
    elif pd.notna(ret20) and ret20 >= 0.35:
        tags.append("ret20偏熱")
    if pd.notna(ret60) and ret60 <= 0.8:
        tags.append("ret60未極熱")
    elif pd.notna(ret60) and ret60 > 1.5:
        tags.append("ret60過熱")
    if pd.notna(days) and 20 <= days <= 90:
        tags.append("最大量距離適中")
    elif pd.notna(days) and days <= 10:
        tags.append("最大量太近")
    if pd.notna(rng) and rng < 0.8:
        tags.append("區間未頂滿")
    elif pd.notna(rng) and rng >= 0.9:
        tags.append("高位區間")
    if pd.notna(amount) and amount >= 1_000_000_000:
        tags.append("大型成交金額")
    return ";".join(tags)


def build_cases(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["flag_top10_gap_ge2"] = out["top1_to_top10_volume_ratio"].ge(2.0)
    out["case_class_60d"] = out.apply(classify_case, axis=1)
    out["rescue_pattern_tags"] = out.apply(rescue_pattern, axis=1)
    out["is_flagged_right_tail"] = out["flag_top10_gap_ge2"] & out["t1_open_fwd_60d"].ge(0.5)
    out["is_flagged_failure"] = out["flag_top10_gap_ge2"] & out["t1_open_fwd_60d"].lt(0)
    out["is_flagged_mature"] = out["flag_top10_gap_ge2"] & out["t1_open_fwd_60d"].notna()
    keep = [
        "date", "stock_id", "stock_name", "industry_category", "price_mode", "case_class_60d",
        "ret_20d", "ret_60d_signal", "range_pos", "days_since_max_volume", "avg_amount_20d",
        "signal_day_ret_1d", "next_open_gap", "top1_to_top3_volume_ratio", "top1_to_top5_volume_ratio",
        "top1_to_top10_volume_ratio", "risk_long_ma_score", "t1_open_fwd_60d", "t1_open_excess_60d",
        "fixed20_ret", "t1_open_excess_20d", "flag_top10_gap_ge2", "is_flagged_right_tail",
        "is_flagged_failure", "rescue_pattern_tags",
    ]
    return out[[c for c in keep if c in out.columns]].sort_values(
        ["price_mode", "is_flagged_right_tail", "t1_open_fwd_60d"], ascending=[True, False, False]
    )


def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for mode, mdf in df.groupby("price_mode"):
        mature = mdf.dropna(subset=["t1_open_fwd_60d", "t1_open_excess_60d"])
        base_n = len(mature)
        flagged = mdf[mdf["top1_to_top10_volume_ratio"].ge(2.0)]
        clean = mdf[mdf["top1_to_top10_volume_ratio"].lt(2.0)]
        rows.append(summarize(mdf, "baseline", f"{mode}: baseline", base_n))
        rows.append(summarize(clean, "top10_gap", f"{mode}: top1/top10 < 2", base_n))
        rows.append(summarize(flagged, "top10_gap_flagged", f"{mode}: flagged top1/top10 >= 2", base_n))

        # Candidate rescue conditions inside flagged top10 gap.
        rules = [
            ("top3_ok", flagged[flagged["top1_to_top3_volume_ratio"].lt(1.5)], f"{mode}: flagged + top3<1.5"),
            ("top5_ok", flagged[flagged["top1_to_top5_volume_ratio"].lt(2.0)], f"{mode}: flagged + top5<2"),
            ("ret20_cool", flagged[flagged["ret_20d"].lt(0.25)], f"{mode}: flagged + ret20<25%"),
            ("ret60_not_hot", flagged[flagged["ret_60d_signal"].le(0.8)], f"{mode}: flagged + ret60<=80%"),
            ("not_high_range", flagged[flagged["range_pos"].lt(0.8)], f"{mode}: flagged + range_pos<80%"),
            ("mid_volume_age", flagged[flagged["days_since_max_volume"].between(20, 90, inclusive="both")], f"{mode}: flagged + maxVol 20-90d"),
            ("liquid", flagged[flagged["avg_amount_20d"].ge(1_000_000_000)], f"{mode}: flagged + amount>=10億"),
            (
                "rescue_combo",
                flagged[
                    flagged["top1_to_top10_volume_ratio"].lt(2.2)
                    & flagged["top1_to_top3_volume_ratio"].lt(1.5)
                    & flagged["ret_60d_signal"].le(0.8)
                ],
                f"{mode}: rescue candidate top10<2.2 + top3<1.5 + ret60<=80%",
            ),
            (
                "danger_combo",
                flagged[
                    flagged["top1_to_top10_volume_ratio"].ge(2.5)
                    | flagged["ret_60d_signal"].gt(0.8)
                ],
                f"{mode}: danger candidate top10>=2.5 or ret60>80%",
            ),
        ]
        for group, part, label in rules:
            rows.append(summarize(part, group, label, base_n))
    return pd.DataFrame(rows)


def fmt_line(r: pd.Series) -> str:
    return (
        f"n={int(r.trades)}，保留 {pct(r.get('retention'))}，"
        f"60D中位 {pct(r.get('median_return_60d'))}，"
        f"60D excess中位 {pct(r.get('median_excess_60d'))}，"
        f"勝率 {pct(r.get('win_excess_60d'))}，"
        f"50%右尾 {pct(r.get('right_tail_50pct_60d'))}，"
        f"100%右尾 {pct(r.get('right_tail_100pct_60d'))}，"
        f"-20%大虧 {pct(r.get('bad_loss_minus20pct_60d'))}"
    )


def by_label(summary: pd.DataFrame, label: str) -> pd.Series | None:
    rows = summary[summary["label"].eq(label)]
    return None if rows.empty else rows.iloc[0]


def write_report(summary: pd.DataFrame, cases: pd.DataFrame) -> None:
    md: list[str] = []
    md.append("# Magic26 Round 21：大量斷層右尾 / 誤殺案例 review（2026-07-01）\n")
    md.append("## 目的\n")
    md.append("Round 20 顯示 `top1/top10<2` 的 60D 右尾率明顯較好，但 `top1/top10>=2` 仍存在右尾反例。本輪逐檔檢查 flagged cases，找『大量斷層可救』與『危險斷層』的簡單分界。\n")
    md.append("## 方法限制\n")
    md.append("- 使用 Round19 enriched Candidate-A detail；決策仍以 adjusted 為主。\n")
    md.append("- 右尾定義：60D 報酬 >= 50%。\n")
    md.append("- 這是 case-review / research-routing，不改主規格、不產生買賣訊號。\n")

    md.append("\n## A. adjusted 主要比較\n")
    for label in [
        "adj: baseline",
        "adj: top1/top10 < 2",
        "adj: flagged top1/top10 >= 2",
        "adj: flagged + top5<2",
        "adj: flagged + ret60<=80%",
        "adj: flagged + range_pos<80%",
        "adj: rescue candidate top10<2.2 + top3<1.5 + ret60<=80%",
        "adj: danger candidate top10>=2.5 or ret60>80%",
    ]:
        r = by_label(summary, label)
        if r is not None:
            md.append(f"- `{label}`：{fmt_line(r)}")

    adj_cases = cases[(cases["price_mode"].eq("adj")) & (cases["flag_top10_gap_ge2"]) & (cases["t1_open_fwd_60d"].notna())].copy()
    right_tail = adj_cases[adj_cases["t1_open_fwd_60d"].ge(0.5)].sort_values("t1_open_fwd_60d", ascending=False)
    fail = adj_cases[adj_cases["t1_open_fwd_60d"].lt(0)].sort_values("t1_open_fwd_60d")

    md.append("\n## B. top1/top10>=2 但 60D 仍右尾的反例\n")
    if right_tail.empty:
        md.append("- 無。")
    else:
        for _, r in right_tail.iterrows():
            md.append(
                f"- `{r.date} {int(r.stock_id)} {r.stock_name}`：60D {pct(r.t1_open_fwd_60d)}，excess {pct(r.t1_open_excess_60d)}，"
                f"top10 {num(r.top1_to_top10_volume_ratio)}，top5 {num(r.top1_to_top5_volume_ratio)}，top3 {num(r.top1_to_top3_volume_ratio)}，"
                f"ret20 {pct(r.ret_20d)}，ret60訊號 {pct(r.ret_60d_signal)}，tags={r.rescue_pattern_tags}"
            )

    md.append("\n## C. top1/top10>=2 且 60D 失敗的案例\n")
    if fail.empty:
        md.append("- 無。")
    else:
        for _, r in fail.head(12).iterrows():
            md.append(
                f"- `{r.date} {int(r.stock_id)} {r.stock_name}`：60D {pct(r.t1_open_fwd_60d)}，excess {pct(r.t1_open_excess_60d)}，"
                f"top10 {num(r.top1_to_top10_volume_ratio)}，top5 {num(r.top1_to_top5_volume_ratio)}，ret20 {pct(r.ret_20d)}，ret60訊號 {pct(r.ret_60d_signal)}，tags={r.rescue_pattern_tags}"
            )

    md.append("\n## 初步決策\n")
    md.append("1. `top1/top10>=2` 不應當硬 veto，因為右尾反例存在；但整體右尾率明顯變差，應維持負分。\n")
    md.append("2. 可救條件初版非常窄：`top1/top10<2.2`、`top1/top3<1.5`、`ret60_signal<=80%` 同時成立，可標成 `大量斷層可救觀察`；這不是加分，只是避免誤殺。\n")
    md.append("3. 危險條件初版：`top1/top10>=2.5` 或 `ret60_signal>80%`，標成 `危險斷層`；樣本中這群幾乎沒有 50% 右尾，排序應明顯下調。\n")
    md.append("4. 下一步若要產品化：dashboard 加一個 `volgap_subtype_zh` 欄位，值為 `正常 / 可救斷層 / 危險斷層 / 待補`，比單純大量斷層更有用。\n")

    md.append("\n## 輸出\n")
    for p in [SUMMARY_CSV, CASES_CSV, MANIFEST]:
        md.append(f"- `{p}`")
    REPORT.write_text("\n".join(md), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-suffix", default=DEFAULT_SNAPSHOT_SUFFIX)
    args = parser.parse_args()
    configure_paths(args.snapshot_suffix)

    df = pd.read_csv(DETAIL)
    df["date"] = pd.to_datetime(df["date"])
    numeric = [
        "ret_20d", "ret_60d_signal", "range_pos", "days_since_max_volume", "avg_amount_20d",
        "signal_day_ret_1d", "next_open_gap", "top1_to_top3_volume_ratio", "top1_to_top5_volume_ratio",
        "top1_to_top10_volume_ratio", "risk_long_ma_score", "t1_open_fwd_60d", "t1_open_excess_60d",
        "fixed20_ret", "t1_open_excess_20d",
    ]
    for col in numeric:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    cases = build_cases(df)
    summary = build_summary(df)
    cases.to_csv(CASES_CSV, index=False, encoding="utf-8-sig")
    summary.to_csv(SUMMARY_CSV, index=False, encoding="utf-8-sig")
    write_report(summary, cases)
    MANIFEST.write_text(
        json.dumps(
            {
                "snapshot_suffix": SNAPSHOT_SUFFIX,
                "source_detail": str(DETAIL),
                "outputs": {"summary": str(SUMMARY_CSV), "cases": str(CASES_CSV), "report": str(REPORT)},
                "rows_source": int(len(df)),
                "rows_cases": int(len(cases)),
                "rows_summary": int(len(summary)),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"wrote {SUMMARY_CSV}")
    print(f"wrote {CASES_CSV}")
    print(f"wrote {REPORT}")


if __name__ == "__main__":
    main()
