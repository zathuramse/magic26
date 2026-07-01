from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import magic26_signal_pilot as pilot  # noqa: E402

CACHE = Path("C:/Users/abckf/research-brain/sources/strategy-checks/magic26/cache")
OLD_SUFFIX = "20210101_20260622"
NEW_SUFFIX = "20210101_20260701"
TAIL_START = date(2026, 6, 23)
TAIL_END = date(2026, 7, 1)


def trading_days(start: date, end: date) -> list[str]:
    out = []
    d = start
    while d <= end:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def fetch_daily(dataset: str, tag: str) -> pd.DataFrame:
    frames = []
    for day in trading_days(TAIL_START, TAIL_END):
        cache_name = f"daily_{tag}_{day.replace('-', '')}.parquet"
        df = pilot.finmind_get(dataset, cache_name, start_date=day, end_date=day, sleep_s=0)
        if df.empty:
            print(f"WARN empty {dataset} {day}")
            continue
        df = df.copy()
        df["stock_id"] = df["stock_id"].astype(str)
        # Keep normal stock ids and benchmark rows required by round4/9.
        df = df[df["stock_id"].str.match(r"^\d{4}$") | df["stock_id"].isin(["TAIEX", "TPEx"])]
        frames.append(df)
        print(f"daily {tag} {day} rows={len(df)} stocks={df['stock_id'].nunique()}")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def extend_one(old_path: Path, daily: pd.DataFrame) -> bool:
    new_path = Path(str(old_path).replace(OLD_SUFFIX, NEW_SUFFIX))
    if new_path.exists():
        return False
    stock_id = old_path.name.split("_")[1]
    old = pd.read_parquet(old_path)
    old = old.copy()
    add = daily[daily["stock_id"].astype(str).eq(stock_id)].copy()
    if old.empty and "stock_id" not in old.columns:
        out = add.iloc[0:0].copy() if add.empty else add
    elif add.empty:
        # Preserve old empty/no-tail cases under the new cache name so the scanner remains deterministic.
        out = old
    else:
        old["stock_id"] = old["stock_id"].astype(str)
        out = pd.concat([old, add], ignore_index=True)
    if not out.empty and "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
        out = out.drop_duplicates(["date", "stock_id"], keep="last").sort_values("date")
    out.to_parquet(new_path, index=False)
    return True


def main() -> None:
    raw_daily = fetch_daily("TaiwanStockPrice", "raw")
    adj_daily = fetch_daily("TaiwanStockPriceAdj", "adj")
    counts = {}
    for tag, daily in [("raw", raw_daily), ("adj", adj_daily)]:
        made = 0
        skipped = 0
        for old_path in CACHE.glob(f"{tag}_*_{OLD_SUFFIX}.parquet"):
            if extend_one(old_path, daily):
                made += 1
            else:
                skipped += 1
        counts[tag] = {"made": made, "skipped_existing": skipped}
    # Benchmarks used by round4/9.
    for tag, daily in [("benchmark_TAIEX", raw_daily), ("benchmark_TAIEX", adj_daily)]:
        pass
    old_bench = CACHE / f"benchmark_TAIEX_{OLD_SUFFIX}.parquet"
    new_bench = CACHE / f"benchmark_TAIEX_{NEW_SUFFIX}.parquet"
    if old_bench.exists() and not new_bench.exists():
        old = pd.read_parquet(old_bench)
        add = raw_daily[raw_daily["stock_id"].eq("TAIEX")].copy()
        out = pd.concat([old, add], ignore_index=True)
        out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
        out = out.drop_duplicates(["date", "stock_id"], keep="last").sort_values("date")
        out.to_parquet(new_bench, index=False)
        counts["benchmark_TAIEX"] = {"made": 1, "skipped_existing": 0}
    else:
        counts["benchmark_TAIEX"] = {"made": 0, "skipped_existing": int(new_bench.exists())}
    print(counts)


if __name__ == "__main__":
    main()
