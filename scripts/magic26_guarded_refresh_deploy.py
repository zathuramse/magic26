#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Guarded Magic26 daily refresh + deploy pipeline.

Default behaviour is safe for cron:
- If the probe finds no newer complete trading day, write a local report and exit 0 with no stdout.
- If a newer complete day exists, run the full regeneration/export/verify/commit/push/deploy pipeline.
- If a blocker appears, exit non-zero so Hermes cron alerts instead of failing silently.

This script intentionally does not schedule itself. Scheduling is handled by Hermes cron.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[1]
REPORT_DIR = PROJECT / "reports" / "daily_refresh"
DEFAULT_APP_CACHE_BUST = "20260702riskv2"
DEFAULT_CSS_CACHE_BUST = "20260701q"

# Import probe helpers from the sibling script.
sys.path.insert(0, str(PROJECT / "scripts"))
import daily_refresh_magic26 as probe  # noqa: E402
from magic26_paths import out_dir  # noqa: E402


@dataclass
class CmdResult:
    label: str
    command: list[str]
    output_tail: str


def run(cmd: list[str], *, label: str, timeout: int = 900, dry_run: bool = False) -> CmdResult:
    if dry_run:
        return CmdResult(label, cmd, "DRY-RUN: command not executed")
    proc = subprocess.run(cmd, cwd=PROJECT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"[{label}] failed with exit {proc.returncode}:\n{proc.stdout}")
    tail = "\n".join(proc.stdout.splitlines()[-40:])
    return CmdResult(label, cmd, tail)


def git_output(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=PROJECT, text=True).strip()


def require_clean_worktree() -> None:
    dirty = git_output(["status", "--porcelain"])
    if dirty:
        raise RuntimeError(f"Refusing unattended refresh with dirty worktree:\n{dirty}")


def next_calendar_day(day_s: str) -> str:
    return (date.fromisoformat(day_s) + timedelta(days=1)).isoformat()


