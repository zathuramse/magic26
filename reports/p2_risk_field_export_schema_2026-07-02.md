# Magic26 P2-9 風險欄位資料輸出設計

日期：2026-07-02
狀態：schema 規格草案；未改 export、未改 dashboard、未部署。

## 一句話結論

Magic26 未來若要把 P2 risk-veto 納入 dashboard，應先新增一組 **v2 風險顯示欄位**，不要覆蓋既有 `risk_badge_zh` / `risk_reason` / `priority_reason`。

原因：

- 既有欄位已被 UI 與資料下載使用。
- P2 risk-veto 是新一層「追高風險顯示」語意。
- 直接覆蓋會混淆舊風險標籤、量能風險、長均線風險與追高 risk-veto。

## 目前既有風險欄位

目前 `latest_signal_groups.json` / `all_signal_groups.json` 已有：

- `risk_signal_day_gt9`
- `risk_next_gap_gt3`
- `risk_liquidity_lt100m`
- `is_high_open_risk`
- `is_low_liquidity_risk`
- `research_priority_zh`
- `research_tags`
- `volume_gap_risk_zh`
- `risk_daily_long_ma_bear`
- `risk_weekly_long_ma_bear`
- `risk_any_long_ma_bear`
- `risk_long_ma_score`
- `risk_badge_zh`
- `risk_reason`
- `priority_reason`

6213 目前樣本：

```json
{
  "risk_next_gap_gt3": true,
  "is_high_open_risk": true,
  "research_priority_zh": "中優先-有交易風險",
  "research_tags": "主規格;floor15觀察;高開風險",
  "risk_badge_zh": "研究中",
  "risk_reason": "隔日開盤高 3.8%，可能有追高風險",
  "priority_reason": "可看，但先查風險"
}
```

## 新增欄位命名原則

為避免污染既有欄位，建議新增前綴：

```text
risk_v2_*
```

理由：

- 清楚表示這是 P2 後的新風險顯示層。
- 舊 UI 可以繼續使用舊欄位。
- 新 UI 可逐步切換。
- 下載 CSV 可同時保留舊欄位與新欄位，方便比對。

## 建議新增欄位

### 1. `risk_v2_level`

型別：integer
允許值：0 / 1 / 2 / 3
必填：是

語意：

- 0：正常候選 / 可以研究
- 1：追高警戒 / 可看但不要追
- 2：高追高 / 只觀察
- 3：暫不追 / 風險 veto

排序：數字越小，風險越低。

範例：

```json
"risk_v2_level": 2
```

### 2. `risk_v2_label_zh`

型別：string
必填：是

允許值：

```text
正常候選 / 可以研究
追高警戒 / 可看但不要追
高追高 / 只觀察
暫不追 / 風險 veto
```

範例：

```json
"risk_v2_label_zh": "高追高 / 只觀察"
```

### 3. `risk_v2_primary_badge_zh`

型別：string
必填：是

允許值：

```text
可以研究
不要追價
只觀察
暫不追
```

用途：主卡第一個風險 badge。

範例：

```json
"risk_v2_primary_badge_zh": "只觀察"
```

### 4. `risk_v2_badges_zh`

型別：array of string in JSON；CSV 版本用 `;` 分隔
必填：是，可為空陣列

用途：卡片或 detail 顯示的輔助 badge。

建議 badge 值：

```text
可以研究
不要追價
追高警戒
只觀察
高追高
暫不追
風險 veto
開高風險
漲幅已大
低流動性
```

範例 JSON：

```json
"risk_v2_badges_zh": ["只觀察", "高追高", "開高風險", "漲幅已大"]
```

CSV 範例：

```text
只觀察;高追高;開高風險;漲幅已大
```

### 5. `risk_v2_reasons_zh`

型別：array of string in JSON；CSV 版本用 `;` 分隔
必填：是，可為空陣列

用途：可審計的觸發原因，不要只放一句概括。

範例 JSON：

```json
"risk_v2_reasons_zh": [
  "隔日開盤高 3.8%，超過 3% 高追高門檻",
  "近 20 天已漲 25.3%，接近追高警戒區"
]
```

CSV 範例：

```text
隔日開盤高 3.8%，超過 3% 高追高門檻;近 20 天已漲 25.3%，接近追高警戒區
```

### 6. `risk_v2_action_hint_zh`

型別：string
必填：是

允許值建議：

```text
可以研究；仍需看圖形與基本面
可看，但不要追價；等回檔或整理後再研究
只觀察；已偏追高，不建議直接追價
暫不追；只保留研究紀錄
```

範例：

```json
"risk_v2_action_hint_zh": "只觀察；已偏追高，不建議直接追價"
```

### 7. `risk_v2_sort_rank`

型別：integer
必填：是

建議：

```text
risk_v2_sort_rank = risk_v2_level
```

保留獨立欄位的原因：未來若排序規則需要微調，不必改 level 語意。

範例：

```json
"risk_v2_sort_rank": 2
```

### 8. `risk_v2_rule_version`

型別：string
必填：是

建議值：

```text
p2_2026_07_02
```

