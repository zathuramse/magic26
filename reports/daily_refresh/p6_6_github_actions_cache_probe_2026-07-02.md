# P6-6 GitHub Actions CI cache probe

日期：2026-07-02

## 目的

P6-6 的目標是驗證 GitHub Actions 在已有 `FINMIND_TOKEN` secret 後，能否在 repo-relative `.ci` staging cache 內產生 sample parquet，並把 cache/report artifact 帶回來驗證。

本階段仍然不做：

```text
schedule
full refresh
Cloudflare deploy
generated data commit
關閉 Hermes cron
```

## 變更

### 新增 script

```text
scripts/magic26_ci_cache_probe.py
```

功能：

```text
抓 sample stock 6213 raw price
抓 sample stock 6213 adjusted price
抓 benchmark TAIEX
寫入 MAGIC26_CACHE_DIR
寫 JSON/MD report 到 MAGIC26_REPORT_DIR
```

預設測試區間：

```text
2026-07-01 ~ 2026-07-02
```

輸出 parquet：

```text
ci_probe_raw_6213_20260701_20260702.parquet
ci_probe_adj_6213_20260701_20260702.parquet
ci_probe_benchmark_TAIEX_20260701_20260702.parquet
```

### Workflow 更新

更新：

```text
.github/workflows/magic26-ci-probe.yml
```

新增手動 input：

```text
run_cache_extension_probe
```

新增 env：

```text
RUN_CACHE_EXTENSION_PROBE
```

新增 step：

```text
CI cache extension probe only
```

Artifact upload 現在包含：

```text
MAGIC26_ARTIFACT_DIR
MAGIC26_CACHE_DIR/ci_probe_*.parquet
```

## 本地驗證

本地以 `.ci` staging 執行 sample probe：

```text
MAGIC26_CACHE_DIR=.ci/research-brain/sources/strategy-checks/magic26/cache
MAGIC26_REPORT_DIR=.ci/artifacts/reports/daily_refresh
python scripts/magic26_ci_cache_probe.py --stock-id 6213 --start-date 2026-07-01 --end-date 2026-07-02
```

結果：

```text
report_count=1
parquet_count=3
success=true
finmind_token_present=true
```

Frames：

```text
raw_sample rows=2 date_min=2026-07-01 date_max=2026-07-02 stock_ids=6213
adj_sample rows=2 date_min=2026-07-01 date_max=2026-07-02 stock_ids=6213
benchmark_TAIEX rows=2 date_min=2026-07-01 date_max=2026-07-02 stock_ids=TAIEX
```

Validation：

