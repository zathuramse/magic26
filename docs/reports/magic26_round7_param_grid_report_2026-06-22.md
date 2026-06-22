# 魔26 v0 第七輪：regime_all3 下的小型參數穩健性網格

日期：2026-06-22  
狀態：完成小型參數網格。研究用途；不是交易建議。

## 本輪目的

第六輪確認：Magic26 類訊號在 `regime_all3=True` 時明顯改善，`regime_all3=False` 時不適合追多。

所以第七輪不再做全市場最佳化，而是固定：

- Regime：`regime_all3=True`
- Entry：`t+1 open`
- 主 horizon：20D excess vs TAIEX
- Universe：全普通股 + 20D 均成交金額 >= 3000 萬
- raw / adjusted 都測

只做小型穩健性網格：

1. repo volume ratio：40% / 50% / 60%
2. C4 20D 漲幅上限：25% / 40% / 60%
3. C5 最大量排除天數：3 / 5 / 8

## 實作

新增腳本：

`C:/Users/abckf/research-brain/tools/magic26_round7_param_grid.py`

輸入：

- `magic26_round4_checked_signals_round6_regime_all_liquid30000000_raw_20210101_20260622.csv`
- `magic26_round4_checked_signals_round6_regime_all_liquid30000000_adj_20210101_20260622.csv`

輸出：

- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_round7_param_grid_summary_20210101_20260622.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_round7_param_grid_yearly_20210101_20260622.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_round7_param_grid_top_20210101_20260622.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_round7_param_grid_manifest_20210101_20260622.json`

驗證：

```bash
python -m py_compile C:/Users/abckf/research-brain/tools/magic26_round7_param_grid.py
python C:/Users/abckf/research-brain/tools/magic26_round7_param_grid.py
```

已跑完。

## 重要提醒：不要被最高分誤導

網格排名最高的是：

```text
magic_repo60_c425_c5gt5/8_regime
```

raw / adjusted：

- 訊號：20 / 18 筆
- 20D median：+20.09% / +20.09%
- 20D win：73.68% / 70.59%

但這組樣本太少，而且容易被 2026 強勢行情拉高。這不是穩健主規格，只能當「高濃度觀察組」。

## 核心發現一：repo volume ratio 50% 最平衡

只看 `C1+C2+C3 + repo ratio + regime_all3`：

### repo50

- raw / adjusted 訊號：89 / 87
- raw / adjusted 20D median：+6.05% / +3.81%
- 平均 20D median：約 +4.93%
- 平均 20D win：約 55.03%
- raw / adjusted 60D median：+6.92% / +1.88%

### repo60

- 訊號：63 / 61
- 平均 20D median：約 +4.46%
- adjusted 60D median 轉負：-4.42%

### repo40

- 訊號：115 / 115
- 平均 20D median：約 +4.05%
- 勝率較弱：約 52.94%

判讀：

- 40% 太寬，品質下降。
- 60% 太窄，樣本下降且 adjusted 60D 不穩。
- **50% 是目前最平衡的 repo overlay。**

## 核心發現二：C4 25% 很強，但太窄；C4 40% 更適合主規格

### C4 25%，不加 repo

`magic_c425_c5gt5_regime`：

- raw / adjusted 訊號：41 / 39
- raw / adjusted 20D median：+13.03% / +12.08%
- raw / adjusted 20D win：66.67% / 64.86%
- raw / adjusted 60D median：+13.08% / +8.76%

看起來很漂亮，但年度穩健性有問題：

- 2024 median：raw -7.52%，adjusted -5.78%
- 2025 median：raw/adjusted -3.45%
- 2026 median：約 +20%

判讀：C4 25% 很可能變成「強 regime 裡的高濃度訊號」，但它不是穩健主規格。

### C4 40%，不加 repo，也就是接近 Magic26 v0 主版

`magic_c440_c5gt5_regime`：

- raw / adjusted 訊號：75 / 72
- raw / adjusted 20D median：+9.66% / +7.43%
- 平均 20D median：約 +8.54%
- 平均 20D win：約 61.28%
- raw / adjusted 60D median：+7.23% / +3.15%

年度負 median 較少，樣本也比較夠。

判讀：**C4 40% 仍是目前較合理的主規格上限。**

### C4 60%

`magic_c460_c5gt5_regime`：

- raw / adjusted 訊號：87 / 85
- 平均 20D median：約 +5.40%
- adjusted 60D median：-0.62%

判讀：太寬，品質稀釋。

## 核心發現三：C5 >5 與 >8 幾乎沒差；>3 稍弱

多數主候選中：

- C5 >5 與 C5 >8 結果完全或幾乎相同。
- C5 >3 會多一點訊號，但中位數通常變差。

判讀：

- Magic26 原始的 `>5` 合理。
- 沒必要為了這個條件最佳化。
- 後續保留 C5 >5 即可。

## 最值得升級的主候選

### Candidate A：Magic26 v0 + repo50 overlay

規格：

```text
regime_all3=True
C1+C2+C3
repo_vol5 >= 50%
0 < 20D return < 40%
days_since_max_volume > 5
```

代號：

```text
magic_repo50_c440_c5gt5_regime
```

結果：

- raw / adjusted 訊號：53 / 49
- raw / adjusted 20D avg：+17.76% / +17.09%
- raw / adjusted 20D median：+11.76% / +9.66%
- raw / adjusted 20D win：70.00% / 65.22%
- raw / adjusted 60D median：+10.94% / +5.04%

年度：

- 2023：raw median +11.46%，adjusted +3.03%
- 2024：raw/adjusted median -8.41%
- 2025：raw/adjusted median +6.72%
- 2026：raw +20.09%，adjusted +20.09%

判讀：

- 它比純 Magic26 v0 更濃縮，20D median/win 更好。
- 但 2024 仍會虧，不能宣稱已解決所有 regime 問題。
- 目前可升為「主觀察策略」。

### Candidate B：Magic26 v0 原始主版，regime_all3=True

規格：

```text
regime_all3=True
C1+C2+C3
0 < 20D return < 40%
days_since_max_volume > 5
```

代號：

```text
magic_c440_c5gt5_regime
```

結果：

- raw / adjusted 訊號：75 / 72
- raw / adjusted 20D avg：+13.01% / +12.35%
- raw / adjusted 20D median：+9.66% / +7.43%
- raw / adjusted 20D win：62.86% / 59.70%
- raw / adjusted 60D median：+7.23% / +3.15%

判讀：

- 樣本比 Candidate A 多。
- 品質略低，但比較不濃縮。
- 適合作為「寬主版」。

### Candidate C：C4 25% 高濃度觀察組

規格：

```text
regime_all3=True
C1+C2+C3
0 < 20D return < 25%
days_since_max_volume > 5
```

代號：

```text
magic_c425_c5gt5_regime
```

結果很強，但樣本只有 41 / 39，而且年度不穩。

判讀：只作觀察，不升主策略。

## 第七輪研究決策

目前主線調整為：

1. **主觀察策略：`magic_repo50_c440_c5gt5_regime`**
   - repo50 + C4 40 + C5 >5
   - 最佳平衡：品質提升、樣本仍可接受。

2. **寬主版：`magic_c440_c5gt5_regime`**
   - 保留原 Magic26 v0 在 regime_all3 下的版本。
   - 作為 Candidate A 的對照基準。

3. **高濃度觀察：`magic_c425_c5gt5_regime`**
   - 20D 表現很強，但樣本少、年度不穩，不作主規格。

不採用：

- repo60 當主規格：太窄。
- C4 60：品質稀釋。
- C5 >3：略放寬但品質下降。
- C5 >8：跟 >5 幾乎沒差，不需要增加複雜度。

## 還沒解決的問題

1. **2024 仍是弱點**
   - 即使用 regime_all3，2024 仍有負 median。
   - 代表大盤均線 gate 不足以處理所有盤整/假突破環境。

2. **2026 對平均與中位數拉抬很明顯**
   - 不能把 2026 的強表現外推。

3. **樣本仍偏少**
   - Candidate A raw/adjusted 只有 53 / 49 筆。
   - 已可作研究候選，但還不是自動交易規格。

## 下一輪建議

第八輪不要再擴參數。下一步應該做「交易化檢查」：

1. 訊號日與隔日開盤風險：
   - signal-day 漲停/接近漲停比例
   - next-open gap > 3%、> 5% 的分布

2. 進出場規則：
   - 固定 20D 出場
   - 或 10D/20D 移動停利停損簡化測試

3. 2024 敗因切片：
   - 2024 負貢獻訊號清單
   - 是否集中在特定產業 / 低流動性 / 大盤假突破區段

目前不建議繼續網格最佳化，否則會開始過擬合。
