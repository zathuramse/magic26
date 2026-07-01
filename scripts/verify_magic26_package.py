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
    root / "public/data/kline/raw_6213.json",
    root / "public/data/kline/adj_6213.json",
    root / "public/data/magic26_candidates_history.csv",
    root / "public/data/magic26_round14_bootstrap_summary_20210101_20260701.csv",
    root / "public/data/magic26_round14_excluded_weak_momentum_path_review_20210101_20260701.csv",
    root / "public/data/magic26_round14_baseline_vs_floor15_yearly_20210101_20260701.csv",
    root / "public/data/magic26_round17_b_retest_rearm_watch_20210101_20260701.csv",
    root / "public/data/magic26_round20_60d_validation_summary_20210101_20260701.csv",
    root / "public/data/magic26_round20_60d_flagged_cases_20210101_20260701.csv",
    root / "public/data/magic26_round21_volgap_rescue_summary_20210101_20260701.csv",
    root / "public/data/magic26_round21_volgap_rescue_cases_20210101_20260701.csv",
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
if "round23_decision" not in summary:
    print("missing round23_decision in summary.json")
    sys.exit(1)
if "round24_decision" not in summary:
    print("missing round24_decision in summary.json")
    sys.exit(1)
round20 = pd.read_csv(root / "public/data/magic26_round20_60d_validation_summary_20210101_20260701.csv")
if not round20["label"].astype(str).str.contains("top1/top10 < 2", regex=False).any():
    print("round20 summary missing top1/top10 validation row")
    sys.exit(1)
if not round20["label"].astype(str).str.contains("ret60 <= 150%", regex=False).any():
    print("round20 summary missing ret60 cap row")
    sys.exit(1)
round21 = pd.read_csv(root / "public/data/magic26_round21_volgap_rescue_summary_20210101_20260701.csv")
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
if "volgapRescue" not in html or "volgapDanger" not in html:
    print("round22 UI filters/text missing from index.html")
    sys.exit(1)
if "Magic26 研究看板" not in html or "Magic26 候選標的" not in html or "不是買賣訊號，也不會自動更新" not in html:
    print("round25 first-screen plain-language header missing from index.html")
    sys.exit(1)
if "先看哪一組" not in html or "A 組是目前最主要的清單" not in html or "只看 A 組" not in html:
    print("round25 plain-language spec summary missing from index.html")
    sys.exit(1)
if "Magic26 Research Dashboard" in html or "魔26 候選清單" in html or "拉取式研究看板" in html:
    print("round25 old first-screen header copy still present in index.html")
    sys.exit(1)
if "成交量有沒有怪怪的" not in html or "volgapNormal" not in html or "volgapMissing" not in html:
    print("round23 summary panel/filters missing from index.html")
    sys.exit(1)
if "A 組先看清單" not in html or "app.js?v=20260701k" not in html or "styles.css?v=20260701g" not in html:
    print("round24 grouped A list/cache-bust missing from index.html")
    sys.exit(1)
if "A 組怎麼挑" not in html or "大盤背景不能太差" not in html or "怎麼使用" not in html:
    print("round25 batch5 plain-language rule/conclusion copy missing from index.html")
    sys.exit(1)
if "資料下載" not in html or "download-groups" not in html or "候選資料" not in html or "參數研究" not in html or "交易化檢查" not in html or "風險檢查" not in html or "量能落差研究" not in html:
    print("round25 batch5 grouped download UI missing from index.html")
    sys.exit(1)
if "漲勢偏弱" not in html or "漲幅有過15%" not in html or "成交量越穩越前面" not in html or "不是 A 組" not in html:
    print("round25 batch6 plain-language control labels missing from index.html")
    sys.exit(1)
if "regime_all3=True" in html or "repo_vol5" in html or "t+1 open" in html or "第七輪參數網格 Top" in html or "Round 20｜flagged cases" in html or "Watch State CSV" in html or "repo量比高" in html:
    print("round25 batch5 old bottom technical copy still present in index.html")
    sys.exit(1)
