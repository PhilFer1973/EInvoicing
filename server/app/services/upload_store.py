from __future__ import annotations

from app.models.upload import UploadRecord


_UPLOADS: dict[str, UploadRecord] = {}


def save_upload(record: UploadRecord) -> UploadRecord:
    _UPLOADS[record.upload_id] = record
    return record


def get_upload(upload_id: str) -> UploadRecord | None:
    return _UPLOADS.get(upload_id)


def list_uploads() -> list[UploadRecord]:
    return list(_UPLOADS.values())

