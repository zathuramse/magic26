# Magic26 P2-5 Group-dedup + 追高分位 Holdout

日期：2026-07-02

## 驗證邊界

- 觀察窗：2023-2025；holdout：2026。
- Dedup key：`date + stock_id + signal`。
- raw/adjusted 合併去重時，優先取 adjusted，避免同股同日雙重計數。
- 追高分位門檻只用 2023-2025 訓練窗估計，再套到 2026 holdout。
- core_family 目前沒有現成 detail definition 對應欄位，本輪不硬湊。

## 產物

- `reports/p2_group_dedup_chase_holdout_2026-07-02.csv`
- `reports/p2_chase_quantile_buckets_2026-07-02.csv`
- `reports/p2_group_dedup_chase_holdout_2026-07-02.md`

## Verdict 分布

- `dedup_direction_ok_20_60`：21

## 代表性結果

- strict_candidate dedup_prefer_adjusted candidate_a_repo50_c440_c5gt5: train_n=26, holdout_n=26, holdout_avg20=22.5%, holdout_win20=78.3%, holdout_avg60=32.1%, holdout_win60=75.0%, drop=45.8%, verdict=dedup_direction_ok_20_60
- strict_candidate dedup_prefer_adjusted candidate_b_magic_c440_c5gt5: train_n=41, holdout_n=34, holdout_avg20=18.0%, holdout_win20=70.0%, holdout_avg60=21.4%, holdout_win60=70.0%, drop=46.0%, verdict=dedup_direction_ok_20_60
- regime_family dedup_prefer_adjusted magic26_v0: train_n=56, holdout_n=34, holdout_avg20=18.0%, holdout_win20=70.0%, holdout_avg60=21.4%, holdout_win60=70.0%, drop=43.6%, verdict=dedup_direction_ok_20_60
- regime_family dedup_prefer_adjusted magic26_v0_quality: train_n=45, holdout_n=31, holdout_avg20=17.6%, holdout_win20=67.9%, holdout_avg60=21.4%, holdout_win60=70.0%, drop=45.2%, verdict=dedup_direction_ok_20_60

## 追高分位初步觀察

請以 CSV 為主。若 `high` bucket 的 2026 holdout avg/win 明顯低於 low/mid，代表追高有懲罰；若 high 仍強，可能表示 2026 是強動能年份，不能外推。
- strict A `signal_day_ret_1d`：low:n=4,avg20=43.5%,win20=100.0%；mid:n=8,avg20=27.1%,win20=83.3%；high:n=14,avg20=16.0%,win20=71.4%
- strict A `next_open_gap`：low:n=7,avg20=32.1%,win20=100.0%；mid:n=9,avg20=21.3%,win20=77.8%；high:n=10,avg20=16.6%,win20=62.5%
- strict A `ret_20d`：low:n=3,avg20=28.4%,win20=100.0%；mid:n=15,avg20=26.5%,win20=92.3%；high:n=8,avg20=12.6%,win20=42.9%
- strict A `range_pos`：low:n=26,avg20=22.5%,win20=78.3%；mid:n=0,avg20=NA,win20=NA；high:n=0,avg20=NA,win20=NA

## 判讀

1. 這一步比 P2-4 更嚴格，因為它處理 raw/adjusted 與同股同日重複。
2. 若 dedup 後 strict A/B/C 仍方向為正，只能提高「候選排序」信心，仍不能變成買訊。
3. 追高分位若顯示 high bucket 變差，dashboard 應強化「不要追高」而非增加買入語氣。
4. 若 high bucket 在 2026 仍好，需視為強動能年份現象，下一步要跨年度/跨市況驗證。

## 下一步

P2-6 建議把追高分位結果轉成明確的 risk-veto 候選規則草案，但先只寫研究報告，不上 UI。
