# Magic26 P2-7 Risk-veto 回放測試

日期：2026-07-02

## 驗證邊界

- 使用 P2-6 Level 0/1/2/3 草案規則。
- 明細資料使用 strict round8 detail 與 regime round4 checked detail。
- dedup key：`date + stock_id + signal`，raw/adjusted 合併時優先取 adjusted。
- 主要檢查 2026 holdout；同時輸出 train/all CSV。
- 右尾定義：20D excess >= 20%；60D excess >= 50%。

## 產物

- `reports/p2_risk_veto_replay_cases_2026-07-02.csv`
- `reports/p2_risk_veto_replay_summary_2026-07-02.csv`
- `reports/p2_risk_veto_replay_2026-07-02.md`

## 2026 holdout 分層摘要

- `strict_candidate` L0: n=15, n20=12, avg20=35.3%, win20=100.0%, right20=100.0%, n60=3, avg60=42.7%, win60=100.0%, right60=0.0%
- `strict_candidate` L1: n=20, n20=20, avg20=21.0%, win20=85.0%, right20=60.0%, n60=6, avg60=35.8%, win60=50.0%, right60=50.0%
- `strict_candidate` L2: n=25, n20=21, avg20=25.4%, win20=76.2%, right20=38.1%, n60=5, avg60=64.2%, win60=100.0%, right60=80.0%
- `strict_candidate` L3: n=18, n20=17, avg20=3.9%, win20=47.1%, right20=41.2%, n60=8, avg60=-8.8%, win60=62.5%, right60=0.0%
- `regime_family` L0: n=30, n20=24, avg20=21.1%, win20=70.8%, right20=66.7%, n60=11, avg60=7.6%, win60=63.6%, right60=0.0%
- `regime_family` L1: n=39, n20=35, avg20=17.7%, win20=74.3%, right20=51.4%, n60=12, avg60=24.1%, win60=50.0%, right60=33.3%
- `regime_family` L2: n=63, n20=53, avg20=19.2%, win20=67.9%, right20=34.0%, n60=18, avg60=57.2%, win60=94.4%, right60=72.2%
- `regime_family` L3: n=125, n20=96, avg20=-0.9%, win20=42.7%, right20=21.9%, n60=47, avg60=-8.0%, win60=40.4%, right60=8.5%

## strict candidate 代表性回放

### strict candidate_a_repo50_c440_c5gt5
- L0: n=5, n20=4, avg20=35.3%, win20=100.0%, right20=100.0%, n60=1, avg60=42.7%, win60=100.0%, right60=0.0%
- L1: n=7, n20=7, avg20=20.5%, win20=85.7%, right20=57.1%, n60=2, avg60=35.8%, win60=50.0%, right60=50.0%
- L2: n=10, n20=8, avg20=24.8%, win20=75.0%, right20=37.5%, n60=2, avg60=78.4%, win60=100.0%, right60=100.0%
- L3: n=4, n20=4, avg20=8.5%, win20=50.0%, right20=50.0%, n60=3, avg60=-4.8%, win60=66.7%, right60=0.0%
### strict candidate_b_magic_c440_c5gt5
- L0: n=5, n20=4, avg20=35.3%, win20=100.0%, right20=100.0%, n60=1, avg60=42.7%, win60=100.0%, right60=0.0%
- L1: n=7, n20=7, avg20=20.5%, win20=85.7%, right20=57.1%, n60=2, avg60=35.8%, win60=50.0%, right60=50.0%
- L2: n=12, n20=10, avg20=23.2%, win20=70.0%, right20=40.0%, n60=3, avg60=54.8%, win60=100.0%, right60=66.7%
- L3: n=10, n20=9, avg20=2.6%, win20=44.4%, right20=33.3%, n60=4, avg60=-16.1%, win60=50.0%, right60=0.0%
### strict candidate_c_high_concentration_c425_c5gt5
- L0: n=5, n20=4, avg20=35.3%, win20=100.0%, right20=100.0%, n60=1, avg60=42.7%, win60=100.0%, right60=0.0%
- L1: n=6, n20=6, avg20=22.2%, win20=83.3%, right20=66.7%, n60=2, avg60=35.8%, win60=50.0%, right60=50.0%
- L2: n=3, n20=3, avg20=34.1%, win20=100.0%, right20=33.3%, n60=0, avg60=NA, win60=NA, right60=NA
- L3: n=4, n20=4, avg20=2.2%, win20=50.0%, right20=50.0%, n60=1, avg60=8.8%, win60=100.0%, right60=0.0%

## 初步判讀

1. Level 2/3 不應被解讀成「必跌」；它們在 2026 強動能環境仍可能有正報酬與右尾。
2. 但 Level 3 通常混入低流動性或極端追高，應至少降級為 secondary / 只記錄。
3. 若 Level 1/2 的右尾率仍高，risk-veto 應是「禁止追價 / 降級排序」，而不是直接刪除候選，避免錯殺右尾。
4. 6213 屬 Level 2：合理做法是只觀察/等回檔，而不是從候選清單刪除。

## 下一步

P2-8 建議把 Level 2/3 規則轉成 dashboard 顯示層的規格草案：只改風險 badge 與排序提示，不改訊號產生，也不刪候選。
