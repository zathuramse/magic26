# P6-9 GitHub Actions base signal + round4 sample probe

日期：2026-07-02

## 目的

P6-9 的目標是證明 Magic26 在 GitHub Actions `.ci` staging 中，可以把 sample stock `6213` 的 base signal output 接到 round4 execution checks。

本階段仍然不做：

```text
round7 / round8 / round9
full market refresh
public/data export
Cloudflare deploy
schedule
generated data commit
關閉 Hermes cron
```

## 變更

新增：

```text
scripts/magic26_ci_base_round4_sample_probe.py
```

功能：

1. 跑 `magic26_signal_pilot.py` raw sample：

```text
--universe manual
--stock-ids 6213
--start-date 2021-01-01
--end-date 2026-07-02
```

2. 跑 `magic26_signal_pilot.py` adjusted sample。
3. 讀取 base signal manifest，取得 generated signal CSV。
4. 將 signal CSV 接到 `magic26_round4_execution_checks.py`。
5. 使用 deterministic sample run-label：

```text
round6_regime_sample6213_raw_20210101_20260702
round6_regime_sample6213_adj_20210101_20260702
```

6. 驗證 round4 checked signal 欄位：

```text
bench_close
risk_next_gap_gt3
regime_all3
excess_20d
t1_excess_20d
```

7. 輸出 JSON/MD artifact report。

更新：

```text
.github/workflows/magic26-ci-probe.yml
```

新增 input：

```text
run_base_round4_sample_probe
```

新增 step：

```text
CI base signal and round4 sample probe only
```

Artifact upload 新增：

```text
MAGIC26_OUT_DIR/magic26_v0_*manual_*_20210101_20260702_1stocks.*
MAGIC26_OUT_DIR/magic26_round4_*sample6213*20210101_20260702.*
```

## 本地驗證

本地 `.ci` staging 直接跑 P6-9 wrapper 成功：

```text
raw signals_rows=1 round4_rows=1
adj signals_rows=1 round4_rows=1
```

核心檢查：

```text
OK column bench_close present
OK column risk_next_gap_gt3 present
OK column regime_all3 present
OK column excess_20d present
OK column t1_excess_20d present
OK bench_close_missing=0
OK sample stock 6213 present
OK rows > 0
```

Local gates：

```text
python -m py_compile scripts/*.py
node --check public/app.js
python scripts/verify_magic26_package.py --snapshot-suffix 20210101_20260702 --data-through 2026-07-02 --app-cache-bust 20260702riskv2 --css-cache-bust 20260701q
git diff --check
```

結果：

```text
ok magic26 package 2026-07-02 latest 2026-06-26
```

## CI run 1：失敗與根因

第一次 P6-9 CI run：

```text
url: https://github.com/zathuramse/magic26/actions/runs/28601265665
status: failure
```

錯誤：

```text
RuntimeError: base signal raw produced no sample signal rows:
.../magic26_v0_signals_manual_raw_20210101_20260702_1stocks.csv
```

根因：

P6-7 sample extension 會先產生短版 sample target cache：

```text
raw_6213_20210101_20260702.parquet
adj_6213_20210101_20260702.parquet
benchmark_TAIEX_20210101_20260702.parquet
```

這些檔名剛好與 `magic26_signal_pilot.py` / round4 使用的 full-range cache 名稱相同。CI restore 後，P6-9 誤讀 4-row 短版 cache，而不是抓 2021-01-01～2026-07-02 full-range sample data，所以 base signal 變成 0 rows。

修正：

`magic26_ci_base_round4_sample_probe.py` 在跑 base/round4 前，會刪除 CI staging 裡可能存在的短版 sample target cache：

```text
raw_6213_20210101_20260702.parquet
adj_6213_20210101_20260702.parquet
benchmark_TAIEX_20210101_20260702.parquet
```

這只作用於 `.ci` staging，不影響 production 或 repo-tracked data。

修正 commit：

```text
31abba8 Avoid short cache shadowing in Magic26 base round4 probe
```

本地也重現了 CI 順序：先 P6-7 建短版 cache，再 P6-9；修正後通過。

## CI run 2：成功

Run：

