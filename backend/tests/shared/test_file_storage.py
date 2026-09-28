import io
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.shared.file_storage import (
    ALLOWED_IMAGE_MIME_TYPES,
    MAX_FILE_SIZE_BYTES,
    FileNotFoundStorageError,
    FileSizeLimitExceededError,
    FileStorageError,
    InvalidFileTypeError,
    LocalFileStorage,
    S3FileStorage,
    detect_mime_type_from_bytes,
    get_file_storage,
    sanitize_storage_path,
    validate_image_file,
)

# Minimal valid magic byte headers for tests
VALID_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00"
VALID_PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
VALID_WEBP = b"RIFF\x1c\x00\x00\x00WEBPVP8 \x10\x00\x00\x00\x30\x01\x00\x9d\x01\x2a\x01\x00\x01\x00"


@pytest.fixture
def temp_storage(tmp_path: Path):
    return LocalFileStorage(base_dir=tmp_path / "uploads", base_url="/test-uploads")


def test_mime_detection_and_validation():
    assert detect_mime_type_from_bytes(VALID_JPEG) == "image/jpeg"
    assert detect_mime_type_from_bytes(VALID_PNG) == "image/png"
    assert detect_mime_type_from_bytes(VALID_WEBP) == "image/webp"
    assert detect_mime_type_from_bytes(b"NOT_AN_IMAGE") is None

    # Valid images pass validation
    assert validate_image_file(VALID_JPEG) == "image/jpeg"
    assert validate_image_file(VALID_PNG) == "image/png"
    assert validate_image_file(VALID_WEBP) == "image/webp"


def test_sanitize_storage_path():
    assert sanitize_storage_path("photos/user1/image.jpg") == "photos/user1/image.jpg"
    assert sanitize_storage_path("/photos//user1/image.jpg") == "photos/user1/image.jpg"
    assert sanitize_storage_path("photos\\user1\\image.jpg") == "photos/user1/image.jpg"

    with pytest.raises(FileStorageError, match="Path traversal detected"):
        sanitize_storage_path("../../etc/passwd")

    with pytest.raises(FileStorageError, match="Path traversal detected"):
        sanitize_storage_path("photos/../../secret.jpg")


@pytest.mark.asyncio
async def test_local_upload_and_get_url(temp_storage: LocalFileStorage):
    dest = "work_photos/entry_1/sample.jpg"
    url = await temp_storage.upload_file(VALID_JPEG, dest, content_type="image/jpeg")

    assert url == "/test-uploads/work_photos/entry_1/sample.jpg"
    assert await temp_storage.file_exists(dest) is True

    # Check signed / access URL
    signed_url = await temp_storage.get_signed_url(dest)
    assert signed_url == "/test-uploads/work_photos/entry_1/sample.jpg"

    # Verify physical file contents
    physical_file = temp_storage.base_dir / "work_photos" / "entry_1" / "sample.jpg"
    assert physical_file.exists()
    assert physical_file.read_bytes() == VALID_JPEG


@pytest.mark.asyncio
async def test_local_upload_png_and_webp(temp_storage: LocalFileStorage):
    png_url = await temp_storage.upload_file(VALID_PNG, "photos/test.png")
    assert png_url == "/test-uploads/photos/test.png"

    webp_url = await temp_storage.upload_file(VALID_WEBP, "photos/test.webp")
    assert webp_url == "/test-uploads/photos/test.webp"


@pytest.mark.asyncio
async def test_local_upload_binary_io(temp_storage: LocalFileStorage):
    stream = io.BytesIO(VALID_JPEG)
    url = await temp_storage.upload_file(stream, "streams/test_stream.jpg")

    assert url == "/test-uploads/streams/test_stream.jpg"
    assert await temp_storage.file_exists("streams/test_stream.jpg") is True


