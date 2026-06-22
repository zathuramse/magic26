# 魔26 v0 第四輪：benchmark-relative / t+1 entry / execution sanity check

日期：2026-06-22  
狀態：完成 liquid universe 主線檢查。研究用途；不是交易建議。

## 本輪目的

第三輪顯示 Magic26 在明確 universe，尤其流動性 universe，有正向平均 forward return。但第三輪還有三個疑問：

1. 是否只是吃到大盤 beta？
2. 訊號日收盤不可買，隔日進場後是否仍有效？
3. 是否有太多訊號發生在漲停/跳空/低流動等不可執行狀態？

本輪先不調參，只做 sanity check。

## 實作更新

更新主腳本：

- `C:/Users/abckf/research-brain/tools/magic26_signal_pilot.py`

新增欄位：

- `signal_day_ret_1d`：訊號日當天收盤對前一日收盤報酬。
- `next_open_gap`：隔日開盤相對訊號日收盤跳空。
- `next_day_intraday_ret`：隔日開盤到收盤。
- `next_close`：隔日收盤。
- `t1_close_fwd_5d / 20d / 60d`：以隔日收盤作為進場價的 forward return。

同時把 signals CSV 改成輸出所有累積條件成立列，不只完整 Magic26 v0，以便檢查 `C1+C2`、`C1+C2+C3`。

新增第四輪分析腳本：

- `C:/Users/abckf/research-brain/tools/magic26_round4_execution_checks.py`

功能：

- 讀取 signals CSV。
- 以 FinMind `TaiwanStockPrice data_id=TAIEX` 作 benchmark。
- 計算 20D / 60D excess return。
- 計算 t+1 close entry 的 raw return 與 excess return。
- 標記簡易執行風險：
  - 訊號日漲幅 >= 9%。
  - 隔日開盤跳空 >= +3%。
  - 隔日開盤跳空 <= -3%。
  - 20D 均成交金額 < 1 億。

驗證：

```bash
python -m py_compile C:/Users/abckf/research-brain/tools/magic26_signal_pilot.py \
  C:/Users/abckf/research-brain/tools/magic26_round4_execution_checks.py
```

通過。

## 主測 universe

第四輪主測：

- `all + liquid`
- 20D 均成交金額 >= 3000 萬
- raw / adjusted 都跑
- benchmark：TAIEX
- 期間：2021-01-01 到 2026-06-22

Raw retained stocks：994  
Adjusted retained stocks：993

## Raw 結果：liquid universe

### C1+C2

- 訊號：380 筆
- 20D raw：+7.03%，勝率 55.12%
- 20D excess：+4.25%，勝率 49.03%，中位數 -0.41%
- 60D raw：+15.79%，勝率 57.81%
- 60D excess：+8.85%，勝率 49.69%，中位數 -0.35%
- t+1 close 60D excess：+8.21%，勝率 46.40%

判讀：候選池有正向平均值，但扣大盤後中位數接近 0，還不能說普遍打贏大盤。

### C1+C2+C3

- 訊號：203 筆
- 20D raw：+9.07%，勝率 56.91%
- 20D excess：+5.76%，勝率 50.00%，中位數 -0.08%
- 60D raw：+20.38%，勝率 59.62%
- 60D excess：+12.66%，勝率 51.28%，中位數 +0.99%
- t+1 close 60D excess：+11.71%，勝率 48.72%

判讀：這是目前最值得保留的主線。扣大盤後平均仍有肉，中位數略轉正，但勝率只略高於 50%，不是穩定勝率型。

### Magic26 v0

- 訊號：93 筆
- 20D raw：+12.75%，勝率 61.80%
- 20D excess：+9.57%，勝率 58.43%，中位數 +4.28%
- 60D raw：+16.71%，勝率 54.29%
- 60D excess：+10.61%，勝率 50.00%，中位數 +0.21%
- t+1 close 60D excess：+10.49%，勝率 48.57%

判讀：短中期 20D excess 最漂亮；到 60D 後，勝率回到約 50%，表示完整 Magic26 更像「提高短期強勢延續濃度」，不是長持穩定 alpha。

### Magic26 v0 + quality

- 訊號：79 筆
- 20D excess：+7.16%，勝率 53.95%
- 60D excess：+9.10%，勝率 47.46%，中位數 -4.47%
- t+1 close 60D excess：+8.57%，勝率 45.76%

判讀：quality overlay 仍沒有穩定改善。它降低低流動比例，但沒有把超額勝率或中位數拉好。

