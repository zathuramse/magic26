# Magic26 手動更新 SOP

這個專案維持 pull-only：更新資料與網頁，但不推播、不下單、不接自動交易。

## 前提

- 研究原始輸出位於：`C:/Users/abckf/research-brain/sources/strategy-checks/magic26/out/`
- 本專案位於：`C:/Users/abckf/research-brain/magic26/`
- Cloudflare Pages project：`magic26`
- Production URL：https://magic26.pages.dev/

## 標準更新流程

在本專案目錄執行：

```bash
cd C:/Users/abckf/research-brain/magic26
npm run export
npm run check
git status --short
git add public/data data/processed
# 如果只更新資料，用資料更新 commit message
git commit -m "Update Magic26 dashboard data"
git push
npm run deploy
```

## 驗證點

`npm run export` 會從 research-brain 的 Magic26 research outputs 重建：

- `public/data/summary.json`
- `public/data/latest_candidates.json`
- `public/data/recent_candidates.json`
- `public/data/magic26_candidates_history.csv`
- `data/processed/*`

`npm run check` 會確認：

- 必要 dashboard 檔案存在；
- `summary.json.main_spec == A_repo50_c4_40_fixed20`；
- public JSON 沒有非法 `NaN` / `Infinity`；
- repo 沒有 `.env` / `.pem` / `.key` / `.parquet`。

`npm run deploy` 會：

1. 先跑 package verifier；
2. 用 Wrangler 部署 `public/` 到 Cloudflare Pages；
3. 列出 deployment；
4. 抓 production homepage 與 `data/summary.json` 驗證 HTTP 200 與核心欄位。

## 注意事項

- 不要把 `cache/`、parquet 價格資料、`.env`、憑證放進 repo。
- 這是研究候選清單，不是交易訊號服務。
- 若資料來源還沒更新，dashboard 仍會顯示舊的 `data_through` 與 `latest_signal_date`，不要假裝資料已更新。
- 若 Cloudflare per-deployment URL 有 SSL/cipher propagation 問題，優先驗證 canonical URL：`https://magic26.pages.dev/`。
