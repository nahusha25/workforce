import io
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.shared.file_storage import (
    ALLOWED_IMAGE_MIME_TYPES,
    ALLOWED_RECEIPT_MIME_TYPES,
    MAX_FILE_SIZE_BYTES,
    AmbiguousReceiptStorageError,
    FileNotFoundStorageError,
    FileSizeLimitExceededError,
    FileStorageError,
    InvalidFileTypeError,
    LocalFileStorage,
    S3FileStorage,
    detect_mime_type_from_bytes,
    get_file_storage,
    get_receipt_file_path,
    sanitize_storage_path,
    save_receipt_file,
    validate_image_file,
    validate_receipt_file,
)

# Minimal valid magic byte headers for tests
VALID_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00"
VALID_PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
VALID_WEBP = b"RIFF\x1c\x00\x00\x00WEBPVP8 \x10\x00\x00\x00\x30\x01\x00\x9d\x01\x2a\x01\x00\x01\x00"
VALID_PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"


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


def test_receipt_validation():
    # Valid types pass
    assert validate_receipt_file(VALID_PDF) == "application/pdf"
    assert validate_receipt_file(VALID_JPEG) == "image/jpeg"
    assert validate_receipt_file(VALID_PNG) == "image/png"
    assert validate_receipt_file(VALID_WEBP) == "image/webp"

    # Empty file rejected
    with pytest.raises(InvalidFileTypeError, match="File is empty"):
        validate_receipt_file(b"")

    # Unsupported format (e.g. text file)
    with pytest.raises(InvalidFileTypeError, match="Unsupported file format"):
        validate_receipt_file(b"Plain text not allowed for receipt")

    # Oversized file (>10MB) rejected
    oversized = VALID_PDF + b"0" * (MAX_FILE_SIZE_BYTES - len(VALID_PDF) + 1)
    with pytest.raises(FileSizeLimitExceededError, match="exceeds the maximum limit"):
        validate_receipt_file(oversized)

    # Spoofed PDF rejected (invalid magic bytes despite application/pdf MIME)
    with pytest.raises(InvalidFileTypeError, match="Unsupported file format"):
        validate_receipt_file(b"<html><body>Spoofed PDF content</body></html>", content_type="application/pdf")


def test_receipt_storage_lifecycle_and_replacement(tmp_path: Path):
    payment_id = "test-payment-uuid-1234"
    receipts_base = tmp_path / "private_receipts"

    # 1. No receipt initially
    assert get_receipt_file_path(payment_id, base_dir=receipts_base) is None

    # 2. Save first receipt (PDF)
    path1, mime1 = save_receipt_file(
        payment_id=payment_id,
        file_bytes=VALID_PDF,
        original_filename="bank_transfer.pdf",
        content_type="application/pdf",
        base_dir=receipts_base,
    )
    assert mime1 == "application/pdf"
    assert path1.exists()
    assert "bank_transfer.pdf" in path1.name

    # Verify retrieval
    retrieved = get_receipt_file_path(payment_id, base_dir=receipts_base)
    assert retrieved is not None
    assert retrieved[0] == path1
    assert retrieved[1] == "application/pdf"

    # 3. Save new receipt (JPEG) - leaves path1 intact until old receipts are cleared
    path2, mime2 = save_receipt_file(
        payment_id=payment_id,
        file_bytes=VALID_JPEG,
        original_filename="deposit_slip.jpg",
        content_type="image/jpeg",
        base_dir=receipts_base,
    )
    assert mime2 == "image/jpeg"
    assert path2.exists()
    assert "deposit_slip.jpg" in path2.name
    # Both exist prior to cleanup
    assert path1.exists()

    # Verify retrieval with missing reference raises AmbiguousReceiptStorageError when multiple files exist
    with pytest.raises(AmbiguousReceiptStorageError, match="Multiple candidate receipt files found"):
        get_receipt_file_path(payment_id, base_dir=receipts_base)

    # Verify retrieval with exact reference returns path2
    retrieved2 = get_receipt_file_path(payment_id, base_dir=receipts_base, storage_ref=path2.name)
    assert retrieved2 is not None
    assert retrieved2[0] == path2
    assert retrieved2[1] == "image/jpeg"

    # Once old file is deleted, single candidate remains and can be retrieved without exact ref
    path1.unlink()
    retrieved_single = get_receipt_file_path(payment_id, base_dir=receipts_base)
    assert retrieved_single is not None
    assert retrieved_single[0] == path2
    assert retrieved_single[1] == "image/jpeg"