## Adjusted 結果：liquid universe

Adjusted 結論與 raw 接近，但 60D 勝率更弱。

### C1+C2+C3

- 訊號：215 筆
- 20D excess：+5.79%，勝率 49.50%，中位數 -0.17%
- 60D excess：+12.84%，勝率 50.00%，中位數 -0.06%
- t+1 close 60D excess：+11.85%，勝率 46.99%

### Magic26 v0

- 訊號：95 筆
- 20D excess：+8.43%，勝率 57.14%，中位數 +2.31%
- 60D excess：+8.35%，勝率 45.71%，中位數 -3.65%
- t+1 close 60D excess：+8.51%，勝率 44.29%

判讀：用 adjusted 後，完整 Magic26 的 60D 中位數與勝率都偏弱；20D 比 60D 更可信。

## 年度穩定性：raw excess return

### C1+C2+C3

- 2022：60D excess +10.03%，中位數 +5.57%，勝率 52.94%。
- 2023：60D excess +17.47%，中位數 +14.98%，勝率 63.83%。
- 2024：60D excess +4.52%，中位數 -11.66%，勝率 30.77%。
- 2025：60D excess +7.06%，中位數 -9.00%，勝率 44.83%。
- 2026：60D excess +25.10%，中位數 +13.40%，勝率 66.67%，但受近期強勢行情與未完整樣本影響。

### Magic26 v0

- 2022：60D excess -0.51%，中位數 -9.00%，勝率 22.22%。
- 2023：60D excess +21.43%，中位數 +17.97%，勝率 73.91%。
- 2024：60D excess -6.61%，中位數 -13.15%，勝率 21.43%。
- 2025：60D excess +4.38%，中位數 -13.11%，勝率 40.00%。
- 2026：60D excess +31.26%，中位數 +13.93%，勝率 77.78%，但可觀察 60D 樣本仍少。

年度結論：2024 是明顯弱點；完整 Magic26 在 regime 不對時會很不穩。

## 執行風險標記

Raw liquid universe：

- C1+C2+C3：
  - 訊號日漲幅 >= 9%：33.50%
  - 隔日開盤跳空 >= 3%：22.17%
  - 20D 均成交金額 < 1 億：27.59%

- Magic26 v0：
  - 訊號日漲幅 >= 9%：24.73%
  - 隔日開盤跳空 >= 3%：15.05%
  - 20D 均成交金額 < 1 億：18.28%

判讀：不少訊號已經在急漲後出現，且隔日追價風險不低。即使 t+1 close 還保留平均超額，實盤若用 t+1 open 追價，仍需另外測。

## 第四輪研究決策

1. `C1+C2`：保留為寬候選池，但不作為交易規則。
2. `C1+C2+C3`：升為下一輪主測版本。
   - 理由：樣本 203/215 筆，扣 TAIEX 後 60D 平均仍正，raw 中位數略正。
3. 完整 `Magic26 v0`：保留為短期強勢濃縮版本。
   - 20D excess 表現比 60D 更好。
   - 60D adjusted 中位數與勝率不足，不能當長持策略。
4. `Q1/Q2 quality overlay`：暫不採用為正式條件。
5. 下一輪不要調參；先測 t+1 open、漲停不可買、處置/注意股，以及分 regime。

## 下一輪建議

第五輪應該做：

1. `t+1 open` entry，而不是 t+1 close。
2. 以 signal-day close 到 t+1 open 的跳空成本，建立追價懲罰。
3. 加入漲停/跌停與注意/處置股資料，如果本地 market-rules DB 可用就接進來；本輪尚未找到本地 market-rules SQLite。
4. 分 regime：至少分 2022 空頭、2023 AI/復甦、2024 震盪、2025/2026 強勢段。
5. 若第五輪仍保留，才做小型參數穩健性網格。

## 輸出檔案

Raw：

- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_round4_summary_all_liquid30000000_raw_20210101_20260622.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_round4_yearly_all_liquid30000000_raw_20210101_20260622.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_round4_checked_signals_all_liquid30000000_raw_20210101_20260622.csv`

Adjusted：

- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_round4_summary_all_liquid30000000_adj_20210101_20260622.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_round4_yearly_all_liquid30000000_adj_20210101_20260622.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_round4_checked_signals_all_liquid30000000_adj_20210101_20260622.csv`

本報告：

- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/magic26_round4_execution_benchmark_report_2026-06-22.md`
