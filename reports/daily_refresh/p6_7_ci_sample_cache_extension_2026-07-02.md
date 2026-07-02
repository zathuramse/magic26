# P6-7 GitHub Actions sample cache-extension dry-run

日期：2026-07-02

## 目的

P6-7 的目標是把 P6-6 的 CI sample cache probe 往正式 cache extension pipeline 推進：不再只用臨時 probe script，而是讓正式 `scripts/extend_magic26_cache.py` 支援 CI sample-only 模式。

本階段仍然不做：

```text
schedule
full refresh
round outputs
public/data export
Cloudflare deploy
generated data commit
關閉 Hermes cron
```

## 變更

### `scripts/extend_magic26_cache.py`

新增能力：

```text
--sample-only
--bootstrap-sample-source
--sample-source-start
--sample-source-end
```

用途：

- `--sample-only`：只延伸指定 sample stock ids，加上 `benchmark_TAIEX`。
- `--bootstrap-sample-source`：CI staging 沒有完整歷史 cache 時，先建立 source-suffix sample cache。
- `--sample-source-start/end`：控制 sample source cache 的最小區間，避免 CI 抓全市場或全歷史。

P6-7 CI 使用：

```text
source_suffix=20210101_20260701
target_suffix=20210101_20260702
tail_start=2026-07-01
target_date=2026-07-02
sample_stock_id=6213
sample_source_start=2026-06-29
sample_source_end=2026-07-01
```

### `.github/workflows/magic26-ci-probe.yml`

新增手動 input：

```text
run_cache_extension_dry_run
```

新增 step：

```text
CI sample-only cache extension dry-run
```

Artifact 上傳新增正式 extender sample parquet：

```text
raw_6213_20210101_20260701.parquet
raw_6213_20210101_20260702.parquet
adj_6213_20210101_20260701.parquet
adj_6213_20210101_20260702.parquet
benchmark_TAIEX_20210101_20260701.parquet
benchmark_TAIEX_20210101_20260702.parquet
```

## 本地驗證

本地 `.ci` staging 執行正式 extender sample-only：

```text
python scripts/extend_magic26_cache.py \
  --source-suffix 20210101_20260701 \
  --target-suffix 20210101_20260702 \
  --tail-start 2026-07-01 \
  --target-date 2026-07-02 \
  --sample-only \
  --bootstrap-sample-source \
  --sample-source-start 2026-06-29 \
  --sample-source-end 2026-07-01 \
  --sample-stock-id 6213 \
  --refresh-daily \
  --overwrite
```

結果：

```text
p6_7_local_ok reports=1 md=1 parquets=12
```

核心驗證：

