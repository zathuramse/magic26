from __future__ import annotations

import argparse
import json
import math
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT = Path(__file__).resolve().parents[1]
DEFAULT_RESEARCH_ROOT = PROJECT.parent
DEFAULT_MAGIC26_SOURCE = DEFAULT_RESEARCH_ROOT / "sources/strategy-checks/magic26"

PROCESSED_NAMES = [
    "magic26_round4_summary_round6_regime_all_liquid30000000_raw_20210101_20260701.csv",
    "magic26_round4_summary_round6_regime_all_liquid30000000_adj_20210101_20260701.csv",
    "magic26_round4_regime_round6_regime_all_liquid30000000_raw_20210101_20260701.csv",
    "magic26_round4_regime_round6_regime_all_liquid30000000_adj_20210101_20260701.csv",
    "magic26_round7_param_grid_summary_20210101_20260701.csv",
    "magic26_round7_param_grid_top_20210101_20260701.csv",
    "magic26_round7_param_grid_yearly_20210101_20260701.csv",
    "magic26_round8_tradeability_summary_20210101_20260701.csv",
    "magic26_round8_tradeability_2024_failures_by_industry_20210101_20260701.csv",
    "magic26_round9_close_exit_summary_20210101_20260701.csv",
    "magic26_round9_close_exit_yearly_20210101_20260701.csv",
    "magic26_round14_bootstrap_summary_20210101_20260701.csv",
    "magic26_round14_excluded_weak_momentum_path_review_20210101_20260701.csv",
    "magic26_round14_baseline_vs_floor15_yearly_20210101_20260701.csv",
    "magic26_round17_b_retest_rearm_watch_20210101_20260701.csv",
    "magic26_round19_author_absorption_detail_20210101_20260701.csv",
    "magic26_round19_ret60_cap_summary_20210101_20260701.csv",
    "magic26_round19_volume_gap_summary_20210101_20260701.csv",
    "magic26_round19_risk_badge_summary_20210101_20260701.csv",
    "magic26_round20_60d_validation_summary_20210101_20260701.csv",
    "magic26_round20_60d_flagged_cases_20210101_20260701.csv",
    "magic26_round21_volgap_rescue_summary_20210101_20260701.csv",
    "magic26_round21_volgap_rescue_cases_20210101_20260701.csv",
]

WATCH_STATE_FILE = "magic26_round17_b_retest_rearm_watch_20210101_20260701.csv"

RAW_CHECKED = "magic26_round4_checked_signals_round6_regime_all_liquid30000000_raw_20210101_20260701.csv"
ADJ_CHECKED = "magic26_round4_checked_signals_round6_regime_all_liquid30000000_adj_20210101_20260701.csv"


def clean_json(value: Any) -> Any:
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean_json(v) for v in value]
    return value


