# 魔26 v0 第九輪：收盤確認式出場測試

日期：2026-06-22  
狀態：完成。研究用途；不是交易建議。

## 本輪目的

第八輪確認：Magic26 主候選不是「大多數買不到」，而是「高波動、容易被日內停損洗掉」。因此第九輪不再測日內 high/low 觸價停損，而是測收盤確認式出場。

本輪測：

- 固定 20D 出場：`fixed20`
- 收盤跌破 entry -8%：`close_sl8`
- 持有 3 天後才啟動收盤 -8%：`delayed3_close_sl8`
- 收盤跌破 MA5 / MA10：`close_below_ma5`、`close_below_ma10`
- 持有 3 天後才啟動 MA5 / MA10：`delayed3_close_below_ma5`、`delayed3_close_below_ma10`
- 持有 3 天後 MA10 或收盤 -8% 任一觸發：`delayed3_ma10_or_sl8`

Entry 全部固定為：

```text
t+1 open
```

變動出場以當日收盤價出場。Excess 使用同 entry/exit 日期的 TAIEX open-to-close 報酬扣除。

## 實作

新增腳本：

`C:/Users/abckf/research-brain/tools/magic26_round9_close_exit_checks.py`

輸出：

- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_round9_close_exit_summary_20210101_20260622.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_round9_close_exit_detail_20210101_20260622.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_round9_close_exit_yearly_20210101_20260622.csv`
- `C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/magic26_round9_close_exit_manifest_20210101_20260622.json`

驗證：

```bash
python -m py_compile C:/Users/abckf/research-brain/tools/magic26_round9_close_exit_checks.py
python C:/Users/abckf/research-brain/tools/magic26_round9_close_exit_checks.py
```

已跑完，run log 無 warning / traceback / error。

## 核心結論

最重要的結論很直接：

> 固定 20D 出場仍然最好。所有收盤確認式提早出場，都降低整體表現。

這代表目前不是「缺一個簡單停損」的問題。Magic26 主候選真正的優勢來自：

- 高波動；
- 大 MFE；
- 需要時間讓動能展開；
- 太早出場會把贏家砍掉。

## Candidate A：主觀察策略

`candidate_a_repo50_c440_c5gt5`

### Fixed20

Raw：

- trades：50
- median return：+16.45%
- win return：72.00%
- median excess：+11.76%
- win excess：70.00%
- hold：21 bars

Adjusted：

- trades：46
- median return：+13.60%
- win return：69.57%
- median excess：+9.66%
- win excess：65.22%
- hold：21 bars

### Delayed3 close SL8

Raw：

- median return：+8.51%
- median excess：+3.81%
- win excess：52.00%
- avg hold：15.64 bars
- exit before 20D：40.00%

Adjusted：

- median return：-4.13%
- median excess：-4.36%
- win excess：45.65%
- avg hold：14.85 bars
- exit before 20D：45.65%

判讀：比日內硬停損溫和，但 adjusted 仍失敗。不採用。

### Delayed3 close below MA5

Raw：

- median return：+0.94%
- median excess：+0.97%
- win excess：54.00%
- avg hold：7.26 bars
- exit before 20D：100%

Adjusted：

- median return：-1.42%
- median excess：-2.27%
- win excess：47.83%
- avg hold：7.26 bars

判讀：能減少 2024 某些傷害，但太早出場，整體吃不到主升段。

### Delayed3 close below MA10 / MA10 or SL8

Raw：

- median excess：約 -3.17%
- win excess：48.00%
- avg hold：約 10.6 bars

Adjusted：

- median excess：約 -3.69%
- win excess：41.30%
- avg hold：約 10 bars

判讀：MA10 類出場也太早，且沒有改善 adjusted。

## Candidate B：寬主版

`candidate_b_magic_c440_c5gt5`

Fixed20 仍最好：

Raw：

- median excess：+9.66%
- win excess：62.86%

Adjusted：

- median excess：+7.43%
- win excess：59.70%

其他提早出場多數 median excess 轉負或接近 0：

- delayed3 MA5 raw median excess：+0.33%，adjusted -2.71%
- delayed3 SL8 raw -1.47%，adjusted -4.14%
- delayed3 MA10 raw/adjusted 約 -3%

判讀：寬主版也不適合簡單收盤停損/均線出場。

## Candidate C：高濃度觀察組

`candidate_c_high_concentration_c425_c5gt5`

Fixed20 仍最好：

Raw：

- median excess：+13.03%
- win excess：66.67%

Adjusted：

- median excess：+12.08%
- win excess：64.86%

比較接近可用的提早出場只有 `delayed3_close_sl8`：

Raw：

- median excess：+3.50%
- win excess：53.85%

Adjusted：

- median excess：+3.03%
- win excess：51.35%

但這仍遠輸 fixed20。

判讀：Candidate C 更乾淨，但也需要持有，不適合太早出場。

## 2024：提早出場有局部改善，但整體不值得

Candidate A 的 2024 raw：

### Fixed20

- trades：6
- median excess：-8.41%
- win excess：33.33%

### Delayed3 close below MA5

- median excess：-3.95%
- win excess：33.33%
- avg hold：6.67 bars

### Delayed3 close below MA10 / MA10 or SL8

- median excess：-5.63%
- win excess：33.33%
- avg hold：7.67 bars

局部來看，MA5 / MA10 出場確實讓 2024 median loss 變小。但代價是：

- 2023 / 2026 的大贏家被提早砍掉；
- 全樣本 median excess 大幅下降；
- adjusted 結果轉弱。

所以不能為了修 2024 而犧牲整體策略邏輯。

## 2024 個案觀察

Candidate A raw 2024 裡有一筆大贏家：

- `6419 京晨科`
  - fixed20 return：+94.11%
  - fixed20 excess：+88.95%
  - delayed3 MA5 exit：+79.38%，仍保留大部分利潤
  - delayed3 MA10 exit：+73.36%

但失敗股像：

- `6231 系微`
  - fixed20 excess：-13.84%
  - delayed3 SL8 / MA5 / MA10 都在 day4 出，excess 約 -7.56%，有改善。

- `8147 正淩`
  - fixed20 excess：-9.25%
  - delayed3 MA5 在 day4 出，excess +4.23%，有明顯改善。

這表示：

> 均線出場可以救某些假突破，但會系統性降低整體勝率與中位數。它像風控工具，不像 alpha-enhancing exit。

## 第九輪研究決策

### 1. 目前主規格仍維持 fixed20

不要因為 2024 幾筆失敗，就把出場改成 MA5 / MA10 / SL8。

目前主規格：

```text
Candidate A + fixed20
```

也就是：

```text
regime_all3=True
C1+C2+C3
repo_vol5 >= 50%
0 < 20D return < 40%
days_since_max_volume > 5
t+1 open entry
20D fixed close exit
```

### 2. Close exits 暫時降級為風控觀察

可保留觀察：

- `delayed3_close_below_ma5`
- `delayed3_close_sl8`

但不升主規格。

### 3. 不採用 MA10 出場

MA10 或 MA10+SL8 在本輪表現不佳：

- 出太早；
- excess median 多為負；
- adjusted 更弱。

### 4. 下一步不是再測出場，而是做候選清單化

第九輪已經確認：簡單 exit rule 沒有改善主結果。

下一輪應該把 Candidate A 固化成「每日候選清單/研究儀表板」規格，而不是繼續過擬合。

## 下一輪建議

第十輪建議做「拉取式研究清單」：

1. 用最新資料產生 Candidate A 候選清單。
2. 每檔列出：
   - signal date
   - regime 狀態
   - repo_vol5 ratio
   - 20D ret
   - days_since_max_volume
   - signal-day return
   - next-open gap，如果已有隔日資料
   - liquidity
   - industry
3. 加上風險標籤：
   - 接近漲停
   - 高 gap
   - 低流動性
   - 高波動候選
4. 產出 CSV / Markdown / HTML，不推播，只做 pull dashboard。

目前判斷：

> 魔26研究已經足夠形成「候選清單工具」，但還不足以自動交易。下一步應該產品化成研究看板，而不是繼續找更漂亮的回測參數。