if "主規格 A 斷層分組優先清單" in html or "斷層正常" in html:
    print("round25 batch2 old volume-gap section/filter copy still present in index.html")
    sys.exit(1)
if "subtypeLabels" not in app or "有落差但可看" not in app or "量太集中，先避開" not in app or "A 組｜" not in app:
    print("round25 batch2 plain-language volume-gap app copy missing from app.js")
    sys.exit(1)
if "A 組：先看這組" not in app or "最近有候選" not in app or "A 組平均勝出大盤" not in app:
    print("round25 first-screen app copy missing from app.js")
    sys.exit(1)
if "displayPriorityLabel" not in app or "近20天漲幅" not in app or "漲幅區間" not in app or "近20天日均成交" not in app:
    print("round25 batch3 candidate-card metric copy missing from app.js")
    sys.exit(1)
if "原始股價" not in app or "還原股價" not in app or "還要人工看圖" not in app or "流動性不足" not in app:
    print("round25 batch3 candidate-card tag/status copy missing from app.js")
    sys.exit(1)
if "lightweight-charts.standalone.production.js" not in html:
    print("TradingView-style chart library missing from index.html")
    sys.exit(1)
if "renderInteractiveKline" not in app or "MA5" not in app or "setMarkers" not in app:
    print("interactive kline MA/candidate marker logic missing from app.js")
    sys.exit(1)
if "klinePanelHtml" not in app or "K 線圖" not in app or "renderKline" not in app:
    print("kline detail chart missing from app.js")
    sys.exit(1)
if "detailSectionHtml" not in app or "基本資料" not in app or "價格與表現" not in app or "量能集中度" not in app or "風險檢查" not in app or "研究狀態" not in app:
    print("round25 batch4 detail sections missing from app.js")
    sys.exit(1)
if "短均線強度1" not in app or "20天後勝大盤" not in app or "前5大量占比" not in app or "白話分類" not in app:
    print("round25 batch4 detail plain-language labels missing from app.js")
    sys.exit(1)
if "白話分類" not in app or "volgap_score_impact" not in app:
    print("round22 detail/score logic missing from app.js")
    sys.exit(1)
if "renderVolgapSummary" not in app or "subtype-card" not in app:
    print("round23 summary rendering missing from app.js")
    sys.exit(1)
if "main-a-group" not in app or "applyCandidateFilter({range:'recent', candidate:'A_repo50_c4_40_fixed20'" not in app:
    print("round24 main-A grouped rendering missing from app.js")
    sys.exit(1)
css = (root / "public/styles.css").read_text(encoding="utf-8")
if "subtype-summary" not in css or "subtype-card" not in css:
    print("round23 summary styles missing from styles.css")
    sys.exit(1)
if "main-a-groups" not in css or "main-a-head" not in css:
    print("round24 main-A group styles missing from styles.css")
    sys.exit(1)
if "detail-sections" not in css or "detail-section" not in css:
    print("round25 batch4 detail section styles missing from styles.css")
    sys.exit(1)
if "kline-legend" not in css or "kline-panel" not in css or "kline-chart" not in css:
    print("kline styles missing from styles.css")
    sys.exit(1)
raw_kline = json.loads((root / "public/data/kline/raw_6213.json").read_text(encoding="utf-8"))
if raw_kline.get("data_through") != summary.get("data_through") or len(raw_kline.get("rows", [])) < 30:
    print("bad kline payload", raw_kline.get("data_through"), len(raw_kline.get("rows", [])))
    sys.exit(1)
if "download-groups" not in css or "freshness" not in css:
    print("round25 batch5 download group styles missing from styles.css")
    sys.exit(1)

for p in root.rglob("*"):
    if p.is_file() and p.suffix.lower() in {".env", ".pem", ".key", ".parquet"}:
        print("forbidden packaged file:", p)
        sys.exit(1)

print("ok magic26 package", summary.get("data_through"), "latest", summary.get("latest_signal_date"))
