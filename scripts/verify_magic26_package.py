from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

root = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT_SUFFIX = "20210101_20260701"
DEFAULT_DATA_THROUGH = "2026-06-30"
DEFAULT_APP_CACHE_BUST = "20260702riskv2"
DEFAULT_CSS_CACHE_BUST = "20260701q"


def data_file(name: str, snapshot_suffix: str) -> Path:
    return root / "public/data" / name.format(suffix=snapshot_suffix)


parser = argparse.ArgumentParser(description="Verify Magic26 static package.")
parser.add_argument("--snapshot-suffix", default=DEFAULT_SNAPSHOT_SUFFIX)
parser.add_argument("--data-through", default=DEFAULT_DATA_THROUGH)
parser.add_argument("--app-cache-bust", default=DEFAULT_APP_CACHE_BUST)
parser.add_argument("--css-cache-bust", default=DEFAULT_CSS_CACHE_BUST)
args = parser.parse_args()

required = [
    root / "public/index.html",
    root / "public/app.js",
    root / "public/styles.css",
    root / "public/data/summary.json",
    root / "public/data/latest_candidates.json",
    root / "public/data/recent_candidates.json",
    root / "public/data/all_candidates.json",
    root / "public/data/latest_signal_groups.json",
    root / "public/data/recent_signal_groups.json",
    root / "public/data/all_signal_groups.json",
    root / "public/data/watch_states.json",
    root / "public/data/kline/raw_6213.json",
    root / "public/data/kline/adj_6213.json",
    root / "public/data/magic26_candidates_history.csv",
    data_file("magic26_round14_bootstrap_summary_{suffix}.csv", args.snapshot_suffix),
    data_file("magic26_round14_excluded_weak_momentum_path_review_{suffix}.csv", args.snapshot_suffix),
    data_file("magic26_round14_baseline_vs_floor15_yearly_{suffix}.csv", args.snapshot_suffix),
    data_file("magic26_round17_b_retest_rearm_watch_{suffix}.csv", args.snapshot_suffix),
    data_file("magic26_round20_60d_validation_summary_{suffix}.csv", args.snapshot_suffix),
    data_file("magic26_round20_60d_flagged_cases_{suffix}.csv", args.snapshot_suffix),
    data_file("magic26_round21_volgap_rescue_summary_{suffix}.csv", args.snapshot_suffix),
    data_file("magic26_round21_volgap_rescue_cases_{suffix}.csv", args.snapshot_suffix),
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

for json_path in [
    root / "public/data/summary.json",
    root / "public/data/latest_candidates.json",
    root / "public/data/recent_candidates.json",
    root / "public/data/all_candidates.json",
    root / "public/data/latest_signal_groups.json",
    root / "public/data/recent_signal_groups.json",
    root / "public/data/all_signal_groups.json",
    root / "public/data/watch_states.json",
]:
    text = json_path.read_text(encoding="utf-8")
    if "NaN" in text or "Infinity" in text:
        print("invalid non-strict JSON token in", json_path)
        sys.exit(1)
    json.loads(text)


latest_groups = json.loads((root / "public/data/latest_signal_groups.json").read_text(encoding="utf-8"))
all_groups = json.loads((root / "public/data/all_signal_groups.json").read_text(encoding="utf-8"))
if summary.get("latest_signal_groups") != len(latest_groups) or len(latest_groups) != 1:
    print("bad latest signal group count", summary.get("latest_signal_groups"), len(latest_groups))
    sys.exit(1)
if latest_groups[0].get("stock_id") != "6213" or latest_groups[0].get("alias_count") != 4:
    print("latest 6213 group not merged as expected", latest_groups[0].get("stock_id"), latest_groups[0].get("alias_count"))
    sys.exit(1)
risk_v2_fields = {
    "risk_v2_level",
    "risk_v2_label_zh",
    "risk_v2_primary_badge_zh",
    "risk_v2_badges_zh",
    "risk_v2_reasons_zh",
    "risk_v2_action_hint_zh",
    "risk_v2_sort_rank",
    "risk_v2_rule_version",
    "risk_v2_is_display_only",
}
required_group_fields = {"signal_group_id", "signal_date", "data_through", "generated_at", "hit_candidates", "price_modes", "alias_rows", "primary_reason", "risk_reason", "priority_reason"} | risk_v2_fields
missing_group_fields = sorted(required_group_fields - set(latest_groups[0]))
if missing_group_fields:
    print("latest signal group missing fields", missing_group_fields)
    sys.exit(1)
for group in latest_groups + all_groups:
    if not risk_v2_fields.issubset(group):
        print("signal group missing risk_v2 fields", group.get("signal_group_id"))
        sys.exit(1)
    if group.get("risk_v2_level") not in {0, 1, 2, 3}:
        print("bad risk_v2_level", group.get("signal_group_id"), group.get("risk_v2_level"))
        sys.exit(1)
    if group.get("risk_v2_sort_rank") != group.get("risk_v2_level"):
        print("bad risk_v2_sort_rank", group.get("signal_group_id"), group.get("risk_v2_sort_rank"))
        sys.exit(1)
    if group.get("risk_v2_is_display_only") is not True:
        print("risk_v2 must be display-only", group.get("signal_group_id"), group.get("risk_v2_is_display_only"))
        sys.exit(1)
    if not isinstance(group.get("risk_v2_badges_zh"), list) or not isinstance(group.get("risk_v2_reasons_zh"), list):
        print("risk_v2 list fields must stay arrays in signal group JSON", group.get("signal_group_id"))
        sys.exit(1)
latest_6213 = latest_groups[0]
if latest_6213.get("risk_v2_level") != 2 or latest_6213.get("risk_v2_primary_badge_zh") != "只觀察" or latest_6213.get("risk_v2_label_zh") != "高追高 / 只觀察":
    print("latest 6213 risk_v2 classification mismatch", latest_6213.get("risk_v2_level"), latest_6213.get("risk_v2_primary_badge_zh"), latest_6213.get("risk_v2_label_zh"))
    sys.exit(1)
if "不建議直接追價" not in str(latest_6213.get("risk_v2_action_hint_zh")):
    print("latest 6213 risk_v2 no-chase hint missing", latest_6213.get("risk_v2_action_hint_zh"))
    sys.exit(1)
if len({(g.get("stock_id"), g.get("signal_date")) for g in all_groups}) != len(all_groups):
    print("duplicate stock/date groups remain in all_signal_groups")
    sys.exit(1)
if summary.get("all_signal_groups") != len(all_groups):
    print("bad all signal group count", summary.get("all_signal_groups"), len(all_groups))
    sys.exit(1)
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
} | risk_v2_fields
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
round20 = pd.read_csv(data_file("magic26_round20_60d_validation_summary_{suffix}.csv", args.snapshot_suffix))
if not round20["label"].astype(str).str.contains("top1/top10 < 2", regex=False).any():
    print("round20 summary missing top1/top10 validation row")
    sys.exit(1)
