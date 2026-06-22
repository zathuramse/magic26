# 魔26 v0 第六輪：TAIEX regime gate 檢查

日期：2026-06-22  
狀態：完成 TAIEX regime gate 對照。研究用途；不是交易建議。

## 本輪目的

第五輪確認：

- `C1+C2+C3+repo_vol5` 對 20D t+1 open excess 有改善。
- `Magic26 v0` 也是 20D 強、60D 弱。
- 但 2022 / 2024 regime 明顯拖累結果。

所以第六輪先不調參，測大盤 regime gate 是否能過濾弱環境。

## 實作更新

更新腳本：

`C:/Users/abckf/research-brain/tools/magic26_round4_execution_checks.py`

新增 TAIEX regime 欄位：

- `regime_close_gt_ma60`：TAIEX close > MA60
- `regime_ma20_gt_ma60`：TAIEX MA20 > MA60
- `regime_close_gt_ma120`：TAIEX close > MA120
- `regime_any2`：上述三者至少兩個成立
- `regime_all3`：上述三者全部成立

新增輸出：

- `magic26_round4_regime_<run_label>.csv`

驗證：

```bash
python -m py_compile C:/Users/abckf/research-brain/tools/magic26_round4_execution_checks.py
```

通過。

## 主測訊號

主測三組：

1. `C1+C2+C3`
2. `C1+C2+C3+repo_vol5`
3. `Magic26 v0`

主指標：

- `t+1 open 20D excess vs TAIEX`
- 次指標：`t+1 open 60D excess vs TAIEX`

Universe：

- 全普通股
- 20D 均成交金額 >= 3000 萬
- raw / adjusted 都跑

## Raw 結果：regime gate = True

### regime_all3：TAIEX close > MA60、MA20 > MA60、close > MA120

#### C1+C2+C3

- 訊號：158 筆
- t+1 open 20D excess：+8.56%
- 20D excess 中位數：+4.04%
- 20D excess 勝率：52.82%
- t+1 open 60D excess：+15.53%
- 60D excess 中位數：+5.56%
- 60D excess 勝率：53.57%

#### C1+C2+C3+repo_vol5

- 訊號：89 筆
- t+1 open 20D excess：+10.93%
- 20D excess 中位數：+6.05%
- 20D excess 勝率：57.50%
- t+1 open 60D excess：+16.57%
- 60D excess 中位數：+6.92%
- 60D excess 勝率：55.93%

#### Magic26 v0

- 訊號：75 筆
- t+1 open 20D excess：+13.01%
- 20D excess 中位數：+9.66%
- 20D excess 勝率：62.86%
- t+1 open 60D excess：+12.27%
- 60D excess 中位數：+7.23%
- 60D excess 勝率：55.77%

## Raw 結果：regime gate = False

### regime_all3 = False

#### C1+C2+C3

- 訊號：45 筆
- t+1 open 20D excess：-4.57%
- 20D excess 中位數：-4.24%
- 20D excess 勝率：40.00%
- t+1 open 60D excess：-0.54%
- 60D excess 中位數：-9.01%
- 60D excess 勝率：36.36%

#### C1+C2+C3+repo_vol5

- 訊號：22 筆
- t+1 open 20D excess：-5.05%
- 20D excess 中位數：-0.29%
- 20D excess 勝率：45.45%
- t+1 open 60D excess：+2.18%
- 60D excess 中位數：-11.26%
- 60D excess 勝率：31.82%

#### Magic26 v0

- 訊號：18 筆
- t+1 open 20D excess：-3.72%
- 20D excess 中位數：-2.72%
- 20D excess 勝率：38.89%
- t+1 open 60D excess：+2.86%
- 60D excess 中位數：-10.17%
- 60D excess 勝率：27.78%

## Adjusted 結果：regime_all3

Adjusted 與 raw 方向一致，但數字稍弱。

### regime_all3 = True

#### C1+C2+C3

- 訊號：163 筆
- t+1 open 20D excess：+8.16%
- 20D excess 中位數：+1.40%
- 20D excess 勝率：51.02%
- t+1 open 60D excess：+15.90%
- 60D excess 中位數：+3.15%
- 60D excess 勝率：52.17%

