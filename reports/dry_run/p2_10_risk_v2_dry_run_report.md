# Magic26 P2-10 risk_v2 export dry-run

狀態：dry-run；未覆蓋 public/data，未改 export，未改 UI，未部署。

## 輸出檔

- `reports/dry_run/p2_10_all_signal_groups_risk_v2_dry_run.csv`
- `reports/dry_run/p2_10_all_signal_groups_risk_v2_dry_run.json`
- `reports/dry_run/p2_10_latest_signal_groups_risk_v2_dry_run.csv`
- `reports/dry_run/p2_10_latest_signal_groups_risk_v2_dry_run.json`
- `reports/dry_run/p2_10_risk_v2_dry_run_report.json`

## Row count / Level 分布

- `all_signal_groups.json`: input=75, output=75, levels={'0': 15, '1': 15, '2': 23, '3': 22}, all_fields=True
- `latest_signal_groups.json`: input=1, output=1, levels={'0': 0, '1': 0, '2': 1, '3': 0}, all_fields=True

## 驗證

- PASS: `latest_row_count_unchanged`
- PASS: `all_row_count_unchanged`
- PASS: `latest_has_all_fields`
- PASS: `all_has_all_fields`
- PASS: `risk_v2_level_allowed`
- PASS: `risk_v2_sort_rank_integer`
- PASS: `risk_v2_is_display_only_true`
- PASS: `latest_6213_exists`
- PASS: `latest_6213_level_2`
- PASS: `latest_6213_primary_badge`
- PASS: `latest_6213_label`
- PASS: `latest_6213_hint_no_chase`

## 6213 dry-run 結果

- risk_v2_level: 2
- risk_v2_label_zh: 高追高 / 只觀察
- risk_v2_primary_badge_zh: 只觀察
- risk_v2_badges_zh: 只觀察;高追高;開高風險;漲幅已大
- risk_v2_reasons_zh: 隔日開盤高 3.8%，超過 3% 高追高門檻;同時觸發兩個以上追高警戒條件;隔日開盤高 3.8%，超過 1% 追高警戒門檻;近 20 天已漲 25.3%，超過 25% 追高警戒門檻
- risk_v2_action_hint_zh: 只觀察；已偏追高，不建議直接追價

## 結論

dry-run 通過；schema 可套用於現有 signal group JSON，row count 不變。下一步才考慮正式改 export。
