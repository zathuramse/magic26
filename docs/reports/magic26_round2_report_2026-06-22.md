# 魔26 v0 第二輪分批驗證紀錄

日期：2026-06-22  
狀態：完成 200 檔普通股分批樣本 raw / adjusted 對照、yearly split、流動性分層。仍不是全市場結論。

## 這一輪做什麼

延續第一輪 53 檔手動高流動樣本，本輪先不做參數最佳化，改做三件事：

1. 擴大到 FinMind `TaiwanStockInfo` 過濾後、依 stock_id 排序的前 200 檔普通股樣本。
2. 新增輸出：
   - yearly split：每年訊號數與 forward return。
   - liquidity bucket：以 20 日均成交金額分層。
3. 跑 raw price 與 adjusted price 對照，檢查除權息/還原價差異。

注意：`--max-stocks 200` 是按 stock_id 排序的前 200 檔，不是隨機抽樣，也不是科技股代表樣本；產業偏向傳產/食品/塑化/紡織/電機早期代碼。這一輪用途是壓力測試，不是全市場績效宣稱。

## 腳本更新

腳本：`C:/Users/abckf/research-brain/tools/magic26_signal_pilot.py`

新增：

- `summarize_by_group()`：依年度 / 流動性分層彙總。
- `add_liquidity_bucket()`：用 20 日均成交金額分層：
  - `<1千萬`
  - `1-3千萬`
  - `3千萬-1億`
  - `1-3億`
  - `>=3億`
- 輸出檔名加入 `raw` / `adj`，避免 raw 與 adjusted 互相覆蓋。

驗證：

- `python -m py_compile C:/Users/abckf/research-brain/tools/magic26_signal_pilot.py` 通過。
- raw / adjusted 200 檔樣本均實際執行完成。

## 執行命令

```bash
python C:/Users/abckf/research-brain/tools/magic26_signal_pilot.py \
  --start-date 2021-01-01 \
  --end-date 2026-06-22 \
  --max-stocks 200

python C:/Users/abckf/research-brain/tools/magic26_signal_pilot.py \
  --start-date 2021-01-01 \
  --end-date 2026-06-22 \
  --max-stocks 200 \
  --adjusted
```

兩次執行各有 9 檔空資料錯誤，例如 `1107 empty price data`；其餘樣本正常輸出。

## Raw price 結果：200 檔分批樣本

### 條件累加總表

- C1 only：210 筆
  - 20D 平均：+1.19%
  - 60D 平均：+0.77%
  - 60D 勝率：42.27%

- C1 + C2：46 筆
  - 20D 平均：+1.44%
  - 60D 平均：+2.26%
  - 60D 勝率：40.00%
  - 60D < -20%：15.00%

- C1 + C2 + C3：21 筆
  - 20D 平均：-4.14%
  - 60D 平均：-0.52%
  - 60D 勝率：52.94%

- C1 + C2 + C3 + C4：17 筆
  - 20D 平均：-4.43%
  - 60D 平均：-3.17%

- Magic26 v0 全條件：9 筆
  - 5D 平均：-0.23%
  - 20D 平均：-5.35%
  - 60D 平均：-4.20%
  - 60D 勝率：44.44%

- Magic26 v0 + Q1/Q2 quality：5 筆
  - 20D 平均：-7.83%
  - 60D 平均：-7.15%
  - 60D 勝率：20.00%

### 年度觀察：raw

- 2022：Magic26 v0 2 筆，60D 平均 -17.79%，其中 50% 跌超過 20%。
- 2023：Magic26 v0 3 筆，60D 平均 +10.07%，勝率 66.67%。
- 2024：Magic26 v0 0 筆。
- 2025：Magic26 v0 4 筆，60D 平均 -8.10%，勝率 25.00%。
- 2026：Magic26 v0 0 筆；但 C1+C2 有 8 筆，20D / 60D 可觀察樣本偏弱。

### 流動性觀察：raw

- C1+C2 在 `<1千萬` 低流動性桶看起來最好：60D 平均 +12.85%，但這對實務交易最不可靠，可能有流動性與滑價問題。
- Magic26 v0 在 `>=3億` 高流動桶只有 3 筆，60D 平均 +1.10%，20D 平均 -3.16%。
- Magic26 v0 + Q1/Q2 quality 只剩 5 筆，並沒有改善結果。