@pytest.mark.asyncio
async def test_local_file_storage_receipt_methods(tmp_path: Path):
    storage = LocalFileStorage(receipts_dir=tmp_path / "receipts")
    payment_id = "test-payment-uuid-5678"

    # 1. Initially no receipt
    assert await storage.get_receipt(payment_id) is None

    # 2. Upload initial PDF receipt
    target_ref, mime = await storage.upload_receipt(
        payment_id=payment_id,
        file_bytes=VALID_PDF,
        original_filename="payment_slip.pdf",
        content_type="application/pdf",
    )
    assert mime == "application/pdf"
    assert target_ref.startswith(f"receipts/{payment_id}/")
    file1 = storage._get_receipt_dir(payment_id) / Path(target_ref).name
    assert file1.exists()

    # 3. Retrieve receipt by exact reference
    res = await storage.get_receipt(payment_id, storage_ref=target_ref)
    assert res is not None
    assert res.file_path == file1
    assert res.media_type == "application/pdf"

    # 4. Upload replacement JPEG receipt without deleting old receipt yet
    target2_ref, mime2 = await storage.upload_receipt(
        payment_id=payment_id,
        file_bytes=VALID_JPEG,
        original_filename="deposit.jpg",
        content_type="image/jpeg",
    )
    assert mime2 == "image/jpeg"
    file2 = storage._get_receipt_dir(payment_id) / Path(target2_ref).name
    assert file1.exists()
    assert file2.exists()

    # 5. Clean up old receipt by exact reference (not timestamp-based)
    deleted_old = await storage.delete_receipt(payment_id, storage_ref=target_ref)
    assert deleted_old is True
    assert not file1.exists()
    assert file2.exists()

    # 6. Verify active receipt remains accessible
    res2 = await storage.get_receipt(payment_id, storage_ref=target2_ref)
    assert res2 is not None
    assert res2.file_path == file2

    # 7. Delete active receipt
    deleted = await storage.delete_receipt(payment_id, storage_ref=target2_ref)
    assert deleted is True
    assert await storage.get_receipt(payment_id, storage_ref=target2_ref) is None


@pytest.mark.asyncio
async def test_local_file_storage_equal_timestamps_retrieval_and_exact_cleanup(tmp_path: Path):
    storage = LocalFileStorage(receipts_dir=tmp_path / "receipts_equal_ts")
    payment_id = "test-payment-equal-ts-1234"

    ref1, _ = await storage.upload_receipt(
        payment_id=payment_id,
        file_bytes=VALID_PDF,
        original_filename="slip_one.pdf",
        content_type="application/pdf",
    )
    ref2, _ = await storage.upload_receipt(
        payment_id=payment_id,
        file_bytes=VALID_PNG,
        original_filename="slip_two.png",
        content_type="image/png",
    )
    file1 = storage._get_receipt_dir(payment_id) / Path(ref1).name
    file2 = storage._get_receipt_dir(payment_id) / Path(ref2).name

    # Artificially set both files to the exact same mtime timestamp
    fixed_ts = 1700000000.0
    os.utime(file1, (fixed_ts, fixed_ts))
    os.utime(file2, (fixed_ts, fixed_ts))
    assert file1.stat().st_mtime == file2.stat().st_mtime

    # Retrieve each file by its exact reference - exact match regardless of equal timestamp
    res1 = await storage.get_receipt(payment_id, storage_ref=ref1)
    res2 = await storage.get_receipt(payment_id, storage_ref=ref2)
    assert res1 is not None and res1.file_path == file1
    assert res2 is not None and res2.file_path == file2

    # Delete ref1 by exact reference - ref2 must remain intact despite identical mtime
    await storage.delete_receipt(payment_id, storage_ref=ref1)
    assert not file1.exists()
    assert file2.exists()

    res2_after = await storage.get_receipt(payment_id, storage_ref=ref2)
    assert res2_after is not None and res2_after.file_path == file2


