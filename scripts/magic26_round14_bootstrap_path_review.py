"""Magic26 round 14: baseline vs floor15 bootstrap + path review.

Research-only. Compares Candidate A original ret20 range (0, 40%) against
A-MomentumFloor (15, 40%) using bootstrap, then reviews the excluded ret20<15
trades to decide whether to change the main spec or only add a weak-momentum
risk label.
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
DETAIL = OUT / f"magic26_round8_tradeability_detail_{SNAPSHOT_SUFFIX}.csv"
REPORT = BASE / f"magic26_round14_bootstrap_path_review_report_{SNAPSHOT_SUFFIX}.md"
BOOTSTRAP_CSV = OUT / f"magic26_round14_bootstrap_summary_{SNAPSHOT_SUFFIX}.csv"
PATH_CSV = OUT / f"magic26_round14_excluded_weak_momentum_path_review_{SNAPSHOT_SUFFIX}.csv"
YEARLY_CSV = OUT / f"magic26_round14_baseline_vs_floor15_yearly_{SNAPSHOT_SUFFIX}.csv"
MANIFEST = OUT / f"magic26_round14_bootstrap_path_manifest_{SNAPSHOT_SUFFIX}.json"


def configure_paths(snapshot_suffix: str) -> None:
    global SNAPSHOT_SUFFIX, DETAIL, REPORT, BOOTSTRAP_CSV, PATH_CSV, YEARLY_CSV, MANIFEST
    SNAPSHOT_SUFFIX = snapshot_suffix
    DETAIL = OUT / f"magic26_round8_tradeability_detail_{SNAPSHOT_SUFFIX}.csv"
    REPORT = BASE / f"magic26_round14_bootstrap_path_review_report_{SNAPSHOT_SUFFIX}.md"
    BOOTSTRAP_CSV = OUT / f"magic26_round14_bootstrap_summary_{SNAPSHOT_SUFFIX}.csv"
    PATH_CSV = OUT / f"magic26_round14_excluded_weak_momentum_path_review_{SNAPSHOT_SUFFIX}.csv"
    YEARLY_CSV = OUT / f"magic26_round14_baseline_vs_floor15_yearly_{SNAPSHOT_SUFFIX}.csv"
    MANIFEST = OUT / f"magic26_round14_bootstrap_path_manifest_{SNAPSHOT_SUFFIX}.json"
MAIN = "candidate_a_repo50_c440_c5gt5"
N_BOOT = 20_000
SEED = 260622


def pf(x: pd.Series) -> float:
    x = pd.to_numeric(x, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    gains = x[x > 0].sum()
    losses = -x[x < 0].sum()
    if losses == 0:
        return np.inf if gains > 0 else np.nan
    return float(gains / losses)


def metric_row(df: pd.DataFrame, name: str, mode: str) -> dict[str, Any]:
    v = df.dropna(subset=["t1_open_excess_20d", "fixed20_ret"]).copy()
    out: dict[str, Any] = {"price_mode": mode, "variant": name, "trades": int(len(v))}
    if v.empty:
        return out
    out.update({
        "median_excess": float(v["t1_open_excess_20d"].median()),
        "avg_excess": float(v["t1_open_excess_20d"].mean()),
        "win_excess": float((v["t1_open_excess_20d"] > 0).mean()),
        "pf_excess": pf(v["t1_open_excess_20d"]),
        "median_return": float(v["fixed20_ret"].median()),
        "win_return": float((v["fixed20_ret"] > 0).mean()),
        "median_mae20": float(v["mae20"].median()),
        "median_mfe20": float(v["mfe20"].median()),
        "pct_mae20_le_minus8": float((v["mae20"] <= -0.08).mean()),
        "pct_mfe20_ge20": float((v["mfe20"] >= 0.20).mean()),
    })
    return out


def bootstrap_compare(base: pd.DataFrame, floor: pd.DataFrame, mode: str) -> dict[str, Any]:
    rng = np.random.default_rng(SEED + (0 if mode == "adj" else 1000))
    b = base["t1_open_excess_20d"].dropna().to_numpy(float)
    f = floor["t1_open_excess_20d"].dropna().to_numpy(float)
    bret = base["fixed20_ret"].dropna().to_numpy(float)
    fret = floor["fixed20_ret"].dropna().to_numpy(float)
    diffs_med = np.empty(N_BOOT)
    diffs_win = np.empty(N_BOOT)
    diffs_ret_med = np.empty(N_BOOT)
    for i in range(N_BOOT):
        bs = rng.choice(b, size=len(b), replace=True)
        fs = rng.choice(f, size=len(f), replace=True)
        brs = rng.choice(bret, size=len(bret), replace=True)
        frs = rng.choice(fret, size=len(fret), replace=True)
        diffs_med[i] = np.median(fs) - np.median(bs)
        diffs_win[i] = np.mean(fs > 0) - np.mean(bs > 0)
        diffs_ret_med[i] = np.median(frs) - np.median(brs)
    return {
        "price_mode": mode,
        "baseline_n": int(len(b)),
        "floor15_n": int(len(f)),
        "observed_delta_median_excess": float(np.median(f) - np.median(b)),
        "boot_delta_median_excess_mean": float(diffs_med.mean()),
        "boot_delta_median_excess_p05": float(np.quantile(diffs_med, 0.05)),
        "boot_delta_median_excess_p50": float(np.quantile(diffs_med, 0.50)),
        "boot_delta_median_excess_p95": float(np.quantile(diffs_med, 0.95)),
        "prob_delta_median_excess_gt0": float(np.mean(diffs_med > 0)),
        "observed_delta_win_excess": float(np.mean(f > 0) - np.mean(b > 0)),
        "boot_delta_win_excess_p05": float(np.quantile(diffs_win, 0.05)),
        "boot_delta_win_excess_p50": float(np.quantile(diffs_win, 0.50)),
        "boot_delta_win_excess_p95": float(np.quantile(diffs_win, 0.95)),
        "prob_delta_win_excess_gt0": float(np.mean(diffs_win > 0)),
        "observed_delta_median_return": float(np.median(fret) - np.median(bret)),
        "boot_delta_median_return_p05": float(np.quantile(diffs_ret_med, 0.05)),
        "boot_delta_median_return_p50": float(np.quantile(diffs_ret_med, 0.50)),
        "boot_delta_median_return_p95": float(np.quantile(diffs_ret_med, 0.95)),
        "prob_delta_median_return_gt0": float(np.mean(diffs_ret_med > 0)),
    }


def bucket_loss_reason(row: pd.Series) -> str:
    ex = row["t1_open_excess_20d"]
    if pd.isna(ex):
        return "no_forward"
    if ex >= 0:
        return "winner"
    if row.get("mae20", 0) <= -0.15:
        return "deep_drawdown"
    if row.get("mfe20", 0) >= 0.15 and ex < 0:
        return "gave_back_after_mfe"
    if row.get("mfe20", 0) < 0.08:
        return "no_upside_followthrough"
    return "mild_loss"


def path_review(excluded: pd.DataFrame, mode: str) -> pd.DataFrame:
    if excluded.empty:
        return pd.DataFrame()
    rows = []
    x = excluded.copy()
    x["path_class"] = x.apply(bucket_loss_reason, axis=1)
    for key in ["year", "industry_category", "path_class"]:
        for val, g in x.groupby(key, dropna=False):
            rows.append({
                "price_mode": mode,
                "slice_type": key,
                "slice_value": str(val),
                "trades": int(len(g)),
                "median_excess": float(g["t1_open_excess_20d"].median()),
                "win_excess": float((g["t1_open_excess_20d"] > 0).mean()),
                "median_return": float(g["fixed20_ret"].median()),
                "median_ret20_signal": float(g["ret_20d"].median()),
                "median_mae20": float(g["mae20"].median()),
                "median_mfe20": float(g["mfe20"].median()),
                "pct_mae20_le_minus8": float((g["mae20"] <= -0.08).mean()),
                "pct_mfe20_ge20": float((g["mfe20"] >= 0.20).mean()),
            })
    return pd.DataFrame(rows)


def pct(x: Any) -> str:
    return "—" if pd.isna(x) else f"{float(x)*100:.1f}%"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-suffix", default=DEFAULT_SNAPSHOT_SUFFIX)
    args = parser.parse_args()
    configure_paths(args.snapshot_suffix)

    df = pd.read_csv(DETAIL)
    df = df[df["candidate"].eq(MAIN)].copy()
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year

    metric_rows = []
    boot_rows = []
    path_rows = []
    yearly_rows = []

    for mode, g in df.groupby("price_mode"):
        base = g[(g["ret_20d"] > 0) & (g["ret_20d"] < 0.40)].copy()
        floor = g[(g["ret_20d"] >= 0.15) & (g["ret_20d"] < 0.40)].copy()
        excluded = g[(g["ret_20d"] > 0) & (g["ret_20d"] < 0.15)].copy()
        metric_rows.append(metric_row(base, "baseline_0_40", mode))
        metric_rows.append(metric_row(floor, "floor15_15_40", mode))
        metric_rows.append(metric_row(excluded, "excluded_ret20_0_15", mode))
        boot_rows.append(bootstrap_compare(base, floor, mode))
        pr = path_review(excluded, mode)
        if not pr.empty:
            path_rows.append(pr)
        for name, part in [("baseline_0_40", base), ("floor15_15_40", floor), ("excluded_ret20_0_15", excluded)]:
            for year, yg in part.groupby("year"):
                r = metric_row(yg, name, mode)
                r["year"] = int(year)
                yearly_rows.append(r)

    metrics = pd.DataFrame(metric_rows)
    boot = pd.DataFrame(boot_rows)
    path = pd.concat(path_rows, ignore_index=True) if path_rows else pd.DataFrame()
    yearly = pd.DataFrame(yearly_rows)

    # add deltas to metric rows
    for mode in metrics["price_mode"].unique():
        b = metrics[(metrics.price_mode == mode) & (metrics.variant == "baseline_0_40")].iloc[0]
        idx = metrics.price_mode == mode
        metrics.loc[idx, "delta_median_excess_vs_base"] = metrics.loc[idx, "median_excess"] - b["median_excess"]
        metrics.loc[idx, "delta_win_excess_vs_base"] = metrics.loc[idx, "win_excess"] - b["win_excess"]
        metrics.loc[idx, "trade_retention_vs_base"] = metrics.loc[idx, "trades"] / b["trades"]

    # save combined bootstrap file with metrics embedded for quick read
    combined = boot.merge(
        metrics[metrics.variant.eq("floor15_15_40")][["price_mode", "trades", "median_excess", "win_excess", "pf_excess", "trade_retention_vs_base"]],
        on="price_mode",
        how="left",
    )
    combined.to_csv(BOOTSTRAP_CSV, index=False, encoding="utf-8-sig")
    path.to_csv(PATH_CSV, index=False, encoding="utf-8-sig")
    yearly.to_csv(YEARLY_CSV, index=False, encoding="utf-8-sig")

    adj_m = metrics[metrics.price_mode.eq("adj")].copy()
    raw_m = metrics[metrics.price_mode.eq("raw")].copy()
    adj_b = boot[boot.price_mode.eq("adj")].iloc[0]
    raw_b = boot[boot.price_mode.eq("raw")].iloc[0]

    def mline(row: pd.Series) -> str:
        return f"- `{row.variant}`：n={int(row.trades)}，保留 {pct(row.trade_retention_vs_base)}，excess中位 {pct(row.median_excess)}，勝率 {pct(row.win_excess)}，PF {row.pf_excess:.2f}，Δ中位 {pct(row.delta_median_excess_vs_base)}"

    md: list[str] = []
    md.append("# Magic26 第十四輪：baseline vs floor15 bootstrap + path review（2026-07-01）\n")
    md.append("## 目的\n")
    md.append("承接 Round 13，只比較 `baseline_0_40` 與唯一正式挑戰者 `floor15_15_40`，用 bootstrap 檢查 +0.8% 中位 excess 是否可靠，並回看被排除的 `ret20<15` 弱動能樣本。\n")
    md.append("## 一眼結論\n")
    md.append(f"1. **floor15 的改善存在但不強**：adjusted 觀察值 Δ中位 excess {pct(adj_b.observed_delta_median_excess)}，bootstrap P(Δ>0) {pct(adj_b.prob_delta_median_excess_gt0)}，90%區間約 {pct(adj_b.boot_delta_median_excess_p05)}~{pct(adj_b.boot_delta_median_excess_p95)}。\n")
    md.append("2. **證據不足以改主規格**：bootstrap 下緣仍可為負，表示改善可能只是小樣本波動。\n")
    md.append("3. **`ret20<15` 應變成弱動能風險標籤，而不是從策略中硬刪**：被排除樣本確實較弱，但數量太少，且刪除後只是小幅改善。\n")
    md.append("4. **下一步應產品化為 dashboard 標籤 / 研究分級，而不是再最佳化參數。**\n")
    md.append("\n## adjusted 三組比較\n")
    md.extend([mline(r) for _, r in adj_m.iterrows()])
    md.append("\n## raw 三組比較\n")
    md.extend([mline(r) for _, r in raw_m.iterrows()])
    md.append("\n## bootstrap 結果\n")
    for b in [adj_b, raw_b]:
        md.append(f"- {b.price_mode}: Δmedian_excess obs {pct(b.observed_delta_median_excess)}, boot mean {pct(b.boot_delta_median_excess_mean)}, p05/p50/p95 {pct(b.boot_delta_median_excess_p05)} / {pct(b.boot_delta_median_excess_p50)} / {pct(b.boot_delta_median_excess_p95)}, P(>0) {pct(b.prob_delta_median_excess_gt0)}")
        md.append(f"  - Δwin_excess obs {pct(b.observed_delta_win_excess)}, p05/p50/p95 {pct(b.boot_delta_win_excess_p05)} / {pct(b.boot_delta_win_excess_p50)} / {pct(b.boot_delta_win_excess_p95)}, P(>0) {pct(b.prob_delta_win_excess_gt0)}")
    md.append("\n## 被排除 ret20<15 path review：adjusted\n")
    adj_path = path[path.price_mode.eq("adj")].sort_values(["slice_type", "trades"], ascending=[True, False])
    for _, r in adj_path.iterrows():
        md.append(f"- {r.slice_type}={r.slice_value}：n={int(r.trades)}，excess中位 {pct(r.median_excess)}，勝率 {pct(r.win_excess)}，MAE中位 {pct(r.median_mae20)}，MFE中位 {pct(r.median_mfe20)}")
    md.append("\n## 研究決定\n")
    md.append("- **不改主規格**：Candidate A 仍維持 `0<ret20<40`。\n")
    md.append("- **加入研究標籤**：`ret20<15` 標記為 `弱動能` / lower-priority，不直接刪除。\n")
    md.append("- **floor15 保留為觀察規格**：可在 dashboard / report 中並列，但不替代 Candidate A。\n")
    md.append("- **停止 ret20 人工區間最佳化**：再做就是過擬合。下一步回到產品化與風險標籤，或改做逐檔圖形審查。\n")
    md.append("\n## 輸出\n")
    md.append(f"- bootstrap: `{BOOTSTRAP_CSV}`")
    md.append(f"- path review: `{PATH_CSV}`")
    md.append(f"- yearly: `{YEARLY_CSV}`")
    md.append(f"- manifest: `{MANIFEST}`")
    REPORT.write_text("\n".join(md), encoding="utf-8")

    MANIFEST.write_text(json.dumps({
        "snapshot_suffix": SNAPSHOT_SUFFIX,
        "source_detail": str(DETAIL),
        "candidate": MAIN,
        "n_bootstrap": N_BOOT,
        "seed": SEED,
        "variants": ["baseline_0_40", "floor15_15_40", "excluded_ret20_0_15"],
        "outputs": {"bootstrap": str(BOOTSTRAP_CSV), "path_review": str(PATH_CSV), "yearly": str(YEARLY_CSV), "report": str(REPORT)},
        "rows_bootstrap": int(len(combined)),
        "rows_path_review": int(len(path)),
        "rows_yearly": int(len(yearly)),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"wrote {BOOTSTRAP_CSV}")
    print(f"wrote {PATH_CSV}")
    print(f"wrote {YEARLY_CSV}")
    print(f"wrote {REPORT}")


if __name__ == "__main__":
    main()
