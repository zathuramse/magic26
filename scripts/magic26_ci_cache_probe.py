from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import magic26_signal_pilot as pilot  # noqa: E402
from magic26_paths import cache_dir  # noqa: E402

PROJECT = Path(__file__).resolve().parents[1]
REPORT_DIR = Path(os.getenv("MAGIC26_REPORT_DIR", PROJECT / "reports" / "daily_refresh"))


def frame_summary(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {"rows": 0, "date_min": None, "date_max": None, "stock_ids": []}
    dates = pd.to_datetime(df["date"], errors="coerce") if "date" in df.columns else pd.Series(dtype="datetime64[ns]")
    stock_ids = sorted(str(x) for x in df.get("stock_id", pd.Series(dtype=str)).astype(str).dropna().unique().tolist())
    return {
        "rows": int(len(df)),
        "date_min": dates.min().strftime("%Y-%m-%d") if len(dates.dropna()) else None,
        "date_max": dates.max().strftime("%Y-%m-%d") if len(dates.dropna()) else None,
        "stock_ids": stock_ids[:10],
    }


def fetch_probe_frame(dataset: str, cache_name: str, *, data_id: str, start_date: str, end_date: str) -> pd.DataFrame:
    df = pilot.finmind_get(
        dataset,
        cache_name,
        data_id=data_id,
        start_date=start_date,
        end_date=end_date,
        sleep_s=0,
    )
    if not df.empty and "date" in df.columns:
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    return df


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# P6-6 Magic26 CI cache probe",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- stock_id: `{report['stock_id']}`",
        f"- start_date: `{report['start_date']}`",
        f"- end_date: `{report['end_date']}`",
        f"- cache_dir: `{report['cache_dir']}`",
        "- scope: CI cache probe only; no production data, no deploy, no schedule",
        "",
        "## Frames",
        "",
    ]
    for key, info in report["frames"].items():
        lines.append(
            f"- {key}: rows={info['rows']} date_min={info['date_min']} date_max={info['date_max']} stock_ids={','.join(info['stock_ids'])}"
        )
    lines.extend(["", "## Validation", ""])
    for item in report["validation"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Magic26 CI-only FinMind cache probe.")
    parser.add_argument("--stock-id", default="6213")
    parser.add_argument("--start-date", default="2026-07-01")
    parser.add_argument("--end-date", default="2026-07-02")
    args = parser.parse_args()

    cache = cache_dir()
    cache.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    safe_start = args.start_date.replace("-", "")
    safe_end = args.end_date.replace("-", "")

    frames = {
        "raw_sample": fetch_probe_frame(
            "TaiwanStockPrice",
            f"ci_probe_raw_{args.stock_id}_{safe_start}_{safe_end}.parquet",
            data_id=args.stock_id,
            start_date=args.start_date,
            end_date=args.end_date,
        ),
        "adj_sample": fetch_probe_frame(
            "TaiwanStockPriceAdj",
            f"ci_probe_adj_{args.stock_id}_{safe_start}_{safe_end}.parquet",
            data_id=args.stock_id,
            start_date=args.start_date,
            end_date=args.end_date,
        ),
        "benchmark_TAIEX": fetch_probe_frame(
            "TaiwanStockPrice",
            f"ci_probe_benchmark_TAIEX_{safe_start}_{safe_end}.parquet",
            data_id="TAIEX",
            start_date=args.start_date,
            end_date=args.end_date,
        ),
    }

    summaries = {key: frame_summary(df) for key, df in frames.items()}
    validation: list[str] = []
    for key, info in summaries.items():
        if info["rows"] <= 0:
            validation.append(f"FAIL {key} has no rows.")
        elif info["date_max"] != args.end_date:
            validation.append(f"FAIL {key} date_max={info['date_max']} expected={args.end_date}.")
        else:
            validation.append(f"OK {key} extends to {args.end_date}.")
    success = all(item.startswith("OK ") for item in validation)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "stock_id": args.stock_id,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "cache_dir": str(cache),
        "report_dir": str(REPORT_DIR),
        "finmind_token_present": bool(pilot.read_token()),
        "frames": summaries,
        "validation": validation,
        "success": success,
        "note": "CI cache probe only; no generated data commit, no deploy, no schedule.",
    }

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = REPORT_DIR / f"p6_6_magic26_ci_cache_probe_{stamp}.json"
    md_path = REPORT_DIR / f"p6_6_magic26_ci_cache_probe_{stamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    report["report_paths"] = {"json": str(json_path), "markdown": str(md_path)}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not success:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
