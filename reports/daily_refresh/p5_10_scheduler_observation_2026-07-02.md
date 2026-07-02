# P5-10 Magic26 guarded scheduler observation

日期：2026-07-02

## 目的

延續 P5-9 guarded scheduler setup，確認 Hermes cron 排程層、Magic26 cron wrapper、production dashboard 狀態都可正常運作。

本階段不是新增資料刷新功能，也不是重新部署。目標是確認：

1. 08:00 / 16:00 兩個 Magic26 guarded cron jobs 都能被 scheduler 執行。
2. Dashboard 已是最新時，cron wrapper 會靜默 skip，不打擾 Telegram。
3. skip run 不污染 git worktree。
4. production dashboard 仍維持 P5-8 部署後的正確狀態。

## Cron jobs

### Magic26 guarded refresh 08:00

```text
job_id: 4176e26699eb
schedule: 0 8 * * 1-5
script: magic26_guarded_refresh_cron.py
no_agent: true
profile: jojo
last_run_at: 2026-07-02T19:19:54.990207+08:00
last_status: ok
next_run_at: 2026-07-03T08:00:00+08:00
```

### Magic26 guarded refresh 16:00

```text
job_id: e86814f1e768
schedule: 0 16 * * 1-5
script: magic26_guarded_refresh_cron.py
no_agent: true
profile: jojo
last_run_at: 2026-07-02T19:39:57.222643+08:00
last_status: ok
next_run_at: 2026-07-03T16:00:00+08:00
```

## Scheduler status

檢查時間：

```text
2026-07-02 19:37:48 +0800
```

Hermes cron status 顯示 gateway running：

```text
Gateway is running — cron jobs will fire automatically
PID: 17124
6 active job(s)
```

手動觸發 16:00 job 後，scheduler 曾短暫顯示 next run 為剛排入的時間。等待完整 tick 後，next run 正常前進到下一個 job：

```text
Next run: 2026-07-02T21:00:00+08:00
```

再讀 cron list，16:00 Magic26 job 已回寫：

```text
last_status: ok
next_run_at: 2026-07-03T16:00:00+08:00
```

## Wrapper 靜默 skip 測試

直接執行 cron wrapper：

```text
python C:/Users/abckf/AppData/Local/hermes/profiles/jojo/scripts/magic26_guarded_refresh_cron.py
```

結果：

```text
rc=0
stdout_bytes=0
```

這表示目前 dashboard 已是最新時，no-agent cron 不會輸出訊息，也不會打擾 Telegram。

## Local package verification

執行：

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

## Production HTTP verification

Production URL：

```text
https://magic26.pages.dev
```

確認結果：

```text
/data/summary.json: 200 application/json
summary: data_through=2026-07-02, latest_signal_date=2026-06-26, total_candidate_rows=311

/data/kline/raw_6213.json: 200 application/json
raw_6213 last=2026-07-02, rows=520

/data/kline/adj_6213.json: 200 application/json
adj_6213 last=2026-07-02, rows=520

/data/latest_signal_groups.json: 200 application/json
latest_groups=1
6213 risk_v2_level=2
6213 risk_v2_label_zh=高追高 / 只觀察
6213 risk_v2_is_display_only=True
```

## Git state

檢查結果：

```text
## main...origin/main
0 0
```

Runtime skip reports 寫入 ignored path：

```text
reports/daily_refresh/runtime/
```

不納入 git commit，避免 cron skip 污染 worktree。

## 注意事項

同一個 Hermes cron list 中有一個非 Magic26 job 顯示 error：

```text
Market rules Cloudflare deploy
last_status: error
```

這不是 Magic26 guarded scheduler 的錯誤，P5-10 未處理該 job。

## 結論

P5-10 通過。

Magic26 guarded scheduler 目前符合預期：

1. 08:00 / 16:00 兩個 Magic26 cron jobs 都已驗證可執行，狀態為 ok。
2. Dashboard 已是最新時，wrapper 會靜默 skip。
3. Production dashboard 仍維持 2026-07-02 資料與 6213 risk_v2 正確顯示。
4. Scheduler gateway running，下一次 Magic26 自然排程為 2026-07-03 08:00 與 16:00。

下一階段建議：P5-11 等待第一個自然排程日，觀察 08:00 / 16:00 是否在無手動觸發下正常運作；若 FinMind 出現新完整交易日，檢查完整 refresh/deploy path。