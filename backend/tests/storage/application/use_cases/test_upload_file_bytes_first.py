"""E6 · W5: bytes-first upload + per-call channel audio MIME allowlist."""

from __future__ import annotations

from uuid import uuid4

import pytest
from expects import equal, expect

from src.common.domain.exceptions.storage import UnsupportedMimeError
from src.storage.application.use_cases import upload_file as upload_module
from src.storage.application.use_cases.upload_file import (
    UploadFileUseCase,
    bytes_to_upload_file,
)


class _FakeS3:
    def __init__(self):
        self.objects = []

    def put_object(self, **kwargs):
        self.objects.append(kwargs)


class _FakeFileRepo:
    async def save(self, document):
        return document


@pytest.fixture(autouse=True)
def _patch_s3(monkeypatch):
    fake = _FakeS3()
    monkeypatch.setattr(upload_module, "get_s3_client", lambda: fake)
    monkeypatch.setattr(upload_module.settings, "AWS_STORAGE_BUCKET_NAME", "bucket", raising=False)
    return fake


def test_bytes_to_upload_file__wraps_bytes_with_content_type():
    upload = bytes_to_upload_file(b"voice-bytes", "note.ogg", "audio/ogg")

    expect(upload.filename).to(equal("note.ogg"))
    expect(upload.content_type).to(equal("audio/ogg"))
    expect(upload.size).to(equal(len(b"voice-bytes")))


async def test_upload__audio_allowed_only_with_channel_extra_mimes(_patch_s3):
    upload = bytes_to_upload_file(b"OggS-bytes", "note.ogg", "audio/ogg")

    doc = await UploadFileUseCase(
        tenant_id=uuid4(),
        file=upload,
        file_repository=_FakeFileRepo(),
        extra_allowed_mimes=["audio/ogg"],
    ).execute()

    expect(doc.mime).to(equal("audio/ogg"))
    expect(len(_patch_s3.objects)).to(equal(1))
    expect(_patch_s3.objects[0]["ContentType"]).to(equal("audio/ogg"))


async def test_upload__audio_rejected_without_extra_mimes():
    upload = bytes_to_upload_file(b"OggS-bytes", "note.ogg", "audio/ogg")

    with pytest.raises(UnsupportedMimeError):
        await UploadFileUseCase(
            tenant_id=uuid4(),
            file=upload,
            file_repository=_FakeFileRepo(),
        ).execute()