```json
{
  "raw_out": {
    "rows": 4,
    "date_min": "2026-06-29",
    "date_max": "2026-07-02"
  },
  "adj_out": {
    "rows": 4,
    "date_min": "2026-06-29",
    "date_max": "2026-07-02"
  },
  "benchmark_out": {
    "rows": 4,
    "date_min": "2026-06-29",
    "date_max": "2026-07-02"
  }
}
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

Secret scan：

```text
scripts/extend_magic26_cache.py long_token_like_count=0 FINMIND_TOKEN_count=0
.github/workflows/magic26-ci-probe.yml long_token_like_count=0 FINMIND_TOKEN_count=4
```

workflow 裡只有 secret 名稱與 GitHub mask，不含 token 值。

## CI run

Run：

```text
url: https://github.com/zathuramse/magic26/actions/runs/28599749409
head_sha: 899720cdb5b1eff176bb38e45764e466b5413527
status: completed
conclusion: success
created_at: 2026-07-02T14:56:50Z
updated_at: 2026-07-02T14:57:34Z
```

手動 inputs：

```text
run_finmind_probe=true
run_cache_extension_probe=true
run_cache_extension_dry_run=true
snapshot_suffix=20210101_20260702
data_through=2026-07-02
```

## Artifact 驗證

Downloaded artifact files included：

```text
artifacts/magic26_ci_probe_manifest.json
artifacts/reports/daily_refresh/p5_daily_refresh_probe_20260702_145724.json
artifacts/reports/daily_refresh/p5_daily_refresh_probe_20260702_145724.md
artifacts/reports/daily_refresh/p6_6_magic26_ci_cache_probe_20260702_145725.json
artifacts/reports/daily_refresh/p6_6_magic26_ci_cache_probe_20260702_145725.md
artifacts/reports/daily_refresh/p5_3_extend_magic26_cache_local_write_20260702_145729.json
artifacts/reports/daily_refresh/p5_3_extend_magic26_cache_local_write_20260702_145729.md
```

正式 extender sample parquet：

```text
raw_6213_20210101_20260701.parquet
raw_6213_20210101_20260702.parquet
adj_6213_20210101_20260701.parquet
adj_6213_20210101_20260702.parquet
benchmark_TAIEX_20210101_20260701.parquet
benchmark_TAIEX_20210101_20260702.parquet
```

P6-6 legacy probe parquet 也仍在 artifact：

```text
ci_probe_raw_6213_20260701_20260702.parquet
ci_probe_adj_6213_20260701_20260702.parquet
ci_probe_benchmark_TAIEX_20260701_20260702.parquet
```

Manifest：

```json
{
  "github_run_id": "28599749409",
  "github_sha": "899720cdb5b1eff176bb38e45764e466b5413527",
  "run_finmind_probe": "true",
  "run_cache_extension_probe": "true",
  "run_cache_extension_dry_run": "true",
  "finmind_token_present": true,
  "counts": {
    "cache_files": 15,
    "out_files": 0,
    "report_files": 6
  }
}
```

Artifact counts：

```json
{
  "daily_report_json": 1,
  "p6_6_probe_report_json": 1,
  "p6_7_extend_report_json": 1,
  "parquet_files": 9
}
```

Daily probe：

```json
{
  "complete_data_through": "2026-07-02",
  "probe_error_count": 0
}
```

Extension report：

```json
{
  "dry_run": false,
  "sample_only": true,
  "bootstrap_sample_source": true,
  "source_suffix": "20210101_20260701",
  "target_suffix": "20210101_20260702",
  "tail_start": "2026-07-01",
  "target_date": "2026-07-02",
  "raw_6213_out": {
    "rows": 4,
    "date_min": "2026-06-29",
    "date_max": "2026-07-02"
  },
  "adj_6213_out": {
    "rows": 4,
    "date_min": "2026-06-29",
    "date_max": "2026-07-02"
  },
  "benchmark_out": {
    "rows": 4,
    "date_min": "2026-06-29",
    "date_max": "2026-07-02"
  }
}
```

Validation notes：

```text
raw sample 6213 extends to target date 2026-07-02.
adj sample 6213 extends to target date 2026-07-02.
benchmark_TAIEX extends to target date 2026-07-02.
```

## 結論

P6-7 成功：

```text
正式 extend_magic26_cache.py 已支援 sample-only CI staging
CI 可 bootstrap source sample cache
CI 可用 FinMind token 延伸 sample raw/adj/TAIEX 到 target_suffix
artifact 內包含正式 extender report 與 source/target sample parquet
static package verifier 與 repo guardrail 通過
```

這仍不是 full refresh。它只證明「正式 cache extension 腳本」可以在 GitHub Actions 的 `.ci` staging 裡做 sample extension。

## 下一步建議：P6-8

P6-8 應做「round pipeline dry-run feasibility」：

1. 不跑全市場。
2. 先把 round scripts 的硬編碼路徑/日期與 sample mode blocker 列出。
3. 建立 CI-only round feasibility probe，確認 round7/8/9 或 base signal scripts 哪些能吃 `.ci` cache/out。
4. 仍不 export、不 deploy、不 schedule。

若 P6-8 發現 round scripts 還強綁完整市場 cache，就先做 parameterization，不要硬跑 full refresh。