#### C1+C2+C3+repo_vol5

- 訊號：87 筆
- t+1 open 20D excess：+9.82%
- 20D excess 中位數：+3.81%
- 20D excess 勝率：52.56%
- t+1 open 60D excess：+16.90%
- 60D excess 中位數：+1.88%
- 60D excess 勝率：52.73%

#### Magic26 v0

- 訊號：72 筆
- t+1 open 20D excess：+12.35%
- 20D excess 中位數：+7.43%
- 20D excess 勝率：59.70%
- t+1 open 60D excess：+11.68%
- 60D excess 中位數：+3.15%
- 60D excess 勝率：53.19%

### regime_all3 = False

#### C1+C2+C3

- 訊號：52 筆
- t+1 open 20D excess：-2.33%
- 20D excess 中位數：-2.80%
- 20D excess 勝率：40.38%
- t+1 open 60D excess：-0.02%
- 60D excess 中位數：-9.00%
- 60D excess 勝率：37.25%

#### C1+C2+C3+repo_vol5

- 訊號：28 筆
- t+1 open 20D excess：-0.28%
- 20D excess 中位數：-0.29%
- 20D excess 勝率：46.43%
- t+1 open 60D excess：+3.34%
- 60D excess 中位數：-9.72%
- 60D excess 勝率：32.14%

#### Magic26 v0

- 訊號：23 筆
- t+1 open 20D excess：-2.43%
- 20D excess 中位數：-1.20%
- 20D excess 勝率：43.48%
- t+1 open 60D excess：-0.50%
- 60D excess 中位數：-10.42%
- 60D excess 勝率：26.09%

## Regime gate 比較

### 最有效 gate

`regime_all3` 最乾淨：

```text
TAIEX close > MA60
AND TAIEX MA20 > MA60
AND TAIEX close > MA120
```

原因：

- True 時三組訊號的 20D / 60D t+1 open excess 都明顯改善。
- False 時 20D 幾乎都轉負，60D 中位數大幅負值。
- 它比單一 close > MA120 更嚴格，也比 any2 更乾淨。

### 策略排序

在 `regime_all3=True` 時：

1. **Magic26 v0**
   - 20D 最強，raw/adjusted 都最好。
   - 但樣本最少。
2. **C1+C2+C3+repo_vol5**
   - 比 C1+C2+C3 更穩，20D 中位數與勝率改善。
   - 樣本比 Magic26 多。
3. **C1+C2+C3**
   - 寬候選池，仍可保留，但單獨交易品質較弱。

## 第六輪研究決策

### 升級為主規格候選

```text
Regime gate: TAIEX close > MA60 AND MA20 > MA60 AND close > MA120
Entry: t+1 open
Main horizon: 20D
Candidate A: Magic26 v0
Candidate B: C1+C2+C3+repo_vol5
```

### 降級

- `regime_all3=False` 時暫不做多方追價訊號。
- 60D 不再作為主 horizon，只作延伸觀察。
- 單獨 `C1+C2+C3` 作為寬候選池，不作主策略。

## 下一輪建議

第七輪才可以開始做小型參數穩健性，但要很克制：

1. 固定 `regime_all3=True`。
2. 固定 `t+1 open`。
3. 主測 20D excess。
4. 只測少量參數：
   - repo_vol5：第 5 大量比例 40% / 50% / 60%
   - C4 20D 漲幅上限：25% / 40% / 60%
   - C5 最大量排除天數：3 / 5 / 8
5. 每個參數都要看 raw + adjusted + 年度 split，不只看總平均。

## 輸出檔案

Raw：

- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_round4_regime_round6_regime_all_liquid30000000_raw_20210101_20260622.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_round4_summary_round6_regime_all_liquid30000000_raw_20210101_20260622.csv`

Adjusted：

- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_round4_regime_round6_regime_all_liquid30000000_adj_20210101_20260622.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_round4_summary_round6_regime_all_liquid30000000_adj_20210101_20260622.csv`

本報告：

- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/magic26_round6_regime_gate_report_2026-06-22.md`