@pytest.mark.asyncio
async def test_s3_file_storage_receipt_methods():
    storage = S3FileStorage(bucket_name="test-bucket")
    mock_s3 = MagicMock()
    storage._client = mock_s3

    payment_id = "payment-s3-1122"

    # 1. Upload receipt to S3
    key, mime = await storage.upload_receipt(
        payment_id=payment_id,
        file_bytes=VALID_PDF,
        original_filename="cheque.pdf",
        content_type="application/pdf",
    )
    assert mime == "application/pdf"
    assert key.startswith(f"receipts/{payment_id}/")
    mock_s3.put_object.assert_called_once_with(
        Bucket="test-bucket",
        Key=key,
        Body=VALID_PDF,
        ContentType="application/pdf",
    )

    # 2. Get receipt from S3 by exact reference
    mock_body = MagicMock()
    mock_body.read.return_value = VALID_PDF
    mock_s3.get_object.return_value = {
        "Body": mock_body,
        "ContentType": "application/pdf",
    }

    res = await storage.get_receipt(payment_id, storage_ref=key)
    assert res is not None
    assert res.file_bytes == VALID_PDF
    assert res.media_type == "application/pdf"
    mock_s3.get_object.assert_called_with(Bucket="test-bucket", Key=key)

    # 3. Delete old receipts
    old_key = f"receipts/{payment_id}/old_receipt.png"
    mock_s3.list_objects_v2.return_value = {
        "Contents": [
            {"Key": key},
            {"Key": old_key},
        ]
    }
    await storage.delete_old_receipts(payment_id, keep_ref=key)
    mock_s3.delete_object.assert_called_with(Bucket="test-bucket", Key=old_key)

    # 4. Delete receipt by exact reference
    await storage.delete_receipt(payment_id, storage_ref=key)
    mock_s3.delete_object.assert_called_with(Bucket="test-bucket", Key=key)


def test_s3_file_storage_boto3_missing():
    storage = S3FileStorage(bucket_name="test-bucket")
    storage._client = None
    with patch.dict("sys.modules", {"boto3": None}):
        with pytest.raises(FileStorageError, match="boto3 is required"):
            storage._get_client()


@pytest.mark.asyncio
async def test_local_file_storage_legacy_fallback_matrix(tmp_path: Path):
    """
    Tests LocalFileStorage legacy fallback matrix:
    - 0 files: return None / False
    - 1 file: return single file / delete single file
    - Multiple files: raise AmbiguousReceiptStorageError on missing or /api/ reference (never guess or delete multiple)
    - Exact reference: works even when multiple files exist
    """
    storage = LocalFileStorage(receipts_dir=tmp_path / "legacy_matrix")
    payment_id = "test-legacy-matrix-pid-999"

    # Case 0 files
    assert await storage.get_receipt(payment_id, storage_ref=None) is None
    assert await storage.get_receipt(payment_id, storage_ref=f"/api/v1/client-payments/{payment_id}/receipt") is None
    assert await storage.delete_receipt(payment_id, storage_ref=None) is False
    assert await storage.delete_receipt(payment_id, storage_ref=f"/api/v1/client-payments/{payment_id}/receipt") is False

    # Upload 1 file
    ref1, _ = await storage.upload_receipt(
        payment_id=payment_id,
        file_bytes=VALID_PDF,
        original_filename="receipt_one.pdf",
        content_type="application/pdf",
    )
    p_dir = storage._get_receipt_dir(payment_id)
    file1 = p_dir / Path(ref1).name
    assert file1.exists()

    # Case 1 file: legacy retrieval succeeds with both None and /api/
    res_none = await storage.get_receipt(payment_id, storage_ref=None)
    assert res_none is not None and res_none.file_path == file1
    res_api = await storage.get_receipt(payment_id, storage_ref=f"/api/v1/client-payments/{payment_id}/receipt")
    assert res_api is not None and res_api.file_path == file1

    # Upload second file to create ambiguity
    ref2, _ = await storage.upload_receipt(
        payment_id=payment_id,
        file_bytes=VALID_PNG,
        original_filename="receipt_two.png",
        content_type="image/png",
    )
    file2 = p_dir / Path(ref2).name
    assert file2.exists()
    assert len(list(p_dir.iterdir())) == 2

    # Case multiple files: missing or /api/ reference MUST raise AmbiguousReceiptStorageError
    with pytest.raises(AmbiguousReceiptStorageError, match="Multiple candidate receipt files found"):
        await storage.get_receipt(payment_id, storage_ref=None)

    with pytest.raises(AmbiguousReceiptStorageError, match="Multiple candidate receipt files found"):
        await storage.get_receipt(payment_id, storage_ref=f"/api/v1/client-payments/{payment_id}/receipt")

    # Exact reference retrieves exact file despite multiple files present
    res_exact1 = await storage.get_receipt(payment_id, storage_ref=ref1)
    assert res_exact1 is not None and res_exact1.file_path == file1

    res_exact2 = await storage.get_receipt(payment_id, storage_ref=ref2)
    assert res_exact2 is not None and res_exact2.file_path == file2

    # Ambiguous deletion with missing or /api/ reference NEVER deletes any files
    with pytest.raises(AmbiguousReceiptStorageError, match="Cannot delete receipt: multiple candidate files found"):
        await storage.delete_receipt(payment_id, storage_ref=None)
    assert file1.exists() and file2.exists()

    with pytest.raises(AmbiguousReceiptStorageError, match="Cannot delete receipt: multiple candidate files found"):
        await storage.delete_receipt(payment_id, storage_ref=f"/api/v1/client-payments/{payment_id}/receipt")
    assert file1.exists() and file2.exists()

    # Exact deletion deletes only targeted file
    deleted_exact1 = await storage.delete_receipt(payment_id, storage_ref=ref1)
    assert deleted_exact1 is True
    assert not file1.exists()
    assert file2.exists()

    # Now exactly 1 file remains: backward-compatible retrieval succeeds again
    res_single = await storage.get_receipt(payment_id, storage_ref=None)
    assert res_single is not None and res_single.file_path == file2

    # And single-file legacy deletion works
    deleted_single = await storage.delete_receipt(payment_id, storage_ref=None)
    assert deleted_single is True
    assert not file2.exists()


