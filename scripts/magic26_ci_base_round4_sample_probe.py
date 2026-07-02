from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from magic26_paths import cache_dir, out_dir  # noqa: E402

PROJECT = Path(__file__).resolve().parents[1]
REPORT_DIR = Path(os.getenv("MAGIC26_REPORT_DIR", PROJECT / "reports" / "daily_refresh"))
TARGET_SUFFIX = os.getenv("SNAPSHOT_SUFFIX", "20210101_20260702")
TARGET_DATE = os.getenv("DATA_THROUGH", "2026-07-02")
START_DATE = "2021-01-01"
SAMPLE_STOCK = "6213"


def run_command(args: list[str]) -> dict[str, Any]:
    proc = subprocess.run(
        args,
        cwd=PROJECT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return {
        "args": args,
        "returncode": proc.returncode,
        "output_tail": proc.stdout[-4000:],
    }


def read_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def csv_info(path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {"path": str(path), "exists": path.exists()}
    if not path.exists():
        return info
    df = pd.read_csv(path)
    info["rows"] = int(len(df))
    info["columns"] = list(df.columns)
    if "date" in df.columns and not df.empty:
        dates = pd.to_datetime(df["date"], errors="coerce")
        info["date_min"] = dates.min().strftime("%Y-%m-%d") if len(dates.dropna()) else None
        info["date_max"] = dates.max().strftime("%Y-%m-%d") if len(dates.dropna()) else None
    if "stock_id" in df.columns and not df.empty:
        info["stock_ids"] = sorted(str(x).replace(".0", "") for x in df["stock_id"].dropna().unique().tolist())[:20]
    return info


def find_latest_manifest(pattern: str, before: set[Path]) -> Path:
    candidates = sorted(out_dir().glob(pattern), key=lambda p: p.stat().st_mtime)
    new_candidates = [p for p in candidates if p not in before]
    if not new_candidates:
        raise RuntimeError(f"No new manifest matched {pattern}")
    return new_candidates[-1]


def validate_round4(path: Path) -> dict[str, Any]:
    info = csv_info(path)
    if not path.exists():
        info["checks"] = ["FAIL missing round4 checked-signal CSV"]
        return info
    df = pd.read_csv(path)
    checks: list[str] = []
    required_cols = ["bench_close", "risk_next_gap_gt3", "regime_all3", "excess_20d", "t1_excess_20d"]
    for col in required_cols:
        checks.append(("OK " if col in df.columns else "FAIL ") + f"column {col} present")
    if "bench_close" in df.columns:
        checks.append(f"OK bench_close_missing={int(df['bench_close'].isna().sum())}")
    if "stock_id" in df.columns:
        stock_ids = set(str(x).replace(".0", "") for x in df["stock_id"].dropna().unique().tolist())
        checks.append(("OK " if SAMPLE_STOCK in stock_ids else "WARN ") + f"sample stock {SAMPLE_STOCK} present")
    checks.append(("OK " if len(df) > 0 else "FAIL ") + "rows > 0")
    info["checks"] = checks
    return info


def remove_conflicting_sample_cache(mode: str) -> dict[str, Any]:
    """Remove short P6-7 sample cache files that share full-range cache names.

    P6-7 creates 4-row sample files named like the real per-stock cache, e.g.
    raw_6213_20210101_20260702.parquet. magic26_signal_pilot uses the same
    cache name for a full 2021-01-01..target-date fetch. In CI, the restored
    P6-7 cache can therefore shadow the full-range fetch and produce zero
    signals. This probe is CI-staging only, so removing the conflicting sample
    cache is safer than silently using it.
    """
    removed: list[str] = []
    tag = "adj" if mode == "adj" else "raw"
    for path in [
        cache_dir() / f"{tag}_{SAMPLE_STOCK}_{TARGET_SUFFIX}.parquet",
        cache_dir() / f"benchmark_TAIEX_{TARGET_SUFFIX}.parquet",
    ]:
        if path.exists():
            path.unlink()
            removed.append(str(path))
    return {"mode": mode, "removed": removed}


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# P6-9 Magic26 base signal + round4 sample probe",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- sample_stock: `{report['sample_stock']}`",
        f"- target_suffix: `{report['target_suffix']}`",
        f"- target_date: `{report['target_date']}`",
        f"- out_dir: `{report['out_dir']}`",
        "- scope: sample base signal + round4 only; no round7/8/9, no export, no deploy, no schedule",
        "",
        "## Outputs",
        "",
    ]
    for mode in ["raw", "adj"]:
        item = report["modes"][mode]
        lines.append(f"- {mode} base signals: rows={item['signals_info'].get('rows')} date_max={item['signals_info'].get('date_max')} path=`{item['signals_path']}`")
        lines.append(f"- {mode} round4 checked: rows={item['round4_checked_info'].get('rows')} date_max={item['round4_checked_info'].get('date_max')} path=`{item['round4_checked_path']}`")
        for check in item["round4_checked_info"].get("checks", []):
            lines.append(f"  - {check}")
    lines.extend(["", "## Commands", ""])
    for mode in ["raw", "adj"]:
        for command in report["modes"][mode]["commands"]:
            lines.append(f"- {mode}: `{ ' '.join(command['args']) }` -> rc={command['returncode']}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_dir().mkdir(parents=True, exist_ok=True)
    modes: dict[str, Any] = {}

    for mode, adjusted_flag in [("raw", False), ("adj", True)]:
        cache_cleanup = remove_conflicting_sample_cache(mode)
        before_manifests = set(out_dir().glob("magic26_v0_manifest_*.json"))
        base_cmd = [
            sys.executable,
            "scripts/magic26_signal_pilot.py",
            "--start-date",
            START_DATE,
            "--end-date",
            TARGET_DATE,
            "--universe",
            "manual",
            "--stock-ids",
            SAMPLE_STOCK,
        ]
        if adjusted_flag:
            base_cmd.append("--adjusted")
        base_result = run_command(base_cmd)
        if base_result["returncode"] != 0:
            raise RuntimeError(f"base signal {mode} failed: {base_result['output_tail']}")

        manifest_path = find_latest_manifest("magic26_v0_manifest_*.json", before_manifests)
        manifest = read_manifest(manifest_path)
        signals_path = Path(manifest["outputs"]["signals"])
        if not signals_path.is_absolute():
            signals_path = PROJECT / signals_path
        signals_info = csv_info(signals_path)
        if not signals_info.get("rows"):
            raise RuntimeError(f"base signal {mode} produced no sample signal rows: {signals_path}")

        run_label = f"round6_regime_sample{SAMPLE_STOCK}_{mode}_{TARGET_SUFFIX}"
        round4_cmd = [
            sys.executable,
            "scripts/magic26_round4_execution_checks.py",
            "--signals",
            str(signals_path),
            "--start-date",
            START_DATE,
            "--end-date",
            TARGET_DATE,
            "--run-label",
            run_label,
        ]
        round4_result = run_command(round4_cmd)
        if round4_result["returncode"] != 0:
            raise RuntimeError(f"round4 {mode} failed: {round4_result['output_tail']}")
        round4_checked_path = out_dir() / f"magic26_round4_checked_signals_{run_label}.csv"
        round4_manifest_path = out_dir() / f"magic26_round4_manifest_{run_label}.json"
        modes[mode] = {
            "cache_cleanup": cache_cleanup,
            "base_manifest_path": str(manifest_path),
            "signals_path": str(signals_path),
            "signals_info": signals_info,
            "round4_run_label": run_label,
            "round4_checked_path": str(round4_checked_path),
            "round4_manifest_path": str(round4_manifest_path),
            "round4_checked_info": validate_round4(round4_checked_path),
            "commands": [base_result, round4_result],
        }

    failures = []
    for mode, item in modes.items():
        for check in item["round4_checked_info"].get("checks", []):
            if check.startswith("FAIL"):
                failures.append(f"{mode}: {check}")
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sample_stock": SAMPLE_STOCK,
        "target_suffix": TARGET_SUFFIX,
        "target_date": TARGET_DATE,
        "start_date": START_DATE,
        "out_dir": str(out_dir()),
        "modes": modes,
        "success": not failures,
        "failures": failures,
        "note": "CI sample base+round4 probe only; no round7/8/9, no export, no deploy, no schedule.",
    }
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = REPORT_DIR / f"p6_9_base_round4_sample_probe_{stamp}.json"
    md_path = REPORT_DIR / f"p6_9_base_round4_sample_probe_{stamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    report["report_paths"] = {"json": str(json_path), "markdown": str(md_path)}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
