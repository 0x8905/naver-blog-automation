"""역할: 환경변수·경로. 비밀값은 출력하지 않는다.
고칠 때: 새 환경변수 기본값은 여기. 취향 필드는 taste.py.
"""

from __future__ import annotations

import os
from pathlib import Path


PKG_DIR = Path(__file__).resolve().parent


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'").strip('"'))


def load_env_files(cwd: Path | None = None) -> None:
    root = cwd or Path.cwd()
    load_dotenv(root / ".env")
    load_dotenv(Path.home() / ".nblog.env")


def data_dir() -> Path:
    raw = os.environ.get("NBLOG_DATA_DIR", "data")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def masked(value: str | None) -> str:
    if not value:
        return "(없음)"
    if len(value) <= 6:
        return "***"
    return value[:3] + "…" + value[-2:]
