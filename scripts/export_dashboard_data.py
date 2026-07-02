from __future__ import annotations

import argparse
import json
import math
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from magic26_paths import research_root, source_root  # noqa: E402

PROJECT = Path(__file__).resolve().parents[1]
DEFAULT_RESEARCH_ROOT = research_root()
DEFAULT_MAGIC26_SOURCE = source_root()
DEFAULT_SNAPSHOT_SUFFIX = "20210101_20260701"
DEFAULT_DATA_THROUGH = "2026-06-30"


PROCESSED_NAME_PATTERNS = [
    "magic26_round4_summary_round6_regime_all_liquid30000000_raw_{suffix}.csv",
    "magic26_round4_summary_round6_regime_all_liquid30000000_adj_{suffix}.csv",
    "magic26_round4_regime_round6_regime_all_liquid30000000_raw_{suffix}.csv",
    "magic26_round4_regime_round6_regime_all_liquid30000000_adj_{suffix}.csv",
    "magic26_round7_param_grid_summary_{suffix}.csv",
    "magic26_round7_param_grid_top_{suffix}.csv",
    "magic26_round7_param_grid_yearly_{suffix}.csv",
    "magic26_round8_tradeability_summary_{suffix}.csv",
    "magic26_round8_tradeability_2024_failures_by_industry_{suffix}.csv",
    "magic26_round9_close_exit_summary_{suffix}.csv",
    "magic26_round9_close_exit_yearly_{suffix}.csv",
    "magic26_round14_bootstrap_summary_{suffix}.csv",
    "magic26_round14_excluded_weak_momentum_path_review_{suffix}.csv",
    "magic26_round14_baseline_vs_floor15_yearly_{suffix}.csv",
    "magic26_round17_b_retest_rearm_watch_{suffix}.csv",
    "magic26_round19_author_absorption_detail_{suffix}.csv",
    "magic26_round19_ret60_cap_summary_{suffix}.csv",
    "magic26_round19_volume_gap_summary_{suffix}.csv",
    "magic26_round19_risk_badge_summary_{suffix}.csv",
    "magic26_round20_60d_validation_summary_{suffix}.csv",
    "magic26_round20_60d_flagged_cases_{suffix}.csv",
    "magic26_round21_volgap_rescue_summary_{suffix}.csv",
    "magic26_round21_volgap_rescue_cases_{suffix}.csv",
]


def processed_names(snapshot_suffix: str) -> list[str]:
    return [name.format(suffix=snapshot_suffix) for name in PROCESSED_NAME_PATTERNS]


def watch_state_file(snapshot_suffix: str) -> str:
    return f"magic26_round17_b_retest_rearm_watch_{snapshot_suffix}.csv"


def raw_checked_file(snapshot_suffix: str) -> str:
    return f"magic26_round4_checked_signals_round6_regime_all_liquid30000000_raw_{snapshot_suffix}.csv"


def adj_checked_file(snapshot_suffix: str) -> str:
    return f"magic26_round4_checked_signals_round6_regime_all_liquid30000000_adj_{snapshot_suffix}.csv"


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


def add_round19_author_badges(candidates: pd.DataFrame, out_dir: Path, snapshot_suffix: str) -> pd.DataFrame:
    """Merge Round 19 source-derived research badges into candidate rows.

    These are research labels only. They must not alter Candidate A/B/C membership.
    Round 19 was computed on the main Candidate-A detail set; joining by
    date/stock/price mode also lets duplicate B/C rows show the same stock-date
    context when applicable.
    """
    out = candidates.copy()
    out["source_type"] = "reconstructed"
    path = out_dir / f"magic26_round19_author_absorption_detail_{snapshot_suffix}.csv"
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


