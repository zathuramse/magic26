# 魔26 v0 第一輪執行紀錄

日期：2026-06-22  
狀態：已完成規格化與小樣本 smoke test；尚未做全市場結論。

## 已完成

1. 建立可回測規格：`magic26_research_spec_2026-06-22.md`
2. 建立研究腳本：`tools/magic26_signal_pilot.py`
3. 修正 FinMind 單股查詢參數：必須用 `data_id`，不是 `stock_id`。
4. 加入普通股 universe 過濾：排除 ETF / ETN / 受益證券 / 權證等。
5. 完成兩組 smoke test：
   - 10 檔科技/權值樣本
   - 53 檔手動流動性較高樣本

## 53檔流動性樣本初步結果

樣本：2021-01-01 到 2026-06-22，53 檔手動挑選的台股權值/科技/金融/航運樣本。  
注意：這不是全市場，也不是隨機樣本，不能拿來宣稱策略有效。

### 條件累加結果

- C1 only：90 筆訊號
  - 20D 平均：+4.21%
  - 60D 平均：+10.45%
  - 60D 勝率：52.44%
  - 60D > 50%：8.54%

- C1 + C2：28 筆訊號
  - 20D 平均：+4.53%
  - 60D 平均：+15.79%
  - 60D 勝率：65.38%
  - 60D > 50%：11.54%

- C1 + C2 + C3：9 筆訊號
  - 20D 平均：+20.26%
  - 60D 平均：+27.03%
  - 60D 勝率：71.43%
  - 60D > 50%：28.57%

- C1 + C2 + C3 + C4：8 筆訊號
  - 20D 平均：+23.63%
  - 60D 平均：+29.88%
  - 60D 勝率：66.67%
  - 60D > 50%：33.33%

- Magic26 v0 全條件：5 筆訊號
  - 5D 平均：+11.58%
  - 20D 平均：+34.08%
  - 60D 可觀察樣本：3 筆
  - 60D 平均：+7.14%

- Magic26 v0 + Q1/Q2 quality overlay：4 筆訊號
  - 5D 平均：+10.06%
  - 20D 平均：+33.24%
  - 60D 可觀察樣本：2 筆
  - 60D 平均：-9.58%

## 實際 Magic26 v0 訊號例子

53檔樣本中，完整 Magic26 v0 出現：

- 2368，2022-09-23
- 3443，2023-02-01
- 3443，2023-11-14
- 3443，2026-04-14
- 2454，2026-04-17

觀察：訊號高度集中在高波動強勢科技股，尤其 3443。這是優點也是風險：代表條件確實會抓到強勢段，但樣本太少，且可能高度依賴少數強股。

## 第一輪判讀

### 暫時保留的觀察

1. C1+C2 後，60D 平均與勝率改善，表示「日線轉強 + 區間高位」有基本合理性。
2. C3 加入後，樣本大幅收斂，但 forward return 在這組樣本中改善明顯，值得繼續研究。
3. C4 20日漲幅上限沒有殺掉太多好樣本，暫時看起來像合理風控。
4. C5 最大量位置加入後，訊號只剩 5 筆，樣本太少，不能下結論；但它確實會挑出「沒有剛爆長期第一大量」的啟動型樣本。

### 需要警惕

1. 目前樣本不是全市場，不能判定有穩定 alpha。
2. 60D 有些訊號尚未有完整 forward return，例如 2026-04 訊號。
3. Q1/Q2 overlay 在 53檔樣本中沒有改善60D，不能先入為主以為流動性/溫和放量一定加分。
4. C3 目前用「連續 run length」近似，未必完全等於原始 XQ 腳本的 countif / truecount。
5. C2 用 300交易日近似60週，不是精準 weekly bar。

## 輸出檔案

- 規格：`C:/Users/abckf/research-brain/sources/strategy-checks/magic26/magic26_research_spec_2026-06-22.md`
- 腳本：`C:/Users/abckf/research-brain/tools/magic26_signal_pilot.py`
- 10檔摘要：`C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_v0_summary_20210101_20260622_10stocks.csv`
- 53檔摘要：`C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_v0_summary_20210101_20260622_53stocks.csv`
- 53檔訊號：`C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_v0_signals_20210101_20260622_53stocks.csv`

## 下一步

建議第二步不要急著最佳化，而是先做「全市場但分批」：

1. 抓 2021-2026 普通股全市場 daily data。
2. 加上市值/成交金額分層，避免只看到冷門小股。
3. 輸出每年訊號數與 forward return，不只看全樣本。
4. 比較 raw price vs adjusted price，確認除權息是否扭曲訊號。
5. 若能取得作者 GitHub 原始腳本，修正 C3 / C2 定義後重跑。
