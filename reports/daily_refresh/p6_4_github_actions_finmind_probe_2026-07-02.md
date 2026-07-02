# P6-4 GitHub Actions FinMind probe artifact run

日期：2026-07-02

## 目的

P6-4 延續 P6-3：在 GitHub Actions 手動 workflow 中打開 `run_finmind_probe=true`，確認 CI 能執行 `daily_refresh_magic26.py --dry-run`，並把 probe report 放進 artifact。

本階段仍然不做：

```text
schedule
full refresh
Cloudflare deploy
generated data commit
關閉 Hermes cron
```

## Preflight

本地 repo 狀態：

```text
origin/main...HEAD = 0 0
worktree clean
```

GitHub workflow 存在：

```text
Magic26 CI probe - magic26-ci-probe.yml
```

GitHub repo-level secrets 檢查：

```text
gh secret list --repo zathuramse/magic26
```

結果：沒有列出 `FINMIND_TOKEN`。

判斷：不應靜默把本機 FinMind token 搬到 GitHub。這是敏感憑證移轉，需明確授權後才能做。

## 第一次 CI probe：run_finmind_probe=true

Run：

```text
url: https://github.com/zathuramse/magic26/actions/runs/28596046308
head_sha: b1608e17101e5c9b4f0ee78a14f7fd473b55ee03
status: completed
conclusion: success
created_at: 2026-07-02T14:02:20Z
updated_at: 2026-07-02T14:03:02Z
```

Artifact 下載後確認：

```text
magic26_ci_probe_manifest.json
reports/daily_refresh/p5_daily_refresh_probe_20260702_140254.json
reports/daily_refresh/p5_daily_refresh_probe_20260702_140254.md
```

Probe 結果摘要：

```text
run_finmind_probe: true
report_files: 2
current_snapshot_suffix: 20210101_20260702
current_dashboard_data_through: 2026-07-02
complete_data_through: null
probe_count: 0
probe_error_count: 9
```

所有 probe dates 都是 HTTP 400。當時錯誤訊息只顯示 `<HTTPError 400: 'Bad Request'>`，不夠可診斷。

## 診斷

用不帶 token 的最小 FinMind request 測試：

```text
TaiwanStockPrice start_date=2026-07-02 end_date=2026-07-02
```

回應：

```json
{
  "status": 400,
  "msg": "Your level is free. Please update your user level. Detail information:https://finmindtrade.com/analysis/#/Sponsor/sponsor"
}
```

判斷：GitHub Actions 沒有 `FINMIND_TOKEN` 時，FinMind completeness probe 不能取得資料。這不是 Magic26 研究邏輯錯誤，而是 CI credential / FinMind quota 層 blocker。

## 修正：讓 artifact 更可診斷

新增 commit：

```text
b97452f Improve Magic26 CI FinMind probe diagnostics
```

變更：

```text
scripts/daily_refresh_magic26.py
.github/workflows/magic26-ci-probe.yml
```

內容：

1. `daily_refresh_magic26.py` 捕捉 `urllib.error.HTTPError`，解析 FinMind JSON body，將 `status/msg` 寫進 `probe_errors`。
2. CI artifact manifest 新增：

```text
finmind_token_present: boolean
```

只記錄 token 是否存在，不輸出 token 值。

本地 gates：

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

## 第二次 CI probe：diagnostic run

Run：

```text
url: https://github.com/zathuramse/magic26/actions/runs/28596234305
head_sha: b97452f53c753d06c69edf82f2d4a17887488e2a
status: completed
conclusion: success
created_at: 2026-07-02T14:04:59Z
updated_at: 2026-07-02T14:05:35Z
```

Artifact：

```text
magic26_ci_probe_manifest.json
reports/daily_refresh/p5_daily_refresh_probe_20260702_140532.json
reports/daily_refresh/p5_daily_refresh_probe_20260702_140532.md
```

Manifest 摘要：

```json
{
  "github_run_id": "28596234305",
  "github_sha": "b97452f53c753d06c69edf82f2d4a17887488e2a",
  "run_finmind_probe": "true",
  "finmind_token_present": false,
  "counts": {
    "cache_files": 0,
    "out_files": 0,
    "report_files": 2
  }
}
```

Probe 摘要：

```json
{
  "current_snapshot_suffix": "20210101_20260702",
  "target_snapshot_suffix": null,
  "current_dashboard_data_through": "2026-07-02",
  "complete_data_through": null,
  "should_refresh": false,
  "can_auto_refresh_now": false,
  "probe_count": 0,
  "probe_error_count": 9,
  "first_probe_error": {
    "date": "2026-07-02",
    "error": "RuntimeError('FinMind TaiwanStockPrice HTTP 400: status=400 msg=Your level is free. Please update your user level. Detail information:https://finmindtrade.com/analysis/#/Sponsor/sponsor')"
  }
}
```

Blockers：

```text
No complete raw+adjusted+benchmark trading day found in probe window.
Found 4 remaining snapshot/date refs in round/cache scripts; parameterize before unattended refresh.
Dry-run mode: no cache/export/deploy side effects were executed.
```

## 結論

P6-4 達成：

```text
GitHub Actions 可以執行 run_finmind_probe=true path
artifact 會包含 daily_refresh JSON/MD report
artifact manifest 可確認 token presence 與 report count
repo guardrail 不被 .ci artifact 污染
```

P6-4 同時確認 blocker：

```text
GitHub repo 目前沒有 FINMIND_TOKEN secret
沒有 token 時 FinMind completeness probe 回 HTTP 400 / free-level limitation
因此 GitHub Actions 還不能可靠執行資料完整性 probe
```

## 不做的事

這次沒有把本機 token 搬到 GitHub，也沒有啟用 deploy/schedule/full refresh。

## 下一步建議：P6-5

P6-5 應該是「credential decision gate」，而不是繼續寫 pipeline：

選項 A：QQ 明確授權後，把 FinMind token 設為 GitHub repo secret：

```text
FINMIND_TOKEN
```

然後重跑 P6-4，確認：

```text
finmind_token_present: true
complete_data_through != null
probe_count > 0
probe_error_count = 0 或只剩非交易日錯誤
```

選項 B：不把 FinMind token 放 GitHub。則 GitHub Actions 只能做 static package / artifact probe，資料 ingestion 繼續由 Hermes/Windows runner 執行。

選項 C：改用外部 storage / worker / self-hosted runner，把 token 留在受控環境，不放 GitHub repo secrets。
