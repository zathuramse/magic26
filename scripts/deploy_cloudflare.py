from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
CANONICAL_URL = "https://magic26.pages.dev/"
SUMMARY_URL = "https://magic26.pages.dev/data/summary.json"
LATEST_URL = "https://magic26.pages.dev/data/latest_candidates.json"
ALL_CANDIDATES_URL = "https://magic26.pages.dev/data/all_candidates.json"
ROUND14_BOOTSTRAP_URL = "https://magic26.pages.dev/data/magic26_round14_bootstrap_summary_20210101_20260622.csv"
ROUND19_VOLGAP_URL = "https://magic26.pages.dev/data/magic26_round19_volume_gap_summary_20210101_20260622.csv"


def run(cmd: list[str], *, timeout: int = 300) -> str:
    print("RUN", " ".join(cmd), flush=True)
    proc = subprocess.run(
        cmd,
        cwd=PROJECT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    print(proc.stdout, flush=True)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)
    return proc.stdout


def fetch(url: str, *, attempts: int = 6, delay: int = 5) -> bytes:
    last: Exception | None = None
    for i in range(1, attempts + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Magic26DeployVerifier/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read()
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status}")
                print(f"FETCH OK {url} bytes={len(body)} attempt={i}", flush=True)
                return body
        except Exception as exc:  # Cloudflare canonical propagation can lag.
            last = exc
            print(f"FETCH retry {i}/{attempts} {url}: {exc}", flush=True)
            time.sleep(delay)
    raise RuntimeError(f"Failed to fetch {url}: {last}")


def verify_production(expected_data_through: str | None = None) -> None:
    html = fetch(CANONICAL_URL).decode("utf-8", errors="replace")
    if "魔26 候選清單" not in html:
        raise RuntimeError("Production HTML does not contain dashboard title")
    summary = json.loads(fetch(SUMMARY_URL).decode("utf-8"))
    if summary.get("main_spec") != "A_repo50_c4_40_fixed20":
        raise RuntimeError(f"Unexpected main_spec: {summary.get('main_spec')}")
    if expected_data_through and summary.get("data_through") != expected_data_through:
        raise RuntimeError(f"Unexpected data_through: {summary.get('data_through')}")
    if "round14_decision" not in summary:
        raise RuntimeError("Production summary missing round14_decision")
    if "round19_decision" not in summary:
        raise RuntimeError("Production summary missing round19_decision")
    latest = json.loads(fetch(LATEST_URL).decode("utf-8"))
    if latest:
        required = {"research_tags", "research_priority_zh", "momentum_bucket_zh", "source_type", "risk_badge_zh"}
        missing = required - set(latest[0])
        if missing:
            raise RuntimeError(f"Production latest candidates missing fields: {sorted(missing)}")
    all_candidates = json.loads(fetch(ALL_CANDIDATES_URL).decode("utf-8"))
    if not all_candidates:
        raise RuntimeError("Production all_candidates.json is empty")
    if not any(float(row.get("ret_60d_signal") or 0) > 1.5 for row in all_candidates):
        raise RuntimeError("Production all candidates missing ret60 hot rows")
    if not any("大量斷層" in str(row.get("volume_gap_risk_zh")) for row in all_candidates):
        raise RuntimeError("Production all candidates missing volume-gap research rows")
    boot = fetch(ROUND14_BOOTSTRAP_URL).decode("utf-8", errors="replace")
    if "prob_delta_median_excess_gt0" not in boot:
        raise RuntimeError("Production Round14 bootstrap CSV missing expected column")
    volgap = fetch(ROUND19_VOLGAP_URL).decode("utf-8", errors="replace")
    if "top1_to_top10_volume_ratio" not in volgap:
        raise RuntimeError("Production Round19 volume-gap CSV missing expected column")
    print(
        "PRODUCTION OK",
        json.dumps(
            {
                "url": CANONICAL_URL,
                "data_through": summary.get("data_through"),
                "latest_signal_date": summary.get("latest_signal_date"),
                "total_candidate_rows": summary.get("total_candidate_rows"),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


def npx_cmd() -> str:
    path = shutil.which("npx") or shutil.which("npx.cmd")
    if not path:
        raise SystemExit("npx/npx.cmd not found on PATH")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy Magic26 Cloudflare Pages dashboard and verify production.")
    parser.add_argument("--project-name", default="magic26")
    parser.add_argument("--skip-deploy", action="store_true", help="Only run package and production checks")
    parser.add_argument("--data-through", default=None, help="Expected summary.data_through")
    args = parser.parse_args()

    run([sys.executable, "scripts/verify_magic26_package.py"])
    if not args.skip_deploy:
        npx = npx_cmd()
        run([npx, "--yes", "wrangler", "pages", "deploy", "public", "--project-name", args.project_name], timeout=600)
        run([npx, "--yes", "wrangler", "pages", "deployment", "list", "--project-name", args.project_name], timeout=180)
    verify_production(args.data_through)


if __name__ == "__main__":
    main()
