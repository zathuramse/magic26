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
PRODUCTION_BASE = "https://magic26.pages.dev"
DEFAULT_SNAPSHOT_SUFFIX = "20210101_20260701"
DEFAULT_APP_CACHE_BUST = "20260702riskv2"
DEFAULT_CSS_CACHE_BUST = "20260701q"


def with_cache(path: str, cache_bust: str) -> str:
    return f"{path}?v={cache_bust}" if cache_bust else path


def data_url(name: str, snapshot_suffix: str) -> str:
    return f"{PRODUCTION_BASE}/data/{name.format(suffix=snapshot_suffix)}"


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


def verify_production(expected_data_through: str | None = None, *, snapshot_suffix: str = DEFAULT_SNAPSHOT_SUFFIX, app_cache_bust: str = DEFAULT_APP_CACHE_BUST, css_cache_bust: str = DEFAULT_CSS_CACHE_BUST) -> None:
    canonical_url = f"{PRODUCTION_BASE}/?v={app_cache_bust}"
    summary_url = f"{PRODUCTION_BASE}/data/summary.json"
    latest_url = with_cache(f"{PRODUCTION_BASE}/data/latest_candidates.json", app_cache_bust)
    latest_groups_url = with_cache(f"{PRODUCTION_BASE}/data/latest_signal_groups.json", app_cache_bust)
    all_groups_url = with_cache(f"{PRODUCTION_BASE}/data/all_signal_groups.json", app_cache_bust)
    all_candidates_url = f"{PRODUCTION_BASE}/data/all_candidates.json"
    html = fetch(canonical_url).decode("utf-8", errors="replace")
    if "Magic26 研究看板" not in html or "Magic26 候選標的" not in html:
        raise RuntimeError("Production HTML does not contain Round25 plain-language header")
    if "Magic26 Research Dashboard" in html or "魔26 候選清單" in html or "拉取式研究看板" in html:
        raise RuntimeError("Production HTML still contains old Round25 first-screen copy")
    if "次要篩選：量能狀態" not in html or "volgapNormal" not in html or "volgapMissing" not in html:
        raise RuntimeError("Production HTML missing Round25 volume-gap plain-language UI")
    expected_app_ref = f"app.js?v={app_cache_bust}"
    expected_css_ref = f"styles.css?v={css_cache_bust}"
    if "lightweight-charts.standalone.production.js" not in html or expected_app_ref not in html or expected_css_ref not in html:
        raise RuntimeError("Production HTML missing TradingView-style chart loader")
    if "K 線圖" not in html and expected_app_ref not in html:
        raise RuntimeError("Production HTML/cache missing kline-capable app")
    if "今日主清單" not in html or "次要清單：今年 A 組" not in html:
        raise RuntimeError("Production HTML missing Round25 grouped main-A list copy")
    if expected_app_ref not in html or expected_css_ref not in html:
        raise RuntimeError("Production HTML missing Round25 cache-bust")
    summary = json.loads(fetch(summary_url).decode("utf-8"))
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
    latest = json.loads(fetch(latest_url).decode("utf-8"))
    if latest:
        required = {"research_tags", "research_priority_zh", "momentum_bucket_zh", "source_type", "risk_badge_zh", "volgap_subtype_zh", "volgap_score_impact"}
        missing = required - set(latest[0])
        if missing:
            raise RuntimeError(f"Production latest candidates missing fields: {sorted(missing)}")
    latest_groups = json.loads(fetch(latest_groups_url).decode("utf-8"))
    if len(latest_groups) != 1 or latest_groups[0].get("stock_id") != "6213" or latest_groups[0].get("alias_count") != 4:
        raise RuntimeError(f"Production latest signal groups not merged as expected: {latest_groups[:1]}")
    required_group = {"signal_group_id", "signal_date", "data_through", "generated_at", "hit_candidates", "price_modes", "alias_rows", "primary_reason", "risk_reason", "risk_v2_level", "risk_v2_label_zh", "risk_v2_primary_badge_zh", "risk_v2_action_hint_zh", "risk_v2_is_display_only"}
    missing_group = required_group - set(latest_groups[0])
    if missing_group:
        raise RuntimeError(f"Production latest signal group missing fields: {sorted(missing_group)}")
    if latest_groups[0].get("risk_v2_level") != 2 or latest_groups[0].get("risk_v2_primary_badge_zh") != "只觀察" or latest_groups[0].get("risk_v2_label_zh") != "高追高 / 只觀察":
        raise RuntimeError(f"Production latest signal group risk_v2 mismatch: {latest_groups[0]}")
    if "不建議直接追價" not in str(latest_groups[0].get("risk_v2_action_hint_zh")) or latest_groups[0].get("risk_v2_is_display_only") is not True:
        raise RuntimeError(f"Production latest signal group risk_v2 hint/display_only mismatch: {latest_groups[0]}")
    all_groups = json.loads(fetch(all_groups_url).decode("utf-8"))
    if len({(g.get("stock_id"), g.get("signal_date")) for g in all_groups}) != len(all_groups):
        raise RuntimeError("Production all_signal_groups still has duplicate stock/date groups")
    all_candidates = json.loads(fetch(all_candidates_url).decode("utf-8"))
    if not all_candidates:
        raise RuntimeError("Production all_candidates empty")
    subtypes = {str(r.get("volgap_subtype_zh")) for r in all_candidates}
    if not {"正常", "可救斷層", "危險斷層"}.issubset(subtypes):
        raise RuntimeError(f"Production all_candidates missing Round22 subtypes: {sorted(subtypes)}")
    if not any(str(r.get("volgap_score_impact")) == "-10" for r in all_candidates):
        raise RuntimeError("Production all_candidates missing Round22 danger score impact")
    if max(float(row.get("ret_60d_signal") or 0) for row in all_candidates) < 1.0:
        raise RuntimeError("Production all candidates missing high-ret60 context rows")
    if not any("大量斷層" in str(row.get("volume_gap_risk_zh")) for row in all_candidates):
        raise RuntimeError("Production all candidates missing volume-gap research rows")
    boot = fetch(data_url("magic26_round14_bootstrap_summary_{suffix}.csv", snapshot_suffix)).decode("utf-8", errors="replace")
    if "prob_delta_median_excess_gt0" not in boot:
        raise RuntimeError("Production Round14 bootstrap CSV missing expected column")
    volgap = fetch(data_url("magic26_round19_volume_gap_summary_{suffix}.csv", snapshot_suffix)).decode("utf-8", errors="replace")
    if "volume_gap_top10" not in volgap:
        raise RuntimeError("Production Round19 volume-gap CSV missing expected group")
    round20 = fetch(data_url("magic26_round20_60d_validation_summary_{suffix}.csv", snapshot_suffix)).decode("utf-8", errors="replace")
    if "top1/top10 < 2" not in round20 or "ret60 <= 150%" not in round20:
        raise RuntimeError("Production Round20 summary missing expected validation rows")
    round21 = fetch(data_url("magic26_round21_volgap_rescue_summary_{suffix}.csv", snapshot_suffix)).decode("utf-8", errors="replace")
    if "rescue candidate" not in round21 or "danger candidate" not in round21:
        raise RuntimeError("Production Round21 summary missing expected rescue/danger rows")
    print(
        "PRODUCTION OK",
        json.dumps(
            {
                "url": canonical_url,
                "data_through": summary.get("data_through"),
                "latest_signal_date": summary.get("latest_signal_date"),
                "total_candidate_rows": summary.get("total_candidate_rows"),
                "latest_signal_groups": summary.get("latest_signal_groups"),
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
    parser.add_argument("--snapshot-suffix", default=DEFAULT_SNAPSHOT_SUFFIX)
    parser.add_argument("--app-cache-bust", default=DEFAULT_APP_CACHE_BUST)
    parser.add_argument("--css-cache-bust", default=DEFAULT_CSS_CACHE_BUST)
    args = parser.parse_args()

    verify_cmd = [
        sys.executable,
        "scripts/verify_magic26_package.py",
        "--snapshot-suffix",
        args.snapshot_suffix,
        "--app-cache-bust",
        args.app_cache_bust,
        "--css-cache-bust",
        args.css_cache_bust,
    ]
    if args.data_through:
        verify_cmd.extend(["--data-through", args.data_through])
    run(verify_cmd)
    if not args.skip_deploy:
        npx = npx_cmd()
        run([npx, "--yes", "wrangler", "pages", "deploy", "public", "--project-name", args.project_name], timeout=600)
        run([npx, "--yes", "wrangler", "pages", "deployment", "list", "--project-name", args.project_name], timeout=180)
    verify_production(args.data_through, snapshot_suffix=args.snapshot_suffix, app_cache_bust=args.app_cache_bust, css_cache_bust=args.css_cache_bust)


if __name__ == "__main__":
    main()
