from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

root = Path(__file__).resolve().parents[1]
required = [
    root / "public/index.html",
    root / "public/app.js",
    root / "public/styles.css",
    root / "public/data/summary.json",
    root / "public/data/latest_candidates.json",
    root / "public/data/recent_candidates.json",
    root / "public/data/all_candidates.json",
    root / "public/data/watch_states.json",
    root / "public/data/magic26_candidates_history.csv",
    root / "public/data/magic26_round14_bootstrap_summary_20210101_20260622.csv",
    root / "public/data/magic26_round14_excluded_weak_momentum_path_review_20210101_20260622.csv",
    root / "public/data/magic26_round14_baseline_vs_floor15_yearly_20210101_20260622.csv",
    root / "public/data/magic26_round17_b_retest_rearm_watch_20210101_20260622.csv",
    root / "public/data/magic26_round20_60d_validation_summary_20210101_20260622.csv",
    root / "public/data/magic26_round20_60d_flagged_cases_20210101_20260622.csv",
    root / "public/data/magic26_round21_volgap_rescue_summary_20210101_20260622.csv",
    root / "public/data/magic26_round21_volgap_rescue_cases_20210101_20260622.csv",
    root / "scripts/export_dashboard_data.py",
    root / "scripts/deploy_cloudflare.py",
]
missing = [str(p) for p in required if not p.exists()]

if missing:
    print("missing required files:")
    print("\n".join(missing))
    sys.exit(1)

summary = json.loads((root / "public/data/summary.json").read_text(encoding="utf-8"))
if summary.get("main_spec") != "A_repo50_c4_40_fixed20":
    print("bad main_spec", summary.get("main_spec"))
    sys.exit(1)

for json_path in [root / "public/data/summary.json", root / "public/data/latest_candidates.json", root / "public/data/recent_candidates.json", root / "public/data/all_candidates.json", root / "public/data/watch_states.json"]:
    text = json_path.read_text(encoding="utf-8")
    if "NaN" in text or "Infinity" in text:
        print("invalid non-strict JSON token in", json_path)
        sys.exit(1)
    json.loads(text)

if "round14_decision" not in summary:
    print("missing round14_decision in summary.json")
    sys.exit(1)
if summary.get("watch_state", {}).get("rows") != 4:
    print("bad watch_state summary", summary.get("watch_state"))
    sys.exit(1)
watch_states = json.loads((root / "public/data/watch_states.json").read_text(encoding="utf-8"))
if len(watch_states) != 4:
    print("bad watch_states rows", len(watch_states))
    sys.exit(1)
if not {"等待降溫", "中性等待"}.issubset({str(r.get("rearm_state")) for r in watch_states}):
    print("missing expected watch states")
    sys.exit(1)

candidates = pd.read_csv(root / "public/data/magic26_candidates_history.csv")
required_columns = {
    "is_weak_momentum",
    "is_floor15_observation",
    "momentum_bucket_zh",
    "strategy_role_zh",
    "research_priority_zh",
    "research_tags",
    "source_type",
    "ret_60d_signal",
    "ret60_cap150_pass",
    "top1_to_top10_volume_ratio",
    "volume_gap_risk_zh",
    "volgap_subtype_zh",
    "volgap_score_impact",
    "risk_any_long_ma_bear",
    "risk_long_ma_score",
    "risk_badge_zh",
}
missing_columns = sorted(required_columns - set(candidates.columns))
if missing_columns:
    print("missing candidate label columns:", missing_columns)
    sys.exit(1)
if candidates["research_tags"].astype(str).str.contains("弱動能").sum() == 0:
    print("no weak-momentum tagged rows found")
    sys.exit(1)
if candidates["research_tags"].astype(str).str.contains("floor15觀察").sum() == 0:
    print("no floor15 observation tagged rows found")
    sys.exit(1)
if "round19_decision" not in summary:
    print("missing round19_decision in summary.json")
    sys.exit(1)
if "round20_decision" not in summary:
    print("missing round20_decision in summary.json")
    sys.exit(1)
if "round21_decision" not in summary:
    print("missing round21_decision in summary.json")
    sys.exit(1)
if "round22_decision" not in summary:
    print("missing round22_decision in summary.json")
    sys.exit(1)
round20 = pd.read_csv(root / "public/data/magic26_round20_60d_validation_summary_20210101_20260622.csv")
if not round20["label"].astype(str).str.contains("top1/top10 < 2", regex=False).any():
    print("round20 summary missing top1/top10 validation row")
    sys.exit(1)
if not round20["label"].astype(str).str.contains("ret60 <= 150%", regex=False).any():
    print("round20 summary missing ret60 cap row")
    sys.exit(1)
round21 = pd.read_csv(root / "public/data/magic26_round21_volgap_rescue_summary_20210101_20260622.csv")
if not round21["label"].astype(str).str.contains("rescue candidate", regex=False).any():
    print("round21 summary missing rescue candidate row")
    sys.exit(1)
if not round21["label"].astype(str).str.contains("danger candidate", regex=False).any():
    print("round21 summary missing danger candidate row")
    sys.exit(1)
if set(candidates["source_type"].dropna().unique()) != {"reconstructed"}:
    print("unexpected source_type values", sorted(candidates["source_type"].dropna().unique()))
    sys.exit(1)
if candidates["risk_badge_zh"].astype(str).str.contains("研究中").sum() == 0:
    print("no round19 research badges found")
    sys.exit(1)
if candidates["volume_gap_risk_zh"].astype(str).str.contains("大量斷層").sum() == 0:
    print("no volume-gap watch rows found")
    sys.exit(1)
if not {"正常", "可救斷層", "危險斷層"}.issubset(set(candidates["volgap_subtype_zh"].astype(str))):
    print("missing expected volgap subtypes", sorted(set(candidates["volgap_subtype_zh"].astype(str))))
    sys.exit(1)
impact = pd.to_numeric(candidates["volgap_score_impact"], errors="coerce")
if impact.min() > -10 or impact.max() != 0:
    print("unexpected volgap score impact range", impact.min(), impact.max())
    sys.exit(1)
html = (root / "public/index.html").read_text(encoding="utf-8")
app = (root / "public/app.js").read_text(encoding="utf-8")
if "Round 22 已產品化" not in html or "volgapRescue" not in html or "volgapDanger" not in html:
    print("round22 UI filters/text missing from index.html")
    sys.exit(1)
if "斷層分類" not in app or "volgap_score_impact" not in app:
    print("round22 detail/score logic missing from app.js")
    sys.exit(1)

for p in root.rglob("*"):
    if p.is_file() and p.suffix.lower() in {".env", ".pem", ".key", ".parquet"}:
        print("forbidden packaged file:", p)
        sys.exit(1)

print("ok magic26 package", summary.get("data_through"), "latest", summary.get("latest_signal_date"))