RISK_V2_RULE_VERSION = "p2_2026_07_02"
RISK_V2_LABELS = {
    0: ("正常候選 / 可以研究", "可以研究", ["可以研究"], "可以研究；仍需看圖形與基本面"),
    1: ("追高警戒 / 可看但不要追", "不要追價", ["不要追價", "追高警戒"], "可看，但不要追價；等回檔或整理後再研究"),
    2: ("高追高 / 只觀察", "只觀察", ["只觀察", "高追高"], "只觀察；已偏追高，不建議直接追價"),
    3: ("暫不追 / 風險 veto", "暫不追", ["暫不追", "風險 veto"], "暫不追；只保留研究紀錄"),
}
RISK_V2_FIELDS = [
    "risk_v2_level",
    "risk_v2_label_zh",
    "risk_v2_primary_badge_zh",
    "risk_v2_badges_zh",
    "risk_v2_reasons_zh",
    "risk_v2_action_hint_zh",
    "risk_v2_sort_rank",
    "risk_v2_rule_version",
    "risk_v2_is_display_only",
]


def _safe_float(v: Any) -> float | None:
    try:
        if pd.isna(v):
            return None
        return float(v)
    except Exception:
        return None


def _dedupe_text(items: list[str]) -> list[str]:
    out: list[str] = []
    for item in items:
        if item and item not in out:
            out.append(item)
    return out


def _risk_v2_payload(row: dict[str, Any] | pd.Series) -> dict[str, Any]:
    ret20 = _safe_float(row.get("ret_20d"))
    sig1 = _safe_float(row.get("signal_day_ret_1d"))
    gap = _safe_float(row.get("next_open_gap"))
    avg_amount = _safe_float(row.get("avg_amount_20d"))
    low_liq = _truthy(row.get("risk_liquidity_lt100m")) or _truthy(row.get("is_low_liquidity_risk")) or (avg_amount is not None and avg_amount < 100_000_000)
    reasons: list[str] = []
    badges: list[str] = []

    if gap is not None and gap > 0.05:
        reasons.append(f"隔日開盤高 {_fmt_pct(gap)}，超過 5% 暫不追門檻")
        badges.append("開高風險")
    if ret20 is not None and ret20 > 0.40:
        reasons.append(f"近 20 天已漲 {_fmt_pct(ret20)}，超過 40% 暫不追門檻")
        badges.append("漲幅已大")
    if sig1 is not None and sig1 > 0.09 and gap is not None and gap > 0.03:
        reasons.append(f"訊號日漲 {_fmt_pct(sig1)} 且隔日開盤高 {_fmt_pct(gap)}，屬極端追高組合")
        badges.extend(["高追高", "開高風險"])
    if low_liq:
        reasons.append("低流動性風險成立")
        badges.append("低流動性")

    if reasons:
        level = 3
    else:
        level1: list[tuple[str, str]] = []
        level2: list[str] = []
        if gap is not None and gap > 0.01:
            level1.append((f"隔日開盤高 {_fmt_pct(gap)}，超過 1% 追高警戒門檻", "開高風險"))
        if sig1 is not None and sig1 > 0.04:
            level1.append((f"訊號日漲 {_fmt_pct(sig1)}，超過 4% 追高警戒門檻", "追高警戒"))
        if ret20 is not None and ret20 > 0.25:
            level1.append((f"近 20 天已漲 {_fmt_pct(ret20)}，超過 25% 追高警戒門檻", "漲幅已大"))
        if gap is not None and gap > 0.03:
            level2.append(f"隔日開盤高 {_fmt_pct(gap)}，超過 3% 高追高門檻")
        if sig1 is not None and sig1 > 0.09:
            level2.append(f"訊號日漲 {_fmt_pct(sig1)}，超過 9% 高追高門檻")
        if ret20 is not None and ret20 > 0.27:
            level2.append(f"近 20 天已漲 {_fmt_pct(ret20)}，超過 27% 高追高門檻")
        if len(level1) >= 2:
            level2.append("同時觸發兩個以上追高警戒條件")
        if level2:
            level = 2
            reasons.extend(level2)
            badges.append("高追高")
            for reason, badge in level1:
                reasons.append(reason)
                badges.append(badge)
        elif level1:
            level = 1
            for reason, badge in level1:
                reasons.append(reason)
                badges.append(badge)
        else:
            level = 0
            reasons.append("未觸發 P2 追高風險門檻")
    label, primary_badge, base_badges, action_hint = RISK_V2_LABELS[level]
    return {
        "risk_v2_level": level,
        "risk_v2_label_zh": label,
        "risk_v2_primary_badge_zh": primary_badge,
        "risk_v2_badges_zh": _dedupe_text(base_badges + badges),
        "risk_v2_reasons_zh": _dedupe_text(reasons),
        "risk_v2_action_hint_zh": action_hint,
        "risk_v2_sort_rank": level,
        "risk_v2_rule_version": RISK_V2_RULE_VERSION,
        "risk_v2_is_display_only": True,
    }


