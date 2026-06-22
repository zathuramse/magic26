# 魔26 v0 第八輪：交易化檢查、MFE/MAE、簡化停利停損、2024敗因切片

日期：2026-06-22  
狀態：完成交易化檢查。研究用途；不是交易建議。

## 本輪目的

第七輪已經把主候選收斂到：

1. Candidate A：`magic_repo50_c440_c5gt5_regime`
2. Candidate B：`magic_c440_c5gt5_regime`
3. Candidate C：`magic_c425_c5gt5_regime`，高濃度觀察組

第八輪不再加參數，而是檢查「能不能真的交易」：

- 訊號日是否太容易接近漲停？
- 隔日開盤 gap 是否過高？
- 20D 期間最大有利/不利波動如何？
- 簡化停利停損是否改善？
- 2024 負貢獻集中在哪裡？

## 實作

新增腳本：

`C:/Users/abckf/research-brain/tools/magic26_round8_tradeability_checks.py`

輸入：

- round6 raw checked signals
- round6 adjusted checked signals
- round1~7 期間的 raw/adjusted price cache parquet

輸出：

- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_round8_tradeability_summary_20210101_20260622.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_round8_tradeability_detail_20210101_20260622.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_round8_tradeability_2024_failures_by_industry_20210101_20260622.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_round8_tradeability_manifest_20210101_20260622.json`

驗證：

```bash
python -m py_compile C:/Users/abckf/research-brain/tools/magic26_round8_tradeability_checks.py
python C:/Users/abckf/research-brain/tools/magic26_round8_tradeability_checks.py
```

已跑完；最後一次 run log 無 warning / traceback / error。

## 重要假設

### Entry

使用隔日開盤：

```text
t+1 open
```

### 固定出場

固定 20 個交易日後收盤出場。

### MFE / MAE

從 entry day 到 exit20 day，使用日高低估算：

- MFE：20D 期間最大浮盈
- MAE：20D 期間最大浮虧

### 停利停損模擬

測：

- TP15 / SL8
- TP20 / SL8
- SL8 only
- TP20 only

若同一天 high / low 同時碰到停利與停損，採保守假設：

```text
先停損
```

這會低估 bracket 策略，但比較安全。

### 漲停可交易性

目前沒有逐筆或官方鎖漲停資料，所以只做近似：

- signal-day return >= 9%：接近漲停風險
- next-open gap > 3% / 5% / 7%：隔日追價風險

## Candidate A：主觀察策略

規格：

```text
regime_all3=True
C1+C2+C3
repo_vol5 >= 50%
0 < 20D return < 40%
days_since_max_volume > 5
```

有效 20D path 樣本：

- raw：50
- adjusted：46

### 固定 20D 出場

Raw：

- t+1 open 20D excess median：+11.76%
- t+1 open 20D excess win：70.00%
- fixed20 raw return median：+16.45%
- fixed20 raw return win：72.00%

Adjusted：

- t+1 open 20D excess median：+9.66%
- t+1 open 20D excess win：65.22%
- fixed20 raw return median：+13.60%
- fixed20 raw return win：69.57%

判讀：固定 20D 還是目前最乾淨，不需要急著加停損停利。

### 交易摩擦 / 追價風險

Raw：

- signal-day >= 9%：26.00%
- next-open gap > 3%：12.00%
- next-open gap > 5%：6.00%
- next-open gap > 7%：2.00%

Adjusted：

- signal-day >= 9%：26.09%
- next-open gap > 3%：10.87%
- next-open gap > 5%：4.35%
- next-open gap > 7%：2.17%

判讀：

- 約四分之一訊號已接近漲停，這是實戰追價風險。
- 但隔日開盤 gap > 5% 比例只有約 4%~6%，沒有嚴重到完全不可交易。

### MFE / MAE

Raw：

- median MFE：+28.18%
- median MAE：-8.68%
- 20D 內 MAE <= -8%：50.00%
- 20D 內 MFE >= 15%：72.00%
- 20D 內 MFE >= 20%：68.00%

Adjusted：

- median MFE：+26.59%
- median MAE：-10.44%
- 20D 內 MAE <= -8%：58.70%
- 20D 內 MFE >= 15%：71.74%
- 20D 內 MFE >= 20%：65.22%

判讀：

這不是低波動策略。它常常有很大的上行空間，但 20D 內也常有 -8% 以上回撤。

### 停利停損結果

Raw：

- TP15 / SL8 median：+11.73%，win 52.00%
- TP20 / SL8 median：+10.59%，win 52.00%

Adjusted：

- TP15 / SL8 median：-8.00%，win 43.48%
- TP20 / SL8 median：-8.00%，win 43.48%

為什麼 adjusted 變差？因為 conservative daily-bar assumption 下，只要同日高低都碰到，先算停損。這對高波動股很嚴格。

判讀：

- 目前不建議直接加入硬 SL8 bracket。
- 這組訊號的波動很大，太早停損會吃掉後續反彈/續漲。
- 若要停損，下一輪應測「收盤跌破」或「持有 N 天後才啟動停損」，而不是日內 low 觸價停損。

## Candidate B：寬主版 Magic26 v0

有效 20D path 樣本：

- raw：70
- adjusted：67

Raw：

- t+1 open 20D excess median：+9.66%
- win：62.86%
- fixed20 raw return median：+11.90%
- median MFE：+25.10%
- median MAE：-7.74%
- signal-day >= 9%：28.57%
- next-open gap > 5%：8.57%

Adjusted：

- t+1 open 20D excess median：+7.43%
- win：59.70%
- fixed20 raw return median：+10.55%
- median MFE：+23.78%
- median MAE：-10.09%
- signal-day >= 9%：28.36%
- next-open gap > 5%：7.46%

判讀：

- 樣本較多，但品質低於 Candidate A。
- 追價風險略高。
- 作為寬基準仍合理。

## Candidate C：高濃度觀察組 C4 25

有效 20D path 樣本：

- raw：39
- adjusted：37

Raw：

- t+1 open 20D excess median：+13.03%
- win：66.67%
- fixed20 raw return median：+18.56%
- median MFE：+27.68%
- median MAE：-6.22%
- signal-day >= 9%：15.38%
- next-open gap > 7%：0%

Adjusted：

- t+1 open 20D excess median：+12.08%
- win：64.86%
- fixed20 raw return median：+15.36%
- median MFE：+27.68%
- median MAE：-7.82%
- signal-day >= 9%：16.22%
- next-open gap > 7%：0%

判讀：

這組反而最不追高，MFE/MAE 也漂亮。但它樣本少、年度仍不穩。可升為「低追價高濃度觀察」，但還不是主策略。

## 2024 敗因切片

Candidate A raw 2024 負貢獻只有 4 筆：

- `6231 系微`，資訊服務業，20D excess -13.84%，MAE -22.26%
- `8147 正淩`，電子零組件業，20D excess -9.25%，MAE -29.05%
- `6535 順藥`，生技醫療業，20D excess -8.99%，MAE -12.55%
- `3234 光環`，通信網路業，20D excess -7.83%，MAE -10.10%

這 4 筆共同特徵：

- 不是隔日高 gap 造成，next-open gap 都是負的或接近 0。
- 不是訊號日漲停追價造成，signal-day return 都不高。
- 主要問題是訊號後快速回撤，且多數 hit SL8。

所以 2024 的問題不是「買不到」或「隔日開太高」，而是：

> regime_all3 仍會放過某些假突破，進場後很快失敗。

## 第八輪研究決策

### 保留 Candidate A 作主觀察

`candidate_a_repo50_c440_c5gt5`

理由：

- 20D excess / fixed return 都強。
- 隔日高 gap 風險可接受。
- 樣本比 C 組多。

但加註：

- 它不是低波動策略。
- 20D 內 hit -8% MAE 的比例約 50%~59%。

### 保留 Candidate B 作寬基準

`candidate_b_magic_c440_c5gt5`

理由：

- 樣本多。
- 表現穩定但品質低於 A。

### Candidate C 可升為「低追價觀察組」

`candidate_c_high_concentration_c425_c5gt5`

理由：

- signal-day >=9% 比例較低。
- next-open gap >7% 為 0。
- fixed20 median 很高。

限制：

- 樣本太少。
- 年度不穩問題仍在。

### 暫不採用硬停損停利

尤其是 `TP15/SL8`、`TP20/SL8`：

- raw 看起來尚可。
- adjusted 在保守日內路徑假設下變差。
- 不應直接改成 bracket rule。

## 下一輪建議

第九輪應該測「失敗確認」而不是硬停損：

1. 收盤跌破 5MA / 10MA 出場
2. 進場後至少持有 3 天，再啟動停損
3. 收盤跌破 entry -8%，而不是日內 low 觸價
4. 2024 四筆失敗個案逐檔圖形化/路徑檢查

目前最重要的結論：

> 魔26主候選不是買不到，而是高波動。硬日內停損會太容易把好訊號洗掉；下一步應測「收盤確認式出場」。