```text
url: https://github.com/zathuramse/magic26/actions/runs/28601453558
head_sha: 31abba85e4986bd468c41d713489b9a4ee753019
status: completed
conclusion: success
created_at: 2026-07-02T15:22:24Z
updated_at: 2026-07-02T15:23:46Z
```

Inputs：

```text
run_finmind_probe=true
run_cache_extension_probe=true
run_cache_extension_dry_run=true
run_round_feasibility_probe=true
run_base_round4_sample_probe=true
snapshot_suffix=20210101_20260702
data_through=2026-07-02
```

Manifest：

```json
{
  "github_run_id": "28601453558",
  "github_sha": "31abba85e4986bd468c41d713489b9a4ee753019",
  "run_base_round4_sample_probe": "true",
  "finmind_token_present": true,
  "counts": {
    "cache_files": 16,
    "out_files": 20,
    "report_files": 10
  }
}
```

## Artifact 驗證

Artifact 內包含 base signal outputs：

```text
magic26_v0_signals_manual_raw_20210101_20260702_1stocks.csv
magic26_v0_signals_manual_adj_20210101_20260702_1stocks.csv
magic26_v0_manifest_manual_raw_20210101_20260702_1stocks.json
magic26_v0_manifest_manual_adj_20210101_20260702_1stocks.json
```

Artifact 內包含 round4 outputs：

```text
magic26_round4_checked_signals_round6_regime_sample6213_raw_20210101_20260702.csv
magic26_round4_checked_signals_round6_regime_sample6213_adj_20210101_20260702.csv
magic26_round4_manifest_round6_regime_sample6213_raw_20210101_20260702.json
magic26_round4_manifest_round6_regime_sample6213_adj_20210101_20260702.json
```

驗證摘要：

```json
{
  "success": true,
  "failures": [],
  "raw": {
    "cache_cleanup_removed_count": 2,
    "signals_rows": 1,
    "signals_date_max": "2026-02-24",
    "round4_rows": 1
  },
  "adj": {
    "cache_cleanup_removed_count": 2,
    "signals_rows": 1,
    "signals_date_max": "2026-02-24",
    "round4_rows": 1
  }
}
```

Round4 checks：

```text
OK column bench_close present
OK column risk_next_gap_gt3 present
OK column regime_all3 present
OK column excess_20d present
OK column t1_excess_20d present
OK bench_close_missing=0
OK sample stock 6213 present
OK rows > 0
```

## 重要解讀

`signals_date_max = 2026-02-24` 不是錯誤。

這代表：

```text
price data / cache coverage 可以到 2026-07-02
但 6213 sample 在 Magic26 條件下，最新 qualifying signal 是 2026-02-24
```

這符合先前原則：不要把 `data_through` 偽裝成最新 signal date。

## 結論

P6-9 成功：

```text
GitHub Actions 可以用 sample 6213 跑 base signal raw/adj
base signal outputs 可以接到 round4 raw/adj
round4 checked signal CSV/manifest 已產生
必要欄位與 benchmark merge 驗證通過
短版 sample cache shadowing 問題已發現並修正
```

仍未做：

```text
round7 / round8 / round9
full market base signal
full market round4
public/data export
Cloudflare deploy
schedule
```

## 下一步建議：P6-10

P6-10 應做 **round7/8/9 sample feasibility with synthetic or copied deterministic round4 inputs**，但要非常小心：

1. 現有 round7/8/9 預期檔名是 dashboard full-run naming：

```text
magic26_round4_checked_signals_round6_regime_all_liquid30000000_raw_<suffix>.csv
magic26_round4_checked_signals_round6_regime_all_liquid30000000_adj_<suffix>.csv
```

2. P6-9 產出的 sample round4 檔名是：

```text
magic26_round4_checked_signals_round6_regime_sample6213_raw_<suffix>.csv
magic26_round4_checked_signals_round6_regime_sample6213_adj_<suffix>.csv
```

3. 下一步不應假裝 sample 是 full-run。較安全選項是：
   - 替 round7/8/9 加 `--round4-raw` / `--round4-adj` input override；或
   - 加 `--sample-mode`，讓它明確讀 sample round4 filenames。

4. 仍不 export、不 deploy、不 schedule。