def _risk_v2_payload_for_csv(row: dict[str, Any] | pd.Series) -> dict[str, Any]:
    payload = _risk_v2_payload(row)
    payload["risk_v2_badges_zh"] = ";".join(payload["risk_v2_badges_zh"])
    payload["risk_v2_reasons_zh"] = ";".join(payload["risk_v2_reasons_zh"])
    return payload


def add_risk_v2_columns(candidates: pd.DataFrame) -> pd.DataFrame:
    if candidates.empty:
        return candidates
    out = candidates.copy()
    payloads = [_risk_v2_payload_for_csv(row) for _, row in out.iterrows()]
    for field in RISK_V2_FIELDS:
        out[field] = [payload[field] for payload in payloads]
    return out


def load_candidates(out_dir: Path, snapshot_suffix: str) -> pd.DataFrame:
    all_candidates: list[pd.DataFrame] = []
    for mode, filename in [("raw", raw_checked_file(snapshot_suffix)), ("adjusted", adj_checked_file(snapshot_suffix))]:
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
    candidates = add_round19_author_badges(candidates, out_dir, snapshot_suffix)
    candidates = add_risk_v2_columns(candidates)
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
        "risk_v2_level",
        "risk_v2_label_zh",
        "risk_v2_primary_badge_zh",
        "risk_v2_badges_zh",
        "risk_v2_reasons_zh",
        "risk_v2_action_hint_zh",
        "risk_v2_sort_rank",
        "risk_v2_rule_version",
        "risk_v2_is_display_only",
    ]
    keep_cols = [c for c in keep_cols if c in candidates.columns]
    return candidates[keep_cols].sort_values(["date", "candidate", "stock_id"], ascending=[False, True, True])


def build_watch_states(out_dir: Path, snapshot_suffix: str) -> list[dict[str, Any]]:
    path = out_dir / watch_state_file(snapshot_suffix)
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


def export_kline_files(candidates: pd.DataFrame, source_dir: Path, public_data: Path, processed: Path, data_through: str, snapshot_suffix: str) -> list[str]:
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
        src = cache_dir / f"{mode}_{stock_id}_{snapshot_suffix}.parquet"
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



def _truthy(v: Any) -> bool:
    return v is True or str(v).lower() in {"true", "1", "yes"}


def _candidate_rank(candidate: str) -> int:
    order = {
        "A_repo50_c4_40_fixed20": 0,
        "B_magic_c4_40_fixed20": 1,
        "C_c4_25_fixed20": 2,
    }
    return order.get(str(candidate), 9)


def _price_mode_rank(mode: str) -> int:
    return 0 if str(mode) == "raw" else 1


def _fmt_pct(v: Any) -> str:
    try:
        if pd.isna(v):
            return "—"
        return f"{float(v) * 100:.1f}%"
    except Exception:
        return "—"


def _fmt_money(v: Any) -> str:
    try:
        if pd.isna(v):
            return "—"
        return f"{float(v) / 1e8:.1f}億"
    except Exception:
        return "—"


def _plain_group_label(candidate: str) -> str:
    return {
        "A_repo50_c4_40_fixed20": "A組主清單",
        "B_magic_c4_40_fixed20": "B組補看",
        "C_c4_25_fixed20": "C組較嚴",
    }.get(str(candidate), str(candidate) or "未分類")


