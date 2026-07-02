# Magic26 P2-2 中立擴樣本方案

日期：2026-07-02  
狀態：只讀分析，未改策略、未部署。

## 目的

在不破壞資料中立性的前提下，盡量擴大樣本數、提高統計確立性，並避免以下問題：

- 因為放寬條件而把樣本做大。
- 因為 raw / adjusted 混用而重複計數。
- 因為同一窗資料既調參又驗證而自證。
- 因為只看 2026 而忽略較長歷史。

## 先講結論

**對目前主策略家族，單純把時間往前拉，不會大幅增加樣本；真正中立的擴樣本方式，是使用同一資料管線下更廣的家族，並且分層報告，不混算。**

換句話說：

- 不建議：只靠放寬閾值或混算 raw/adjusted 來衝樣本。
- 建議：建立「嚴格家族 → 較廣家族 → regime 家族」的分層證據階梯。

## 已確認的資料範圍

### 目前主候選歷史

`magic26_candidates_history.csv`

- 312 筆
- 日期範圍：2023-02-01 ～ 2026-06-26
- unique dates：61
- raw / adjusted 幾乎各半
- 同一 `date-stock-candidate` 的 raw / adjusted 重複很常見

結論：

- 這條主候選歷史對「單一嚴格規則」來說，樣本還是偏少。
- 2021-2022 並沒有進入這條主候選歷史，單純往前拉時間對它幫助有限。

### 較廣的 core family：`core_repo40 / core_repo50 / core_repo60`

資料：`magic26_round7_param_grid_yearly_20210101_20260701.csv`

#### raw

| signal | total signals | n20 | n60 |
|---|---:|---:|---:|
| core_repo40_regime | 119 | 106 | 78 |
| core_repo50_regime | 93 | 81 | 58 |
| core_repo60_regime | 63 | 55 | 43 |

#### adj

| signal | total signals | n20 | n60 |
|---|---:|---:|---:|
| core_repo40_regime | 120 | 105 | 76 |
| core_repo50_regime | 91 | 78 | 54 |
| core_repo60_regime | 61 | 52 | 40 |

#### 年度分布示例：`core_repo50_regime`

- raw：
  - 2023：21 signals / 20 n20 / 20 n60
  - 2024：7 / 7 / 7
  - 2025：16 / 16 / 16
  - 2026：49 / 38 / 15
- adj：
  - 2023：16 / 15 / 15
  - 2024：7 / 7 / 7
  - 2025：17 / 17 / 17
  - 2026：51 / 39 / 15

觀察：

- 2021-2022 幾乎沒有 signal，因此單純延長時間不會顯著增樣本。
- 2023-2026 的樣本分布已比主候選歷史穩定。
- 但 2026 仍占比很高，表示年度偏態仍需做 walk-forward 驗證。

## 更廣的 regime family：`c1_c2 / c1_c2_c3_xq / magic26_v0`

資料：`magic26_round4_summary_round6_regime_all_liquid30000000_{raw,adj}_20210101_20260701.csv`

#### raw

| signal | total signals | n_excess_20d | n_excess_60d |
|---|---:|---:|---:|
| c1_c2 | 386 | 369 | 323 |
| c1_c2_c3_xq | 209 | 195 | 160 |
| magic26_v0 | 89 | 87 | 68 |
| magic26_v0_quality | 76 | 74 | 57 |

#### adj

| signal | total signals | n_excess_20d | n_excess_60d |
|---|---:|---:|---:|
| c1_c2 | 450 | 427 | 381 |
| c1_c2_c3_xq | 222 | 205 | 169 |
| magic26_v0 | 92 | 89 | 68 |
| magic26_v0_quality | 81 | 79 | 60 |

觀察：

- 這一層的樣本數明顯比主候選歷史大很多。
- 這是**自然擴樣本**的第一優先來源。
- 但它不是「同一條策略的更多資料」；它是更廣的同源家族，必須作為**獨立驗證層**，不能和主策略混成一個總結論。

## 最嚴謹的擴樣本方案

### 不建議的做法

1. 只為了拉大樣本就放寬主規則閾值。
2. raw / adjusted 不分層直接混算。
3. 同窗調參又同窗宣稱驗證成功。
4. 只看 2026 的最新樣本就下結論。

### 建議的做法

#### Layer 1：嚴格主家族

- 保留目前 dashboard 的主規則。
- 只做單獨報告，不和其他家族混算。
- 作為最保守候選清單。

#### Layer 2：同源較廣家族（core family）

- `core_repo40_regime`
- `core_repo50_regime`
- `core_repo60_regime`

用途：

- 檢查主規則方向是否在較廣設計下仍成立。
- 看 20D / 60D 統計是否同號、同方向。

#### Layer 3：更廣 regime family

- `c1_c2`
- `c1_c2_c3_xq`
- `magic26_v0`
- `magic26_v0_quality`

用途：

- 作為外部一致性檢查。
- 確認不是只在狹窄規則下有效。
- 不能直接當作主規則樣本併表。

## 統計上最重要的原則

### 1) 先分層，再比較，不要先混算

正確順序：

1. 分成嚴格家族 / core family / regime family。
2. 每層內先做 raw 與 adj 分開統計。
3. 再做 group-dedup（同股同日只算一次）。
4. 最後才比較跨層一致性。

### 2) 每層都做 out-of-time

建議最少用：

- 2023-2025：建規則 / 做選擇
- 2026：單獨 holdout

或至少做 rolling yearly validation。

### 3) 以成熟樣本為主

60D 尚未成熟的樣本要單獨列出，不可直接和成熟樣本混同。

### 4) 只看方向一致，不看單點最優

若不同家族、不同年份、不同口徑都同方向，才有資格說「策略方向可信」；
若只有某一小區間好看，通常只是噪音。

## 建議下一步實作順序

### Step A：產生一份「分層樣本總表」

欄位建議：

- family：strict / core / regime
- price_mode：raw / adj
- year
- signals
- n20
- n60
- avg20
- median20
- win20
- avg60
- median60
- win60
- 追高比例
- 高開比例
- 流動性風險比例

### Step B：對每個 family 做年度分層

看 2023 / 2024 / 2025 / 2026 是否一致。

### Step C：再做 group-dedup 版

同一 stock + 同一 date + 同一 family 只算一次。

### Step D：只把通過一致性檢驗的家族留在 dashboard

- 主 dashboard 保留嚴格家族。
- 更廣 family 只作 secondary validation，不作主排序。

## 對目前策略的實務建議

- **現在先不要把主規則放寬只為了增樣本。**
- **可以擴的，是驗證層，不是主規則。**
- 如果未來要提升統計確立性，應該先讓 broader family 先通過 out-of-time，再考慮是否把其中一部分納入主清單。

## 結論

最嚴謹的擴樣本方式不是「把規則弄鬆」，而是：

> 用同源更廣家族做獨立驗證，保留嚴格主規則不動，並且 raw/adjusted / year / family 三層分開。

這樣才能在擴樣本的同時，盡量保持資料中立。
