from __future__ import annotations

import json
from pathlib import Path

from app.models.upload import UploadRecord
from app.storage.file_store import STORAGE_ROOT


_UPLOADS: dict[str, UploadRecord] = {}
_AUDIT_INDEX_PATH = STORAGE_ROOT / "audit" / "audit_index.json"


def save_upload(record: UploadRecord) -> UploadRecord:
    _UPLOADS[record.upload_id] = record
    _persist_audit_index()
    return record


def get_upload(upload_id: str) -> UploadRecord | None:
    if upload_id in _UPLOADS:
        return _UPLOADS[upload_id]
    _load_audit_index()
    return _UPLOADS.get(upload_id)


def list_uploads() -> list[UploadRecord]:
    _load_audit_index()
    return sorted(
        _UPLOADS.values(),
        key=lambda upload: upload.generated_at or upload.uploaded_at or "",
        reverse=True,
    )


def clear_uploads_for_tests() -> None:
    _UPLOADS.clear()
    if _AUDIT_INDEX_PATH.exists():
        _AUDIT_INDEX_PATH.unlink()


def _load_audit_index() -> None:
    if not _AUDIT_INDEX_PATH.exists():
        return
    try:
        payload = json.loads(_AUDIT_INDEX_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(payload, dict):
        return
    for upload_id, raw_record in payload.items():
        if upload_id in _UPLOADS or not isinstance(raw_record, dict):
            continue
        try:
            _UPLOADS[upload_id] = UploadRecord.model_validate(raw_record)
        except ValueError:
            continue


def _persist_audit_index() -> None:
    _AUDIT_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        upload_id: record.model_dump(mode="json")
        for upload_id, record in sorted(_UPLOADS.items())
    }
    _safe_write_json(_AUDIT_INDEX_PATH, payload)


def _safe_write_json(path: Path, payload: dict) -> None:
    temporary_path = path.with_suffix(".tmp")
    temporary_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary_path.replace(path)
