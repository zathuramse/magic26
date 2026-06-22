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
    "magic26_round4_summary_round6_regime_all_liquid30000000_raw_20210101_20260622.csv",
    "magic26_round4_summary_round6_regime_all_liquid30000000_adj_20210101_20260622.csv",
    "magic26_round4_regime_round6_regime_all_liquid30000000_raw_20210101_20260622.csv",
    "magic26_round4_regime_round6_regime_all_liquid30000000_adj_20210101_20260622.csv",
    "magic26_round7_param_grid_summary_20210101_20260622.csv",
    "magic26_round7_param_grid_top_20210101_20260622.csv",
    "magic26_round7_param_grid_yearly_20210101_20260622.csv",
    "magic26_round8_tradeability_summary_20210101_20260622.csv",
    "magic26_round8_tradeability_2024_failures_by_industry_20210101_20260622.csv",
    "magic26_round9_close_exit_summary_20210101_20260622.csv",
    "magic26_round9_close_exit_yearly_20210101_20260622.csv",
]

RAW_CHECKED = "magic26_round4_checked_signals_round6_regime_all_liquid30000000_raw_20210101_20260622.csv"
ADJ_CHECKED = "magic26_round4_checked_signals_round6_regime_all_liquid30000000_adj_20210101_20260622.csv"


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
    ]
    keep_cols = [c for c in keep_cols if c in candidates.columns]
    return candidates[keep_cols].sort_values(["date", "candidate", "stock_id"], ascending=[False, True, True])


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
            raise FileNotFoundError(f"Missing processed output: {src}")
        for dest_dir in [public_data, processed]:
            shutil.copy2(src, dest_dir / name)
        copied.append(name)

    candidates = load_candidates(out_dir)
    candidates.to_csv(processed / "magic26_candidates_history.csv", index=False, encoding="utf-8-sig")
    candidates.to_csv(public_data / "magic26_candidates_history.csv", index=False, encoding="utf-8-sig")

    json_ready = candidates.copy()
    if not json_ready.empty:
        json_ready["date"] = pd.to_datetime(json_ready["date"]).dt.strftime("%Y-%m-%d")
    latest_date = json_ready["date"].max() if not json_ready.empty else None
    latest = json_ready[json_ready["date"] == latest_date].copy() if latest_date else json_ready.copy()
    recent = json_ready[json_ready["date"] >= "2026-01-01"].copy() if not json_ready.empty else json_ready.copy()

    summary = build_summary(candidates, data_through)
    write_json(public_data / "summary.json", summary)
    write_json(public_data / "latest_candidates.json", latest.to_dict(orient="records"))
    write_json(public_data / "recent_candidates.json", recent.to_dict(orient="records"))

    manifest = {
        "source_dir": str(source_dir),
        "data_through": data_through,
        "copied_csv": copied,
        "candidate_rows": int(len(candidates)),
        "latest_signal_date": summary["latest_signal_date"],
        "generated_at": summary["generated_at"],
    }
    write_json(PROJECT / "data" / "processed" / "export_manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Magic26 dashboard data bundle.")
    parser.add_argument("--source-dir", default=str(DEFAULT_MAGIC26_SOURCE), help="Magic26 research source directory")
    parser.add_argument("--data-through", default="2026-06-22", help="Latest data date displayed in dashboard")
    args = parser.parse_args()
    manifest = export(Path(args.source_dir), args.data_through)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
