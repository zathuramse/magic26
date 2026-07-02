# Magic26 P2-1 訊號與策略可信度審計

日期：2026-07-02
範圍：只讀審計；未修改 dashboard 訊號邏輯，未部署。
資料版本：`public/data`，dashboard `https://magic26.pages.dev/?v=20260701y`。

## 一句話結論

Magic26 目前可以作為「人工研究候選排序」，但**不能視為買訊或可直接交易的策略**。最大問題不是 UI，而是：樣本小、訊號偏追高、raw/adjusted 口徑需要嚴格拆開、A/B/C 與 risk tags 可能有事後分類/自證風險。

## 審計方式

本次使用三路交叉：

1. 主線本地程式統計 `summary.json`、`all_signal_groups.json`、`latest_signal_groups.json`、`magic26_candidates_history.csv`、round8/14/20 summary。
2. 隔離 Agent A：資料/統計審計，專查資料口徑、重複、集中度、樣本與 bootstrap/grid 疑義。
3. 隔離 Agent B：策略/交易邏輯審計，專查追高、look-ahead、自證、交易可行性與最新 6213。

兩個 agent 不依賴主線結論，皆為只讀分析。

## 主線量化摘錄

### 基本狀態

- `data_through`: 2026-06-30
- `latest_signal_date`: 2026-06-26
- `latest_signal_groups`: 1
- `total_candidate_rows`: 312
- `all_signal_groups`: 75
- `latest_signal_groups`: 1

### raw / adjusted 口徑

`magic26_candidates_history.csv`：

- 總列數：312
- `raw`: 159
- `adjusted`: 153
- `date-stock-candidate` unique keys：169
- 同一 `date-stock-candidate` 同時有 raw/adjusted：143

解讀：raw/adjusted 並列本身不一定錯，但任何統計若未明確分層或去重，都可能雙重計數或混算。

### 訊號集中度

`all_signal_groups.json` 共 75 筆。

產業集中：

- 電子零組件業：18
- 電子工業：10
- 通信網路業：9
- 半導體業：4
- 電機機械：4

日期集中：

- 2026-04-17：4
- 2026-04-14：4
- 2026-04-15：3
- 2026-05-14：2
- 2026-04-16：2

股票集中前幾名：

- 3163：3
- 4979：2
- 3443：2
- 5292：2
- 6213：1

解讀：樣本偏電子/科技與特定日期，不適合宣稱泛化到全市場。

### 追高相關指標

在 75 筆 signal groups 中：

- `signal_day_ret_1d`
  - n=75
  - 平均：4.79%
  - 中位數：4.01%
  - >3%：44 筆
  - >9%：21 筆

- `ret_20d`（訊號前 20 日表現，不是未來 20 日）
  - n=75
  - 平均：22.77%
  - 中位數：24.11%
  - >9%：68 筆

- `next_open_gap`
  - n=75
  - 平均：0.96%
  - 中位數：0.46%
  - >3%：13 筆
  - >9%：1 筆

解讀：這個策略明顯是在找已經有動能的股票；作為 momentum candidate 可以，但作為「早期訊號」證據不足。大量訊號日已有明顯上漲，next-open 執行需特別保守。

### Forward 表現成熟度

- `t1_open_excess_20d`
  - n=72
  - 平均：11.69%
  - 中位數：9.66%
  - 勝率：61.1%

- `t1_open_excess_60d`
  - n=51
  - 平均：11.42%
  - 中位數：3.15%
  - 勝率：52.9%

解讀：20D 結果偏正，但 60D 勝率接近五五波；且 60D 成熟樣本只有 51 筆，不能過度解讀。

## 最新 6213 聯茂訊號審計

最新訊號：

- 股票：6213 聯茂
- 訊號日：2026-06-26
- `ret_20d`: 25.32%
- `signal_day_ret_1d`: 2.06%
- `next_open_gap`: 3.75%
- `risk_next_gap_gt3`: true
- `research_priority_zh`: 中優先-有交易風險
- `avg_amount_20d`: 約 51.5 億
- `t1_open_excess_20d`: null
- `t1_open_excess_60d`: null