@pytest.mark.asyncio
async def test_s3_file_storage_legacy_fallback_matrix():
    """
    Tests S3FileStorage legacy fallback matrix:
    - 0 files: return None / False
    - 1 file: return single object / delete single object
    - Multiple files: raise AmbiguousReceiptStorageError on missing or /api/ reference
    - Ambiguous deletion never calls client.delete_object
    - Exact reference: directly calls get_object / delete_object by key
    """
    storage = S3FileStorage(bucket_name="test-bucket")
    mock_s3 = MagicMock()
    storage._client = mock_s3
    payment_id = "test-s3-legacy-pid-888"
    api_url = f"/api/v1/client-payments/{payment_id}/receipt"

    # Case 0 files
    mock_s3.list_objects_v2.return_value = {"Contents": []}
    assert await storage.get_receipt(payment_id, storage_ref=None) is None
    assert await storage.get_receipt(payment_id, storage_ref=api_url) is None
    assert await storage.delete_receipt(payment_id, storage_ref=None) is False
    assert await storage.delete_receipt(payment_id, storage_ref=api_url) is False

    # Case 1 file
    mock_body = MagicMock()
    mock_body.read.return_value = VALID_PDF
    mock_s3.get_object.return_value = {
        "Body": mock_body,
        "ContentType": "application/pdf",
    }
    key1 = f"receipts/{payment_id}/111_file1.pdf"
    mock_s3.list_objects_v2.return_value = {"Contents": [{"Key": key1}]}

    res_1 = await storage.get_receipt(payment_id, storage_ref=None)
    assert res_1 is not None and res_1.filename == "111_file1.pdf"
    mock_s3.get_object.assert_called_with(Bucket="test-bucket", Key=key1)

    res_api = await storage.get_receipt(payment_id, storage_ref=api_url)
    assert res_api is not None and res_api.filename == "111_file1.pdf"

    # Case multiple files
    key2 = f"receipts/{payment_id}/222_file2.png"
    mock_s3.list_objects_v2.return_value = {
        "Contents": [{"Key": key1}, {"Key": key2}]
    }

    # Missing or /api/ reference MUST raise AmbiguousReceiptStorageError
    with pytest.raises(AmbiguousReceiptStorageError, match="Multiple candidate receipt objects found"):
        await storage.get_receipt(payment_id, storage_ref=None)

    with pytest.raises(AmbiguousReceiptStorageError, match="Multiple candidate receipt objects found"):
        await storage.get_receipt(payment_id, storage_ref=api_url)

    # Exact reference retrieves exact key directly without listing prefix
    mock_s3.reset_mock()
    res_exact = await storage.get_receipt(payment_id, storage_ref=key1)
    assert res_exact is not None and res_exact.filename == "111_file1.pdf"
    mock_s3.get_object.assert_called_once_with(Bucket="test-bucket", Key=key1)
    mock_s3.list_objects_v2.assert_not_called()

    # Ambiguous deletion with missing or /api/ reference NEVER deletes any objects
    mock_s3.reset_mock()
    mock_s3.list_objects_v2.return_value = {
        "Contents": [{"Key": key1}, {"Key": key2}]
    }
    with pytest.raises(AmbiguousReceiptStorageError, match="Cannot delete receipt: multiple candidate objects found"):
        await storage.delete_receipt(payment_id, storage_ref=None)
    mock_s3.delete_object.assert_not_called()

    with pytest.raises(AmbiguousReceiptStorageError, match="Cannot delete receipt: multiple candidate objects found"):
        await storage.delete_receipt(payment_id, storage_ref=api_url)
    mock_s3.delete_object.assert_not_called()

    # Exact deletion deletes only targeted key
    deleted = await storage.delete_receipt(payment_id, storage_ref=key1)
    assert deleted is True
    mock_s3.delete_object.assert_called_once_with(Bucket="test-bucket", Key=key1)