@pytest.mark.asyncio
async def test_oversized_file_rejected(temp_storage: LocalFileStorage):
    # Construct 10MB + 1 byte data with valid JPEG header
    oversized = VALID_JPEG + b"0" * (MAX_FILE_SIZE_BYTES - len(VALID_JPEG) + 1)
    assert len(oversized) > MAX_FILE_SIZE_BYTES

    with pytest.raises(FileSizeLimitExceededError, match="exceeds the maximum limit"):
        await temp_storage.upload_file(oversized, "photos/large.jpg")


@pytest.mark.asyncio
async def test_empty_file_rejected(temp_storage: LocalFileStorage):
    with pytest.raises(InvalidFileTypeError, match="File is empty"):
        await temp_storage.upload_file(b"", "photos/empty.jpg")


@pytest.mark.asyncio
async def test_invalid_mime_type_rejected(temp_storage: LocalFileStorage):
    # Plain text file
    with pytest.raises(InvalidFileTypeError, match="Unsupported file format"):
        await temp_storage.upload_file(b"This is just a text file", "docs/note.txt")

    # PDF header
    with pytest.raises(InvalidFileTypeError, match="Unsupported file format"):
        await temp_storage.upload_file(b"%PDF-1.4\n...", "docs/file.pdf")


@pytest.mark.asyncio
async def test_delete_file(temp_storage: LocalFileStorage):
    dest = "photos/to_delete.jpg"
    await temp_storage.upload_file(VALID_JPEG, dest)

    assert await temp_storage.file_exists(dest) is True
    assert await temp_storage.delete_file(dest) is True
    assert await temp_storage.file_exists(dest) is False

    # Deleting non-existent file returns False
    assert await temp_storage.delete_file(dest) is False


@pytest.mark.asyncio
async def test_get_signed_url_not_found(temp_storage: LocalFileStorage):
    with pytest.raises(FileNotFoundStorageError, match="File not found"):
        await temp_storage.get_signed_url("non_existent/file.jpg")


@pytest.mark.asyncio
async def test_s3_storage_uninstalled_boto3_raises():
    s3_storage = S3FileStorage(bucket_name="my-bucket")
    # In environments where boto3 is not installed, accessing client raises FileStorageError
    with pytest.raises(FileStorageError, match="boto3 is required"):
        s3_storage._get_client()


@pytest.mark.asyncio
async def test_s3_storage_with_mock_client():
    s3_storage = S3FileStorage(bucket_name="test-bucket")
    mock_boto3_client = MagicMock()
    s3_storage._client = mock_boto3_client

    # Test upload
    url = await s3_storage.upload_file(VALID_JPEG, "uploads/pic.jpg")
    assert url == "https://test-bucket.s3.amazonaws.com/uploads/pic.jpg"
    mock_boto3_client.put_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="uploads/pic.jpg",
        Body=VALID_JPEG,
        ContentType="image/jpeg",
    )

    # Test signed url
    mock_boto3_client.generate_presigned_url.return_value = "https://signed-url.example.com"
    signed_url = await s3_storage.get_signed_url("uploads/pic.jpg", expires_in=1800)
    assert signed_url == "https://signed-url.example.com"
    mock_boto3_client.generate_presigned_url.assert_called_once_with(
        "get_object",
        Params={"Bucket": "test-bucket", "Key": "uploads/pic.jpg"},
        ExpiresIn=1800,
    )

    # Test delete
    res = await s3_storage.delete_file("uploads/pic.jpg")
    assert res is True
    mock_boto3_client.delete_object.assert_called_once_with(Bucket="test-bucket", Key="uploads/pic.jpg")

    # Test exists
    mock_boto3_client.head_object.return_value = {}
    assert await s3_storage.file_exists("uploads/pic.jpg") is True

    mock_boto3_client.head_object.side_effect = Exception("Not found")
    assert await s3_storage.file_exists("uploads/missing.jpg") is False


def test_get_file_storage_factory():
    with patch.dict(os.environ, {"STORAGE_BACKEND": "local"}):
        storage = get_file_storage()
        assert isinstance(storage, LocalFileStorage)

    with patch.dict(os.environ, {"STORAGE_BACKEND": "s3"}):
        storage = get_file_storage()
        assert isinstance(storage, S3FileStorage)