用途：讓未來資料下載可追溯規則版本。

範例：

```json
"risk_v2_rule_version": "p2_2026_07_02"
```

### 9. `risk_v2_is_display_only`

型別：boolean
必填：是

固定值：

```json
true
```

用途：避免被誤解成交易訊號或策略產生條件。

## 6213 完整 JSON 範例

```json
{
  "stock_id": "6213",
  "stock_name": "聯茂",
  "date": "2026-06-26",
  "ret_20d": 0.2531645569620253,
  "signal_day_ret_1d": 0.0206185567010308,
  "next_open_gap": 0.0375180375180375,
  "risk_v2_level": 2,
  "risk_v2_label_zh": "高追高 / 只觀察",
  "risk_v2_primary_badge_zh": "只觀察",
  "risk_v2_badges_zh": ["只觀察", "高追高", "開高風險", "漲幅已大"],
  "risk_v2_reasons_zh": [
    "隔日開盤高 3.8%，超過 3% 高追高門檻",
    "近 20 天已漲 25.3%，接近追高警戒區"
  ],
  "risk_v2_action_hint_zh": "只觀察；已偏追高，不建議直接追價",
  "risk_v2_sort_rank": 2,
  "risk_v2_rule_version": "p2_2026_07_02",
  "risk_v2_is_display_only": true
}
```

## CSV 欄位建議

JSON array 欄位在 CSV 中用 `;` 分隔。

新增欄位：

```text
risk_v2_level
risk_v2_label_zh
risk_v2_primary_badge_zh
risk_v2_badges_zh
risk_v2_reasons_zh
risk_v2_action_hint_zh
risk_v2_sort_rank
risk_v2_rule_version
risk_v2_is_display_only
```

6213 CSV 範例：

```text
risk_v2_level,2
risk_v2_label_zh,高追高 / 只觀察
risk_v2_primary_badge_zh,只觀察
risk_v2_badges_zh,只觀察;高追高;開高風險;漲幅已大
risk_v2_reasons_zh,隔日開盤高 3.8%，超過 3% 高追高門檻;近 20 天已漲 25.3%，接近追高警戒區
risk_v2_action_hint_zh,只觀察；已偏追高，不建議直接追價
risk_v2_sort_rank,2
risk_v2_rule_version,p2_2026_07_02
risk_v2_is_display_only,True
```

## 計算規則草案

### Level 3：暫不追 / 風險 veto

任一條件：

- `next_open_gap > 0.05`
- `ret_20d > 0.40`
- `signal_day_ret_1d > 0.09` 且 `next_open_gap > 0.03`
- `risk_liquidity_lt100m == true`
- 未來：注意/處置/漲跌停限制成立

### Level 2：高追高 / 只觀察

任一條件：

- `next_open_gap > 0.03`
- `signal_day_ret_1d > 0.09`
- `ret_20d > 0.27`
- Level 1 條件同時觸發兩項以上

### Level 1：追高警戒 / 可看但不要追

任一條件：

- `next_open_gap > 0.01`
- `signal_day_ret_1d > 0.04`
- `ret_20d > 0.25`

### Level 0：正常候選 / 可以研究

未觸發 Level 1/2/3。

## 驗證規則

實作 export 前，應新增 verifier 檢查：

1. 所有 `latest_signal_groups.json` rows 都有 `risk_v2_*` 欄位。
2. 所有 `all_signal_groups.json` rows 都有 `risk_v2_*` 欄位。
3. 所有下載 CSV 都保留 `risk_v2_*` 欄位。
4. `risk_v2_level` 僅允許 0/1/2/3。
5. `risk_v2_sort_rank` 是 integer。
6. `risk_v2_is_display_only` 固定為 true。
7. 6213 應為：

```text
risk_v2_level = 2
risk_v2_primary_badge_zh = 只觀察
risk_v2_label_zh = 高追高 / 只觀察
risk_v2_action_hint_zh 包含 不建議直接追價
```

## 與既有欄位的關係

### 不取代

新欄位不取代：

- `risk_badge_zh`
- `risk_reason`
- `priority_reason`
- `research_priority_zh`
- `research_tags`

### 可供 UI 新版優先使用

未來 UI 若導入 P2 顯示層，可優先讀：

```text
risk_v2_primary_badge_zh
risk_v2_action_hint_zh
risk_v2_reasons_zh
risk_v2_sort_rank
```

但舊欄位應繼續保留在 detail 或下載檔。

## 非目標

P2-9 不做：

1. 不改 `export_dashboard_data.py`。
2. 不改 `app.js`。
3. 不改 `index.html`。
4. 不改候選產生邏輯。
5. 不改 strategy score。
6. 不部署。

## 下一步建議

P2-10 可以做：**風險欄位 export dry-run**。

只產出臨時檔或報告，不覆蓋 production data：

- 用現有 `all_signal_groups.json` 產生一份 dry-run JSON。
- 驗證 6213 Level 2。
- 比較新增欄位前後 row count 不變。
- 檢查 CSV array 欄位分隔格式。

P2-10 通過後，才考慮進入 P3：正式改 export + UI。