if not round20["label"].astype(str).str.contains("ret60 <= 150%", regex=False).any():
    print("round20 summary missing ret60 cap row")
    sys.exit(1)
round21 = pd.read_csv(data_file("magic26_round21_volgap_rescue_summary_{suffix}.csv", args.snapshot_suffix))
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
if "快速分流" not in html or "先看 A 組" not in html or "只看 A 組" not in html:
    print("round25 plain-language spec summary missing from index.html")
    sys.exit(1)
if "Magic26 Research Dashboard" in html or "魔26 候選清單" in html or "拉取式研究看板" in html:
    print("round25 old first-screen header copy still present in index.html")
    sys.exit(1)
if "次要篩選：量能狀態" not in html or "volgapNormal" not in html or "volgapMissing" not in html:
    print("round23 summary panel/filters missing from index.html")
    sys.exit(1)
expected_app_ref = f"app.js?v={args.app_cache_bust}"
expected_css_ref = f"styles.css?v={args.css_cache_bust}"
if "今日主清單" not in html or "次要清單：今年 A 組" not in html or expected_app_ref not in html or expected_css_ref not in html:
    print("round24 grouped A list/cache-bust missing from index.html")
    sys.exit(1)
if "使用說明" not in html or "展開看規則與使用方式" not in html or "A 組怎麼挑" not in html or "大盤背景不能太差" not in html or "怎麼使用" not in html:
    print("round25 batch5 plain-language rule/conclusion copy missing from index.html")
    sys.exit(1)