def _priority_label(row: dict[str, Any]) -> str:
    text = str(row.get("research_priority_zh") or "")
    mapping = [
        ("優先研究", "先看"),
        ("中優先-有交易風險", "可看，但先查風險"),
        ("低優先-需人工確認", "先放後面"),
        ("規格觀察", "參考用"),
    ]
    for old, new in mapping:
        if old in text:
            return new
    if row.get("candidate") != "A_repo50_c4_40_fixed20":
        return "參考用"
    return "先看"


def _risk_reason(row: dict[str, Any]) -> str:
    risks: list[str] = []
    if _truthy(row.get("is_high_open_risk")) or float(row.get("next_open_gap") or 0) >= 0.03:
        risks.append(f"隔日開盤高 {_fmt_pct(row.get('next_open_gap'))}，可能有追高風險")
    if _truthy(row.get("is_low_liquidity_risk")):
        risks.append("流動性不足")
    subtype = str(row.get("volgap_subtype_zh") or "")
    if subtype == "危險斷層":
        risks.append("成交量太集中，先避開")
    elif subtype == "大量斷層觀察":
        risks.append("成交量集中在少數幾天，要小心")
    elif subtype == "可救斷層":
        risks.append("成交量有落差，但仍可人工看圖")
    if _truthy(row.get("risk_any_long_ma_bear")):
        risks.append("長期均線偏空")
    if float(row.get("ret_60d_signal") or 0) > 1.5:
        risks.append("前面60天已漲很多")
    return "；".join(risks) if risks else "主要風險不明顯，仍需看圖確認"


def _primary_reason(row: dict[str, Any]) -> str:
    group = _plain_group_label(str(row.get("candidate") or ""))
    ret = _fmt_pct(row.get("ret_20d"))
    amount = _fmt_money(row.get("avg_amount_20d"))
    return f"{group}命中；近20天漲幅 {ret}，近20日均成交 {amount}"


def build_signal_groups(rows: pd.DataFrame, data_through: str, generated_at: str | None) -> list[dict[str, Any]]:
    """Group raw candidate rows into user-facing signal events.

    One dashboard card should represent one stock on one signal date. Strategy
    groups and raw/adjusted price rows are retained as aliases instead of being
    flattened into duplicate cards.
    """
    if rows.empty:
        return []
    df = rows.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    groups: list[dict[str, Any]] = []
    for (date, stock_id), part in df.groupby(["date", "stock_id"], sort=False):
        records = part.to_dict(orient="records")
        records = sorted(records, key=lambda r: (_candidate_rank(str(r.get("candidate"))), _price_mode_rank(str(r.get("price_mode")))))
        canonical = dict(records[0])
        hit_candidates = sorted({str(r.get("candidate")) for r in records}, key=_candidate_rank)
        price_modes = sorted({str(r.get("price_mode")) for r in records}, key=_price_mode_rank)
        group_id = f"{stock_id}_{date}"
        canonical.update({
            "signal_group_id": group_id,
            "signal_date": date,
            "data_through": data_through,
            "generated_at": generated_at,
            "spec_version": "A_repo50_c4_40_fixed20",
            "canonical_candidate": canonical.get("candidate"),
            "canonical_price_mode": canonical.get("price_mode"),
            "hit_candidates": hit_candidates,
            "hit_candidate_labels": [_plain_group_label(c) for c in hit_candidates],
            "price_modes": price_modes,
            "price_mode_labels": ["原始價" if m == "raw" else "還原價" for m in price_modes],
            "alias_count": len(records),
            "alias_rows": records,
            "primary_reason": _primary_reason(canonical),
            "risk_reason": _risk_reason(canonical),
            "priority_reason": _priority_label(canonical),
            "volume_reason": f"近20日均成交 {_fmt_money(canonical.get('avg_amount_20d'))}",
            "trace_reasons": [
                {"kind": "main", "text": _primary_reason(canonical)},
                {"kind": "risk", "text": _risk_reason(canonical)},
                {"kind": "versions", "text": f"同日共 {len(records)} 筆版本：{', '.join(_plain_group_label(c) for c in hit_candidates)}；{', '.join('原始價' if m == 'raw' else '還原價' for m in price_modes)}"},
            ],
        })
        canonical.update(_risk_v2_payload(canonical))
        groups.append(canonical)
    return sorted(groups, key=lambda r: (str(r.get("date")), -_candidate_rank(str(r.get("candidate"))), str(r.get("stock_id"))), reverse=True)

