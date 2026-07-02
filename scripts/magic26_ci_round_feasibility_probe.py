from __future__ import annotations

import ast
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from magic26_paths import cache_dir, out_dir  # noqa: E402

PROJECT = Path(__file__).resolve().parents[1]
REPORT_DIR = Path(os.getenv("MAGIC26_REPORT_DIR", PROJECT / "reports" / "daily_refresh"))
TARGET_SUFFIX = os.getenv("SNAPSHOT_SUFFIX", "20210101_20260702")
SOURCE_SUFFIX = "20210101_20260701"
TARGET_DATE = os.getenv("DATA_THROUGH", "2026-07-02")
SAMPLE_STOCK = "6213"

SCRIPTS = [
    "magic26_signal_pilot.py",
    "magic26_round4_execution_checks.py",
    "magic26_round7_param_grid.py",
    "magic26_round8_tradeability_checks.py",
    "magic26_round9_close_exit_checks.py",
]

PATTERNS = {
    "windows_paths": r"C:/Users|C:\\\\Users",
    "snapshot_20260701": r"20210101_20260701",
    "snapshot_20260702": r"20210101_20260702",
    "date_20260701": r"2026-07-01|20260701",
    "date_20260702": r"2026-07-02|20260702",
    "magic26_paths": r"magic26_paths|cache_dir\(|out_dir\(|source_root\(|research_root\(",
}