def find_signal_file(suffix: str, price_mode: str) -> Path:
    pattern = f"magic26_v0_signals_all_liquid30000000_{price_mode}_{suffix}_*stocks.csv"
    outputs = out_dir()
    matches = sorted(outputs.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    if not matches:
        raise FileNotFoundError(f"Missing signal output matching {pattern}")
    return matches[0]


def build_probe_report(args: argparse.Namespace) -> dict[str, Any]:
    ns = argparse.Namespace(
        dry_run=True,
        as_of=args.as_of,
        lookback_days=args.lookback_days,
        stop_after_complete=args.stop_after_complete,
        check_local=False,
    )
    report = probe.build_report(ns)
    return report


def write_guard_report(report: dict[str, Any], *, runtime: bool = False) -> tuple[Path, Path]:
    out_dir = REPORT_DIR / "runtime" if runtime else REPORT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"p5_9_guarded_refresh_{report['status']}_{stamp}.json"
    md_path = out_dir / f"p5_9_guarded_refresh_{report['status']}_{stamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Magic26 guarded refresh run",
        "",
        f"run_at: {report['run_at']}",
        f"status: `{report['status']}`",
        f"dry_run: `{report['dry_run']}`",
        "",
        "## Decision",
        "",
        f"- current_data_through: `{report.get('current_dashboard_data_through')}`",
        f"- complete_data_through: `{report.get('complete_data_through')}`",
        f"- current_snapshot_suffix: `{report.get('current_snapshot_suffix')}`",
        f"- target_snapshot_suffix: `{report.get('target_snapshot_suffix')}`",
        f"- should_refresh: `{report.get('should_refresh')}`",
        "",
        "## Commands",
        "",
    ]
    for c in report.get("commands", []):
        lines.append(f"- {c['label']}: `{' '.join(c['command'])}`")
    if report.get("message"):
        lines += ["", "## Message", "", str(report["message"])]
    if report.get("error"):
        lines += ["", "## Error", "", "```text", str(report["error"]), "```"]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def full_refresh(args: argparse.Namespace, base: dict[str, Any]) -> dict[str, Any]:
    current_date = str(base["current_dashboard_data_through"])
    target_date = str(base["complete_data_through"])
    current_suffix = str(base["current_snapshot_suffix"])
    target_suffix = str(base["target_snapshot_suffix"])
    tail_start = next_calendar_day(current_date)
    commands: list[CmdResult] = []
    py = sys.executable

    require_clean_worktree()

    commands.append(run([py, "scripts/extend_magic26_cache.py", "--refresh-daily", "--source-suffix", current_suffix, "--target-suffix", target_suffix, "--tail-start", tail_start, "--target-date", target_date], label="extend_cache", timeout=1800, dry_run=args.dry_run))
    commands.append(run([py, "scripts/magic26_signal_pilot.py", "--start-date", "2021-01-01", "--end-date", target_date, "--universe", "all", "--liquid-universe", "--min-avg-amount", "30000000"], label="base_raw", timeout=1800, dry_run=args.dry_run))
    commands.append(run([py, "scripts/magic26_signal_pilot.py", "--start-date", "2021-01-01", "--end-date", target_date, "--universe", "all", "--liquid-universe", "--min-avg-amount", "30000000", "--adjusted"], label="base_adjusted", timeout=1800, dry_run=args.dry_run))

    raw_signals = find_signal_file(target_suffix, "raw") if not args.dry_run else Path(f"<raw_signals_{target_suffix}>")
    adj_signals = find_signal_file(target_suffix, "adj") if not args.dry_run else Path(f"<adj_signals_{target_suffix}>")
    commands.append(run([py, "scripts/magic26_round4_execution_checks.py", "--signals", str(raw_signals), "--start-date", "2021-01-01", "--end-date", target_date, "--run-label", f"round6_regime_all_liquid30000000_raw_{target_suffix}"], label="round4_raw", timeout=1800, dry_run=args.dry_run))
    commands.append(run([py, "scripts/magic26_round4_execution_checks.py", "--signals", str(adj_signals), "--start-date", "2021-01-01", "--end-date", target_date, "--run-label", f"round6_regime_all_liquid30000000_adj_{target_suffix}"], label="round4_adjusted", timeout=1800, dry_run=args.dry_run))

    for script, label in [
        ("magic26_round7_param_grid.py", "round7"),
        ("magic26_round8_tradeability_checks.py", "round8"),
        ("magic26_round9_close_exit_checks.py", "round9"),
        ("magic26_round14_bootstrap_path_review.py", "round14"),
        ("magic26_round19_author_absorption.py", "round19"),
        ("magic26_round20_60d_validation.py", "round20"),
        ("magic26_round21_volgap_rescue_review.py", "round21"),
    ]:
        commands.append(run([py, f"scripts/{script}", "--snapshot-suffix", target_suffix], label=label, timeout=1200, dry_run=args.dry_run))

    # Interim export is required because round15 consumes public/data/magic26_candidates_history.csv.
    commands.append(run([py, "scripts/export_dashboard_data.py", "--snapshot-suffix", target_suffix, "--data-through", target_date], label="export_interim", timeout=1200, dry_run=args.dry_run))
    for script, label in [
        ("magic26_round15_priority_review_pack.py", "round15"),
        ("magic26_round16_top10_manual_review.py", "round16"),
        ("magic26_round17_b_retest_rearm_watch.py", "round17"),
    ]:
        commands.append(run([py, f"scripts/{script}", "--snapshot-suffix", target_suffix], label=label, timeout=1200, dry_run=args.dry_run))
    commands.append(run([py, "scripts/export_dashboard_data.py", "--snapshot-suffix", target_suffix, "--data-through", target_date], label="export_final", timeout=1200, dry_run=args.dry_run))
    commands.append(run([py, "scripts/verify_magic26_package.py", "--snapshot-suffix", target_suffix, "--data-through", target_date, "--app-cache-bust", args.app_cache_bust, "--css-cache-bust", args.css_cache_bust], label="verify_package", timeout=600, dry_run=args.dry_run))

    commit_sha = None
    if not args.dry_run:
        # Stage only expected dashboard/package surfaces and reports. External research output is not committed.
        run(["git", "add", "data/processed", "public/data", "reports/daily_refresh"], label="git_add", timeout=300)
        status = git_output(["status", "--porcelain"])
        if status:
            msg = f"Refresh Magic26 data through {target_date}"
            commands.append(run(["git", "commit", "-m", msg], label="git_commit", timeout=600))
            commit_sha = git_output(["rev-parse", "--short", "HEAD"])
            commands.append(run(["git", "push", "origin", "main"], label="git_push", timeout=900))
        else:
            commit_sha = git_output(["rev-parse", "--short", "HEAD"])
    commands.append(run([py, "scripts/deploy_cloudflare.py", "--project-name", args.project_name, "--data-through", target_date, "--snapshot-suffix", target_suffix, "--app-cache-bust", args.app_cache_bust, "--css-cache-bust", args.css_cache_bust], label="deploy_cloudflare", timeout=1800, dry_run=args.dry_run))

    return {
        "status": "dry_run_refresh_planned" if args.dry_run else "refreshed",
        "commit_sha": commit_sha,
        "commands": [{"label": c.label, "command": c.command, "output_tail": c.output_tail} for c in commands],
        "message": f"Magic26 refreshed to {target_date} ({target_suffix})" if not args.dry_run else f"DRY-RUN planned refresh to {target_date} ({target_suffix})",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Guarded Magic26 refresh/deploy pipeline for Hermes cron.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true", help="Print skip reports too. Cron should omit this for silent skips.")
    parser.add_argument("--as-of", default="")
    parser.add_argument("--lookback-days", type=int, default=10)
    parser.add_argument("--stop-after-complete", type=int, default=2)
    parser.add_argument("--project-name", default="magic26")
    parser.add_argument("--app-cache-bust", default=DEFAULT_APP_CACHE_BUST)
    parser.add_argument("--css-cache-bust", default=DEFAULT_CSS_CACHE_BUST)
    args = parser.parse_args()

    base = build_probe_report(args)
    result: dict[str, Any] = {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "dry_run": bool(args.dry_run),
        "current_dashboard_data_through": base.get("current_dashboard_data_through"),
        "complete_data_through": base.get("complete_data_through"),
        "current_snapshot_suffix": base.get("current_snapshot_suffix"),
        "target_snapshot_suffix": base.get("target_snapshot_suffix"),
        "should_refresh": base.get("should_refresh"),
        "probe": base,
    }
    try:
        if not base.get("complete_data_through"):
            result.update({"status": "skipped_no_complete_day", "message": "No complete trading day found."})
        elif not base.get("should_refresh"):
            result.update({"status": "skipped_up_to_date", "message": "Dashboard already matches latest complete data."})
        elif not base.get("current_snapshot_suffix") or not base.get("target_snapshot_suffix"):
            raise RuntimeError("Missing current or target snapshot suffix; refusing refresh.")
        else:
            result.update(full_refresh(args, base))
    except Exception as exc:
        result.update({"status": "error", "error": repr(exc)})
        json_path, md_path = write_guard_report(result, runtime=True)
        print(f"Magic26 guarded refresh ERROR. report={md_path}\n{exc}")
        raise

    json_path, md_path = write_guard_report(result, runtime=True)
    # Cron no_agent: empty stdout means silent. Print only refresh/error, or skip when verbose.
    if args.verbose or result["status"] not in {"skipped_up_to_date", "skipped_no_complete_day"}:
        print(json.dumps({
            "status": result["status"],
            "current_dashboard_data_through": result.get("current_dashboard_data_through"),
            "complete_data_through": result.get("complete_data_through"),
            "target_snapshot_suffix": result.get("target_snapshot_suffix"),
            "report_md": md_path.as_posix(),
            "message": result.get("message"),
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
