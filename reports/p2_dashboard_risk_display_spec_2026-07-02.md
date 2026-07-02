# Magic26 P2-8 Dashboard 風險顯示層規格草案

日期：2026-07-02  
狀態：規格草案；未改 dashboard、未改資料產生、未部署。

## 一句話結論

P2-7 顯示：risk-veto 應該做成 **顯示層與排序提示**，不是刪除候選，也不是交易規則。

因此 Magic26 dashboard 未來若要改，只應做：

> 保留原始候選，新增 Level 0/1/2/3 風險分層、badge、白話提醒與排序降級。

不應做：

> 把 Level 0/1/2/3 當買賣訊號、直接刪候選、或改變原始策略產生邏輯。

## 依據

來源報告：

- `reports/p2_risk_veto_rules_draft_2026-07-02.md`
- `reports/p2_risk_veto_replay_2026-07-02.md`
- `reports/p2_risk_veto_replay_summary_2026-07-02.csv`

關鍵實證：

- Level 3 在 2026 holdout 明顯較弱：
  - strict L3：20D avg 3.9%，60D avg -8.8%
  - regime L3：20D avg -0.9%，60D avg -8.0%
- Level 2 仍有右尾：
  - strict L2：20D avg 25.4%，60D avg 64.2%
  - regime L2：20D avg 19.2%，60D avg 57.2%

解讀：

- Level 3 可以強烈降級。
- Level 2 不能刪，否則會錯殺右尾；只能標示「只觀察 / 不追價」。

## 顯示層原則

### 原則 1：不改訊號，只加風險解釋

原始候選仍由既有策略產生。

風險顯示層只新增：

- risk level
- risk badge
- risk reason
- sorting hint
- detail explanation

### 原則 2：不刪候選，只降級排序或語氣

Level 2/3 仍可出現在資料裡。

但在 UI 上：

- Level 2：主清單可保留，但應降級顯示「只觀察」。
- Level 3：建議移到 secondary / 風險觀察，不放主排序前段。

### 原則 3：禁止買訊語氣

任何 Level 都不能顯示：

- 買
- 進場
- 推薦
- 可買
- 勝率高所以可追

可使用：

- 可以研究
- 可看但不要追
- 只觀察
- 暫不追
- 等回檔或整理

## Level 顯示規格

### Level 0：正常候選 / 可以研究

條件摘要：

- `next_open_gap <= 1%`
- `signal_day_ret_1d <= 4%`
- `ret_20d <= 25%`
- 無低流動性風險

Badge：

```text
可以研究
```

卡片主文案：

```text
可以研究｜仍需看圖形與基本面
```

Detail 說明：

```text
追價風險目前不高，但這仍只是候選，不是買訊。
```

排序：

- 可維持主清單排序。
- 不額外降級。

### Level 1：追高警戒 / 可看但不要追

任一條件：

- `next_open_gap > 1%`
- `signal_day_ret_1d > 4%`
- `ret_20d > 25%`

Badge：

```text
不要追價
```

可加副 badge：

```text
追高警戒
```

卡片主文案：

```text
可看，但不要追價
```

Detail 說明：

```text
訊號仍有研究價值，但已有追價成本；等回檔或整理後再看。
```

排序：

- 可留在主清單。
- 同分時排在 Level 0 後面。

### Level 2：高追高 / 只觀察

任一條件：

- `next_open_gap > 3%`
- `signal_day_ret_1d > 9%`
- `ret_20d > 27%`
- 同時觸發兩個 Level 1 條件

Badge：

```text
只觀察
```

副 badge：

```text
高追高
```

卡片主文案：

```text
只觀察｜已偏追高
```

Detail 說明：

```text
這類樣本仍可能有右尾，但追價成本高；不適合直接追，等回檔、量縮整理或下一個低追價結構。
```

排序：

- 可保留在主清單，但排序降級。
- 若主清單很多檔，Level 2 排在 Level 0/1 後面。
- 不刪除，避免錯殺右尾。

### Level 3：暫不追 / 風險 veto

任一條件：

