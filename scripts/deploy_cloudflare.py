from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
CANONICAL_URL = "https://magic26.pages.dev/"
SUMMARY_URL = "https://magic26.pages.dev/data/summary.json"


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy Magic26 Cloudflare Pages dashboard and verify production.")
    parser.add_argument("--project-name", default="magic26")
    parser.add_argument("--skip-deploy", action="store_true", help="Only run package and production checks")
    parser.add_argument("--data-through", default=None, help="Expected summary.data_through")
    args = parser.parse_args()

    run([sys.executable, "scripts/verify_magic26_package.py"])
    if not args.skip_deploy:
        run(["npx", "--yes", "wrangler", "pages", "deploy", "public", "--project-name", args.project_name], timeout=600)
        run(["npx", "--yes", "wrangler", "pages", "deployment", "list", "--project-name", args.project_name], timeout=180)
    verify_production(args.data_through)


if __name__ == "__main__":
    main()
