# P6-2 Repo-relative path migration

日期：2026-07-02

## 目的

P6-1 已證明 Magic26 committed static package 可以在 GitHub Actions Linux runner 上驗證，但 full refresh 還不能直接搬到 CI，主因是許多 scripts 仍硬綁 Windows 本機路徑與 repo 外資料目錄。

P6-2 的目標是做最小可逆的 path migration：

1. 保留目前 Windows/Hermes 預設行為。
2. 新增 env-driven repo-relative path override。
3. 讓 GitHub Actions probe 可以驗證 path override 生效。
4. 不跑 full refresh、不 schedule、不 deploy、不關閉 Hermes cron。

## 新增 helper

新增：

```text
scripts/magic26_paths.py
```

提供：

```text
dash_root()
research_root()
source_root()
cache_dir()
out_dir()
```

支援 env vars：

```text
MAGIC26_DASH_ROOT
MAGIC26_RESEARCH_ROOT
MAGIC26_SOURCE_ROOT
MAGIC26_CACHE_DIR
MAGIC26_OUT_DIR
MAGIC26_ENV_FILE
```

預設仍維持目前 Windows 路徑：

```text
C:/Users/abckf/research-brain
C:/Users/abckf/research-brain/sources/strategy-checks/magic26
C:/Users/abckf/research-brain/sources/strategy-checks/magic26/cache
C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out
```

## 已參數化的 scripts

這次把原本硬綁 research root / cache / out 的主要 pipeline scripts 改為透過 helper 取得路徑：

```text
scripts/magic26_signal_pilot.py
scripts/extend_magic26_cache.py
scripts/extend_magic26_cache_to_20260701.py
scripts/magic26_guarded_refresh_deploy.py
scripts/export_dashboard_data.py
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

## GitHub Actions 更新

更新：

```text
.github/workflows/magic26-ci-probe.yml
```

新增 repo-relative staging env：

```text
MAGIC26_RESEARCH_ROOT: ${{ github.workspace }}/.ci/research-brain
MAGIC26_SOURCE_ROOT: ${{ github.workspace }}/.ci/research-brain/sources/strategy-checks/magic26
MAGIC26_CACHE_DIR: ${{ github.workspace }}/.ci/research-brain/sources/strategy-checks/magic26/cache
MAGIC26_OUT_DIR: ${{ github.workspace }}/.ci/research-brain/sources/strategy-checks/magic26/out
MAGIC26_DASH_ROOT: ${{ github.workspace }}
```

新增 workflow step：

```text
Verify repo-relative Magic26 path configuration
```

該 step 會 import `scripts/magic26_paths.py`，印出 dash/research/source/cache/out paths，並 assert cache/out 都走 `.ci` staging path。

## 本地驗證

執行：

```text
python -m py_compile scripts/*.py
```

結果：通過。

檢查預設 Windows 路徑：

```text
default_source_root C:\Users\abckf\research-brain\sources\strategy-checks\magic26
default_cache_dir C:\Users\abckf\research-brain\sources\strategy-checks\magic26\cache
```

檢查 env override：

```text
ci_dash_root C:\Users\abckf\research-brain\magic26
ci_cache_dir C:\Users\abckf\research-brain\magic26\.ci\research-brain\sources\strategy-checks\magic26\cache
ci_out_dir C:\Users\abckf\research-brain\magic26\.ci\research-brain\sources\strategy-checks\magic26\out
```

執行 static package verifier：

```text
python scripts/verify_magic26_package.py \
  --snapshot-suffix 20210101_20260702 \
  --data-through 2026-07-02 \
  --app-cache-bust 20260702riskv2 \
  --css-cache-bust 20260701q
```

結果：

```text
ok magic26 package 2026-07-02 latest 2026-06-26
```

執行 guarded dry-run skip：

```text
python scripts/magic26_guarded_refresh_deploy.py --dry-run --verbose --lookback-days 10 --stop-after-complete 2
```

結果：

```text
status: skipped_up_to_date
current_dashboard_data_through: 2026-07-02
complete_data_through: 2026-07-02
target_snapshot_suffix: 20210101_20260702
message: Dashboard already matches latest complete data.
```

## 剩餘 hard-coded path 掃描

P6-2 後，`C:/Users/abckf/research-brain` 只應存在於：

```text
scripts/magic26_paths.py
```

作為 Windows/Hermes 預設 fallback。

Hermes `.env` fallback 仍保留在 token readers：

```text
scripts/daily_refresh_magic26.py
scripts/magic26_signal_pilot.py
```

但已新增 `MAGIC26_ENV_FILE`，且 CI 優先使用 `FINMIND_TOKEN` env，因此不依賴 Hermes `.env`。

## GitHub Actions 實跑結果

P6-2 push 後手動觸發 `Magic26 CI probe`。

最終通過 run：

```text
url: https://github.com/zathuramse/magic26/actions/runs/28591150149
head_sha: 308f07275bdefd6d76cdfa085306aac8904f0b86
status: completed
conclusion: success
started_at: 2026-07-02T12:47:24Z
updated_at: 2026-07-02T12:47:53Z
```

Job 結果：

```text
Static package and refresh feasibility probe: success in 25s
```

新增的 `Verify repo-relative Magic26 path configuration` step 已通過，代表 GitHub Actions Linux runner 上的 env-driven `.ci` staging path 生效。

## 非目標

這次沒有：

```text
full refresh
Cloudflare deploy
GitHub Actions schedule
generated data commit
cache persistence 設計
關閉 Hermes cron
```

## 結論

P6-2 完成 path migration 的第一層：scripts 現在可以透過 env vars 切換到 repo-relative staging paths，同時不破壞 Windows/Hermes 既有預設。

這讓下一步 P6-3 可以專注於 cache/out persistence，而不是繼續被 Windows 絕對路徑卡住。

## 下一步建議：P6-3

設計 GitHub Actions cache / artifact / external storage：

1. 先用 GitHub Actions cache 保存 `.ci/research-brain/sources/strategy-checks/magic26/cache`。
2. 讓 workflow 能做 FinMind probe + cache dry-run。
3. 上傳 generated research outputs 為 artifact，不 commit、不 deploy。
4. 驗證 artifact 裡有 target suffix 的 round outputs。
5. 再決定是否進 P6-4 full refresh dry-run。