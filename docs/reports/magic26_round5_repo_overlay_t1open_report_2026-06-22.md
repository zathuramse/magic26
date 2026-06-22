# 魔26 v0 第五輪：XQ-Lazy-pack1 repo 補強 + t+1 open 檢查

日期：2026-06-22  
狀態：完成 repo triage、C3 校正檢查、volume-ratio overlay、t+1 open excess。研究用途；不是交易建議。

## 本輪目的

QQ 要求：延續原規劃逐步做，並參考同作者另一個 repo：

`https://github.com/shibainvesttravel/XQ-Lazy-pack1`

本輪做兩件事：

1. 檢查 repo 是否補上 Magic26 遺漏條件或原始 XS 定義。
2. 延續第四輪，把進場假設從 `t+1 close` 推進到 `t+1 open`，並測一個 repo-derived overlay。

## Repo 檢查結果

已保存 repo 原始分支檔案：

`C:/Users/abckf/research-brain/sources/strategy-checks/magic26/repo_xq_lazy_pack1_raw/`

Repo triage note：

`C:/Users/abckf/research-brain/sources/strategy-checks/magic26/xq_lazy_pack1_repo_triage_2026-06-22.md`

### 分支

- `main`
- `魔字4號`
- `魔字21號`
- `魔字24號`
- `魔字26號`
- `魔字27號`
- `魔字28號`

### 對 Magic26 最有用的兩點

#### 1. C3 原始 XS 已確認

`魔字26號/短日均發散多頭排列介於幾天.xs` 顯示 C3 是：

- 最近 2 天都符合：
  - 5MA / 10MA >= 1.02
  - 5MA / 20MA >= 1.05
- 連續符合天數不可超過 11 天。

我新增 `c3_xq_exact_proxy` 後，在本輪 liquid universe 中與原 `c1_c2_c3` 筆數完全一致：

- raw：203 筆 vs 203 筆
- adjusted：215 筆 vs 215 筆

結論：目前原本 C3 proxy 沒有造成差異，但之後報告可以說已用 repo 原始 XS 校正過。

#### 2. Magic26 分支多一個值得測的量能結構條件

`魔字26號/日線第幾大量是第1大量幾趴_Ge.xs`：

- 120 日內第 5 大量 / 第一大量需在 50%~100%。

我把它轉成：

```text
top5_volume_ratio_120 = 120日第5大量 / 120日最大量
repo_top5_volume_ratio_ok = 0.50 <= ratio <= 1.00
```

測試版本：

```text
C1 + C2 + C3_xq + repo_top5_volume_ratio_ok
```

下文簡稱：`repo_vol5 overlay`。

## 第五輪主測：liquid universe

Universe：

- 全普通股
- 最近 20D 均成交金額 >= 3000 萬
- raw / adjusted 都跑
- Benchmark：TAIEX
- Entry：t+1 open

## Raw 結果

### C1+C2+C3 原主線

- 訊號：203 筆
- 20D excess：+5.76%，中位數 -0.08%，勝率 50.00%
- t+1 open 20D excess：+5.40%，中位數 -0.16%，勝率 49.73%
- 60D excess：+12.66%，中位數 +0.99%，勝率 51.28%
- t+1 open 60D excess：+11.00%，中位數 -1.02%，勝率 48.72%
- 訊號日漲幅 >= 9%：33.50%
- 隔日開盤跳空 >= 3%：22.17%

判讀：t+1 open 後平均仍有，但中位數 / 勝率偏弱；追高成本有吃掉一部分品質。

### repo_vol5 overlay

- 訊號：111 筆
- 20D excess：+8.22%，中位數 +2.32%，勝率 55.34%
- t+1 open 20D excess：+7.48%，中位數 +3.81%，勝率 54.90%
- 60D excess：+13.61%，中位數 +0.82%，勝率 50.62%
- t+1 open 60D excess：+12.66%，中位數 -0.62%，勝率 49.38%
- 訊號日漲幅 >= 9%：32.43%
- 隔日開盤跳空 >= 3%：22.52%
- 20D 均成交金額 < 1 億：17.12%

判讀：repo_vol5 對 20D 有明顯改善，尤其 t+1 open 20D excess 的中位數轉正；但 60D 仍主要靠平均值，勝率未突破。

### Magic26 v0

- 訊號：93 筆
- 20D excess：+9.57%，中位數 +4.28%，勝率 58.43%
- t+1 open 20D excess：+9.59%，中位數 +4.04%，勝率 57.95%
- 60D excess：+10.61%，中位數 +0.21%，勝率 50.00%
- t+1 open 60D excess：+9.85%，中位數 -0.65%，勝率 48.57%

判讀：Magic26 v0 仍是 20D 強，60D 普通。它像「短期強勢延續」而不是 60D 長抱策略。

## Adjusted 結果

### C1+C2+C3

