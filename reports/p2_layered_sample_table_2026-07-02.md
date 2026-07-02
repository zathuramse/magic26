# Magic26 P2-3 分層樣本總表

日期：2026-07-02

## 目的

把現有 Magic26 驗證輸出整理成同一個分層 schema，供後續 holdout / walk-forward 使用。這份表不改策略、不混算 raw/adj、不部署。

## 產物

- `reports/p2_layered_sample_table_2026-07-02.csv`
- `reports/p2_layered_sample_table_2026-07-02.md`

## 分層摘要

- `core_family` / `all_period`: rows=6, signals_sum=547, n20_sum=477, n60_sum=349
- `core_family` / `yearly`: rows=36, signals_sum=547, n20_sum=477, n60_sum=349
- `regime_family` / `all_period`: rows=8, signals_sum=1605, n20_sum=1525, n60_sum=1286
- `strict_candidate` / `all_period_candidate_summary`: rows=6, signals_sum=299, n20_sum=299, n60_sum=0

## 解讀原則

1. `strict_candidate` 是目前 dashboard 候選家族，只能作主清單，不可與 broader family 混算。
2. `core_family` 是同源較廣家族，可作中立擴樣本驗證層。
3. `regime_family` 是更廣 regime 驗證層，可檢查方向一致性，但不能直接當主策略績效。
4. raw/adj 保持分開；後續若要合併，必須先做 group-dedup。
5. 年度列與 ALL 列用途不同，不能直接加總作結論。

## 下一步

建議用這份表做 P2-4 holdout 設計：2023-2025 作規則/觀察窗，2026 作 holdout；另外保留 raw-only、adj-only、group-dedup 三種口徑。