def export(source_dir: Path, data_through: str, snapshot_suffix: str = DEFAULT_SNAPSHOT_SUFFIX) -> dict[str, Any]:
    out_dir = source_dir / "out"
    if not out_dir.exists():
        raise FileNotFoundError(f"Missing source out dir: {out_dir}")
    public_data = PROJECT / "public" / "data"
    processed = PROJECT / "data" / "processed"
    public_data.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    for name in processed_names(snapshot_suffix):
        src = out_dir / name
        if not src.exists():
            # Round17 is generated after an initial export builds the candidate history
            # used by Round15/16. Final verification still checks the completed bundle.
            print(f"WARN missing processed output, skipped: {src}")
            continue
        for dest_dir in [public_data, processed]:
            shutil.copy2(src, dest_dir / name)
        copied.append(name)

    candidates = load_candidates(out_dir, snapshot_suffix)
    candidates.to_csv(processed / "magic26_candidates_history.csv", index=False, encoding="utf-8-sig")
    candidates.to_csv(public_data / "magic26_candidates_history.csv", index=False, encoding="utf-8-sig")
    kline_files = export_kline_files(candidates, source_dir, public_data, processed, data_through, snapshot_suffix)

    json_ready = candidates.copy()
    if not json_ready.empty:
        json_ready["date"] = pd.to_datetime(json_ready["date"]).dt.strftime("%Y-%m-%d")
    latest_date = json_ready["date"].max() if not json_ready.empty else None
    latest = json_ready[json_ready["date"] == latest_date].copy() if latest_date else json_ready.copy()
    recent = json_ready[json_ready["date"] >= "2026-01-01"].copy() if not json_ready.empty else json_ready.copy()

    watch_states = build_watch_states(out_dir, snapshot_suffix)
    summary = build_summary(candidates, data_through)
    summary["watch_state"] = watch_state_summary(watch_states)
    latest_groups = build_signal_groups(latest, data_through, summary.get("generated_at"))
    recent_groups = build_signal_groups(recent, data_through, summary.get("generated_at"))
    all_groups = build_signal_groups(json_ready, data_through, summary.get("generated_at"))
    summary["latest_signal_groups"] = len(latest_groups)
    summary["recent_signal_groups"] = len(recent_groups)
    summary["all_signal_groups"] = len(all_groups)
    write_json(public_data / "summary.json", summary)
    write_json(public_data / "latest_candidates.json", latest.to_dict(orient="records"))
    write_json(public_data / "recent_candidates.json", recent.to_dict(orient="records"))
    write_json(public_data / "all_candidates.json", json_ready.to_dict(orient="records"))
    write_json(public_data / "latest_signal_groups.json", latest_groups)
    write_json(public_data / "recent_signal_groups.json", recent_groups)
    write_json(public_data / "all_signal_groups.json", all_groups)
    write_json(public_data / "watch_states.json", watch_states)

    manifest = {
        "source_dir": str(source_dir),
        "snapshot_suffix": snapshot_suffix,
        "data_through": data_through,
        "copied_csv": copied,
        "candidate_rows": int(len(candidates)),
        "latest_signal_groups": len(latest_groups),
        "recent_signal_groups": len(recent_groups),
        "all_signal_groups": len(all_groups),
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
    parser.add_argument("--data-through", default=DEFAULT_DATA_THROUGH, help="Latest complete data date displayed in dashboard")
    parser.add_argument("--snapshot-suffix", default=DEFAULT_SNAPSHOT_SUFFIX, help="Input/output snapshot suffix, e.g. 20210101_20260702")
    args = parser.parse_args()
    manifest = export(Path(args.source_dir), args.data_through, args.snapshot_suffix)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
