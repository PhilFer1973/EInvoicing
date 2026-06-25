from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel


REPO_ROOT = Path(__file__).resolve().parents[3]
STORAGE_ROOT = REPO_ROOT / "server" / "storage"


def month_folder(kind: str) -> Path:
    now = datetime.now(UTC)
    folder = STORAGE_ROOT / kind / f"{now:%Y}" / f"{now:%m}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def save_binary(kind: str, filename: str, content: bytes) -> tuple[Path, str]:
    folder = month_folder(kind)
    path = folder / filename
    path.write_bytes(content)
    return path, sha256_bytes(content)


def save_json(kind: str, filename: str, payload: BaseModel | dict[str, Any]) -> tuple[Path, str]:
    folder = month_folder(kind)
    path = folder / filename
    if isinstance(payload, BaseModel):
        content = payload.model_dump(mode="json")
    else:
        content = payload
    encoded = json.dumps(content, indent=2, sort_keys=True).encode("utf-8")
    path.write_bytes(encoded)
    return path, sha256_bytes(encoded)


def relative_storage_path(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def storage_path_from_relative(relative_path: str) -> Path:
    path = (REPO_ROOT / relative_path).resolve()
    if not path.is_relative_to(REPO_ROOT):
        raise ValueError("Storage path escapes repository root.")
    return path
