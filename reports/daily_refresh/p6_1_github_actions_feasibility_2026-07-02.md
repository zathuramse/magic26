# P6-1 GitHub Actions migration feasibility

日期：2026-07-02

## 背景

P5 已經把 Magic26 daily refresh 先做成 Hermes no-agent guarded scheduler。QQ 提出正確疑問：Cloudflare Pages 已部署後，資料 pipeline 是否應該能獨立自動化，而不是依賴 Hermes/Windows 本機。

本階段目標是把方向切到 CI-driven pipeline，但只做 feasibility 與最小 GitHub Actions probe，不做正式 scheduled refresh，不部署，不關閉 Hermes cron。

## 本階段交付

新增：

```text
requirements-ci.txt
.github/workflows/magic26-ci-probe.yml
reports/daily_refresh/p6_1_github_actions_feasibility_2026-07-02.md
```

## 新 workflow 性質

Workflow 名稱：

```text
Magic26 CI probe
```

觸發方式：

```text
workflow_dispatch only
```

刻意不加：

```text
schedule
push auto deploy
Cloudflare deploy
git commit/push generated data
full refresh
```

目的：先證明 GitHub Actions 能在 Linux runner 上做基本檢查，避免把尚未遷移完成的 full pipeline 偽裝成正式自動化。

## CI probe 目前做什麼

1. checkout repo
2. setup Python 3.11
3. install `requirements-ci.txt`
4. setup Node 20
5. compile Python scripts
6. `node --check public/app.js`
7. verify committed static dashboard package：

```text
python scripts/verify_magic26_package.py \
  --snapshot-suffix 20210101_20260702 \
  --data-through 2026-07-02 \
  --app-cache-bust 20260702riskv2 \
  --css-cache-bust 20260701q
```

8. optional FinMind dry-run probe when manually enabled：

```text
run_finmind_probe: true
```

9. guardrail：probe 不應產生任何 git diff。

## CI dependencies

新增 `requirements-ci.txt`：

```text
pandas>=2.2,<3
numpy>=1.26,<3
requests>=2.31,<3
pyarrow>=16,<23
```

原因：目前 Python scripts 主要 imports 為：

```text
pandas
numpy
requests
pyarrow/parquet backend
```

`pyarrow` 是為 parquet read/write 保留，雖然 P6-1 probe 主要驗證 committed static package，但後續 full refresh migration 一定會用到 parquet cache。

## 盤點出的 CI migration blockers

P6-1 的只讀盤點發現，完整 refresh 目前還不能直接搬到 GitHub Actions schedule，原因如下。

### 1. 多個腳本仍綁 Windows 絕對路徑

代表性路徑：

```text
C:/Users/abckf/research-brain/sources/strategy-checks/magic26/cache
C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out
C:/Users/abckf/research-brain
C:/Users/abckf/AppData/Local/hermes/profiles/jojo/.env
```

受影響腳本包含：

```text
scripts/extend_magic26_cache.py
scripts/magic26_guarded_refresh_deploy.py
scripts/magic26_signal_pilot.py
scripts/magic26_round4_execution_checks.py
scripts/magic26_round7_param_grid.py
scripts/magic26_round8_tradeability_checks.py
scripts/magic26_round9_close_exit_checks.py
scripts/magic26_round14_bootstrap_path_review.py
scripts/magic26_round15_priority_review_pack.py
scripts/magic26_round16_top10_manual_review.py
scripts/magic26_round17_b_retest_rearm_watch.py
scripts/magic26_round19_author_absorption.py
scripts/magic26_round20_60d_validation.py
scripts/magic26_round21_volgap_rescue_review.py
```

### 2. Pipeline 仍依賴 repo 外資料目錄

目前 many research outputs / cache 仍在：

```text
C:/Users/abckf/research-brain/sources/strategy-checks/magic26/
```

GitHub Actions runner 沒有這個目錄。因此 full refresh 需要先解決：

- cache 要放 repo、GitHub Actions cache、artifact、Release asset，或 Cloudflare R2/S3。
- out directory 要改成 repo-relative，例如 `data/research_out/`，或由 workflow artifact 承接。
- scripts 要接受 `--cache-dir` / `--out-dir` / env vars，而不是硬編 Windows 路徑。

### 3. Secrets 尚未遷移

CI 需要的 secrets：

```text
FINMIND_TOKEN
CLOUDFLARE_API_TOKEN
CLOUDFLARE_ACCOUNT_ID 或 wrangler 所需 Cloudflare auth
```

P6-1 workflow 只讀取 `${{ secrets.FINMIND_TOKEN }}`，且只在手動打開 `run_finmind_probe` 時使用。沒有保存或輸出 token。

### 4. Full refresh 的 commit/deploy 權限尚未設計

正式 scheduled workflow 若要 commit generated data，至少需要：

```text
permissions.contents: write
```

若要 deploy Cloudflare，還要配置 Cloudflare secrets。P6-1 刻意只用：

```text
permissions.contents: read
```

避免 probe workflow 具有寫入能力。

### 5. Hermes cron 仍是目前唯一已完整跑通的 full-runner

Hermes cron 不是終局，但目前它已經具備：

- local cache
- local research outputs
- Cloudflare deploy auth
- GitHub auth
- production QA
- Telegram error surface

GitHub Actions 還沒有這些完整條件，所以不能直接停掉 Hermes cron。

## 本地驗證結果

執行：

```text
python -m py_compile scripts/*.py
node --check public/app.js
python scripts/verify_magic26_package.py --snapshot-suffix 20210101_20260702 --data-through 2026-07-02 --app-cache-bust 20260702riskv2 --css-cache-bust 20260701q
git diff --check
git status --short --branch
```

結果：

```text
ok magic26 package 2026-07-02 latest 2026-06-26
## main...origin/main
?? .github/
?? requirements-ci.txt
```

代表新增 workflow/requirements 前，既有 package 驗證通過，沒有 production data 或 UI 變更。

## 現階段架構判斷

目前狀態：

```text
Hermes cron + Windows 本機 = full refresh runner
GitHub Actions = 尚未承擔 full refresh，只新增 probe/check 能力
Cloudflare Pages = static hosting / CDN
```

目標狀態：

```text
GitHub Actions = guarded refresh runner
Cloudflare Pages = static hosting / deploy target
Hermes = 監督/人工介入，不是核心 runtime
```

## 下一步建議：P6-2

P6-2 不應直接 schedule full refresh。建議先做「repo-relative path migration」。

優先順序：

1. 將 `CACHE`、`OUT_DIR`、`RESEARCH_ROOT` 參數化：
   - CLI args: `--cache-dir`, `--out-dir`, `--research-root`
   - env vars: `MAGIC26_CACHE_DIR`, `MAGIC26_OUT_DIR`, `MAGIC26_RESEARCH_ROOT`
   - 預設維持目前 Windows 路徑，避免破壞 Hermes full-runner。
2. 讓 `magic26_guarded_refresh_deploy.py` 把 path 參數傳給下游 scripts。
3. 在 GitHub Actions 中用 repo-relative staging 目錄：

```text
.cache/magic26/
data/research_out/
```

4. 只在 CI 跑 dry-run/probe，不 commit、不 deploy。
5. 等 CI 能產生 target outputs artifact 後，再進 P6-3 設計 cache persistence。

## 結論

P6-1 完成的是正確的第一步：建立 GitHub Actions probe，但不誇大成正式自動化。

目前 full refresh 仍依賴 Hermes/Windows 本機，主要 blocker 是 repo 外 cache/out 與 Windows 絕對路徑。下一步應先把 paths 參數化，再談 GitHub Actions schedule。