# P6-3 GitHub Actions cache / artifact probe

日期：2026-07-02

## 目的

P6-2 已把 Magic26 research/cache/out 路徑改成 env-driven。P6-3 的目標是在 GitHub Actions 上建立下一階段 full refresh 所需的基礎能力：

1. CI staging directories：`.ci/research-brain/...` 與 `.ci/artifacts/...`。
2. GitHub Actions cache：保存/恢復 Magic26 parquet cache 目錄。
3. Artifact upload：每次 probe 上傳一份機器可讀 manifest 與可選 dry-run report。
4. Guardrail：CI 產物不得讓 repo 變 dirty。

## 非目標

這次仍然不做：

```text
schedule
full refresh
Cloudflare deploy
generated data commit
關閉 Hermes cron
```

## 變更

### `.gitignore`

新增：

```text
.ci/
```

讓 CI/local staging 產物不污染 git status。

### Report dir env override

更新：

```text
scripts/daily_refresh_magic26.py
scripts/extend_magic26_cache.py
```

新增支援：

```text
MAGIC26_REPORT_DIR
```

本機預設仍是：

```text
reports/daily_refresh
```

CI 則改寫到：

```text
.ci/artifacts/reports/daily_refresh
```

### GitHub Actions workflow

更新：

```text
.github/workflows/magic26-ci-probe.yml
```

新增 env：

```text
MAGIC26_REPORT_DIR=${{ github.workspace }}/.ci/artifacts/reports/daily_refresh
MAGIC26_ARTIFACT_DIR=${{ github.workspace }}/.ci/artifacts
RUN_FINMIND_PROBE=${{ inputs.run_finmind_probe }}
```

新增 steps：

```text
Prepare CI staging directories
Restore Magic26 research cache
Build CI probe artifact manifest
Upload CI probe artifact
```

使用 action 版本：

```text
actions/cache@v6.1.0
actions/upload-artifact@v7.0.1
```

版本由 GitHub API 查最新 release，不用猜。

## Artifact manifest

每次 CI probe 會產生：

```text
.ci/artifacts/magic26_ci_probe_manifest.json
```

內容包含：

```text
generated_at
github_run_id
github_sha
snapshot_suffix
data_through
run_finmind_probe
paths.dash_root
paths.research_root
paths.source_root
paths.cache_dir
paths.out_dir
paths.report_dir
counts.cache_files
counts.out_files
counts.report_files
note
```

用途是讓 P6-4 以後能確認 CI runner 實際使用哪個 cache/out/report 目錄，以及 dry-run 是否產生 report。

## 本地驗證

已執行：

```text
python -m py_compile scripts/*.py
node --check public/app.js
python scripts/verify_magic26_package.py \
  --snapshot-suffix 20210101_20260702 \
  --data-through 2026-07-02 \
  --app-cache-bust 20260702riskv2 \
  --css-cache-bust 20260701q
git diff --check
```

結果：

```text
ok magic26 package 2026-07-02 latest 2026-06-26
```

也驗證 `.ci/` ignored：在 `.ci/artifacts/reports/daily_refresh/` 建立測試檔後，`git status --porcelain -- .ci` 為空。

## GitHub Actions 實跑結果

待 P6-3 workflow push 後補記。

## 風險與下一步

目前 cache/artifact 層只是基礎設施。即使 CI probe 通過，也還不代表 GitHub Actions 可以 full refresh。

下一步 P6-4 應該做：

1. 手動 workflow with `run_finmind_probe=true`，確認 FinMind probe report 能進 artifact。
2. 小範圍 cache dry-run，確認 cache artifact/cache 行為。
3. 若 token 或 quota 不適合放 GitHub Actions，就改走 external storage 或 keep Hermes for ingestion。
4. 仍不 schedule，直到 full refresh dry-run 真正通過。