- 訊號：215 筆
- t+1 open 20D excess：+5.42%，中位數 -0.33%，勝率 48.24%
- t+1 open 60D excess：+11.01%，中位數 -2.38%，勝率 47.59%

### repo_vol5 overlay

- 訊號：115 筆
- t+1 open 20D excess：+7.15%，中位數 +1.13%，勝率 50.94%
- t+1 open 60D excess：+12.32%，中位數 -7.31%，勝率 45.78%

### Magic26 v0

- 訊號：95 筆
- t+1 open 20D excess：+8.57%，中位數 +2.75%，勝率 55.56%
- t+1 open 60D excess：+7.68%，中位數 -4.68%，勝率 44.29%

Adjusted 判讀：repo_vol5 與 Magic26 v0 對 20D 仍有幫助；60D 中位數與勝率很弱，不能把它當長週期策略。

## 年度 / regime 檢查：raw t+1 open excess

### repo_vol5 overlay

- 2022：20D +0.61%，中位數 -7.27%；60D +14.92%，中位數 -18.08%。
- 2023：20D +13.26%，中位數 +6.05%；60D +17.04%，中位數 +17.47%。
- 2024：20D +0.55%，中位數 -7.83%；60D -7.79%，中位數 -12.55%。
- 2025：20D +1.53%，中位數 -0.33%；60D +4.84%，中位數 -9.13%。
- 2026：20D +11.01%，中位數 +10.20%；60D +35.59%，中位數 +38.10%。

### Magic26 v0

- 2022：20D -3.52%，中位數 -7.18%；60D -1.70%，中位數 -11.65%。
- 2023：20D +13.50%，中位數 +5.89%；60D +20.44%，中位數 +14.52%。
- 2024：20D +0.05%，中位數 -6.80%；60D -4.05%，中位數 -12.69%。
- 2025：20D +2.26%，中位數 +2.47%；60D +4.31%，中位數 -10.88%。
- 2026：20D +19.64%，中位數 +20.09%；60D +25.17%，中位數 +8.76%。

年度判讀：

- 2023 / 2026 很好。
- 2024 明顯不適合。
- 2022 也不穩，尤其 Magic26 v0。
- 2025 平均還可以，但 60D 中位數仍偏弱。

所以 regime filter 不是可有可無，是必要下一步。

## Repo 條件採用決策

### 採用 / 保留

1. `c3_xq_exact_proxy`
   - 已確認與原 C3 目前等價。
   - 保留作為文件與實作校正。

2. `repo_top5_volume_ratio_ok`
   - 對 20D t+1 open excess 有改善。
   - 可升為下一輪主測 overlay。

### 暫不採用

1. 籌碼欄位類：
   - 主力長期收集
   - 籌碼從散戶手裡被收集
   - 籌碼被發散
   - 千張大戶持股持續增加

原因：需要 XQ 的籌碼欄位，不能用 FinMind 價量資料亂代。

2. 股本篩選：
   - 需可靠股本資料。
   - 目前先用流動性 universe，不急著接。

3. 複雜週線條件：
   - 值得後續測，但下一步應先做 regime / 執行處理，不要一次塞太多條件。

## 第五輪研究決策

目前排序：

1. `Magic26 v0`：20D 最強，但樣本較少；適合短期強勢候選。
2. `C1+C2+C3+repo_vol5`：20D 品質改善，樣本比 Magic26 多；值得主測。
3. `C1+C2+C3`：寬主線，保留。
4. `Magic26 v0 quality`：仍不如預期，不採用。

最重要結論：

> repo_vol5 是這次 repo 檢查中最有實證價值的補強；它改善 20D 可交易性，但沒有解決 60D 與 regime 問題。

## 下一步：第六輪建議

不要調參。先做 regime gate：

1. 只在大盤/個股趨勢環境較佳時啟用：
   - TAIEX close > MA60 / MA120
   - 或 TAIEX MA20 > MA60
2. 對比三組：
   - `C1+C2+C3`
   - `C1+C2+C3+repo_vol5`
   - `Magic26 v0`
3. 指標以 t+1 open 20D excess 為主，不再優先看 60D。
4. 若 regime gate 能改善 2022/2024，才進參數穩健性網格。

## 輸出檔案

Repo triage：

- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/xq_lazy_pack1_repo_triage_2026-06-22.md`

Raw round5：

- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_round4_summary_round5_all_liquid30000000_raw_20210101_20260622.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_round4_yearly_round5_all_liquid30000000_raw_20210101_20260622.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_round4_checked_signals_round5_all_liquid30000000_raw_20210101_20260622.csv`

Adjusted round5：

- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_round4_summary_round5_all_liquid30000000_adj_20210101_20260622.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_round4_yearly_round5_all_liquid30000000_adj_20210101_20260622.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_round4_checked_signals_round5_all_liquid30000000_adj_20210101_20260622.csv`

本報告：

- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/magic26_round5_repo_overlay_t1open_report_2026-06-22.md`
