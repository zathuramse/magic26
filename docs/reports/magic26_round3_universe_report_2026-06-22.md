# 魔26 v0 第三輪 universe 驗證紀錄

日期：2026-06-22  
狀態：完成明確 universe 版本：全普通股 / 流動性普通股 / 科技電子子集，並完成 raw / adjusted 對照。仍為 research-only，不是交易建議。

## 本輪目的

第二輪用 `--max-stocks 200` 的前 200 檔 stock_id，樣本偏傳產與低代碼，不能代表市場。本輪修正樣本設計：

1. 不再把前 N 檔當市場代表。
2. 建立明確 universe：
   - `all`：TWSE/TPEx 普通股，排除 ETF/ETN/受益證券/權證/存託憑證等。
   - `all + liquid`：同上，但只保留最近 20D 均成交金額 >= 3000 萬的股票。
   - `tech`：半導體、電子、電腦、通信/通訊、資訊、光電、數位雲端等類股。
3. 每個 universe 都跑 raw 與 adjusted price。
4. 仍不做參數最佳化，只看固定 v0 條件是否有跨 universe 的基本穩健性。

## 腳本更新

腳本：`C:/Users/abckf/research-brain/tools/magic26_signal_pilot.py`

新增參數：

```bash
--universe manual|all|tech
--liquid-universe
--max-stocks N
```

新增邏輯：

- `get_common_stock_info()`：過濾普通股 universe，排除 ETF/ETN/受益證券/權證/存託憑證等。
- `select_universe()`：選擇 `all` 或 `tech` universe。
- `--liquid-universe`：計算完指標後，依最近 20D 均成交金額過濾股票。
- manifest 增加 selected / retained stock count。

驗證：

```bash
python -m py_compile C:/Users/abckf/research-brain/tools/magic26_signal_pilot.py
```

通過。

## Universe 規模

Raw：

- all：選入 2130 檔，保留有效資料 2049 檔，81 檔空資料/錯誤。
- all + liquid：選入 2130 檔，保留 994 檔，81 檔空資料/錯誤。
- tech：選入 1039 檔，保留 986 檔，53 檔空資料/錯誤。

Adjusted：

- all：選入 2130 檔，保留有效資料 2048 檔，82 檔空資料/錯誤。
- all + liquid：選入 2130 檔，保留 993 檔，82 檔空資料/錯誤。
- tech：選入 1039 檔，保留 986 檔，53 檔空資料/錯誤。

## 核心結果總表

### All common stocks

Raw：

- C1+C2：631 筆，20D +4.49%，60D +9.76%，60D 勝率 52.34%。
- C1+C2+C3：330 筆，20D +4.99%，60D +11.73%，60D 勝率 52.73%。
- Magic26 v0：131 筆，20D +8.20%，60D +12.90%，60D 勝率 51.92%。
- Magic26 v0 + quality：90 筆，20D +8.64%，60D +16.47%，60D 勝率 49.28%。

Adjusted：

- C1+C2：675 筆，20D +4.45%，60D +10.21%，60D 勝率 55.02%。
- C1+C2+C3：313 筆，20D +5.44%，60D +12.91%，60D 勝率 50.19%。
- Magic26 v0：116 筆，20D +10.33%，60D +12.96%，60D 勝率 47.73%。
- Magic26 v0 + quality：95 筆，20D +10.55%，60D +16.79%，60D 勝率 50.00%。

### Liquid common stocks：20D 均成交金額 >= 3000 萬

Raw：

- C1+C2：380 筆，20D +7.03%，60D +15.79%，60D 勝率 57.81%。
- C1+C2+C3：203 筆，20D +9.07%，60D +20.38%，60D 勝率 59.62%。
- Magic26 v0：93 筆，20D +12.75%，60D +16.71%，60D 勝率 54.29%。
- Magic26 v0 + quality：79 筆，20D +10.41%，60D +16.53%，60D 勝率 52.54%。

Adjusted：

- C1+C2：443 筆，20D +6.71%，60D +14.41%，60D 勝率 58.58%。
- C1+C2+C3：215 筆，20D +9.18%，60D +20.62%，60D 勝率 57.23%。
- Magic26 v0：95 筆，20D +12.00%，60D +14.50%，60D 勝率 48.57%。
- Magic26 v0 + quality：84 筆，20D +10.91%，60D +16.05%，60D 勝率 50.00%。

### Tech / electronics subset

Raw：

- C1+C2：339 筆，20D +6.54%，60D +13.41%，60D 勝率 53.50%。
- C1+C2+C3：210 筆，20D +7.59%，60D +14.96%，60D 勝率 52.35%。
- Magic26 v0：80 筆，20D +10.92%，60D +14.22%，60D 勝率 45.76%。
- Magic26 v0 + quality：65 筆，20D +10.27%，60D +15.57%，60D 勝率 45.83%。

Adjusted：

