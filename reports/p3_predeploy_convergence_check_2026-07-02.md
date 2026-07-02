# Magic26 P3-3 部署前收斂檢查

日期：2026-07-02
狀態：local predeploy check；未 push、未 deploy。

## 範圍

本輪檢查 P2/P3 的 12 個 ahead commits 是否可進入 P4 push/deploy。

主要變更類型：

- P2 研究與風險規格報告
- P2 risk_v2 schema / dry-run
- P3-1 正式 export `risk_v2_*` 欄位
- P3-2 UI 顯示 `risk_v2` 主卡與 detail 風險文案
- P3-3 cache-bust 更新 `app.js?v=20260702riskv2`

## Git 狀態

```text
main...origin/main [ahead 12]
rev-list origin/main...HEAD = 0 12
```

Ahead commit stack：

```text
950ccac Show Magic26 risk v2 UI hints
bd6aad0 Export Magic26 risk v2 fields
c4f034f Add Magic26 risk v2 export dry run
d7b74b6 Add Magic26 risk field export schema
0c2f7a6 Add Magic26 risk display spec
040cd90 Add Magic26 risk veto replay audit
ca9960c Add Magic26 risk veto draft
67daea3 Add Magic26 dedup chase holdout audit
0d76c47 Add Magic26 holdout walkforward audit
845461d Add Magic26 layered sample table
9dbbdb1 Add neutral sample expansion plan
02da3f2 Add Magic26 signal strategy audit
```

## Local gates

已通過：

```text
node --check public/app.js
python -m py_compile scripts/export_dashboard_data.py scripts/verify_magic26_package.py scripts/deploy_cloudflare.py
python scripts/verify_magic26_package.py
git diff --check
```

Package verifier output：

```text
ok magic26 package 2026-06-30 latest 2026-06-26
```

## risk_v2 local verification summary

`risk_v2_*` 已存在於：

- `latest_signal_groups.json`
- `recent_signal_groups.json`
- `all_signal_groups.json`
- `latest_candidates.json`
- `recent_candidates.json`
- `all_candidates.json`
- `magic26_candidates_history.csv`

6213 正式 export 分類：

```text
risk_v2_level = 2
risk_v2_label_zh = 高追高 / 只觀察
risk_v2_primary_badge_zh = 只觀察
risk_v2_action_hint_zh = 只觀察；已偏追高，不建議直接追價
risk_v2_is_display_only = True
```

Browser QA 已驗：

- 主卡顯示 `只觀察｜已偏追高｜97分`
- 主卡「要小心」顯示 `只觀察；已偏追高，不建議直接追價`
- detail「風險檢查」顯示 `追高分級`、`高追高 / 只觀察`、`只作研究顯示，不是買賣訊號`
- console errors = 0

## Download links

`public/index.html` 的 `./data/...` links：

```text
count = 14
missing = []
```

## Security / packaging scan

Changed file scan：

```text
changed_files = 34
forbidden_files = []
large_files = []
credential_hits_count = 0
```

Forbidden suffix checked：

```text
.env
.pem
.key
.parquet
```

Credential-shaped string patterns checked：

```text
AKIA...
ghp_...
xox...
PRIVATE KEY
api_key / secret / token / password style assignments
```

## Cache-bust / service worker

檢查結果：

```text
app refs = app.js?v=20260702riskv2
css refs = styles.css?v=20260701q
service_workers = []
```

本輪有修改 `public/app.js`，所以已更新 `index.html` 的 app.js query string：

```text
from: app.js?v=20260701y
to:   app.js?v=20260702riskv2
```

CSS 未改，保留：

```text
styles.css?v=20260701q
```

## 注意事項

1. P3-3 尚未 push。
2. P3-3 尚未 deploy。
3. `origin/main...HEAD` range check 需在本報告與 whitespace/cache-bust 修正 commit 後再跑一次。
4. P4 若進行 push/deploy，需再跑：
   - `git diff --check origin/main...HEAD`
   - `gh auth status`
   - `git push origin main`
   - GitHub main readback
   - Cloudflare deploy
   - production canonical + per-deployment QA

## 結論

P3-3 local convergence 通過。下一步可進入 P4：push + deploy + production QA。
