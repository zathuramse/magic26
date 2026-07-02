#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Extend Magic26 per-stock parquet caches to a newer snapshot suffix.

Research-only utility. It writes new cache files under the target suffix and does
not overwrite the source suffix by default.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import magic26_signal_pilot as pilot  # noqa: E402
from magic26_paths import cache_dir  # noqa: E402

CACHE = cache_dir()
REPORT_DIR = Path(os.getenv("MAGIC26_REPORT_DIR", "reports/daily_refresh"))
DEFAULT_SOURCE_SUFFIX = "20210101_20260701"
DEFAULT_TARGET_SUFFIX = "20210101_20260702"
DEFAULT_TARGET_DATE = "2026-07-02"


PRICE_TYPES = {
    "raw": "TaiwanStockPrice",
    "adj": "TaiwanStockPriceAdj",
}


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def suffix_end_date(suffix: str) -> date:
    try:
        return datetime.strptime(suffix.split("_")[-1], "%Y%m%d").date()
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Invalid snapshot suffix: {suffix}") from exc


def trading_days(start: date, end: date) -> list[str]:
    out: list[str] = []
    d = start
    while d <= end:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def fetch_daily(dataset: str, tag: str, days: list[str], sleep_s: float, *, refresh_daily: bool) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for day in days:
        cache_name = f"daily_{tag}_{day.replace('-', '')}.parquet"
        cache_path = CACHE / cache_name
        if refresh_daily and cache_path.exists():
            cache_path.unlink()
        df = pilot.finmind_get(dataset, cache_name, start_date=day, end_date=day, sleep_s=sleep_s)
        if df.empty:
            print(f"WARN empty {dataset} {day}")
            continue
        df = df.copy()
        df["stock_id"] = df["stock_id"].astype(str)
        df = df[df["stock_id"].str.match(r"^\d{4}$") | df["stock_id"].isin(["TAIEX", "TPEx"])]
        frames.append(df)
        print(f"daily {tag} {day} rows={len(df)} stocks={df['stock_id'].nunique()}")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def fetch_range(
    dataset: str,
    cache_name: str,
    *,
    data_id: str,
    start_date: str,
    end_date: str,
    sleep_s: float,
    refresh: bool,
) -> pd.DataFrame:
    cache_path = CACHE / cache_name
    if refresh and cache_path.exists():
        cache_path.unlink()
    df = pilot.finmind_get(
        dataset,
        cache_name,
        data_id=data_id,
        start_date=start_date,
        end_date=end_date,
        sleep_s=sleep_s,
    )
    return normalized_price_frame(df)