結論：6213 可以當研究候選，但不應當直接買訊。它已經有 20 日上漲 25% 與隔日開盤 +3.75% 的追價成本；最新訊號的 20D/60D forward outcome 尚未成熟。

## 高風險疑點

1. **raw / adjusted 口徑混用風險**
   - 大量同一 date-stock-candidate 同時存在 raw/adjusted。
   - UI 合併是好的，但回測/摘要必須保證分層或去重。

2. **訊號偏追高，不是明確早期訊號**
   - 訊號日 1D 平均 +4.79%，75 筆中 44 筆 >3%。
   - 訊號前 20 日平均 +22.77%。

3. **小樣本 + 多輪分組/規則優化，有自證風險**
   - `all_signal_groups` 只有 75。
   - round14 bootstrap baseline 約 43/48；round20 60D baseline 約 28。
   - 在這種樣本下做 A/B/C、volgap、ret60 cap、rescue 等分組，很容易過擬合。

4. **Forward-looking 欄位與特徵欄位同表共存**
   - `t1_open_excess_20d/60d` 等欄位本身可作 outcome，但若未嚴格隔離，會有 label leakage 風險。

5. **交易可行性不足**
   - 未完整驗證漲停/鎖死、注意/處置股、開盤可成交量、滑價與實際 next-open 可執行性。

## 中風險疑點

1. 產業偏電子/科技，泛化性不足。
2. A/B/C 可能不是獨立訊號，而是同一動能樣本的不同包裝。
3. Risk tags 有用，但目前更像提醒/事後分類，不足以證明能改善實際交易績效。
4. 60D 成熟樣本不足，可能有成熟樣本偏誤。
5. 最新資料到 2026-06-30，但最新訊號在 2026-06-26；需要確認這是無訊號還是資料/掃描節奏造成。

## 通過或部分通過的檢查

1. `ret_20d` 經 Agent B 抽查 6213 K 線，確認是訊號前 20 日表現，不是未來報酬；這點不構成直接 look-ahead。
2. UI 現在有明確標示「可看，但先查風險」與「不要直接追價」，沒有把 6213 包裝成買訊。
3. 6213 流動性不差，20 日均成交約 51.5 億，並非低流動性標的。
4. 風險標籤能抓到 6213 的隔日高開問題，`risk_next_gap_gt3=true`。
5. round14 bootstrap 有呈現不確定性：p05 仍可能為負，沒有完全粉飾成鐵證。

## 最少需要的下一步驗證

1. **raw / adjusted 全流程分層重算**
   - 分別用 raw、adjusted、以及 date-stock 去重後的 group-level 版本重算核心統計。

2. **walk-forward / out-of-time 驗證**
   - 例如 2021-2024 設規則、2025-2026 只驗證；或 rolling yearly validation。
   - 禁止同窗調參又同窗宣稱效果。

3. **追高分位測試**
   - 按 `signal_day_ret_1d`、`next_open_gap`、`ret_20d`、`range_pos` 分位分組。
   - 檢查高追高區是否顯著劣化。

4. **A/B/C 與 risk tag 消融測試**
   - 不用 A/B/C 分組，績效是否還在？
   - 不用 risk tags，排序或篩選是否真的變差？

5. **真實交易可行性測試**
   - next-open + 滑價敏感度。
   - 高開 >3% 是否 veto 或等待回測更好。
   - 注意股/處置股/漲跌停/可成交量納入。

## 建議暫定策略定位

目前 Magic26 應定位為：

> 動能研究候選清單 / pull dashboard，不是交易訊號，也不是自動進出場策略。

最新 6213 應定位為：

> 有動能、有成交、有研究價值，但已偏追高；只能列入觀察，等待更好的進場結構或回測確認。

## 建議 P2 下一段

建議做 `P2-2 raw/adjusted 去重與口徑重算`：

- 產生三套統計：raw-only、adjusted-only、group-dedup。
- 比較 20D/60D outcome 是否穩定。
- 若三者差異大，先修研究口徑，不再美化 UI。