- `next_open_gap > 5%`
- `ret_20d > 40%`
- `signal_day_ret_1d > 9%` 且 `next_open_gap > 3%`
- 低流動性風險成立
- 注意/處置/漲跌停等交易限制成立（未來資料補齊）

Badge：

```text
暫不追
```

副 badge：

```text
風險 veto
```

卡片主文案：

```text
暫不追｜只保留研究紀錄
```

Detail 說明：

```text
這類樣本在回放中明顯較弱，且可能混入低流動性或極端追高；建議只保留紀錄，不放主排序前段。
```

排序：

- 不應排在主清單前段。
- 建議放到 secondary / 風險觀察。
- 仍不從資料中刪除。

## 卡片欄位建議

目前卡片可保留既有欄位：

- 代號 / 名稱
- 出訊號日期
- 分組
- 近 20 天漲幅
- 日均成交
- 隔日開盤
- 為什麼出現
- 要小心

新增顯示欄位：

```text
風險分層：Level 2｜只觀察
觸發原因：隔日開盤高 3.8%；近 20 天漲 25.3%
建議動作：不要追價，等回檔或整理後再研究
```

## Detail 區塊建議文案

新增一個「追高風險」小節：

```text
追高風險
這檔屬於 Level 2：高追高 / 只觀察。
原因：隔日開盤高於 3%，且近 20 天已漲超過 25%。
這不代表看壞，而是代表不適合直接追價。
```

## 6213 聯茂 UI 套用

6213 最新資料：

- `ret_20d`: 25.3%
- `signal_day_ret_1d`: 2.06%
- `next_open_gap`: 3.75%
- `risk_next_gap_gt3`: true

分級：

```text
Level 2：高追高 / 只觀察
```

主卡建議文案：

```text
6213 聯茂
只觀察｜已偏追高｜97分
出訊號：2026-06-26
A組主清單 / B組補看

為什麼出現
最近 20 天漲了 25.3%，近20日均成交 51.5億，所以進入候選。

要小心
隔天開盤高 3.8%，屬 Level 2 高追高；不要直接追價，等回檔或整理後再研究。
```

Detail 建議文案：

```text
追高風險
Level 2：高追高 / 只觀察。
觸發原因：next_open_gap > 3%，且 ret_20d > 25%。
這類樣本仍可能有右尾，但追價成本高；比較適合保留觀察，不適合隔日直接追。
```

## 排序規格草案

若未來要導入排序，建議採用：

```text
risk_level ASC
score DESC
signal_date DESC
avg_amount_20d DESC
```

解讀：

1. 先按風險等級排序，L0 優先。
2. 同風險等級內，再看原本分數。
3. 同分再看日期與成交金額。

注意：

- 這只是排序，不是刪除。
- Level 2/3 仍可被 filter 顯示。
- 應提供「全部風險」選項，避免隱藏資料。

## Filter 規格草案

新增 filter：

```text
全部風險
可以研究
不要追價
只觀察
暫不追
```

預設：

```text
全部風險
```

原因：

- 避免預設隱藏 Level 2/3，造成研究資料被看漏。
- 使用者可以自己切換。

## 不應做的事

1. 不應把 Level 0 顯示成「買」。
2. 不應把 Level 2/3 從資料中刪掉。
3. 不應改變原始 candidate 產生邏輯。
4. 不應用 risk-veto 回測結果包裝成交易績效。
5. 不應在未納入注意/處置/漲跌停資料前聲稱交易可行性完整。

## 實作前置條件

在真正改 UI 前，建議先補：

1. `risk_level` / `risk_label` / `risk_reasons` 到 export data。
2. package verifier 檢查 6213 是否正確顯示 Level 2。
3. browser QA：主卡、detail、filter、排序都正常。
4. 確認下載 CSV 保留原始數字與風險欄位。
5. 不改 K 線、不改原始 strategy score。

## 下一步建議

P2-9 可以做：**風險欄位資料輸出設計**。

只設計 data schema，不動 UI：

- `risk_level`
- `risk_label_zh`
- `risk_badges_zh`
- `risk_reasons_zh`
- `risk_sort_rank`
- `risk_action_hint_zh`

等 schema 穩定後，再決定是否進 P3 UI 實作。
