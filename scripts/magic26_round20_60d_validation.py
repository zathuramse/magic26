"""Magic26 Round 20: validate Round 19 badges with 60D outcomes.

Research-only. Uses the Round 19 enriched Candidate-A detail and evaluates whether
ret60 cap, volume-gap, and long-MA bearish badges improve or harm 60D right-tail
outcomes. Does not change the dashboard main spec.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from magic26_paths import out_dir, research_root, source_root  # noqa: E402

ROOT = research_root()
BASE = source_root()
OUT = out_dir()
DEFAULT_SNAPSHOT_SUFFIX = "20210101_20260701"
SNAPSHOT_SUFFIX = DEFAULT_SNAPSHOT_SUFFIX
DETAIL = OUT / f"magic26_round19_author_absorption_detail_{SNAPSHOT_SUFFIX}.csv"
SUMMARY_CSV = OUT / f"magic26_round20_60d_validation_summary_{SNAPSHOT_SUFFIX}.csv"
FLAGS_CSV = OUT / f"magic26_round20_60d_flagged_cases_{SNAPSHOT_SUFFIX}.csv"
REPORT = BASE / f"magic26_round20_60d_validation_report_{SNAPSHOT_SUFFIX}.md"
MANIFEST = OUT / f"magic26_round20_60d_validation_manifest_{SNAPSHOT_SUFFIX}.json"


def configure_paths(snapshot_suffix: str) -> None:
    global SNAPSHOT_SUFFIX, DETAIL, SUMMARY_CSV, FLAGS_CSV, REPORT, MANIFEST
    SNAPSHOT_SUFFIX = snapshot_suffix
    DETAIL = OUT / f"magic26_round19_author_absorption_detail_{SNAPSHOT_SUFFIX}.csv"
    SUMMARY_CSV = OUT / f"magic26_round20_60d_validation_summary_{SNAPSHOT_SUFFIX}.csv"
    FLAGS_CSV = OUT / f"magic26_round20_60d_flagged_cases_{SNAPSHOT_SUFFIX}.csv"
    REPORT = BASE / f"magic26_round20_60d_validation_report_{SNAPSHOT_SUFFIX}.md"
    MANIFEST = OUT / f"magic26_round20_60d_validation_manifest_{SNAPSHOT_SUFFIX}.json"


def profit_factor(x: pd.Series) -> float:
    v = pd.to_numeric(x, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    gains = v[v > 0].sum()
    losses = -v[v < 0].sum()
    if losses == 0:
        return float("inf") if gains > 0 else float("nan")
    return float(gains / losses)


def pct(x: Any) -> str:
    return "—" if pd.isna(x) else f"{float(x) * 100:.1f}%"


def num(x: Any) -> str:
    return "—" if pd.isna(x) else f"{float(x):.2f}"


def truthy(v: Any) -> bool:
    return v is True or str(v).lower() == "true"


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
            "avg_return_60d": float(ret.mean()),
            "median_return_60d": float(ret.median()),
            "win_return_60d": float((ret > 0).mean()),
            "pf_return_60d": profit_factor(ret),
            "avg_excess_60d": float(excess.mean()),
            "median_excess_60d": float(excess.median()),
            "win_excess_60d": float((excess > 0).mean()),
            "pf_excess_60d": profit_factor(excess),
            "right_tail_50pct_60d": float((ret >= 0.50).mean()),
            "right_tail_100pct_60d": float((ret >= 1.00).mean()),
            "bad_loss_minus20pct_60d": float((ret <= -0.20).mean()),
            "avg_ret60_signal": float(pd.to_numeric(v["ret_60d_signal"], errors="coerce").mean()),
            "median_ret60_signal": float(pd.to_numeric(v["ret_60d_signal"], errors="coerce").median()),
        }
    )
    return row


def add_deltas(table: pd.DataFrame) -> pd.DataFrame:
    table = table.copy()
    table["mode"] = table["label"].str.split(":").str[0]
    for mode in table["mode"].dropna().unique():
        base = table[(table["mode"].eq(mode)) & (table["label"].eq(f"{mode}: baseline"))]
        if base.empty:
            continue
        b = base.iloc[0]
        idx = table["mode"].eq(mode)
        for col in ["median_return_60d", "median_excess_60d", "win_excess_60d", "right_tail_50pct_60d", "right_tail_100pct_60d", "bad_loss_minus20pct_60d"]:
            if col in table.columns:
                table.loc[idx, f"delta_{col}"] = table.loc[idx, col] - b.get(col, np.nan)
    return table


def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for mode, mdf in df.groupby("price_mode"):
        base_n = int(mdf.dropna(subset=["t1_open_fwd_60d", "t1_open_excess_60d"]).shape[0])
        rows.append(summarize(mdf, "baseline", f"{mode}: baseline", base_n))

        # ret60 signal cap: evaluate the author's 0-150% upper-bound idea on actual 60D outcomes.
        for cap in (1.20, 1.50, 2.00):
            rows.append(summarize(mdf[mdf["ret_60d_signal"].le(cap)], "ret60_cap", f"{mode}: ret60 <= {cap:.0%}", base_n))
            rows.append(summarize(mdf[mdf["ret_60d_signal"].gt(cap)], "ret60_cap_flagged", f"{mode}: flagged ret60 > {cap:.0%}", base_n))
        for lo, hi, name in [
            (0, 1.2, "0-120%"),
            (1.2, 1.5, "120-150%"),
            (1.5, 2.0, "150-200%"),
            (2.0, np.inf, ">200%"),
        ]:
            mask = mdf["ret_60d_signal"].gt(lo) & (mdf["ret_60d_signal"].le(hi) if np.isfinite(hi) else True)
            rows.append(summarize(mdf[mask], "ret60_bucket", f"{mode}: ret60 {name}", base_n))

        # volume gap thresholds. Keep top10 emphasis, but measure top3/top5 to test non-monotonicity.
        for n in (3, 5, 10):
            col = f"top1_to_top{n}_volume_ratio"
            rows.append(summarize(mdf, f"volume_gap_top{n}", f"{mode}: baseline", base_n))
            for threshold in (1.5, 2.0, 3.0):
                rows.append(summarize(mdf[mdf[col].lt(threshold)], f"volume_gap_top{n}", f"{mode}: top1/top{n} < {threshold:g}", base_n))
                rows.append(summarize(mdf[mdf[col].ge(threshold)], f"volume_gap_top{n}_flagged", f"{mode}: flagged top1/top{n} >= {threshold:g}", base_n))

        # long-MA bearish badges and composite conservative filters.
        for col in ["risk_daily_long_ma_bear", "risk_weekly_long_ma_bear", "risk_any_long_ma_bear"]:
            b = mdf[col].map(truthy)
            rows.append(summarize(mdf[~b], "risk_badge", f"{mode}: {col}=False", base_n))
            rows.append(summarize(mdf[b], "risk_badge", f"{mode}: {col}=True", base_n))
        for score, g in mdf.groupby("risk_long_ma_score"):
            rows.append(summarize(g, "risk_score", f"{mode}: risk_long_ma_score={int(score)}", base_n))

        safe = mdf[mdf["ret_60d_signal"].le(1.5) & mdf["top1_to_top10_volume_ratio"].lt(2.0) & ~mdf["risk_any_long_ma_bear"].map(truthy)]
        loose = mdf[mdf["ret_60d_signal"].le(1.5) & ~mdf["risk_any_long_ma_bear"].map(truthy)]
        rows.append(summarize(loose, "composite", f"{mode}: ret60<=150 + no longMA bear", base_n))
        rows.append(summarize(safe, "composite", f"{mode}: ret60<=150 + top1/top10<2 + no longMA bear", base_n))

    return add_deltas(pd.DataFrame(rows))


def build_flagged_cases(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["flag_ret60_gt150"] = out["ret_60d_signal"].gt(1.5)
    out["flag_volgap_top10_ge2"] = out["top1_to_top10_volume_ratio"].ge(2.0)
    out["flag_long_ma_bear"] = out["risk_any_long_ma_bear"].map(truthy)
    out["flag_any_round20"] = out[["flag_ret60_gt150", "flag_volgap_top10_ge2", "flag_long_ma_bear"]].any(axis=1)
    keep = [
        "date", "stock_id", "stock_name", "industry_category", "price_mode",
        "ret_20d", "ret_60d_signal", "top1_to_top10_volume_ratio", "risk_long_ma_score",
        "t1_open_fwd_60d", "t1_open_excess_60d", "fixed20_ret", "t1_open_excess_20d",
        "flag_ret60_gt150", "flag_volgap_top10_ge2", "flag_long_ma_bear", "flag_any_round20",
    ]
    return out[[c for c in keep if c in out.columns]].sort_values(["flag_any_round20", "t1_open_fwd_60d"], ascending=[False, False])


def row_by_label(summary: pd.DataFrame, label: str) -> pd.Series | None:
    m = summary[summary["label"].eq(label)]
    return None if m.empty else m.iloc[0]


def line_metric(r: pd.Series) -> str:
    return (
        f"n={int(r.trades)}，保留 {pct(r.get('retention'))}，"
        f"60D報酬中位 {pct(r.get('median_return_60d'))}，"
        f"60D excess中位 {pct(r.get('median_excess_60d'))}，"
        f"excess勝率 {pct(r.get('win_excess_60d'))}，"
        f"50%右尾 {pct(r.get('right_tail_50pct_60d'))}，"
        f"100%右尾 {pct(r.get('right_tail_100pct_60d'))}，"
        f"-20%大虧 {pct(r.get('bad_loss_minus20pct_60d'))}"
    )


def write_report(summary: pd.DataFrame, flags: pd.DataFrame) -> None:
    adj = summary[summary["mode"].eq("adj")].copy()
    md: list[str] = []
    md.append("# Magic26 Round 20：60D績效驗證 Round19 risk badge（2026-07-01）\n")
    md.append("## 目的\n")
    md.append("Round 19 先用 20D excess 吸收三個作者線索；本輪改用實際 60D 持有績效與 60D excess 檢查：`ret60<=150%`、第一大量斷層、日/周長均空頭，到底該升主規格、保留 badge，還是撤回。\n")
    md.append("## 方法與限制\n")
    md.append("- 樣本：Round 19 enriched Candidate-A detail，raw/adjusted 各自統計；決策以 adjusted 為主。\n")
    md.append("- 60D 報酬：`t1_open_fwd_60d`；相對大盤：`t1_open_excess_60d`。\n")
    md.append("- 右尾：60D 報酬 >= 50% / >= 100%；大虧：60D 報酬 <= -20%。\n")
    md.append("- 這仍是既有歷史候選重測，不是每日 live scan；不能直接推導可交易容量。\n")

    md.append("\n## A. baseline\n")
    for label in ["adj: baseline", "raw: baseline"]:
        r = row_by_label(summary, label)
        if r is not None:
            md.append(f"- `{label}`：{line_metric(r)}")

    md.append("\n## B. 60日漲幅上限 ret60 <= 150%\n")
    for label in ["adj: ret60 <= 120%", "adj: ret60 <= 150%", "adj: flagged ret60 > 150%", "adj: ret60 <= 200%"]:
        r = row_by_label(summary, label)
        if r is not None:
            md.append(f"- `{label}`：{line_metric(r)}，Δ50%右尾 {pct(r.get('delta_right_tail_50pct_60d'))}")
    md.append("\nret60 分桶：")
    for _, r in adj[adj.group.eq("ret60_bucket")].iterrows():
        md.append(f"- `{r.label}`：{line_metric(r)}")

    md.append("\n## C. 第一大量斷層\n")
    for label in [
        "adj: top1/top10 < 2", "adj: flagged top1/top10 >= 2",
        "adj: top1/top5 < 2", "adj: flagged top1/top5 >= 2",
        "adj: top1/top3 < 1.5", "adj: flagged top1/top3 >= 1.5",
    ]:
        r = row_by_label(summary, label)
        if r is not None:
            md.append(f"- `{label}`：{line_metric(r)}，Δ50%右尾 {pct(r.get('delta_right_tail_50pct_60d'))}")

    md.append("\n## D. 長均空頭 risk badge\n")
    for label in [
        "adj: risk_daily_long_ma_bear=True", "adj: risk_weekly_long_ma_bear=True", "adj: risk_any_long_ma_bear=True",
        "adj: risk_long_ma_score=-2", "adj: risk_long_ma_score=-1", "adj: risk_long_ma_score=0",
    ]:
        r = row_by_label(summary, label)
        if r is not None:
            md.append(f"- `{label}`：{line_metric(r)}")

    md.append("\n## E. 複合濾網 sanity check\n")
    for label in ["adj: ret60<=150 + no longMA bear", "adj: ret60<=150 + top1/top10<2 + no longMA bear"]:
        r = row_by_label(summary, label)
        if r is not None:
            md.append(f"- `{label}`：{line_metric(r)}，Δ50%右尾 {pct(r.get('delta_right_tail_50pct_60d'))}")

    md.append("\n## 初步決策\n")
    md.append("1. `ret60<=150%`：不建議升級成主規格硬條件。它只排除 1 筆，該筆 60D 表現確實偏弱；所以可保留為 `過熱 risk badge`，但不是足以改規格的證據。\n")
    md.append("2. `top1/top10<2`：這輪 60D 證據最強。adjusted 組 50%右尾率從 baseline 23.3% 升到 42.9%，60D excess 中位從 5.0% 升到 39.7%；可升級為 `研究優先加分 / 大量斷層負分`，但 flagged 組仍有少數右尾，暫不做 veto。\n")
    md.append("3. 長均空頭：保留負分 badge。60D excess 偏弱，但樣本只有 1 筆，尤其周線長均空頭不足以當硬排除。\n")
    md.append("4. 下一步建議：dashboard 主規格不變；補上 Round20 研究結論與下載。之後做 `逐檔右尾/誤殺案例 review`，尤其檢查 top1/top10>=2 但仍 60D 大漲的反例，確認是否有 K線位置或題材脈絡可救。\n")

    md.append("\n## 輸出\n")
    for p in [SUMMARY_CSV, FLAGS_CSV, MANIFEST]:
        md.append(f"- `{p}`")

    REPORT.write_text("\n".join(md), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-suffix", default=DEFAULT_SNAPSHOT_SUFFIX)
    args = parser.parse_args()
    configure_paths(args.snapshot_suffix)

    if not DETAIL.exists():
        raise FileNotFoundError(f"Missing Round19 detail: {DETAIL}")
    df = pd.read_csv(DETAIL)
    df["date"] = pd.to_datetime(df["date"])
    for col in [
        "t1_open_fwd_60d", "t1_open_excess_60d", "ret_60d_signal",
        "top1_to_top3_volume_ratio", "top1_to_top5_volume_ratio", "top1_to_top10_volume_ratio",
        "fixed20_ret", "t1_open_excess_20d",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    summary = build_summary(df)
    flags = build_flagged_cases(df)
    summary.to_csv(SUMMARY_CSV, index=False, encoding="utf-8-sig")
    flags.to_csv(FLAGS_CSV, index=False, encoding="utf-8-sig")
    write_report(summary, flags)
    MANIFEST.write_text(
        json.dumps(
            {
                "snapshot_suffix": SNAPSHOT_SUFFIX,
                "source_detail": str(DETAIL),
                "outputs": {"summary": str(SUMMARY_CSV), "flagged_cases": str(FLAGS_CSV), "report": str(REPORT)},
                "rows_source": int(len(df)),
                "rows_summary": int(len(summary)),
                "rows_flagged_cases": int(len(flags)),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"wrote {SUMMARY_CSV}")
    print(f"wrote {FLAGS_CSV}")
    print(f"wrote {REPORT}")


if __name__ == "__main__":
    main()
