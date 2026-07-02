from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[1]
REPORT_DIR = PROJECT / "reports" / "daily_refresh"
PUBLIC_SUMMARY = PROJECT / "public" / "data" / "summary.json"
EXPORT_MANIFEST = PROJECT / "data" / "processed" / "export_manifest.json"
FINMIND_BASE = "https://api.finmindtrade.com/api/v4/data"
SNAPSHOT_START = "20210101"
ENV_CANDIDATES = [
    Path("C:/Users/abckf/AppData/Local/hermes/profiles/jojo/.env"),
    Path("C:/Users/abckf/AppData/Local/hermes/.env"),
]

MIN_RAW_ROWS = 900
MIN_ADJ_ROWS = 900
MIN_BENCH_ROWS = 1


def read_token() -> str:
    if os.getenv("FINMIND_TOKEN"):
        return os.getenv("FINMIND_TOKEN", "").strip()
    for env_path in ENV_CANDIDATES:
        if not env_path.exists():
            continue
        text = env_path.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            if line.startswith("FINMIND_TOKEN="):
                return line.split("=", 1)[1].strip().strip("\"'")
    return ""


def finmind_get_uncached(dataset: str, *, sleep_s: float = 0.15, **params: str) -> list[dict[str, Any]]:
    token = read_token()
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "Magic26DailyRefresh/1.0"} if token else {"User-Agent": "Magic26DailyRefresh/1.0"}
    query = urllib.parse.urlencode({"dataset": dataset, **params})
    req = urllib.request.Request(f"{FINMIND_BASE}?{query}", headers=headers)
    with urllib.request.urlopen(req, timeout=120) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if payload.get("status") != 200:
        raise RuntimeError(f"FinMind {dataset} failed: status={payload.get('status')} msg={payload.get('msg')}")
    time.sleep(sleep_s)
    return payload.get("data") or []


def market_days(end: date, lookback_calendar_days: int) -> list[date]:
    start = end - timedelta(days=lookback_calendar_days)
    days: list[date] = []
    d = start
    while d <= end:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


def stock_row_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ids = {str(r.get("stock_id") or "") for r in rows if re.match(r"^\d{4}$", str(r.get("stock_id") or ""))}
    dates = sorted({str(r.get("date") or "") for r in rows if r.get("date")})
    return {"rows": len(rows), "stock_count": len(ids), "dates": dates}


def probe_day(day: date) -> dict[str, Any]:
    day_s = day.isoformat()
    raw = finmind_get_uncached("TaiwanStockPrice", start_date=day_s, end_date=day_s)
    adj = finmind_get_uncached("TaiwanStockPriceAdj", start_date=day_s, end_date=day_s)
    bench = finmind_get_uncached("TaiwanStockPrice", data_id="TAIEX", start_date=day_s, end_date=day_s)
    raw_stats = stock_row_stats(raw)
    adj_stats = stock_row_stats(adj)
    bench_stats = {"rows": len(bench), "dates": sorted({str(r.get("date") or "") for r in bench if r.get("date")})}
    complete = (
        raw_stats["rows"] >= MIN_RAW_ROWS
        and adj_stats["rows"] >= MIN_ADJ_ROWS
        and bench_stats["rows"] >= MIN_BENCH_ROWS
        and day_s in raw_stats["dates"]
        and day_s in adj_stats["dates"]
        and day_s in bench_stats["dates"]
    )
    return {
        "date": day_s,
        "raw": raw_stats,
        "adjusted": adj_stats,
        "benchmark_TAIEX": bench_stats,
        "complete": complete,
    }


def current_dashboard_summary() -> dict[str, Any]:
    if not PUBLIC_SUMMARY.exists():
        return {}
    return json.loads(PUBLIC_SUMMARY.read_text(encoding="utf-8"))