- C1+C2：361 筆，20D +6.36%，60D +12.86%，60D 勝率 55.05%。
- C1+C2+C3：205 筆，20D +7.46%，60D +15.13%，60D 勝率 51.83%。
- Magic26 v0：77 筆，20D +11.57%，60D +14.43%，60D 勝率 47.27%。
- Magic26 v0 + quality：68 筆，20D +11.04%，60D +16.01%，60D 勝率 46.94%。

## 年度穩定性：raw Magic26 v0

### All common stocks

- 2022：18 筆，60D -6.80%，勝率 27.78%，60D < -20% 為 33.33%。
- 2023：33 筆，60D +20.57%，勝率 66.67%。
- 2024：22 筆，60D +4.86%，但中位數 -10.58%，勝率 40.91%。
- 2025：21 筆，60D +7.16%，中位數 -1.52%，勝率 42.86%。
- 2026：37 筆，60D +52.84%，但可觀察 60D 只有 10 筆，且受近期強勢行情影響大。

### Liquid common stocks

- 2022：9 筆，60D -6.42%，勝率 22.22%，60D < -20% 為 44.44%。
- 2023：23 筆，60D +22.85%，勝率 69.57%。
- 2024：14 筆，60D -2.95%，中位數 -12.73%，勝率 35.71%。
- 2025：15 筆，60D +14.48%，中位數 -1.12%，勝率 46.67%。
- 2026：32 筆，60D +58.41%，但可觀察 60D 只有 9 筆。

### Tech subset

- 2022：9 筆，60D -12.21%，勝率 22.22%。
- 2023：20 筆，60D +16.18%，但中位數 -1.14%，勝率 45.00%。
- 2024：12 筆，60D -4.61%，勝率 25.00%。
- 2025：12 筆，60D +20.58%，中位數 +7.00%，勝率 58.33%。
- 2026：27 筆，60D +72.31%，但可觀察 60D 只有 6 筆。

## 第三輪判讀

### 結論先講

第三輪把第二輪的「偏負面」修正為：

> 魔26 v0 不是完全沒料；在全市場與流動性 universe 裡，固定條件確實抓到一批後續平均報酬偏正的強勢候選。但它還不能升級成穩定策略，因為年度穩定性不足、60D 平均容易被少數大贏家和 2026 強勢行情拉高，中位數與勝率沒有同樣漂亮。

### 保留價值

1. `C1+C2` 是比較穩的核心粗篩：訊號數足夠，raw/adjusted 都偏正。
2. 加上 `C3` 後，在 liquid universe 的 20D/60D 平均和勝率都有改善，值得保留為第二層條件。
3. 完整 Magic26 v0 在平均報酬上更高，但樣本縮小，勝率沒有同步大幅提升；它比較像「提高爆發候選濃度」，不是穩定勝率引擎。
4. 流動性 universe 比全市場更可交易，結果也不差；後續應以 liquid universe 為主線。

### 需要降溫的地方

1. 2022 和 2024 明顯不穩，不能忽略空頭/震盪年失效問題。
2. 2026 的 60D 結果很亮，但樣本尚未完整，且可能受近期強勢行情/AI題材行情拉高。
3. Magic26 v0 的 60D 中位數常接近 0 或為負，代表平均值可能由少數大飆股拉動。
4. `Q1/Q2 quality overlay` 沒有穩定改善勝率；暫時不要當成正式條件。
5. 尚未扣成本、滑價、漲停買不到、處置股、隔日開盤可買性。

## 研究決策

- `C1+C2`：保留為候選池主線。
- `C1+C2+C3`：保留為下一輪主測版本，尤其 liquid universe。
- 完整 `Magic26 v0`：保留，但降級為「高濃度候選」而非唯一策略。
- `Magic26 v0 + Q1/Q2 quality`：暫不升級，僅作分層觀察。
- 不進行參數最佳化，直到先完成 regime / benchmark / execution sanity checks。

## 下一輪建議

第四輪不要調參，先做三個 sanity check：

1. Benchmark-relative：每筆訊號的 20D/60D 報酬扣同期 TAIEX 或同產業平均，確認不是只吃市場 beta。
2. Entry timing：訊號日收盤不可買，改測 `t+1 open` 或 `t+1 close` 進場。
3. Risk state：標記注意/處置股、漲停、成交金額不足、極端跳空，避免把不可執行訊號當 alpha。

若第四輪仍保留，才進入小型參數穩健性網格。

## 輸出檔案

主要 summary：

- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_v0_summary_all_raw_20210101_20260622_2130stocks.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_v0_summary_all_adj_20210101_20260622_2130stocks.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_v0_summary_all_liquid30000000_raw_20210101_20260622_2130stocks.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_v0_summary_all_liquid30000000_adj_20210101_20260622_2130stocks.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_v0_summary_tech_raw_20210101_20260622_1039stocks.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_v0_summary_tech_adj_20210101_20260622_1039stocks.csv`

本報告：

- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/magic26_round3_universe_report_2026-06-22.md`