## Adjusted price 對照

Adjusted 結果比 raw 更弱，完整 Magic26 v0 只剩 5 筆：

- Magic26 v0：5 筆
  - 20D 平均：-7.60%
  - 60D 平均：-6.56%
  - 60D 勝率：20.00%

- C1+C2：45 筆
  - 20D 平均：-1.83%
  - 60D 平均：-1.43%

這表示第一輪 53 檔樣本中的漂亮結果，至少目前不能外推到這個 200 檔分批樣本；也提醒 raw / adjusted 對訊號構成會有實質差異。

## 實際 Magic26 v0 訊號：raw 200 檔

- 1218，2022-11-30，60D -35.85%，quality=True
- 1259，2022-12-09，60D +0.27%，quality=False，低流動
- 1519，2023-07-17，60D +28.28%，quality=True
- 1471，2023-08-23，60D -3.21%，quality=True
- 1538，2023-08-30，60D +5.13%，quality=False，低流動
- 1536，2025-02-17，60D -16.77%，quality=True
- 1443，2025-05-09，60D +0.33%，quality=False，低流動
- 1236，2025-05-23，60D -7.73%，quality=False，低流動
- 1560，2025-08-28，60D -8.21%，quality=True

Adjusted 完整訊號只剩：1218、1519、1471、1536、1560。

## 第二輪判讀

### 結論先講

這輪結果偏負面：魔26 v0 在「前 200 檔普通股分批樣本」沒有重現第一輪 53 檔科技/高流動樣本的漂亮 forward return。暫時不能說它是穩定策略；比較合理的定位是「強勢科技/高波動股候選池條件」，不是一般台股全市場通用 alpha。

### 保留的部分

1. C1+C2 仍有一點合理性：日線轉強 + 區間高位可以作為候選池粗篩。
2. 訊號會明顯收斂，表示條件不是亂撒網。
3. 在 2023 特定行情段，完整條件能抓到一些強勢延伸；但年度穩定性不足。

### 降級的部分

1. C3 / C4 / C5 加入後，在 200 檔樣本沒有改善整體結果，反而樣本太少且 20D 表現變差。
2. Q1/Q2 quality overlay 目前沒有證明加分，不能先驗地當成強化條件。
3. 低流動桶的好數字不應視為可交易優勢，反而要提高警覺。

### 主要風險

1. 這個 200 檔樣本不是隨機；偏傳產、低代碼，可能不是魔26原本想抓的題材股環境。
2. 完整 Magic26 v0 訊號太少，年度 split 非常不穩。
3. C2 仍是 300 日 proxy，不是精準週線 60 週。
4. C3 仍是 run-length proxy，不一定等於原始 XQ `countif` / `truecount`。
5. 尚未加入處置股、成本、隔日可買性、漲停/流動性滑價。

## 輸出檔案

Raw：

- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_v0_summary_raw_20210101_20260622_200stocks.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_v0_yearly_raw_20210101_20260622_200stocks.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_v0_liquidity_raw_20210101_20260622_200stocks.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_v0_signals_raw_20210101_20260622_200stocks.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_v0_manifest_raw_20210101_20260622_200stocks.json`

Adjusted：

- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_v0_summary_adj_20210101_20260622_200stocks.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_v0_yearly_adj_20210101_20260622_200stocks.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_v0_liquidity_adj_20210101_20260622_200stocks.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_v0_signals_adj_20210101_20260622_200stocks.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_v0_manifest_adj_20210101_20260622_200stocks.json`

## 建議第三輪

不要參數最佳化。下一步應該先修正樣本設計：

1. 建立「全市場分批但保留產業/流動性標籤」的 universe，不要只用前 N 個 stock_id。
2. 做三個固定 universe 對照：
   - 全普通股；
   - 20D 均成交金額 >= 3000萬；
   - 科技/電子/半導體/AI 題材相關子集。
3. 先跑 C1+C2 與 C1+C2+C3，不急著用完整 C5；因為完整 v0 樣本太少。
4. 若找得到作者 GitHub 原始 XQ 腳本，先修 C2/C3 定義再重跑。
