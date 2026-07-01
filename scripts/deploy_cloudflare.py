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
ROUND20_SUMMARY_URL = "https://magic26.pages.dev/data/magic26_round20_60d_validation_summary_20210101_20260622.csv"
ROUND21_SUMMARY_URL = "https://magic26.pages.dev/data/magic26_round21_volgap_rescue_summary_20210101_20260622.csv"


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
    if "Magic26 研究看板" not in html or "Magic26 候選標的" not in html:
        raise RuntimeError("Production HTML does not contain Round25 plain-language header")
    if "Magic26 Research Dashboard" in html or "魔26 候選清單" in html or "拉取式研究看板" in html:
        raise RuntimeError("Production HTML still contains old Round25 first-screen copy")
    if "量能落差分類" not in html or "volgapNormal" not in html or "volgapMissing" not in html:
        raise RuntimeError("Production HTML missing Round25 volume-gap plain-language UI")
    if "A 組量能落差優先清單" not in html:
        raise RuntimeError("Production HTML missing Round25 grouped main-A list copy")
    if "app.js?v=20260701f" not in html or "styles.css?v=20260701a" not in html:
        raise RuntimeError("Production HTML missing Round25 cache-bust")
    summary = json.loads(fetch(SUMMARY_URL).decode("utf-8"))
    if summary.get("main_spec") != "A_repo50_c4_40_fixed20":
        raise RuntimeError(f"Unexpected main_spec: {summary.get('main_spec')}")
    if expected_data_through and summary.get("data_through") != expected_data_through:
        raise RuntimeError(f"Unexpected data_through: {summary.get('data_through')}")
    if "round14_decision" not in summary:
        raise RuntimeError("Production summary missing round14_decision")
    if "round19_decision" not in summary:
        raise RuntimeError("Production summary missing round19_decision")
    if "round20_decision" not in summary:
        raise RuntimeError("Production summary missing round20_decision")
    if "round21_decision" not in summary:
        raise RuntimeError("Production summary missing round21_decision")
    if "round22_decision" not in summary:
        raise RuntimeError("Production summary missing round22_decision")
    if "round23_decision" not in summary:
        raise RuntimeError("Production summary missing round23_decision")
    if "round24_decision" not in summary:
        raise RuntimeError("Production summary missing round24_decision")
    latest = json.loads(fetch(LATEST_URL).decode("utf-8"))
    if latest:
        required = {"research_tags", "research_priority_zh", "momentum_bucket_zh", "source_type", "risk_badge_zh", "volgap_subtype_zh", "volgap_score_impact"}
        missing = required - set(latest[0])
        if missing:
            raise RuntimeError(f"Production latest candidates missing fields: {sorted(missing)}")
    all_candidates = json.loads(fetch(ALL_CANDIDATES_URL).decode("utf-8"))
    if not all_candidates:
        raise RuntimeError("Production all_candidates empty")
    subtypes = {str(r.get("volgap_subtype_zh")) for r in all_candidates}
    if not {"正常", "可救斷層", "危險斷層"}.issubset(subtypes):
        raise RuntimeError(f"Production all_candidates missing Round22 subtypes: {sorted(subtypes)}")
    if not any(str(r.get("volgap_score_impact")) == "-10" for r in all_candidates):
        raise RuntimeError("Production all_candidates missing Round22 danger score impact")
    if not any(float(row.get("ret_60d_signal") or 0) > 1.5 for row in all_candidates):
        raise RuntimeError("Production all candidates missing ret60 hot rows")
    if not any("大量斷層" in str(row.get("volume_gap_risk_zh")) for row in all_candidates):
        raise RuntimeError("Production all candidates missing volume-gap research rows")
    boot = fetch(ROUND14_BOOTSTRAP_URL).decode("utf-8", errors="replace")
    if "prob_delta_median_excess_gt0" not in boot:
        raise RuntimeError("Production Round14 bootstrap CSV missing expected column")
    volgap = fetch(ROUND19_VOLGAP_URL).decode("utf-8", errors="replace")
    if "volume_gap_top10" not in volgap:
        raise RuntimeError("Production Round19 volume-gap CSV missing expected group")
    round20 = fetch(ROUND20_SUMMARY_URL).decode("utf-8", errors="replace")
    if "top1/top10 < 2" not in round20 or "ret60 <= 150%" not in round20:
        raise RuntimeError("Production Round20 summary missing expected validation rows")
    round21 = fetch(ROUND21_SUMMARY_URL).decode("utf-8", errors="replace")
    if "rescue candidate" not in round21 or "danger candidate" not in round21:
        raise RuntimeError("Production Round21 summary missing expected rescue/danger rows")
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
