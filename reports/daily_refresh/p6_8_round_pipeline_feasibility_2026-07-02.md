# P6-8 GitHub Actions round pipeline feasibility probe

日期：2026-07-02

## 目的

P6-8 的目標是確認 Magic26 round pipeline 能否在 GitHub Actions `.ci` staging 中往下推進。這一步是 feasibility inventory，不直接跑 full round pipeline。

本階段仍然不做：

```text
full market round execution
public/data export
Cloudflare deploy
schedule
generated data commit
關閉 Hermes cron
```

## 變更

新增：

```text
scripts/magic26_ci_round_feasibility_probe.py
```

功能：

1. 盤點 base signal / round4 / round7 / round8 / round9 scripts。
2. 讀取 CLI args、hard-coded snapshot/date/path pattern。
3. 檢查 `.ci` cache sample prerequisites。
4. 檢查 target round4 checked-signal inputs 是否存在。
5. 輸出 JSON/MD artifact report。

更新：

```text
.github/workflows/magic26-ci-probe.yml
```

新增 input：

```text
run_round_feasibility_probe
```

新增 step：

```text
CI round pipeline feasibility probe only
```

## 本地驗證

本地流程：

1. 建立 `.ci` staging。
2. 先跑 P6-7 sample-only cache extension，建立：

```text
raw_6213_20210101_20260702.parquet
adj_6213_20210101_20260702.parquet
benchmark_TAIEX_20210101_20260702.parquet
```

3. 跑 P6-8 feasibility probe。

本地結果：

```text
p6_8_local_ok reports=1 blockers=7
```

核心確認：

```text
sample_cache_raw_target date_max=2026-07-02
sample_cache_adj_target date_max=2026-07-02
sample_cache_benchmark_target date_max=2026-07-02
round4_raw_target exists=false
round4_adj_target exists=false
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

## CI run

Run：

```text
url: https://github.com/zathuramse/magic26/actions/runs/28600519677
head_sha: 9a42e5f726397cb66d007de4d86bfa397e2557eb
status: completed
conclusion: success
created_at: 2026-07-02T15:08:13Z
updated_at: 2026-07-02T15:09:08Z
```

Inputs：

```text
run_finmind_probe=true
run_cache_extension_probe=true
run_cache_extension_dry_run=true
run_round_feasibility_probe=true
snapshot_suffix=20210101_20260702
data_through=2026-07-02
```

Artifact：

```text
magic26-ci-probe-28600519677
```

## Artifact 驗證

Artifact 內有：

```text
artifacts/magic26_ci_probe_manifest.json
artifacts/reports/daily_refresh/p5_daily_refresh_probe_20260702_150857.json
artifacts/reports/daily_refresh/p5_3_extend_magic26_cache_local_write_20260702_150903.json
artifacts/reports/daily_refresh/p6_8_round_feasibility_probe_20260702_150904.json
```

以及 sample parquet：

```text
raw_6213_20210101_20260701.parquet
raw_6213_20210101_20260702.parquet
adj_6213_20210101_20260701.parquet
adj_6213_20210101_20260702.parquet
benchmark_TAIEX_20210101_20260701.parquet
benchmark_TAIEX_20210101_20260702.parquet
```

Manifest：

```json
{
  "github_run_id": "28600519677",
  "github_sha": "9a42e5f726397cb66d007de4d86bfa397e2557eb",
  "run_finmind_probe": "true",
  "run_cache_extension_probe": "true",
  "run_cache_extension_dry_run": "true",
  "run_round_feasibility_probe": "true",
  "finmind_token_present": true,
  "counts": {
    "cache_files": 15,
    "out_files": 0,
    "report_files": 8
  }
}
```

P6-8 round feasibility：

```json
{
  "target_suffix": "20210101_20260702",
  "target_date": "2026-07-02",
  "sample_cache_raw_target": {
    "exists": true,
    "rows": 4,
    "date_min": "2026-06-29",
    "date_max": "2026-07-02"
  },
  "sample_cache_adj_target": {
    "exists": true,
    "rows": 4,
    "date_min": "2026-06-29",
    "date_max": "2026-07-02"
  },
  "sample_cache_benchmark_target": {
    "exists": true,
    "rows": 4,
    "date_min": "2026-06-29",
    "date_max": "2026-07-02"
  },
  "round4_raw_target_exists": false,
  "round4_adj_target_exists": false
}
```

## Script inventory 結論

### `magic26_signal_pilot.py`

有 sample controls：

```text
--stock-ids
--max-stocks
```

但 output `run_id` 會使用實際 stock count，例如 sample run 會變成 `1stocks`，不是 dashboard pipeline 預期的 `2130stocks` 命名。

### `magic26_round4_execution_checks.py`

有：

```text
--signals
--run-label
--start-date
--end-date
```

但沒有：

```text
--snapshot-suffix
```

所以 round4 不是不能跑，但需要明確接收 base signal output 檔案與 run-label。CI sample mode 需要一個 deterministic wrapper 或命名規則。

### `magic26_round7_param_grid.py`

已有：

```text
--snapshot-suffix
```

但它直接期待：

```text
magic26_round4_checked_signals_round6_regime_all_liquid30000000_raw_<suffix>.csv
magic26_round4_checked_signals_round6_regime_all_liquid30000000_adj_<suffix>.csv
```

### `magic26_round8_tradeability_checks.py`

已有：

```text
--snapshot-suffix
```

但同樣依賴 round4 checked signals，並會讀 per-stock cache。

### `magic26_round9_close_exit_checks.py`

已有：

```text
--snapshot-suffix
```

但同樣依賴 round4 checked signals、per-stock cache、benchmark cache。

## Blockers

CI artifact 中 P6-8 blocker 清單：

```text
base signal has sample controls (--stock-ids/--max-stocks), but output run_id uses selected stock count rather than dashboard 2130stocks naming.

