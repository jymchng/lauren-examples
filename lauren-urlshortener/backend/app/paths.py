from __future__ import annotations

import os
from pathlib import Path


def ensure_data_dir(db_path: str) -> None:
    if db_path in (":memory:", "file::memory:?cache=shared") or not db_path:
        return
    parent = Path(db_path).expanduser().parent
    if parent and str(parent) and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