def infer_current_snapshot_suffix() -> str | None:
    if EXPORT_MANIFEST.exists():
        manifest = json.loads(EXPORT_MANIFEST.read_text(encoding="utf-8"))
        if manifest.get("snapshot_suffix"):
            return str(manifest["snapshot_suffix"])
        for name in manifest.get("copied_csv") or []:
            m = re.search(r"(20\d{6}_20\d{6})", str(name))
            if m:
                return m.group(1)
    for path in (PROJECT / "public" / "data").glob("magic26_*_20*.csv"):
        m = re.search(r"(20\d{6}_20\d{6})", path.name)
        if m:
            return m.group(1)
    return None


def target_snapshot_suffix(complete_data_through: str | None) -> str | None:
    if not complete_data_through:
        return None
    return f"{SNAPSHOT_START}_{complete_data_through.replace('-', '')}"


def hardcoded_snapshot_refs() -> dict[str, Any]:
    # P5-2 intentionally parameterizes export/verify/deploy first. Remaining refs
    # are blockers only when they live in round/cache regeneration scripts or when
    # non-default call sites still hard-code dates instead of CLI args.
    refs: dict[str, list[dict[str, Any]]] = {}
    ignored_default_lines = (
        "DEFAULT_SNAPSHOT_SUFFIX",
        "DEFAULT_DATA_THROUGH",
        "DEFAULT_APP_CACHE_BUST",
        "DEFAULT_CSS_CACHE_BUST",
        "SNAPSHOT_START",
        "hardcoded_snapshot_refs",
        "any(token in line for token",
    )
    for path in sorted((PROJECT / "scripts").glob("*.py")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        matches = []
        for i, line in enumerate(text.splitlines(), 1):
            if any(token in line for token in ["20210101_20260701", "2026-06-30", "20260702riskv2"]):
                if any(marker in line for marker in ignored_default_lines):
                    continue
                matches.append({"line": i, "text": line.strip()[:220]})
        if matches:
            refs[path.relative_to(PROJECT).as_posix()] = matches
    return {"files": refs, "count": sum(len(v) for v in refs.values())}


def run(cmd: list[str], *, timeout: int = 300) -> str:
    proc = subprocess.run(cmd, cwd=PROJECT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed {cmd}:\n{proc.stdout}")
    return proc.stdout


def write_report(report: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = REPORT_DIR / f"p5_daily_refresh_probe_{stamp}.json"
    md_path = REPORT_DIR / f"p5_daily_refresh_probe_{stamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Magic26 daily refresh probe",
        "",
        f"run_at: {report['run_at']}",
        f"mode: {report['mode']}",
        "",
        "## Decision",
        "",
        f"- current_snapshot_suffix: `{report['current_snapshot_suffix']}`",
        f"- target_snapshot_suffix: `{report['target_snapshot_suffix']}`",
        f"- current_dashboard_data_through: `{report['current_dashboard_data_through']}`",
        f"- complete_data_through: `{report['complete_data_through']}`",
        f"- should_refresh: `{report['should_refresh']}`",
        f"- can_auto_refresh_now: `{report['can_auto_refresh_now']}`",
        "",
        "## Probe days",
        "",
    ]
    for p in report["probes"]:
        lines.append(f"- `{p['date']}` complete={p['complete']} raw_rows={p['raw']['rows']} adj_rows={p['adjusted']['rows']} bench_rows={p['benchmark_TAIEX']['rows']}")
    lines += [
        "",
        "## Blockers",
        "",
    ]
    for b in report["blockers"]:
        lines.append(f"- {b}")
    lines += [
        "",
        "## Next steps",
        "",
    ]
    for n in report["next_steps"]:
        lines.append(f"- {n}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report["report_json"] = json_path.as_posix()
    report["report_md"] = md_path.as_posix()


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    today = date.fromisoformat(args.as_of) if args.as_of else date.today()
    probes = []
    errors = []
    for d in reversed(market_days(today, args.lookback_days)):
        try:
            p = probe_day(d)
            probes.append(p)
            if p["complete"] and len([x for x in probes if x["complete"]]) >= args.stop_after_complete:
                break
        except Exception as exc:
            errors.append({"date": d.isoformat(), "error": repr(exc)})
    complete_dates = [p["date"] for p in probes if p["complete"]]
    complete_data_through = max(complete_dates) if complete_dates else None
    summary = current_dashboard_summary()
    current_data_through = summary.get("data_through")
    current_suffix = infer_current_snapshot_suffix()
    target_suffix = target_snapshot_suffix(complete_data_through)
    should_refresh = bool(complete_data_through and current_data_through and complete_data_through > str(current_data_through))
    refs = hardcoded_snapshot_refs()
    blockers = []
    can_auto_refresh_now = False
    if not complete_data_through:
        blockers.append("No complete raw+adjusted+benchmark trading day found in probe window.")
    if should_refresh:
        blockers.append("Refresh needed, but full automatic regeneration is not enabled yet because round/cache regeneration scripts still contain snapshot-specific refs.")
    if not current_suffix:
        blockers.append("Could not infer current snapshot suffix from export manifest or public data filenames.")
    if target_suffix and current_suffix == target_suffix:
        blockers.append("Target snapshot suffix equals current suffix; no new suffix transition is needed.")
    if refs["count"]:
        blockers.append(f"Found {refs['count']} remaining snapshot/date refs in round/cache scripts; parameterize before unattended refresh.")
    if args.dry_run:
        blockers.append("Dry-run mode: no cache/export/deploy side effects were executed.")
    next_steps = [
        "Parameterize round/cache regeneration scripts that still contain snapshot-specific refs.",
        "Replace one-off extend_magic26_cache_to_20260701.py with generic cache extension from current_snapshot_suffix to target_snapshot_suffix.",
        "Add guarded full-run mode: regenerate raw/adjusted base outputs, dependent rounds, export, verifier, commit/push/deploy only when complete_data_through advances.",
        "Only after a successful full-run manual test, schedule 08:00 and 16:00 weekday cron jobs.",
    ]
    return {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "dry-run" if args.dry_run else "probe-only",
        "as_of": today.isoformat(),
        "lookback_days": args.lookback_days,
        "thresholds": {"min_raw_rows": MIN_RAW_ROWS, "min_adj_rows": MIN_ADJ_ROWS, "min_bench_rows": MIN_BENCH_ROWS},
        "current_snapshot_suffix": current_suffix,
        "target_snapshot_suffix": target_suffix,
        "current_dashboard_data_through": current_data_through,
        "current_latest_signal_date": summary.get("latest_signal_date"),
        "complete_data_through": complete_data_through,
        "should_refresh": should_refresh,
        "can_auto_refresh_now": can_auto_refresh_now,
        "probes": probes,
        "probe_errors": errors,
        "hardcoded_snapshot_refs": refs,
        "blockers": blockers,
        "next_steps": next_steps,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Magic26 daily refresh orchestrator probe. Safe by default; does not deploy.")
    parser.add_argument("--dry-run", action="store_true", help="Probe and write report only; no cache/export/deploy side effects.")
    parser.add_argument("--as-of", default="", help="Override today date YYYY-MM-DD for testing.")
    parser.add_argument("--lookback-days", type=int, default=10)
    parser.add_argument("--stop-after-complete", type=int, default=2, help="Stop probing after N complete trading days are found.")
    parser.add_argument("--check-local", action="store_true", help="Run local package gates after probe.")
    args = parser.parse_args()
    report = build_report(args)
    if args.check_local:
        report["local_checks"] = {
            "py_compile": run([sys.executable, "-m", "py_compile", "scripts/daily_refresh_magic26.py", "scripts/export_dashboard_data.py", "scripts/verify_magic26_package.py"]),
            "package_verifier": run([sys.executable, "scripts/verify_magic26_package.py"]),
        }
    write_report(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