```text
OK raw_sample extends to 2026-07-02.
OK adj_sample extends to 2026-07-02.
OK benchmark_TAIEX extends to 2026-07-02.
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

## CI run 1：發現 ordering 問題

第一次 P6-6 CI run：

```text
url: https://github.com/zathuramse/magic26/actions/runs/28598397004
head_sha: 921ea1bf076dad04610d428bf2b99d0063bf298c
status: completed
conclusion: success
```

Artifact 驗證：

```text
manifest counts.cache_files=3
cache_report success=true
parquet_files in downloaded artifact=0
```

判斷：cache probe 成功產生 parquet，但 artifact 當時只包含 `.ci/artifacts`，沒有包含 `MAGIC26_CACHE_DIR/ci_probe_*.parquet`。因此補上 artifact path。

## CI run 2：發現 cache restore ordering 問題

第二次 P6-6 CI run：

```text
url: https://github.com/zathuramse/magic26/actions/runs/28598515208
status: failure
```

失敗點：

```text
Verify committed static dashboard package
```

Log：

```text
forbidden packaged file: .../.ci/research-brain/sources/strategy-checks/magic26/cache/ci_probe_raw_6213_20260701_20260702.parquet
```

原因：上一輪 CI cache 已保存 `ci_probe_*.parquet`。workflow 在 static package verifier 之前 restore cache，導致 verifier 掃到 `.ci` cache 內的 parquet，判定為 forbidden packaged file。

修正：把 `Restore Magic26 research cache` 移到 static package verifier 之後、FinMind/cache probe 之前。

Commit：

```text
60f6915 Restore Magic26 CI cache after package verification
```

## CI run 3：成功結果

Run：

```text
url: https://github.com/zathuramse/magic26/actions/runs/28598605156
head_sha: 60f69159df3d87f2d77c272993bdadfd19676ce4
status: completed
conclusion: success
created_at: 2026-07-02T14:39:55Z
updated_at: 2026-07-02T14:40:41Z
```

Downloaded artifact files：

```text
artifacts/magic26_ci_probe_manifest.json
artifacts/reports/daily_refresh/p5_daily_refresh_probe_20260702_144031.json
artifacts/reports/daily_refresh/p5_daily_refresh_probe_20260702_144031.md
artifacts/reports/daily_refresh/p6_6_magic26_ci_cache_probe_20260702_144032.json
artifacts/reports/daily_refresh/p6_6_magic26_ci_cache_probe_20260702_144032.md
research-brain/sources/strategy-checks/magic26/cache/ci_probe_adj_6213_20260701_20260702.parquet
research-brain/sources/strategy-checks/magic26/cache/ci_probe_benchmark_TAIEX_20260701_20260702.parquet
research-brain/sources/strategy-checks/magic26/cache/ci_probe_raw_6213_20260701_20260702.parquet
```

Manifest：

```json
{
  "github_run_id": "28598605156",
  "github_sha": "60f69159df3d87f2d77c272993bdadfd19676ce4",
  "run_finmind_probe": "true",
  "run_cache_extension_probe": "true",
  "finmind_token_present": true,
  "counts": {
    "cache_files": 3,
    "out_files": 0,
    "report_files": 4
  }
}
```

Artifact counts：

```json
{
  "daily_report_json": 1,
  "cache_report_json": 1,
  "parquet_files": 3
}
```

Daily probe：

```json
{
  "complete_data_through": "2026-07-02",
  "probe_error_count": 0,
  "probe_count": 2
}
```

Cache probe：

```json
{
  "success": true,
  "finmind_token_present": true,
  "frames": {
    "raw_sample": {
      "rows": 2,
      "date_min": "2026-07-01",
      "date_max": "2026-07-02",
      "stock_ids": ["6213"]
    },
    "adj_sample": {
      "rows": 2,
      "date_min": "2026-07-01",
      "date_max": "2026-07-02",
      "stock_ids": ["6213"]
    },
    "benchmark_TAIEX": {
      "rows": 2,
      "date_min": "2026-07-01",
      "date_max": "2026-07-02",
      "stock_ids": ["TAIEX"]
    }
  },
  "validation": [
    "OK raw_sample extends to 2026-07-02.",
    "OK adj_sample extends to 2026-07-02.",
    "OK benchmark_TAIEX extends to 2026-07-02."
  ]
}
```

## 結論

P6-6 成功：

```text
GitHub Actions 可以使用 FINMIND_TOKEN 抓 sample FinMind data
CI 可以在 MAGIC26_CACHE_DIR 產生 sample parquet
artifact 內包含 manifest + daily probe report + cache probe report + 3 個 sample parquet
static package verifier 不再受 restored cache 污染
repo guardrail 通過
```

仍未完成：

```text
完整 per-stock cache extension
round outputs 產生
public/data export
Cloudflare deploy
schedule
```

## 下一步建議：P6-7

P6-7 應做「CI full cache-extension dry-run design」，但仍不要 full refresh：

1. 改善 `extend_magic26_cache.py`，讓它支援 sample-only 模式或明確的 `--sample-stock-id` 實寫/驗證。
2. 在 CI 使用 restored cache + FinMind token 做小範圍 target suffix dry-run。
3. Artifact 檢查 source/target suffix、6213 raw/adj、benchmark_TAIEX。
4. 若通過，再進 P6-8：round pipeline dry-run。
