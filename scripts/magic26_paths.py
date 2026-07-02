from __future__ import annotations

import os
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
DEFAULT_RESEARCH_ROOT = Path("C:/Users/abckf/research-brain")


def _path_from_env(name: str, default: Path) -> Path:
    value = os.getenv(name, "").strip()
    return Path(value).expanduser() if value else default


def dash_root() -> Path:
    """Magic26 dashboard repo root."""
    return _path_from_env("MAGIC26_DASH_ROOT", PROJECT)


def research_root() -> Path:
    """Research-brain root used by legacy Magic26 research scripts."""
    return _path_from_env("MAGIC26_RESEARCH_ROOT", DEFAULT_RESEARCH_ROOT)


def source_root() -> Path:
    """Magic26 source/research output root."""
    default = research_root() / "sources" / "strategy-checks" / "magic26"
    return _path_from_env("MAGIC26_SOURCE_ROOT", default)


def cache_dir() -> Path:
    """Per-stock parquet cache directory."""
    return _path_from_env("MAGIC26_CACHE_DIR", source_root() / "cache")


def out_dir() -> Path:
    """Research CSV/JSON output directory."""
    return _path_from_env("MAGIC26_OUT_DIR", source_root() / "out")
