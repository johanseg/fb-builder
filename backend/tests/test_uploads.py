"""Upload endpoint tests at the shared storage boundary."""

from io import BytesIO
from unittest.mock import MagicMock

import pytest
from fastapi import status


JPEG = b"\xff\xd8\xff\xe0" + b"jpeg"
PNG = b"\x89PNG\r\n\x1a\n" + b"png"
GIF = b"GIF89a" + b"gif"
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"webp"
MP4 = b"\x00\x00\x00\x18ftypisom" + b"mp4"
AVI = b"RIFF\x00\x00\x00\x00AVI " + b"avi"
WEBM = b"\x1aE\xdf\xa3" + b"webm"


@pytest.fixture(autouse=True)
def mock_storage(monkeypatch):
    storage = MagicMock(side_effect=lambda _stream, filename: f"/uploads/{filename}")
    monkeypatch.setattr("app.api.v1.uploads.store_upload", storage)
    return storage


@pytest.mark.parametrize(
    ("filename", "content", "media_type"),
    [
        ("test.jpg", JPEG, "image"),
        ("test.jpeg", JPEG, "image"),
        ("test.png", PNG, "image"),
        ("test.gif", GIF, "image"),
        ("test.webp", WEBP, "image"),
        ("test.mp4", MP4, "video"),
        ("test.mov", MP4, "video"),
        ("test.avi", AVI, "video"),
        ("test.webm", WEBM, "video"),
    ],
)
def test_upload_valid_media(client, auth_headers, filename, content, media_type):
    response = client.post(
        "/api/v1/uploads/",
        files={"file": (filename, BytesIO(content), "application/octet-stream")},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK, response.text
    body = response.json()
    assert body["media_type"] == media_type
    assert body["url"].endswith(filename.split(".")[-1])


def test_upload_rejects_invalid_extension(client, auth_headers):
    response = client.post(
        "/api/v1/uploads/",
        files={"file": ("test.exe", BytesIO(b"MZ"), "application/octet-stream")},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_upload_rejects_mislabeled_signature(client, auth_headers):
    response = client.post(
        "/api/v1/uploads/",
        files={"file": ("test.png", BytesIO(JPEG), "image/png")},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_upload_rejects_oversized_image(client, auth_headers):
    response = client.post(
        "/api/v1/uploads/",
        files={"file": ("large.jpg", BytesIO(JPEG + b"x" * (11 * 1024 * 1024)), "image/jpeg")},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_upload_uses_shared_storage_result(client, auth_headers, mock_storage):
    mock_storage.side_effect = None
    mock_storage.return_value = "https://r2.example.test/uploads/asset.png"
    response = client.post(
        "/api/v1/uploads/",
        files={"file": ("asset.png", BytesIO(PNG), "image/png")},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["url"] == "https://r2.example.test/uploads/asset.png"
    mock_storage.assert_called_once()
