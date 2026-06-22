from __future__ import annotations

import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
required = [
    root / "public/index.html",
    root / "public/app.js",
    root / "public/styles.css",
    root / "public/data/summary.json",
    root / "public/data/latest_candidates.json",
    root / "public/data/recent_candidates.json",
    root / "public/data/magic26_candidates_history.csv",
    root / "scripts/export_dashboard_data.py",
    root / "scripts/deploy_cloudflare.py",
]
missing = [str(p) for p in required if not p.exists()]
if missing:
    print("missing required files:")
    print("\n".join(missing))
    sys.exit(1)

summary = json.loads((root / "public/data/summary.json").read_text(encoding="utf-8"))
if summary.get("main_spec") != "A_repo50_c4_40_fixed20":
    print("bad main_spec", summary.get("main_spec"))
    sys.exit(1)

for json_path in [root / "public/data/summary.json", root / "public/data/latest_candidates.json", root / "public/data/recent_candidates.json"]:
    text = json_path.read_text(encoding="utf-8")
    if "NaN" in text or "Infinity" in text:
        print("invalid non-strict JSON token in", json_path)
        sys.exit(1)
    json.loads(text)

for p in root.rglob("*"):
    if p.is_file() and p.suffix.lower() in {".env", ".pem", ".key", ".parquet"}:
        print("forbidden packaged file:", p)
        sys.exit(1)

print("ok magic26 package", summary.get("data_through"), "latest", summary.get("latest_signal_date"))
