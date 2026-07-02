# P6-5 FinMind GitHub secret probe

日期：2026-07-02

## 目的

QQ 選擇 P6-5 credential decision gate 的 A 選項：授權把本機 FinMind token 設成 GitHub repo secret `FINMIND_TOKEN`，然後重跑 GitHub Actions FinMind probe。

本階段仍然不做：

```text
schedule
full refresh
Cloudflare deploy
generated data commit
關閉 Hermes cron
```

## Secret 設定

本機 token 來源：

```text
C:/Users/abckf/AppData/Local/hermes/profiles/jojo/.env
```

安全處理：

- 只檢查 token 存在與長度。
- 用 stdin 傳給 `gh secret set`。
- 不在 shell output、報告、git diff、artifact 中輸出 token 值。

GitHub repo secret 設定結果：

```text
FINMIND_TOKEN updatedAt=2026-07-02T14:25:11Z
```

## GitHub Actions probe

手動觸發：

```text
Magic26 CI probe
run_finmind_probe=true
snapshot_suffix=20210101_20260702
data_through=2026-07-02
```

Run：

```text
url: https://github.com/zathuramse/magic26/actions/runs/28597610924
head_sha: d6b8f159bd8482b0adb1ab6da24fcd9eb01a2315
status: completed
conclusion: success
created_at: 2026-07-02T14:25:20Z
updated_at: 2026-07-02T14:26:01Z
```

Artifact：

```text
magic26-ci-probe-28597610924
```

Artifact files：

```text
magic26_ci_probe_manifest.json
reports/daily_refresh/p5_daily_refresh_probe_20260702_142554.json
reports/daily_refresh/p5_daily_refresh_probe_20260702_142554.md
```

## Artifact verification

Downloaded artifact and parsed `magic26_ci_probe_manifest.json` plus daily refresh probe JSON.

Manifest summary：

```json
{
  "github_run_id": "28597610924",
  "github_sha": "d6b8f159bd8482b0adb1ab6da24fcd9eb01a2315",
  "run_finmind_probe": "true",
  "finmind_token_present": true,
  "counts": {
    "cache_files": 0,
    "out_files": 0,
    "report_files": 2
  }
}
```

Probe summary：

```json
{
  "current_snapshot_suffix": "20210101_20260702",
  "target_snapshot_suffix": "20210101_20260702",
  "current_dashboard_data_through": "2026-07-02",
  "complete_data_through": "2026-07-02",
  "should_refresh": false,
  "can_auto_refresh_now": false,
  "probe_count": 2,
  "probe_error_count": 0
}
```

Probe dates：

```text
2026-07-02 complete=true raw_rows=40874 adjusted_rows=2768 benchmark_rows=1
2026-07-01 complete=true raw_rows=40779 adjusted_rows=2768 benchmark_rows=1
```

Blockers still present：

```text
Target snapshot suffix equals current suffix; no new suffix transition is needed.
Found 4 remaining snapshot/date refs in round/cache scripts; parameterize before unattended refresh.
Dry-run mode: no cache/export/deploy side effects were executed.
```

## 結論

P6-5 成功：

```text
GitHub repo secret FINMIND_TOKEN 已設定
GitHub Actions 可用 token 跑 FinMind completeness probe
complete_data_through=2026-07-02
probe_error_count=0
artifact 內有 manifest + JSON/MD report
```

這代表 GitHub Actions 已經能做資料完整性 probe，但仍不能直接 full refresh，因為：

1. 還有 4 個 remaining snapshot/date refs。
2. 目前只 probe completeness，沒有產生 parquet cache、round outputs、dashboard export。
3. 沒有 deploy / schedule / generated-data commit permission。

## 下一步建議：P6-6

P6-6 應該做「CI cache dry-run with real FinMind token」：

1. 手動 workflow 增加一個選項，例如 `run_cache_extension_probe=true`。
2. 在 CI 使用 repo-relative `.ci/research-brain/.../cache`。
3. 只跑小範圍 cache dry-run / sample stock，不寫 production data。
4. Artifact 內確認：
   - daily raw/adj parquet 或 dry-run report
   - sample stock 6213 raw/adj 可延伸至 target date
   - benchmark_TAIEX 可延伸至 target date
5. 仍不 schedule、不 deploy、不 commit generated data。