if "研究資料 / 下載" not in html or "展開下載完整研究檔" not in html or "download-groups" not in html or "候選資料" not in html or "參數研究" not in html or "交易化檢查" not in html or "風險檢查" not in html or "量能落差研究" not in html:
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
if "資料算到" not in app or "最近出訊號" not in app or "今日主清單" not in app or "A 組平均勝出大盤" in app:
    print("round25 first-screen operational KPI copy missing/stale in app.js")
    sys.exit(1)
if "displayPriorityLabel" not in app or "出訊號：" not in app or "為什麼出現" not in app or "要小心" not in app or "cardVersionText" not in app or "今日主清單" not in app or "signal_group_id" not in app:
    print("round25 batch3 candidate-card metric copy missing from app.js")
    sys.exit(1)
if "riskV2Headline" not in app or "risk_v2_primary_badge_zh" not in app or "risk_v2_action_hint_zh" not in app or "追高分級" not in app or "只作研究顯示，不是買賣訊號" not in app:
    print("risk_v2 UI display copy missing from app.js")
    sys.exit(1)
if "原始股價" not in app or "還原股價" not in app or "同股同日已合併" not in app or "流動性不足" not in app:
    print("round25 batch3 candidate-card tag/status copy missing from app.js")
    sys.exit(1)
if "lightweight-charts.standalone.production.js" not in html:
    print("TradingView-style chart library missing from index.html")
    sys.exit(1)

# kline one-year minimum: exported chart data must cover at least 2025-07-01 through package data_through,
# and the UI must not default to shorter 3M/6M views.
kline_path = root / "public/data/kline/raw_6213.json"
if not kline_path.exists():
    print("representative kline file missing: raw_6213.json")
    sys.exit(1)
kline = json.loads(kline_path.read_text(encoding="utf-8"))
krows = kline.get("rows") or []
if not krows or krows[0].get("date") > "2025-07-01" or krows[-1].get("date") < args.data_through:
    print("kline rows do not cover required one-year minimum from 2025-07-01")
    sys.exit(1)
if "range:'1Y'" not in app or "'3M':66" in app or "'6M':132" in app or "data-kline-range=\"3M\"" in app or "data-kline-range=\"6M\"" in app:
    print("kline UI must default to at least 1Y and avoid shorter built-in ranges")
    sys.exit(1)

if "klineMeasureInfo" not in app or "measureText" not in app or "updateMeasure" not in app or "data-kline-action=\"measure\"" not in app:
    print("kline measure tool missing from app.js")
    sys.exit(1)
if "klineCursorInfo" not in app or "cursorInfoText" not in app or "updateCursorInfo" not in app:
    print("kline cursor info bar missing from app.js")
    sys.exit(1)
if "data-kline-type" not in app or "setKlineType" not in app or "addBarSeries" not in app or "addAreaSeries" not in app:
    print("kline chart type controls missing from app.js")
    sys.exit(1)
if "bindGlobalKlineShortcuts" not in app or "magic26:kline-options" not in app or "setKlineRange" not in app or "ondblclick" not in app:
    print("kline shortcuts/persistent options missing from app.js")
    sys.exit(1)
if "toggleKlineFullscreen" not in app or "data-kline-scale" not in app or "klineScaleMode" not in app or "data-kline-action" not in app:
    print("kline scale/reset/fullscreen controls missing from app.js")
    sys.exit(1)
