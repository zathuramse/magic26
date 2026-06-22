# XQ-Lazy-pack1 repo triage for Magic26 validation

日期：2026-06-22  
Repo：`https://github.com/shibainvesttravel/XQ-Lazy-pack1`  
處理方式：只做研究抽取與可驗證條件重建；不採用為商業用途、不包裝轉售、不視為交易建議。

## Repo 結構

Repo 以分支作為策略分類，而不是單一 main 目錄：

- `main`：只有 README / 授權與免責。
- `魔字4號`
- `魔字21號`
- `魔字24號`
- `魔字26號`
- `魔字27號`
- `魔字28號`

已把原始檔備份到：

`C:/Users/abckf/research-brain/sources/strategy-checks/magic26/repo_xq_lazy_pack1_raw/`

## 對 Magic26 最重要的發現

### 1. Magic26 原始 C3 不是單純 run length，但目前 proxy 等價度很高

Repo `魔字26號/短日均發散多頭排列介於幾天.xs`：

```xs
value1=ma1/ma2;
value2=ma1/ma3;
value3=countif(value1>=(1+percent1),period1);
value4=countIf(value2>=(1+percent2),period1);
value7=truecount(value1>=(1+percent1),period2+2);
value8=truecount(value2>=(1+percent2),period2+2);

if value3=period1 and value4=period1
   and value7<=period2 and value8<=period2
then ret = 1;
```

解讀：

- 最近 `period1=2` 天必須都符合 5/10 gap >= 2%、5/20 gap >= 5%。
- 連續符合的長度不可超過 `period2=11`。
- 我們原本的 `gap_ok` run length 2~11 在這組資料上與 `c3_xq_exact_proxy` 跑出同樣筆數：liquid raw / adjusted 都相同。

結論：C3 不需要立刻大改，但之後報告要標記為「已用 repo 近似校正」。

### 2. Magic26 分支多了一個「第 N 大量 / 第一大量比例」條件，值得測

Repo `魔字26號/日線第幾大量是第1大量幾趴_Ge.xs`：

- Window：120 日
- Nth：第 5 大量
- 第 5 大量需在第一大量的 50%~100%

研究解讀：

這不是單純排除近期最大量，而是檢查「120 日內是否有多根相對大的量」。可能代表資金不是只有一天爆量，而是有一段較密集的換手/進場痕跡。

本輪已做簡化 overlay：

```text
top5_volume_ratio_120 = 120日第5大量 / 120日最大量
repo_top5_volume_ratio_ok = 0.50 <= ratio <= 1.00
```

並測：

```text
C1 + C2 + C3_xq + repo_top5_volume_ratio_ok
```

### 3. 其他可後續測但本輪不直接採用

可直接用 OHLCV 回測：

- 魔字4：
  - 股價高於幾日均線比例
  - 日線最低價在幾日前
  - 60日漲跌幅
- 魔字21：
  - 5MA 金叉 60MA 幾次
  - 創 120 周新高
- 魔字24/28：
  - 週線 MA 擴散
  - 60 日低點最大漲幅
  - 第2型多頭排列
- 魔字27：
  - 第6型多頭排列：長均線多頭 + 短均線糾結在長均線上方

需要 XQ/籌碼欄位，不宜用 FinMind proxy 亂替代：

- 主力長期收集
- 籌碼從散戶手裡被收集
- 籌碼被發散
- 千張大戶持股持續增加
- 股本篩選：需要最新股本欄位；可另找官方/FinMind財務資料補。

## 研究採用決策

- 採用：`C3_xq_exact_proxy`，但實測與原 C3 目前等價。
- 採用為 overlay：`repo_top5_volume_ratio_ok`。
- 暫不採用：XQ 籌碼欄位類條件，除非後續找到可靠資料源。
- 暫不採用：股本條件，因為 Magic26 目前已有流動性 universe；股本要另接資料，不應先用錯誤 proxy。

## 後續建議

1. 先看 volume-ratio overlay 是否改善 t+1 open excess。
2. 若有效，再把它與 Magic26 full condition 比較：
   - `C1+C2+C3`
   - `C1+C2+C3+vol5`
   - `Magic26 v0`
3. 若仍有價值，再測週線條件：真 weekly 60W range，而不是 daily 300D proxy。
