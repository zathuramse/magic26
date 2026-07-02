# Magic26 P2-4 Holdout / Walk-forward 初步驗證

日期：2026-07-02

## 驗證邊界

- 觀察窗：2023-2025
- Holdout：2026
- 不用 2026 調規則。
- 不混算 strict / core / regime。
- raw / adj 保持分開。
- regime family 目前缺年度表，本輪不做 holdout。

## 產物

- `reports/p2_holdout_walkforward_2026-07-02.csv`
- `reports/p2_holdout_walkforward_2026-07-02.md`

## 結果摘要

- 總驗證列：18
- `core_family`：12 rows
- `strict_candidate`：6 rows

### Verdict 分布

- `direction_ok_but_yearly_unstable`：9
- `provisionally_pass`：9

## 重要判讀

1. strict_candidate 在 2026 多數方向仍為正，但樣本偏薄，且 win rate 不一定強。這支持「候選排序」，不支持直接買訊。
2. core_family 的 20D holdout 多數方向為正，但 60D 更不穩，尤其 win rate 與年度穩定性需要警戒。
3. 2024 在多個家族裡偏弱，是策略壓力測試年；不能只用 2026 好看來提高信心。
4. 本輪沒有把 regime_family 納入 holdout，因為目前只有 all-period summary；硬做會污染驗證。

## 代表性列

- strict adj candidate_a_repo50_c440_c5gt5: train_n=20, train_avg=8.5%, train_win=45.0%; holdout_n=23, holdout_avg=22.5%, holdout_win=78.3%; verdict=provisionally_pass
- strict raw candidate_a_repo50_c440_c5gt5: train_n=26, train_avg=11.2%, train_win=57.7%; holdout_n=22, holdout_avg=23.2%, holdout_win=81.8%; verdict=provisionally_pass
- core adj core_repo50_regime 20D: train_n=39, train_avg=6.9%, train_win=41.0%; holdout_n=39, holdout_avg=10.0%, holdout_win=59.0%; verdict=provisionally_pass
- core raw core_repo50_regime 20D: train_n=43, train_avg=9.3%, train_win=51.2%; holdout_n=38, holdout_avg=10.0%, holdout_win=60.5%; verdict=provisionally_pass

## 下一步建議

P2-5 應補 `group-dedup` 版本：同一 stock/date/family 只算一次，並把高開、追高分位加入 holdout。若 dedup 後 2026 仍成立，可信度才可再提高。