if "klinePriceLabel" not in app or "klineTimeLabel" not in app or "showAxisLabels" not in app or "handleScale" not in app:
    print("kline crosshair axis labels missing from app.js")
    sys.exit(1)
if "klineTooltip" not in app or "tooltipHtml" not in app or "showTooltipAt" not in app or "dataset.date" not in app:
    print("kline hover price tooltip missing from app.js")
    sys.exit(1)
if "kline-toolbar" not in app or "data-kline-range" not in app or "data-kline-mode" not in app or "rowsForRange" not in app:
    print("kline toolbar/range controls missing from app.js")
    sys.exit(1)
if "renderInteractiveKline" not in app or "MA5" not in app or "setMarkers" not in app:
    print("interactive kline MA/candidate marker logic missing from app.js")
    sys.exit(1)
if "klinePanelHtml" not in app or "K 線圖" not in app or "renderKline" not in app:
    print("kline detail chart missing from app.js")
    sys.exit(1)
if "detailSectionHtml" not in app or "訊號摘要" not in app or "基本資料" not in app or "價格與表現" not in app or "量能集中度" not in app or "風險檢查" not in app or "研究狀態" not in app:
    print("round25 batch4 detail sections missing from app.js")
    sys.exit(1)
if "短均線強度1" not in app or "20天後勝大盤" not in app or "前5大量占比" not in app or "白話分類" not in app:
    print("round25 batch4 detail plain-language labels missing from app.js")
    sys.exit(1)
if "白話分類" not in app or "volgap_score_impact" not in app:
    print("round22 detail/score logic missing from app.js")
    sys.exit(1)
if "renderVolgapSummary" not in app or "compact-subtype" not in app or "compact-spec" not in app:
    print("round23 summary rendering missing from app.js")
    sys.exit(1)
if "main-a-group" not in app or "applyCandidateFilter({range:'recent', candidate:'A_repo50_c4_40_fixed20'" not in app or "hasCandidate(r, 'A_repo50_c4_40_fixed20')" not in app:
    print("round24 main-A grouped rendering missing from app.js")
    sys.exit(1)
css = (root / "public/styles.css").read_text(encoding="utf-8")
if "subtype-summary" not in css or "subtype-card" not in css:
    print("round23 summary styles missing from styles.css")
    sys.exit(1)
if "main-a-groups" not in css or "main-a-head" not in css or "secondary-panel" not in css or "compact-spec" not in css or "compact-subtype" not in css or "compact-kpi" not in css:
    print("round24 main-A group styles missing from styles.css")
    sys.exit(1)
if "detail-sections" not in css or "detail-section" not in css or "signal-reason" not in css or "signal-reason.version" not in css or "alias-list" not in css:
    print("round25 batch4 detail section styles missing from styles.css")
    sys.exit(1)
if "kline-measure-info" not in css or "kline-cursor-info" not in css or "kline-action" not in css or "fullscreen" not in css or "kline-axis-label" not in css or "kline-tooltip" not in css or "kline-chart-wrap" not in css or "kline-toolbar" not in css or "kline-legend" not in css or "kline-panel" not in css or "kline-chart" not in css:
    print("kline styles missing from styles.css")
    sys.exit(1)
raw_kline = json.loads((root / "public/data/kline/raw_6213.json").read_text(encoding="utf-8"))
if raw_kline.get("data_through") != summary.get("data_through") or len(raw_kline.get("rows", [])) < 260:
    print("bad kline payload", raw_kline.get("data_through"), len(raw_kline.get("rows", [])))
    sys.exit(1)
if "download-groups" not in css or "freshness" not in css or "guide-panel" not in css:
    print("round25 batch5 download group styles missing from styles.css")
    sys.exit(1)

for p in root.rglob("*"):
    if p.is_file() and p.suffix.lower() in {".env", ".pem", ".key", ".parquet"}:
        print("forbidden packaged file:", p)
        sys.exit(1)

print("ok magic26 package", summary.get("data_through"), "latest", summary.get("latest_signal_date"))