def cli_args(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    args: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument":
            if node.args and isinstance(node.args[0], ast.Constant):
                args.append(str(node.args[0].value))
    return args


def script_inventory(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    return {
        "path": str(path),
        "lines": text.count("\n") + 1,
        "cli_args": cli_args(path),
        "pattern_counts": {name: len(re.findall(pattern, text)) for name, pattern in PATTERNS.items()},
        "uses_magic26_paths": "magic26_paths" in text,
        "has_snapshot_suffix_arg": "--snapshot-suffix" in text,
        "has_stock_ids_arg": "--stock-ids" in text,
        "has_max_stocks_arg": "--max-stocks" in text,
        "has_output_dir_arg": "--out-dir" in text,
        "has_cache_dir_arg": "--cache-dir" in text,
    }


def file_info(path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {"path": str(path), "exists": path.exists()}
    if not path.exists():
        return info
    info["size_bytes"] = path.stat().st_size
    try:
        if path.suffix == ".csv":
            df = pd.read_csv(path, nrows=20)
            info["sample_rows_read"] = int(len(df))
            info["columns"] = list(df.columns)
        elif path.suffix == ".parquet":
            df = pd.read_parquet(path)
            info["rows"] = int(len(df))
            info["columns"] = list(df.columns)
            if "date" in df.columns:
                dates = pd.to_datetime(df["date"], errors="coerce")
                info["date_min"] = dates.min().strftime("%Y-%m-%d") if len(dates.dropna()) else None
                info["date_max"] = dates.max().strftime("%Y-%m-%d") if len(dates.dropna()) else None
    except Exception as exc:  # noqa: BLE001
        info["read_error"] = str(exc)
    return info


def expected_files() -> dict[str, dict[str, Any]]:
    cache = cache_dir()
    out = out_dir()
    expected = {
        "sample_cache_raw_source": cache / f"raw_{SAMPLE_STOCK}_{SOURCE_SUFFIX}.parquet",
        "sample_cache_raw_target": cache / f"raw_{SAMPLE_STOCK}_{TARGET_SUFFIX}.parquet",
        "sample_cache_adj_source": cache / f"adj_{SAMPLE_STOCK}_{SOURCE_SUFFIX}.parquet",
        "sample_cache_adj_target": cache / f"adj_{SAMPLE_STOCK}_{TARGET_SUFFIX}.parquet",
        "sample_cache_benchmark_source": cache / f"benchmark_TAIEX_{SOURCE_SUFFIX}.parquet",
        "sample_cache_benchmark_target": cache / f"benchmark_TAIEX_{TARGET_SUFFIX}.parquet",
        "round4_raw_target": out / f"magic26_round4_checked_signals_round6_regime_all_liquid30000000_raw_{TARGET_SUFFIX}.csv",
        "round4_adj_target": out / f"magic26_round4_checked_signals_round6_regime_all_liquid30000000_adj_{TARGET_SUFFIX}.csv",
        "round7_manifest_target": out / f"magic26_round7_param_grid_manifest_{TARGET_SUFFIX}.json",
        "round8_manifest_target": out / f"magic26_round8_tradeability_manifest_{TARGET_SUFFIX}.json",
        "round9_manifest_target": out / f"magic26_round9_close_exit_manifest_{TARGET_SUFFIX}.json",
    }
    return {key: file_info(path) for key, path in expected.items()}


def make_blockers(inventory: dict[str, Any], files: dict[str, dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    signal = inventory["magic26_signal_pilot.py"]
    if signal["has_stock_ids_arg"] and signal["has_max_stocks_arg"]:
        blockers.append("base signal has sample controls (--stock-ids/--max-stocks), but output run_id uses selected stock count rather than dashboard 2130stocks naming.")
    if not inventory["magic26_round4_execution_checks.py"]["has_snapshot_suffix_arg"]:
        blockers.append("round4 has no --snapshot-suffix; it needs explicit --signals and --run-label from a prior base-signal output.")
    for script in ["magic26_round7_param_grid.py", "magic26_round8_tradeability_checks.py", "magic26_round9_close_exit_checks.py"]:
        if inventory[script]["has_snapshot_suffix_arg"]:
            blockers.append(f"{script} is suffix-parameterized, but still expects round4 checked-signal filenames for both raw/adj under OUT.")
    missing_round4 = [k for k in ["round4_raw_target", "round4_adj_target"] if not files[k]["exists"]]
    if missing_round4:
        blockers.append("target round4 checked-signal inputs are missing in CI staging; round7/8/9 cannot run yet without base signal + round4 regeneration.")
    cache_bad = []
    for key in [
        "sample_cache_raw_target", "sample_cache_adj_target", "sample_cache_benchmark_target",
    ]:
        item = files[key]
        if not item.get("exists") or item.get("date_max") != TARGET_DATE:
            cache_bad.append(key)
    if cache_bad:
        blockers.append("sample target cache prerequisites are missing or not extended to target date: " + ", ".join(cache_bad))
    blockers.append("P6-8 is inventory-only: no heavy round scripts were executed, no public/data export, no deploy, no schedule.")
    return blockers


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# P6-8 Magic26 round pipeline feasibility probe",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- target_suffix: `{report['target_suffix']}`",
        f"- target_date: `{report['target_date']}`",
        f"- cache_dir: `{report['paths']['cache_dir']}`",
        f"- out_dir: `{report['paths']['out_dir']}`",
        "- scope: inventory only; no heavy round execution, no export, no deploy, no schedule",
        "",
        "## Script inventory",
        "",
    ]
    for name, item in report["inventory"].items():
        lines.append(f"- {name}: args={', '.join(item['cli_args'])}; uses_magic26_paths={item['uses_magic26_paths']}")
    lines.extend(["", "## Expected files", ""])
    for key, item in report["files"].items():
        extra = f" date_max={item.get('date_max')}" if item.get("date_max") else ""
        lines.append(f"- {key}: exists={item['exists']}{extra}")
    lines.extend(["", "## Blockers / notes", ""])
    for blocker in report["blockers"]:
        lines.append(f"- {blocker}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    inventory = {script: script_inventory(PROJECT / "scripts" / script) for script in SCRIPTS}
    files = expected_files()
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "target_suffix": TARGET_SUFFIX,
        "source_suffix": SOURCE_SUFFIX,
        "target_date": TARGET_DATE,
        "sample_stock": SAMPLE_STOCK,
        "paths": {"cache_dir": str(cache_dir()), "out_dir": str(out_dir()), "report_dir": str(REPORT_DIR)},
        "inventory": inventory,
        "files": files,
        "blockers": make_blockers(inventory, files),
        "recommended_next_step": "Parameterize and prove base signal + round4 sample regeneration before attempting round7/8/9 in CI.",
        "note": "CI feasibility probe only; no generated data commit, no deploy, no schedule.",
    }
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = REPORT_DIR / f"p6_8_round_feasibility_probe_{stamp}.json"
    md_path = REPORT_DIR / f"p6_8_round_feasibility_probe_{stamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    report["report_paths"] = {"json": str(json_path), "markdown": str(md_path)}
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