def fetch_sample_daily(
    tag: str,
    dataset: str,
    days: list[str],
    sample_stock_ids: set[str],
    sleep_s: float,
    *,
    refresh_daily: bool,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    safe_start = days[0].replace("-", "") if days else "none"
    safe_end = days[-1].replace("-", "") if days else "none"
    for stock_id in sorted(sample_stock_ids):
        df = fetch_range(
            dataset,
            f"sample_daily_{tag}_{stock_id}_{safe_start}_{safe_end}.parquet",
            data_id=stock_id,
            start_date=days[0],
            end_date=days[-1],
            sleep_s=sleep_s,
            refresh=refresh_daily,
        )
        frames.append(df)
        print(f"sample daily {tag} {stock_id} rows={len(df)}")
    if tag == "raw":
        bench = fetch_range(
            dataset,
            f"sample_daily_benchmark_TAIEX_{safe_start}_{safe_end}.parquet",
            data_id="TAIEX",
            start_date=days[0],
            end_date=days[-1],
            sleep_s=sleep_s,
            refresh=refresh_daily,
        )
        frames.append(bench)
        print(f"sample daily benchmark_TAIEX rows={len(bench)}")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def bootstrap_sample_sources(
    sample_stock_ids: set[str],
    source_suffix: str,
    source_start: str,
    source_end: str,
    *,
    overwrite: bool,
    sleep_s: float,
) -> dict[str, Any]:
    summary: dict[str, Any] = {"source_start": source_start, "source_end": source_end, "stocks": {}, "benchmark_TAIEX": {}}
    for tag, dataset in PRICE_TYPES.items():
        summary["stocks"][tag] = {}
        for stock_id in sorted(sample_stock_ids):
            path = CACHE / f"{tag}_{stock_id}_{source_suffix}.parquet"
            status = "exists"
            if overwrite or not path.exists():
                df = fetch_range(
                    dataset,
                    f"bootstrap_{tag}_{stock_id}_{source_start.replace('-', '')}_{source_end.replace('-', '')}.parquet",
                    data_id=stock_id,
                    start_date=source_start,
                    end_date=source_end,
                    sleep_s=sleep_s,
                    refresh=overwrite,
                )
                df.to_parquet(path, index=False)
                status = "written"
            else:
                df = pd.read_parquet(path)
            summary["stocks"][tag][stock_id] = {"path": str(path), "status": status, **frame_date_bounds(df)}
    bench_path = CACHE / f"benchmark_TAIEX_{source_suffix}.parquet"
    bench_status = "exists"
    if overwrite or not bench_path.exists():
        bench = fetch_range(
            "TaiwanStockPrice",
            f"bootstrap_benchmark_TAIEX_{source_start.replace('-', '')}_{source_end.replace('-', '')}.parquet",
            data_id="TAIEX",
            start_date=source_start,
            end_date=source_end,
            sleep_s=sleep_s,
            refresh=overwrite,
        )
        bench.to_parquet(bench_path, index=False)
        bench_status = "written"
    else:
        bench = pd.read_parquet(bench_path)
    summary["benchmark_TAIEX"] = {"path": str(bench_path), "status": bench_status, **frame_date_bounds(bench)}
    return summary


def stock_id_from_cache(path: Path, tag: str, source_suffix: str) -> str:
    prefix = f"{tag}_"
    suffix = f"_{source_suffix}.parquet"
    name = path.name
    if not name.startswith(prefix) or not name.endswith(suffix):
        raise ValueError(f"Unexpected {tag} cache name: {name}")
    return name[len(prefix) : -len(suffix)]


def normalized_price_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if not out.empty and "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    if not out.empty and "stock_id" in out.columns:
        out["stock_id"] = out["stock_id"].astype(str)
    return out


def combine_cache(old: pd.DataFrame, add: pd.DataFrame) -> pd.DataFrame:
    old = normalized_price_frame(old)
    add = normalized_price_frame(add)
    if old.empty and add.empty:
        return old
    if old.empty:
        out = add
    elif add.empty:
        out = old
    else:
        out = pd.concat([old, add], ignore_index=True)
    if not out.empty and {"date", "stock_id"}.issubset(out.columns):
        out = out.drop_duplicates(["date", "stock_id"], keep="last").sort_values("date")
    return out.reset_index(drop=True)


def frame_date_bounds(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty or "date" not in df.columns:
        return {"rows": int(len(df)), "date_min": None, "date_max": None}
    dates = pd.to_datetime(df["date"])
    return {
        "rows": int(len(df)),
        "date_min": dates.min().strftime("%Y-%m-%d"),
        "date_max": dates.max().strftime("%Y-%m-%d"),
    }


def extend_one(
    old_path: Path,
    new_path: Path,
    stock_id: str,
    daily: pd.DataFrame,
    *,
    dry_run: bool,
    overwrite: bool,
) -> dict[str, Any]:
    old = pd.read_parquet(old_path)
    add = daily[daily["stock_id"].astype(str).eq(stock_id)].copy() if not daily.empty else pd.DataFrame()
    out = combine_cache(old, add)
    status = "planned"
    if new_path.exists() and not overwrite:
        status = "exists_skipped"
    elif not dry_run:
        out.to_parquet(new_path, index=False)
        status = "written"
    return {
        "stock_id": stock_id,
        "old_path": str(old_path),
        "new_path": str(new_path),
        "status": status,
        "old": frame_date_bounds(old),
        "add": frame_date_bounds(add),
        "out": frame_date_bounds(out),
    }


def extend_price_type(
    tag: str,
    daily: pd.DataFrame,
    source_suffix: str,
    target_suffix: str,
    *,
    dry_run: bool,
    overwrite: bool,
    sample_stock_ids: set[str],
    sample_only: bool,
) -> dict[str, Any]:
    paths = sorted(CACHE.glob(f"{tag}_*_{source_suffix}.parquet"))
    if sample_only:
        paths = [p for p in paths if stock_id_from_cache(p, tag, source_suffix) in sample_stock_ids]
    summary = {
        "source_files": len(paths),
        "planned_or_written": 0,
        "exists_skipped": 0,
        "sample_outputs": {},
    }
    for old_path in paths:
        stock_id = stock_id_from_cache(old_path, tag, source_suffix)
        new_path = Path(str(old_path).replace(source_suffix, target_suffix))
        result = extend_one(old_path, new_path, stock_id, daily, dry_run=dry_run, overwrite=overwrite)
        if result["status"] == "exists_skipped":
            summary["exists_skipped"] += 1
        else:
            summary["planned_or_written"] += 1
        if stock_id in sample_stock_ids:
            summary["sample_outputs"][stock_id] = result
    return summary


def extend_benchmark(
    raw_daily: pd.DataFrame,
    source_suffix: str,
    target_suffix: str,
    *,
    dry_run: bool,
    overwrite: bool,
) -> dict[str, Any]:
    old_path = CACHE / f"benchmark_TAIEX_{source_suffix}.parquet"
    new_path = CACHE / f"benchmark_TAIEX_{target_suffix}.parquet"
    if not old_path.exists():
        return {"source_exists": False, "status": "missing_source"}
    add = raw_daily[raw_daily["stock_id"].astype(str).eq("TAIEX")].copy() if not raw_daily.empty else pd.DataFrame()
    old = pd.read_parquet(old_path)
    out = combine_cache(old, add)
    status = "planned"
    if new_path.exists() and not overwrite:
        status = "exists_skipped"
    elif not dry_run:
        out.to_parquet(new_path, index=False)
        status = "written"
    return {
        "source_exists": True,
        "old_path": str(old_path),
        "new_path": str(new_path),
        "status": status,
        "old": frame_date_bounds(old),
        "add": frame_date_bounds(add),
        "out": frame_date_bounds(out),
    }


def write_report(report: dict[str, Any]) -> dict[str, str]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = "dry_run" if report["dry_run"] else "local_write"
    base = REPORT_DIR / f"p5_3_extend_magic26_cache_{mode}_{stamp}"
    json_path = base.with_suffix(".json")
    md_path = base.with_suffix(".md")
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# P5-3 Magic26 cache extension report",
        "",
        f"- mode: {'dry-run' if report['dry_run'] else 'local-write'}",
        f"- refresh_daily: `{report.get('refresh_daily', False)}`",
        f"- overwrite: `{report.get('overwrite', False)}`",
        f"- sample_only: `{report.get('sample_only', False)}`",
        f"- bootstrap_sample_source: `{report.get('bootstrap_sample_source', False)}`",
        f"- sample_stock_ids: {', '.join(report.get('sample_stock_ids', []))}",
        f"- source_suffix: `{report['source_suffix']}`",
        f"- target_suffix: `{report['target_suffix']}`",
        f"- tail_start: `{report['tail_start']}`",
        f"- target_date: `{report['target_date']}`",
        f"- trading_days: {', '.join(report['trading_days'])}",
        "- scope: cache parquet only; no round regeneration, no dashboard export, no deploy, no cron",
        "",
        "## Daily feed rows",
    ]
    for tag, info in report["daily_feeds"].items():
        lines.append(f"- {tag}: rows={info['rows']} date_min={info['date_min']} date_max={info['date_max']}")
    lines.extend(["", "## Cache extension summary"])
    for tag in ["raw", "adj"]:
        info = report["extensions"][tag]
        lines.append(
            f"- {tag}: source_files={info['source_files']} planned_or_written={info['planned_or_written']} "
            f"exists_skipped={info['exists_skipped']}"
        )
        for stock_id, sample in info.get("sample_outputs", {}).items():
            lines.append(
                f"  - sample {stock_id}: old_max={sample['old']['date_max']} add_rows={sample['add']['rows']} "
                f"out_max={sample['out']['date_max']} status={sample['status']}"
            )
    bench = report["extensions"]["benchmark_TAIEX"]
    lines.append(
        f"- benchmark_TAIEX: status={bench.get('status')} old_max={bench.get('old', {}).get('date_max')} "
        f"add_rows={bench.get('add', {}).get('rows')} out_max={bench.get('out', {}).get('date_max')}"
    )
    lines.extend(["", "## Validation notes", ""])
    lines.extend(f"- {note}" for note in report["validation_notes"])
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extend Magic26 per-stock cache parquet files to a target suffix.")
    parser.add_argument("--source-suffix", default=DEFAULT_SOURCE_SUFFIX)
    parser.add_argument("--target-suffix", default=DEFAULT_TARGET_SUFFIX)
    parser.add_argument("--target-date", default=DEFAULT_TARGET_DATE)
    parser.add_argument(
        "--tail-start",
        default=None,
        help="First date to fetch. Defaults to source suffix end + 1 day; set earlier when source files lag their suffix.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Fetch inputs and plan outputs without writing target cache files.")
    parser.add_argument("--refresh-daily", action="store_true", help="Ignore cached daily FinMind parquet inputs and re-fetch tail days.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing target cache files. Default is skip existing.")
    parser.add_argument("--sample-stock-id", action="append", default=["6213"], help="Stock id to include in detailed report.")
    parser.add_argument("--sample-only", action="store_true", help="Only extend sample stock ids plus benchmark_TAIEX.")
    parser.add_argument(
        "--bootstrap-sample-source",
        action="store_true",
        help="Create missing source-suffix sample stock and benchmark caches before extension.",
    )
    parser.add_argument("--sample-source-start", default="2026-06-29")
    parser.add_argument("--sample-source-end", default=None, help="Defaults to source suffix end date.")
    parser.add_argument("--sleep-s", type=float, default=0.0)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    target_date = parse_date(args.target_date)
    tail_start = parse_date(args.tail_start) if args.tail_start else suffix_end_date(args.source_suffix) + timedelta(days=1)
    if tail_start > target_date:
        raise SystemExit(f"tail-start {tail_start} is after target-date {target_date}")
    if args.source_suffix == args.target_suffix:
        raise SystemExit("source-suffix and target-suffix must differ")

    days = trading_days(tail_start, target_date)
    sample_stock_ids = set(str(x) for x in args.sample_stock_id)
    bootstrap_report = None
    if args.bootstrap_sample_source:
        source_end = args.sample_source_end or suffix_end_date(args.source_suffix).isoformat()
        bootstrap_report = bootstrap_sample_sources(
            sample_stock_ids,
            args.source_suffix,
            args.sample_source_start,
            source_end,
            overwrite=args.overwrite,
            sleep_s=args.sleep_s,
        )
    if args.sample_only:
        daily = {
            tag: fetch_sample_daily(
                tag, dataset, days, sample_stock_ids, args.sleep_s, refresh_daily=args.refresh_daily
            )
            for tag, dataset in PRICE_TYPES.items()
        }
    else:
        daily = {
            tag: fetch_daily(dataset, tag, days, args.sleep_s, refresh_daily=args.refresh_daily)
            for tag, dataset in PRICE_TYPES.items()
        }
    extensions = {
        tag: extend_price_type(
            tag,
            df,
            args.source_suffix,
            args.target_suffix,
            dry_run=args.dry_run,
            overwrite=args.overwrite,
            sample_stock_ids=sample_stock_ids,
            sample_only=args.sample_only,
        )
        for tag, df in daily.items()
    }
    extensions["benchmark_TAIEX"] = extend_benchmark(
        daily["raw"], args.source_suffix, args.target_suffix, dry_run=args.dry_run, overwrite=args.overwrite
    )

    validation_notes = []
    for tag in ["raw", "adj"]:
        for stock_id, sample in extensions[tag].get("sample_outputs", {}).items():
            if sample["out"]["date_max"] == args.target_date:
                validation_notes.append(f"{tag} sample {stock_id} extends to target date {args.target_date}.")
            else:
                validation_notes.append(
                    f"WARN {tag} sample {stock_id} out_max={sample['out']['date_max']} target={args.target_date}."
                )
    bench = extensions["benchmark_TAIEX"]
    if bench.get("out", {}).get("date_max") == args.target_date:
        validation_notes.append(f"benchmark_TAIEX extends to target date {args.target_date}.")
    else:
        validation_notes.append(
            f"WARN benchmark_TAIEX out_max={bench.get('out', {}).get('date_max')} target={args.target_date}."
        )

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "dry_run": bool(args.dry_run),
        "refresh_daily": bool(args.refresh_daily),
        "overwrite": bool(args.overwrite),
        "sample_only": bool(args.sample_only),
        "bootstrap_sample_source": bool(args.bootstrap_sample_source),
        "bootstrap_report": bootstrap_report,
        "sample_stock_ids": sorted(sample_stock_ids),
        "source_suffix": args.source_suffix,
        "target_suffix": args.target_suffix,
        "tail_start": tail_start.isoformat(),
        "target_date": args.target_date,
        "trading_days": days,
        "daily_feeds": {tag: frame_date_bounds(df) for tag, df in daily.items()},
        "extensions": extensions,
        "validation_notes": validation_notes,
    }
    report["report_paths"] = write_report(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