def write_json(path: Path, obj: Any) -> None:
    path.write_text(
        json.dumps(clean_json(obj), ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )


def candidate_mask(df: pd.DataFrame) -> dict[str, pd.Series]:
    base = (
        df["regime_all3"].astype(bool)
        & df["c1_cross_confirm"].astype(bool)
        & df["c2_range_strength"].astype(bool)
        & df["c3_xq_exact_proxy"].astype(bool)
        & (df["ret_20d"] > 0)
        & (df["days_since_max_volume"] > 5)
        & (df["days_since_max_volume"] < 120)
    )
    return {
        "A_repo50_c4_40_fixed20": base
        & (df["ret_20d"] < 0.40)
        & df["top5_volume_ratio_120"].between(0.50, 1.00, inclusive="both"),
        "B_magic_c4_40_fixed20": base & (df["ret_20d"] < 0.40),
        "C_c4_25_fixed20": base & (df["ret_20d"] < 0.25),
    }


def research_labels(candidates: pd.DataFrame) -> pd.DataFrame:
    """Add Round-14 research labels without changing candidate membership.

    Main decision from Round 14:
    - Keep Candidate A original spec as main.
    - Mark ret20 < 15% as weak momentum / lower priority.
    - Mark 15% <= ret20 < 40% inside Candidate A as floor15 observation.
    """
    if candidates.empty:
        return candidates
    out = candidates.copy()
    is_a = out["candidate"].eq("A_repo50_c4_40_fixed20")
    ret = pd.to_numeric(out["ret_20d"], errors="coerce")
    gap = pd.to_numeric(out.get("next_open_gap"), errors="coerce")
    avg_amount = pd.to_numeric(out.get("avg_amount_20d"), errors="coerce")
    weak = is_a & ret.lt(0.15)
    floor15 = is_a & ret.ge(0.15) & ret.lt(0.40)
    high_open = gap.ge(0.03).fillna(False)
    low_liq = avg_amount.lt(100_000_000).fillna(False)
    out["is_main_spec"] = is_a
    out["is_weak_momentum"] = weak
    out["is_floor15_observation"] = floor15
    out["is_high_open_risk"] = high_open
    out["is_low_liquidity_risk"] = low_liq

    def bucket(v: Any) -> str:
        if pd.isna(v):
            return "NA"
        v = float(v)
        if v < 0.15:
            return "弱動能<15%"
        if v < 0.25:
            return "中段15-25%"
        if v < 0.30:
            return "中高25-30%"
        return "高動能30-40%"

    out["momentum_bucket_zh"] = ret.map(bucket)
    roles = []
    priorities = []
    tags = []
    for _, r in out.iterrows():
        row_tags: list[str] = []
        cand = r["candidate"]
        if cand == "A_repo50_c4_40_fixed20":
            role = "主規格CandidateA"
            row_tags.append("主規格")
            if bool(r["is_weak_momentum"]):
                row_tags.append("弱動能")
                priority = "低優先-需人工確認"
            else:
                row_tags.append("floor15觀察")
                priority = "優先研究" if not bool(r["is_high_open_risk"]) and not bool(r["is_low_liquidity_risk"]) else "中優先-有交易風險"
        elif cand == "B_magic_c4_40_fixed20":
            role = "寬基準觀察"
            row_tags.append("非主規格")
            priority = "規格觀察"
        elif cand == "C_c4_25_fixed20":
            role = "高濃度觀察"
            row_tags.append("高濃度")
            priority = "規格觀察"
        else:
            role = "其他觀察"
            priority = "規格觀察"
        if bool(r["is_high_open_risk"]):
            row_tags.append("高開風險")
        if bool(r["is_low_liquidity_risk"]):
            row_tags.append("低流動")
        roles.append(role)
        priorities.append(priority)
        tags.append(";".join(row_tags))
    out["strategy_role_zh"] = roles
    out["research_priority_zh"] = priorities
    out["research_tags"] = tags
    return out


def add_round19_author_badges(candidates: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    """Merge Round 19 source-derived research badges into candidate rows.

    These are research labels only. They must not alter Candidate A/B/C membership.
    Round 19 was computed on the main Candidate-A detail set; joining by
    date/stock/price mode also lets duplicate B/C rows show the same stock-date
    context when applicable.
    """
    out = candidates.copy()
    out["source_type"] = "reconstructed"
    path = out_dir / "magic26_round19_author_absorption_detail_20210101_20260701.csv"
    default_cols = [
        "ret_60d_signal", "ret60_cap150_pass", "volume_gap_risk_zh",
        "top1_to_top3_volume_ratio", "top1_to_top5_volume_ratio", "top1_to_top10_volume_ratio",
        "risk_daily_long_ma_bear", "risk_weekly_long_ma_bear", "risk_any_long_ma_bear",
        "risk_long_ma_score", "risk_badge_zh", "volgap_subtype_zh", "volgap_score_impact",
    ]
    if not path.exists() or out.empty:
        for col in default_cols:
            if col not in out.columns:
                out[col] = None
        return out

    detail = pd.read_csv(path)
    detail["date"] = pd.to_datetime(detail["date"])
    detail["stock_id"] = detail["stock_id"].astype(str)
    out["stock_id"] = out["stock_id"].astype(str)
    keep = [
        "date", "stock_id", "price_mode", "ret_60d_signal",
        "top1_to_top3_volume_ratio", "top1_to_top5_volume_ratio", "top1_to_top10_volume_ratio",
        "risk_daily_long_ma_bear", "risk_weekly_long_ma_bear", "risk_any_long_ma_bear",
        "risk_long_ma_score",
    ]
    detail = detail[[c for c in keep if c in detail.columns]].drop_duplicates(["date", "stock_id", "price_mode"])
    out = out.merge(detail, on=["date", "stock_id", "price_mode"], how="left")

    ret60 = pd.to_numeric(out.get("ret_60d_signal"), errors="coerce")
    vol3 = pd.to_numeric(out.get("top1_to_top3_volume_ratio"), errors="coerce")
    vol10 = pd.to_numeric(out.get("top1_to_top10_volume_ratio"), errors="coerce")
    score = pd.to_numeric(out.get("risk_long_ma_score"), errors="coerce").fillna(0)
    out["ret60_cap150_pass"] = ret60.le(1.5).where(ret60.notna(), None)

    missing_volgap = vol10.isna() | ret60.isna()
    normal_volgap = vol10.lt(2)
    rescue_volgap = vol10.ge(2) & vol10.lt(2.2) & vol3.lt(1.5) & ret60.le(0.8)
    danger_volgap = vol10.ge(2.5) | ret60.gt(0.8)
    out["volgap_subtype_zh"] = "待補"
    out.loc[normal_volgap, "volgap_subtype_zh"] = "正常"
    out.loc[rescue_volgap, "volgap_subtype_zh"] = "可救斷層"
    out.loc[danger_volgap & ~normal_volgap, "volgap_subtype_zh"] = "危險斷層"
    out.loc[vol10.ge(2) & ~rescue_volgap & ~danger_volgap, "volgap_subtype_zh"] = "大量斷層觀察"
    out.loc[missing_volgap, "volgap_subtype_zh"] = "待補"
    out["volgap_score_impact"] = 0
    out.loc[out["volgap_subtype_zh"].eq("可救斷層"), "volgap_score_impact"] = -2
    out.loc[out["volgap_subtype_zh"].eq("大量斷層觀察"), "volgap_score_impact"] = -5
    out.loc[out["volgap_subtype_zh"].eq("危險斷層"), "volgap_score_impact"] = -10

    def vol_label(v: Any) -> str:
        if pd.isna(v):
            return "待補"
        if float(v) >= 3:
            return "大量斷層高"
        if float(v) >= 2:
            return "大量斷層觀察"
        return "量能結構正常"

    out["volume_gap_risk_zh"] = vol10.map(vol_label)

    def truthy(v: Any) -> bool:
        return v is True or str(v).lower() == "true"

    def risk_badge(row: pd.Series) -> str:
        tags: list[str] = ["研究中"]
        if pd.notna(row.get("ret_60d_signal")) and float(row["ret_60d_signal"]) > 1.5:
            tags.append("60日漲幅>150%")
        if row.get("volgap_subtype_zh") in {"可救斷層", "危險斷層", "大量斷層觀察"}:
            tags.append(str(row["volgap_subtype_zh"]))
        if truthy(row.get("risk_daily_long_ma_bear")):
            tags.append("日長均空頭")
        if truthy(row.get("risk_weekly_long_ma_bear")):
            tags.append("周長均空頭")
        return ";".join(tags)

    out["risk_badge_zh"] = out.apply(risk_badge, axis=1)
    out["risk_long_ma_score"] = score.astype(int)
    return out


def load_candidates(out_dir: Path) -> pd.DataFrame:
    all_candidates: list[pd.DataFrame] = []
    for mode, filename in [("raw", RAW_CHECKED), ("adjusted", ADJ_CHECKED)]:
        path = out_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing checked-signal input: {path}")
        df = pd.read_csv(path)
        df["date"] = pd.to_datetime(df["date"])
        for name, mask in candidate_mask(df).items():
            part = df.loc[mask].copy()
            part["price_mode"] = mode
            part["candidate"] = name
            all_candidates.append(part)
    candidates = pd.concat(all_candidates, ignore_index=True) if all_candidates else pd.DataFrame()
    candidates = research_labels(candidates)
    candidates = add_round19_author_badges(candidates, out_dir)
    keep_cols = [
        "date",
        "stock_id",
        "stock_name",
        "industry_category",
        "price_mode",
        "candidate",
        "close",
        "avg_amount_20d",
        "range_pos",
        "gap1",
        "gap2",
        "ret_20d",
        "days_since_max_volume",
        "top5_volume_ratio_120",
        "signal_day_ret_1d",
        "next_open_gap",
        "t1_open_excess_20d",
        "t1_open_excess_60d",
        "risk_signal_day_gt9",
        "risk_next_gap_gt3",
        "risk_liquidity_lt100m",
        "is_main_spec",
        "is_weak_momentum",
        "is_floor15_observation",
        "is_high_open_risk",
        "is_low_liquidity_risk",
        "momentum_bucket_zh",
        "strategy_role_zh",
        "research_priority_zh",
        "research_tags",
        "source_type",
        "ret_60d_signal",
        "ret60_cap150_pass",
        "top1_to_top3_volume_ratio",
        "top1_to_top5_volume_ratio",
        "top1_to_top10_volume_ratio",
        "volume_gap_risk_zh",
        "volgap_subtype_zh",
        "volgap_score_impact",
        "risk_daily_long_ma_bear",
        "risk_weekly_long_ma_bear",
        "risk_any_long_ma_bear",
        "risk_long_ma_score",
        "risk_badge_zh",
    ]
    keep_cols = [c for c in keep_cols if c in candidates.columns]
    return candidates[keep_cols].sort_values(["date", "candidate", "stock_id"], ascending=[False, True, True])


def build_watch_states(out_dir: Path) -> list[dict[str, Any]]:
    path = out_dir / WATCH_STATE_FILE
    if not path.exists():
        return []
    df = pd.read_csv(path)
    if df.empty:
        return []
    keep_cols = [
        "stock_id", "stock_name", "industry_category", "theme_bucket", "rearm_state",
        "suggested_action", "rule_reason", "trigger_condition_next", "date",
        "latest_date", "post_signal_ret", "pullback_from_post_signal_high",
        "ma20_gap", "ma60_gap", "rsi14", "volume_ratio20", "close_vs_prev20_high",
        "latest_close", "signal_close", "prev20_high", "manual_decision",
    ]
    keep_cols = [c for c in keep_cols if c in df.columns]
    out = df[keep_cols].copy()
    if "stock_id" in out.columns:
        out["stock_id"] = out["stock_id"].astype(str).str.replace(r"\.0$", "", regex=True)
    return out.to_dict(orient="records")


def export_kline_files(candidates: pd.DataFrame, source_dir: Path, public_data: Path, processed: Path, data_through: str) -> list[str]:
    """Export compact OHLC windows for candidate detail charts.

    Static JSON keeps the dashboard self-contained on Cloudflare Pages and avoids
    live market-data calls. One file is written per stock_id + price_mode.
    """
    if candidates.empty:
        return []
    cache_dir = source_dir / "cache"
    public_kline = public_data / "kline"
    processed_kline = processed / "kline"
    public_kline.mkdir(parents=True, exist_ok=True)
    processed_kline.mkdir(parents=True, exist_ok=True)
    cutoff = pd.Timestamp(data_through)
    written: list[str] = []
    keys = candidates[["stock_id", "price_mode"]].drop_duplicates()
    for _, row in keys.iterrows():
        stock_id = str(row["stock_id"]).replace(".0", "")
        mode = "adj" if str(row["price_mode"]) == "adjusted" else "raw"
        src = cache_dir / f"{mode}_{stock_id}_20210101_20260701.parquet"
        if not src.exists():
            continue
        df = pd.read_parquet(src)
        if df.empty or "date" not in df.columns:
            continue
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df[df["date"].notna() & df["date"].le(cutoff)].sort_values("date").tail(520)
        if df.empty:
            continue
        rows = []
        for col in ["open", "max", "min", "close", "Trading_Volume"]:
            if col not in df.columns:
                df[col] = pd.NA
        for _, bar in df.iterrows():
            rows.append({
                "date": bar["date"].strftime("%Y-%m-%d"),
                "open": float(bar["open"]) if pd.notna(bar["open"]) else None,
                "high": float(bar["max"]) if pd.notna(bar["max"]) else None,
                "low": float(bar["min"]) if pd.notna(bar["min"]) else None,
                "close": float(bar["close"]) if pd.notna(bar["close"]) else None,
                "volume": float(bar["Trading_Volume"]) if pd.notna(bar["Trading_Volume"]) else None,
            })
        payload = {
            "stock_id": stock_id,
            "price_mode": str(row["price_mode"]),
            "data_through": data_through,
            "rows": rows,
        }
        rel = f"kline/{mode}_{stock_id}.json"
        write_json(public_data / rel, payload)
        write_json(processed / rel, payload)
        written.append(rel)
    return sorted(written)

def watch_state_summary(watch_states: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for row in watch_states:
        state = str(row.get("rearm_state") or "未分類")
        counts[state] = counts.get(state, 0) + 1
    return {
        "rows": len(watch_states),
        "state_counts": counts,
        "decision": "Watch State 是二次觀察/再啟動條件，不是買進訊號",
    }


def build_summary(candidates: pd.DataFrame, data_through: str) -> dict[str, Any]:
    latest_date = candidates["date"].max() if not candidates.empty else None
    latest = candidates[candidates["date"] == latest_date].copy() if latest_date is not None else candidates.copy()
    recent = candidates[candidates["date"] >= pd.Timestamp("2026-01-01")].copy() if not candidates.empty else candidates.copy()
    summary: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "data_through": data_through,
        "latest_signal_date": latest_date.strftime("%Y-%m-%d") if latest_date is not None else None,
        "total_candidate_rows": int(len(candidates)),
        "latest_candidate_rows": int(len(latest)),
        "recent_2026_rows": int(len(recent)),
        "main_spec": "A_repo50_c4_40_fixed20",
        "main_spec_zh": "Candidate A：regime_all3 + C1/C2/C3 + repo_vol5>=50% + 20D漲幅<40% + 最大量>5日前 + 固定20D出場",
        "round14_decision": {
            "main_spec_action": "維持原主規格，不改成floor15",
            "weak_momentum_label": "ret20<15% 標記為弱動能/低優先，需人工確認，不直接排除",
            "floor15_observation": "15%<=ret20<40% 保留為觀察規格，不取代Candidate A",
        },
        "round19_decision": {
            "status": "研究中 risk badge；不改主規格、不自動排除",
            "ret60_cap150": "60日漲幅<=150% 可列風報比濾網候選，需再用60日績效驗證",
            "volume_gap": "top1/top10大量斷層先做風險標籤；top3/top5/top10不可粗暴視為同一訊號",
            "long_ma_bear": "日/周長均空頭作為負分欄位；樣本少，不作硬排除",
            "source_type": "目前候選資料標記為 reconstructed，後續需區分 live_scan/backtest_export/reconstructed",
        },
        "round20_decision": {
            "status": "60D validation；主規格不變",
            "ret60_cap150": "只排除極少數過熱樣本，可保留過熱 risk badge，不升硬條件",
            "volume_gap_top10": "top1/top10<2 的 60D 右尾率較佳，可作研究優先加分；top1/top10>=2 作大量斷層負分，但不作 veto",
            "long_ma_bear": "長均空頭樣本太少，僅保留負分 badge",
            "next_step": "逐檔檢查 top1/top10>=2 但 60D 仍大漲的反例，找可救脈絡",
        },
        "round21_decision": {
            "status": "volgap false-kill review；主規格不變",
            "top10_gap": "top1/top10>=2 維持負分，不硬 veto",
            "rescue_candidate": "top1/top10<2.2 + top1/top3<1.5 + ret60_signal<=80% 可標大量斷層可救觀察；不是加分，只是避免誤殺",
            "danger_candidate": "top1/top10>=2.5 或 ret60_signal>80% 標危險斷層，排序應明顯下調",
            "next_step": "產品化 volgap_subtype_zh：正常 / 可救斷層 / 危險斷層 / 待補",
        },
        "round22_decision": {
            "status": "volgap subtype productized；主規格不變",
            "field": "volgap_subtype_zh = 正常 / 可救斷層 / 危險斷層 / 大量斷層觀察 / 待補",
            "score": "可救斷層 -2；大量斷層觀察 -5；危險斷層 -10；只影響研究排序，不排除候選",
            "ui": "卡片、篩選、細節欄位顯示 subtype；可救斷層不是加分，只是避免誤殺",
        },
        "round23_decision": {
            "status": "volgap summary panel；主規格不變",
            "ui": "新增斷層分類總覽卡，顯示全歷史/近期/最新/A類數量，點擊即套用全歷史分類篩選",
            "scope": "純 UI 研究入口；不新增交易訊號、不改候選資格",
        },
        "round24_decision": {
            "status": "main-A subtype grouped priority list；主規格不變",
            "ui": "主規格 A 近期清單依斷層分類分組，每組顯示前三筆並可點標題套用 2026近期 + A + 分類篩選",
            "scope": "只改善人工研究順序；不新增交易訊號、不改候選資格",
        },
        "candidates": [],
    }
    if not candidates.empty:
        for candidate, part in candidates.groupby("candidate"):
            excess = part["t1_open_excess_20d"].dropna()
            summary["candidates"].append(
                {
                    "candidate": candidate,
                    "rows": int(len(part)),
                    "latest_date": part["date"].max().strftime("%Y-%m-%d"),
                    "raw_rows": int((part["price_mode"] == "raw").sum()),
                    "adjusted_rows": int((part["price_mode"] == "adjusted").sum()),
                    "median_t1_open_excess_20d": None if excess.empty else float(excess.median()),
                    "win_t1_open_excess_20d": None if excess.empty else float((excess > 0).mean()),
                    "weak_momentum_rows": int(part.get("is_weak_momentum", pd.Series(dtype=bool)).sum()),
                    "floor15_observation_rows": int(part.get("is_floor15_observation", pd.Series(dtype=bool)).sum()),
                    "high_open_risk_rows": int(part.get("is_high_open_risk", pd.Series(dtype=bool)).sum()),
                    "low_liquidity_risk_rows": int(part.get("is_low_liquidity_risk", pd.Series(dtype=bool)).sum()),
                    "ret60_over150_rows": int(pd.to_numeric(part.get("ret_60d_signal"), errors="coerce").gt(1.5).sum()),
                    "volume_gap_watch_rows": int(part.get("volume_gap_risk_zh", pd.Series(dtype=str)).astype(str).str.contains("大量斷層").sum()),
                    "volgap_rescue_rows": int(part.get("volgap_subtype_zh", pd.Series(dtype=str)).astype(str).eq("可救斷層").sum()),
                    "volgap_danger_rows": int(part.get("volgap_subtype_zh", pd.Series(dtype=str)).astype(str).eq("危險斷層").sum()),
                    "long_ma_bear_rows": int(part.get("risk_any_long_ma_bear", pd.Series(dtype=bool)).map(lambda v: v is True or str(v).lower() == "true").sum()),
                }
            )
    return summary


def export(source_dir: Path, data_through: str) -> dict[str, Any]:
    out_dir = source_dir / "out"
    if not out_dir.exists():
        raise FileNotFoundError(f"Missing source out dir: {out_dir}")
    public_data = PROJECT / "public" / "data"
    processed = PROJECT / "data" / "processed"
    public_data.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    for name in PROCESSED_NAMES:
        src = out_dir / name
        if not src.exists():
            # Round17 is generated after an initial export builds the candidate history
            # used by Round15/16. Final verification still checks the completed bundle.
            print(f"WARN missing processed output, skipped: {src}")
            continue
        for dest_dir in [public_data, processed]:
            shutil.copy2(src, dest_dir / name)
        copied.append(name)

    candidates = load_candidates(out_dir)
    candidates.to_csv(processed / "magic26_candidates_history.csv", index=False, encoding="utf-8-sig")
    candidates.to_csv(public_data / "magic26_candidates_history.csv", index=False, encoding="utf-8-sig")
    kline_files = export_kline_files(candidates, source_dir, public_data, processed, data_through)

    json_ready = candidates.copy()
    if not json_ready.empty:
        json_ready["date"] = pd.to_datetime(json_ready["date"]).dt.strftime("%Y-%m-%d")
    latest_date = json_ready["date"].max() if not json_ready.empty else None
    latest = json_ready[json_ready["date"] == latest_date].copy() if latest_date else json_ready.copy()
    recent = json_ready[json_ready["date"] >= "2026-01-01"].copy() if not json_ready.empty else json_ready.copy()

    watch_states = build_watch_states(out_dir)
    summary = build_summary(candidates, data_through)
    summary["watch_state"] = watch_state_summary(watch_states)
    write_json(public_data / "summary.json", summary)
    write_json(public_data / "latest_candidates.json", latest.to_dict(orient="records"))
    write_json(public_data / "recent_candidates.json", recent.to_dict(orient="records"))
    write_json(public_data / "all_candidates.json", json_ready.to_dict(orient="records"))
    write_json(public_data / "watch_states.json", watch_states)

    manifest = {
        "source_dir": str(source_dir),
        "data_through": data_through,
        "copied_csv": copied,
        "candidate_rows": int(len(candidates)),
        "watch_state_rows": int(len(watch_states)),
        "kline_files": kline_files,
        "latest_signal_date": summary["latest_signal_date"],
        "generated_at": summary["generated_at"],
    }
    write_json(PROJECT / "data" / "processed" / "export_manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Magic26 dashboard data bundle.")
    parser.add_argument("--source-dir", default=str(DEFAULT_MAGIC26_SOURCE), help="Magic26 research source directory")
    parser.add_argument("--data-through", default="2026-06-30", help="Latest complete data date displayed in dashboard")
    args = parser.parse_args()
    manifest = export(Path(args.source_dir), args.data_through)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