round4 has no --snapshot-suffix; it needs explicit --signals and --run-label from a prior base-signal output.

magic26_round7_param_grid.py is suffix-parameterized, but still expects round4 checked-signal filenames for both raw/adj under OUT.

magic26_round8_tradeability_checks.py is suffix-parameterized, but still expects round4 checked-signal filenames for both raw/adj under OUT.

magic26_round9_close_exit_checks.py is suffix-parameterized, but still expects round4 checked-signal filenames for both raw/adj under OUT.

target round4 checked-signal inputs are missing in CI staging; round7/8/9 cannot run yet without base signal + round4 regeneration.

P6-8 is inventory-only: no heavy round scripts were executed, no public/data export, no deploy, no schedule.
```

## 結論

P6-8 成功完成 feasibility inventory，結論是：

```text
sample cache target 已可在 CI 產生並延伸到 2026-07-02
round7/8/9 已有 snapshot-suffix 參數化
但 round7/8/9 不能直接跑，因為 target round4 checked-signal inputs 尚未產生
下一步應先證明 base signal + round4 sample regeneration
```

這個結論很重要：現在不應該硬跑 full refresh，也不應該直接啟用 GitHub Actions schedule。

## 下一步建議：P6-9

P6-9 應做 **base signal + round4 sample regeneration in CI staging**：

1. 用 sample stock `6213` 跑 `magic26_signal_pilot.py` raw/adj。
2. 不使用 `--liquid-universe` 或用明確 sample wrapper，避免 sample 被 liquidity filter 清掉。
3. 將 sample base signal output 接到 `magic26_round4_execution_checks.py`。
4. 用 deterministic sample run-label，例如：

```text
round6_regime_sample6213_raw_20210101_20260702
round6_regime_sample6213_adj_20210101_20260702
```

5. Artifact 驗證：

```text
base signal CSV/manifest exists
round4 checked signals CSV/manifest exists
bench merge columns exist
risk_next_gap_gt3 exists
regime_all3 exists
```

6. 仍不跑 round7/8/9、不 export、不 deploy、不 schedule。
