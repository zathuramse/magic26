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
from magic26_paths import out_dir  # noqa: E402

PROJECT = Path(__file__).resolve().parents[1]
REPORT_DIR = Path(os.getenv("MAGIC26_REPORT_DIR", PROJECT / "reports" / "daily_refresh"))
TARGET_SUFFIX = os.getenv("SNAPSHOT_SUFFIX", "20210101_20260702")
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
    return {"args": args, "returncode": proc.returncode, "output_tail": proc.stdout[-4000:]}


def csv_info(path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {"path": str(path), "exists": path.exists(), "size_bytes": path.stat().st_size if path.exists() else 0}
    if not path.exists() or path.stat().st_size == 0:
        return info
    try:
        df = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        info["rows"] = 0
        info["columns"] = []
        return info
    info["rows"] = int(len(df))
    info["columns"] = list(df.columns)
    return info


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    raw = out_dir() / f"magic26_round4_checked_signals_round6_regime_sample{SAMPLE_STOCK}_raw_{TARGET_SUFFIX}.csv"
    adj = out_dir() / f"magic26_round4_checked_signals_round6_regime_sample{SAMPLE_STOCK}_adj_{TARGET_SUFFIX}.csv"
    missing = [str(p) for p in [raw, adj] if not p.exists()]
    if missing:
        raise SystemExit(f"missing P6-9 sample round4 inputs: {missing}")

    commands = {
        "round7": [sys.executable, "scripts/magic26_round7_param_grid.py", "--snapshot-suffix", TARGET_SUFFIX, "--round4-raw", str(raw), "--round4-adj", str(adj)],
        "round8": [sys.executable, "scripts/magic26_round8_tradeability_checks.py", "--snapshot-suffix", TARGET_SUFFIX, "--round4-raw", str(raw), "--round4-adj", str(adj)],
        "round9": [sys.executable, "scripts/magic26_round9_close_exit_checks.py", "--snapshot-suffix", TARGET_SUFFIX, "--round4-raw", str(raw), "--round4-adj", str(adj)],
    }
    command_results = {name: run_command(args) for name, args in commands.items()}
    failures = [f"{name} rc={result['returncode']}" for name, result in command_results.items() if result["returncode"] != 0]

    outputs = {
        "round7_summary": csv_info(out_dir() / f"magic26_round7_param_grid_summary_{TARGET_SUFFIX}.csv"),
        "round7_top": csv_info(out_dir() / f"magic26_round7_param_grid_top_{TARGET_SUFFIX}.csv"),
        "round8_summary": csv_info(out_dir() / f"magic26_round8_tradeability_summary_{TARGET_SUFFIX}.csv"),
        "round8_detail": csv_info(out_dir() / f"magic26_round8_tradeability_detail_{TARGET_SUFFIX}.csv"),
        "round9_summary": csv_info(out_dir() / f"magic26_round9_close_exit_summary_{TARGET_SUFFIX}.csv"),
        "round9_detail": csv_info(out_dir() / f"magic26_round9_close_exit_detail_{TARGET_SUFFIX}.csv"),
    }
    for key, info in outputs.items():
        if not info["exists"]:
            failures.append(f"missing output {key}")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "target_suffix": TARGET_SUFFIX,
        "sample_stock": SAMPLE_STOCK,
        "inputs": {"round4_raw": str(raw), "round4_adj": str(adj)},
        "commands": command_results,
        "outputs": outputs,
        "success": not failures,
        "failures": failures,
        "note": "CI sample round7/8/9 probe only; no full market refresh, no export, no deploy, no schedule.",
    }
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = REPORT_DIR / f"p6_10_round789_sample_probe_{stamp}.json"
    md_path = REPORT_DIR / f"p6_10_round789_sample_probe_{stamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_lines = [
        "# P6-10 Magic26 round7/8/9 sample probe",
        "",
        f"- target_suffix: `{TARGET_SUFFIX}`",
        f"- sample_stock: `{SAMPLE_STOCK}`",
        f"- success: `{report['success']}`",
        "- scope: sample downstream rounds only; no export, no deploy, no schedule",
        "",
        "## Outputs",
    ]
    for key, info in outputs.items():
        md_lines.append(f"- {key}: exists={info['exists']} rows={info.get('rows')} size={info.get('size_bytes')} path=`{info['path']}`")
    md_lines.extend(["", "## Failures", ""])
    md_lines.extend([f"- {x}" for x in failures] or ["- none"])
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    report["report_paths"] = {"json": str(json_path), "markdown": str(md_path)}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
