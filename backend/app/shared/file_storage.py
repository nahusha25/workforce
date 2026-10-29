"""File storage service abstraction with local filesystem and pluggable S3 support."""

import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO, List, Optional, Set, Tuple, Union

from app.core.config import settings

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

ALLOWED_IMAGE_MIME_TYPES: Set[str] = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

ALLOWED_RECEIPT_MIME_TYPES: Set[str] = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
}

RECEIPTS_STORAGE_DIR = Path("storage/receipts").resolve()


class FileStorageError(Exception):
    """Base exception for file storage operations."""
    pass


class InvalidFileTypeError(FileStorageError):
    """Raised when a file's MIME type or extension is not allowed."""
    pass


class FileSizeLimitExceededError(FileStorageError):
    """Raised when a file exceeds the maximum allowed size limit."""
    pass


class FileNotFoundStorageError(FileStorageError):
    """Raised when a requested file is not found in storage."""
    pass


class AmbiguousReceiptStorageError(FileStorageError):
    """Raised when multiple candidate receipt files exist for a payment without an exact reference."""
    pass


def detect_mime_type_from_bytes(data: bytes) -> Optional[str]:
    """Detect image or document MIME type from binary magic bytes (pure Python)."""
    if len(data) >= 3 and data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if len(data) >= 4 and data[:4] == b"%PDF":
        return "application/pdf"
    return None


def sanitize_storage_path(path: str) -> str:
    """Sanitize and normalize storage relative path to prevent path traversal."""
    normalized = os.path.normpath(path).replace("\\", "/")
    if normalized.startswith("../") or "/../" in normalized or normalized == "..":
        raise FileStorageError(f"Path traversal detected: {path}")
    return normalized.lstrip("/")


def validate_image_file(
    file_bytes: bytes,
    content_type: Optional[str] = None,
) -> str:
    """Validate that file_bytes is a non-empty image within size limits and allowed MIME types."""
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise FileSizeLimitExceededError(
            f"File size ({len(file_bytes)} bytes) exceeds the maximum limit of {MAX_FILE_SIZE_BYTES} bytes (10MB)"
        )
    if len(file_bytes) == 0:
        raise InvalidFileTypeError("File is empty (0 bytes)")

    detected_mime = detect_mime_type_from_bytes(file_bytes)
    if detected_mime not in ALLOWED_IMAGE_MIME_TYPES:
        raise InvalidFileTypeError(
            f"Unsupported file format '{detected_mime or 'unknown'}'. "
            f"Allowed image types: {', '.join(sorted(ALLOWED_IMAGE_MIME_TYPES))}"
        )

    if content_type and content_type.lower() != detected_mime:
        if content_type.lower() not in ALLOWED_IMAGE_MIME_TYPES:
            raise InvalidFileTypeError(f"Invalid content type: {content_type}")

    return detected_mime


def validate_receipt_file(
    file_bytes: bytes,
    content_type: Optional[str] = None,
) -> str:
    """Validate that file_bytes is a non-empty receipt document or image within size limits (<= 10MB)."""
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise FileSizeLimitExceededError(
            f"File size ({len(file_bytes)} bytes) exceeds the maximum limit of {MAX_FILE_SIZE_BYTES} bytes (10MB)"
        )
    if len(file_bytes) == 0:
        raise InvalidFileTypeError("File is empty (0 bytes)")

    detected_mime = detect_mime_type_from_bytes(file_bytes)
    if detected_mime not in ALLOWED_RECEIPT_MIME_TYPES:
        raise InvalidFileTypeError(
            f"Unsupported file format '{detected_mime or 'unknown'}'. "
            f"Allowed receipt types: {', '.join(sorted(ALLOWED_RECEIPT_MIME_TYPES))}"
        )

    if content_type and content_type.lower() != detected_mime:
        if content_type.lower() not in ALLOWED_RECEIPT_MIME_TYPES:
            raise InvalidFileTypeError(f"Invalid content type: {content_type}")

    return detected_mime


class ReceiptFileResult:
    """Encapsulates a receipt retrieved from private storage (local filesystem or remote S3)."""

    def __init__(
        self,
        file_path: Optional[Path] = None,
        file_bytes: Optional[bytes] = None,
        media_type: str = "application/octet-stream",
        filename: str = "receipt",
    ):
        self.file_path = file_path
        self.file_bytes = file_bytes
        self.media_type = media_type
        self.filename = filename

    def __iter__(self):
        """Allows unpacking as (file_path, media_type, filename) for backwards compatibility."""
        yield self.file_path
        yield self.media_type
        yield self.filename


class FileStorageService(ABC):
    """Abstract base class for file storage providers."""

    @abstractmethod
    async def upload_file(
        self,
        file_data: Union[bytes, BinaryIO],
        destination_path: str,
        content_type: Optional[str] = None,
    ) -> str:
        """Upload a file to storage and return its access URL/path."""
        pass

    @abstractmethod
    async def get_signed_url(self, file_path: str, expires_in: int = 3600) -> str:
        """Generate a signed or accessible URL for retrieving the file."""
        pass

    @abstractmethod
    async def delete_file(self, file_path: str) -> bool:
        """Delete a file from storage. Returns True if deleted, False if not found."""
        pass

    @abstractmethod
    async def file_exists(self, file_path: str) -> bool:
        """Check if a file exists in storage."""
        pass

    @abstractmethod
    async def upload_receipt(
        self,
        payment_id: Union[uuid.UUID, str],
        file_bytes: bytes,
        original_filename: str,
        content_type: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Uploads and validates a receipt file (PDF, JPG, PNG, WebP <= 10MB) to private storage.
        Returns (storage_ref, mime_type).
        """
        pass

    @abstractmethod
    async def get_receipt(
        self,
        payment_id: Union[uuid.UUID, str],
        storage_ref: Optional[str] = None,
    ) -> Optional[ReceiptFileResult]:
        """
        Retrieves a receipt file from private storage.
        Returns ReceiptFileResult with file_path (if local) or file_bytes (if S3/remote), or None.
        """
        pass

    @abstractmethod
    async def delete_receipt(
        self,
        payment_id: Union[uuid.UUID, str],
        storage_ref: Optional[str] = None,
    ) -> bool:
        """Deletes a receipt file or specific reference from private storage."""
        pass


class LocalFileStorage(FileStorageService):
    """Local filesystem storage implementation for development and testing."""

    def __init__(
        self,
        base_dir: Optional[Union[str, Path]] = None,
        base_url: str = "/uploads",
        receipts_dir: Optional[Union[str, Path]] = None,
    ):
        if base_dir is None:
            self.base_dir = Path("uploads").resolve()
        else:
            self.base_dir = Path(base_dir).resolve()

        self.base_url = base_url.rstrip("/")
        self.base_dir.mkdir(parents=True, exist_ok=True)

        if receipts_dir is None:
            self.receipts_dir = RECEIPTS_STORAGE_DIR
        else:
            self.receipts_dir = Path(receipts_dir).resolve()
        self.receipts_dir.mkdir(parents=True, exist_ok=True)

    def _get_target_path(self, relative_path: str) -> Path:
        clean_rel = sanitize_storage_path(relative_path)
        target = (self.base_dir / clean_rel).resolve()
        if not str(target).startswith(str(self.base_dir)):
            raise FileStorageError("Access outside of base directory is forbidden")
        return target

    def _get_receipt_dir(self, payment_id: Union[uuid.UUID, str]) -> Path:
        target = (self.receipts_dir / str(payment_id)).resolve()
        if not str(target).startswith(str(self.receipts_dir)):
            raise FileStorageError(f"Path traversal detected for payment_id: {payment_id}")
        return target

    async def upload_file(
        self,
        file_data: Union[bytes, BinaryIO],
        destination_path: str,
        content_type: Optional[str] = None,
    ) -> str:
        if isinstance(file_data, (bytes, bytearray)):
            raw_bytes = bytes(file_data)
        elif hasattr(file_data, "read"):
            raw_bytes = file_data.read()
            if hasattr(file_data, "seek"):
                file_data.seek(0)
        else:
            raise FileStorageError("Unsupported file_data type: must be bytes or file-like object")

        validate_image_file(raw_bytes, content_type=content_type)
        target_path = self._get_target_path(destination_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        with open(target_path, "wb") as f:
            f.write(raw_bytes)

        clean_rel = sanitize_storage_path(destination_path)
        return f"{self.base_url}/{clean_rel}"

    async def get_signed_url(self, file_path: str, expires_in: int = 3600) -> str:
        clean_rel = sanitize_storage_path(file_path)
        target_path = self._get_target_path(file_path)
        if not target_path.exists() or not target_path.is_file():
            raise FileNotFoundStorageError(f"File not found: {file_path}")

        return f"{self.base_url}/{clean_rel}"

    async def delete_file(self, file_path: str) -> bool:
        target_path = self._get_target_path(file_path)
        if target_path.exists() and target_path.is_file():
            target_path.unlink()
            return True
        return False

    async def file_exists(self, file_path: str) -> bool:
        target_path = self._get_target_path(file_path)
        return target_path.exists() and target_path.is_file()

    def _save_receipt_sync(
        self,
        payment_id: Union[uuid.UUID, str],
        file_bytes: bytes,
        original_filename: str,
        content_type: Optional[str] = None,
    ) -> Tuple[Path, str]:
        """Synchronously validates and stores receipt in private directory without deleting prior files."""
        mime = validate_receipt_file(file_bytes, content_type=content_type)
        p_dir = self._get_receipt_dir(payment_id)
        p_dir.mkdir(parents=True, exist_ok=True)

        safe_name = os.path.basename(original_filename.replace("\\", "/"))
        safe_name = "".join(c for c in safe_name if c.isalnum() or c in "._- ")
        name_part, ext_part = os.path.splitext(safe_name)
        if not name_part:
            name_part = "receipt"

        ext_map = {
            "application/pdf": ".pdf",
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
        }
        expected_ext = ext_map.get(mime, "")
        if not ext_part or ext_part.lower() not in (".pdf", ".jpg", ".jpeg", ".png", ".webp"):
            ext_part = expected_ext

        # Use unique prefix to prevent overwriting existing files before DB commit completes
        candidate_filename = f"{uuid.uuid4().hex[:8]}_{name_part}{ext_part}"
        target_path = p_dir / candidate_filename
        with open(target_path, "wb") as f:
            f.write(file_bytes)

        return target_path, mime

    def _get_receipt_sync(
        self,
        payment_id: Union[uuid.UUID, str],
        storage_ref: Optional[str] = None,
    ) -> Optional[ReceiptFileResult]:
        """Synchronously retrieves existing receipt file from private storage."""
        p_dir = self._get_receipt_dir(payment_id)
        if not p_dir.exists() or not p_dir.is_dir():
            return None

        if storage_ref and not storage_ref.startswith("/api/"):
            filename = os.path.basename(storage_ref.replace("\\", "/"))
            candidate = (p_dir / filename).resolve()
            if candidate.exists() and candidate.is_file():
                try:
                    if candidate.is_relative_to(p_dir):
                        raw = candidate.read_bytes()[:16]
                        mime = detect_mime_type_from_bytes(raw) or "application/octet-stream"
                        return ReceiptFileResult(file_path=candidate, media_type=mime, filename=candidate.name)
                except (ValueError, AttributeError):
                    pass
                if str(candidate).lower().startswith(str(p_dir).lower()):
                    raw = candidate.read_bytes()[:16]
                    mime = detect_mime_type_from_bytes(raw) or "application/octet-stream"
                    return ReceiptFileResult(file_path=candidate, media_type=mime, filename=candidate.name)
            return None

        files = [f for f in p_dir.iterdir() if f.is_file()]
        if not files:
            return None

        if len(files) == 1:
            target_file = files[0]
            raw = target_file.read_bytes()[:16]
            mime = detect_mime_type_from_bytes(raw) or "application/octet-stream"
            return ReceiptFileResult(file_path=target_file, media_type=mime, filename=target_file.name)

        raise AmbiguousReceiptStorageError(
            f"Multiple candidate receipt files found ({len(files)}) for payment {payment_id} without an exact storage reference."
        )

    async def upload_receipt(
        self,
        payment_id: Union[uuid.UUID, str],
        file_bytes: bytes,
        original_filename: str,
        content_type: Optional[str] = None,
    ) -> Tuple[str, str]:
        target_path, mime = self._save_receipt_sync(
            payment_id=payment_id,
            file_bytes=file_bytes,
            original_filename=original_filename,
            content_type=content_type,
        )
        storage_ref = sanitize_storage_path(f"receipts/{payment_id}/{target_path.name}")
        return storage_ref, mime

    async def get_receipt(
        self,
        payment_id: Union[uuid.UUID, str],
        storage_ref: Optional[str] = None,
    ) -> Optional[ReceiptFileResult]:
        return self._get_receipt_sync(payment_id, storage_ref)

    async def delete_receipt(
        self,
        payment_id: Union[uuid.UUID, str],
        storage_ref: Optional[str] = None,
    ) -> bool:
        p_dir = self._get_receipt_dir(payment_id)
        if not p_dir.exists() or not p_dir.is_dir():
            return False

        if storage_ref and not storage_ref.startswith("/api/"):
            filename = os.path.basename(storage_ref.replace("\\", "/"))
            candidate = (p_dir / filename).resolve()
            if candidate.exists() and candidate.is_file():
                try:
                    if candidate.is_relative_to(p_dir):
                        candidate.unlink()
                        return True
                except (ValueError, AttributeError):
                    pass
                if str(candidate).lower().startswith(str(p_dir).lower()):
                    candidate.unlink()
                    return True
            return False

        files = [f for f in p_dir.iterdir() if f.is_file()]
        if not files:
            return False

        if len(files) == 1:
            files[0].unlink()
            return True

        raise AmbiguousReceiptStorageError(
            f"Cannot delete receipt: multiple candidate files found ({len(files)}) for payment {payment_id} without an exact storage reference."
        )

    async def delete_old_receipts(
        self,
        payment_id: Union[uuid.UUID, str],
        keep_ref: str,
    ) -> None:
        """Deletes any old receipt file in payment directory other than keep_ref."""
        p_dir = self._get_receipt_dir(payment_id)
        if not p_dir.exists() or not p_dir.is_dir():
            return
        keep_name = os.path.basename(keep_ref.replace("\\", "/"))
        for f in p_dir.iterdir():
            if f.is_file() and f.name != keep_name:
                try:
                    f.unlink()
                except Exception:
                    pass


class S3FileStorage(FileStorageService):
    """Pluggable S3-compatible object storage implementation."""

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = "us-east-1",
    ):
        self.bucket_name = bucket_name or getattr(settings, "STORAGE_BUCKET", "workforce-uploads")
        self.endpoint_url = endpoint_url
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.region_name = region_name
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client(
                    "s3",
                    endpoint_url=self.endpoint_url,
                    aws_access_key_id=self.aws_access_key_id,
                    aws_secret_access_key=self.aws_secret_access_key,
                    region_name=self.region_name,
                )
            except ImportError:
                raise FileStorageError(
                    "boto3 is required to use S3FileStorage. Install boto3 to enable S3 storage."
                )
        return self._client

    async def upload_file(
        self,
        file_data: Union[bytes, BinaryIO],
        destination_path: str,
        content_type: Optional[str] = None,
    ) -> str:
        if isinstance(file_data, (bytes, bytearray)):
            raw_bytes = bytes(file_data)
        elif hasattr(file_data, "read"):
            raw_bytes = file_data.read()
            if hasattr(file_data, "seek"):
                file_data.seek(0)
        else:
            raise FileStorageError("Unsupported file_data type: must be bytes or file-like object")

        mime = validate_image_file(raw_bytes, content_type=content_type)
        clean_path = sanitize_storage_path(destination_path)

        client = self._get_client()
        client.put_object(
            Bucket=self.bucket_name,
            Key=clean_path,
            Body=raw_bytes,
            ContentType=mime,
        )

        return f"https://{self.bucket_name}.s3.amazonaws.com/{clean_path}"

    async def get_signed_url(self, file_path: str, expires_in: int = 3600) -> str:
        clean_path = sanitize_storage_path(file_path)
        client = self._get_client()
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": clean_path},
            ExpiresIn=expires_in,
        )

    async def delete_file(self, file_path: str) -> bool:
        clean_path = sanitize_storage_path(file_path)
        client = self._get_client()
        client.delete_object(Bucket=self.bucket_name, Key=clean_path)
        return True

    async def file_exists(self, file_path: str) -> bool:
        clean_path = sanitize_storage_path(file_path)
        client = self._get_client()
        try:
            client.head_object(Bucket=self.bucket_name, Key=clean_path)
            return True
        except Exception:
            return False

    async def upload_receipt(
        self,
        payment_id: Union[uuid.UUID, str],
        file_bytes: bytes,
        original_filename: str,
        content_type: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Uploads receipt object privately to S3 without public read permissions."""
        mime = validate_receipt_file(file_bytes, content_type=content_type)

        safe_name = os.path.basename(original_filename.replace("\\", "/"))
        safe_name = "".join(c for c in safe_name if c.isalnum() or c in "._- ")
        name_part, ext_part = os.path.splitext(safe_name)
        if not name_part:
            name_part = "receipt"

        ext_map = {
            "application/pdf": ".pdf",
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
        }
        expected_ext = ext_map.get(mime, "")
        if not ext_part or ext_part.lower() not in (".pdf", ".jpg", ".jpeg", ".png", ".webp"):
            ext_part = expected_ext

        candidate_filename = f"{uuid.uuid4().hex[:8]}_{name_part}{ext_part}"
        key = sanitize_storage_path(f"receipts/{payment_id}/{candidate_filename}")

        client = self._get_client()
        client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=file_bytes,
            ContentType=mime,
        )
        return key, mime

    async def get_receipt(
        self,
        payment_id: Union[uuid.UUID, str],
        storage_ref: Optional[str] = None,
    ) -> Optional[ReceiptFileResult]:
        """Retrieves receipt object privately from S3."""
        client = self._get_client()
        if storage_ref and not storage_ref.startswith("/api/"):
            key = sanitize_storage_path(storage_ref)
            try:
                obj = client.get_object(Bucket=self.bucket_name, Key=key)
                body = obj["Body"].read()
                mime = obj.get("ContentType") or detect_mime_type_from_bytes(body) or "application/octet-stream"
                filename = key.split("/")[-1]
                return ReceiptFileResult(file_bytes=body, media_type=mime, filename=filename)
            except Exception:
                return None

        prefix = sanitize_storage_path(f"receipts/{payment_id}/")
        res = client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
        contents = res.get("Contents", [])
        if not contents:
            return None
        if len(contents) == 1:
            key = contents[0]["Key"]
            try:
                obj = client.get_object(Bucket=self.bucket_name, Key=key)
                body = obj["Body"].read()
                mime = obj.get("ContentType") or detect_mime_type_from_bytes(body) or "application/octet-stream"
                filename = key.split("/")[-1]
                return ReceiptFileResult(file_bytes=body, media_type=mime, filename=filename)
            except Exception:
                return None

        raise AmbiguousReceiptStorageError(
            f"Multiple candidate receipt objects found ({len(contents)}) in S3 for payment {payment_id} without an exact storage reference."
        )

    async def delete_receipt(
        self,
        payment_id: Union[uuid.UUID, str],
        storage_ref: Optional[str] = None,
    ) -> bool:
        """Deletes receipt object from S3."""
        client = self._get_client()
        if storage_ref and not storage_ref.startswith("/api/"):
            key = sanitize_storage_path(storage_ref)
            client.delete_object(Bucket=self.bucket_name, Key=key)
            return True

        prefix = sanitize_storage_path(f"receipts/{payment_id}/")
        res = client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
        contents = res.get("Contents", [])
        if not contents:
            return False
        if len(contents) == 1:
            client.delete_object(Bucket=self.bucket_name, Key=contents[0]["Key"])
            return True

        raise AmbiguousReceiptStorageError(
            f"Cannot delete receipt: multiple candidate objects found ({len(contents)}) in S3 for payment {payment_id} without an exact storage reference."
        )

    async def delete_old_receipts(
        self,
        payment_id: Union[uuid.UUID, str],
        keep_ref: str,
    ) -> None:
        """Deletes any old receipt object in S3 other than keep_ref."""
        client = self._get_client()
        prefix = sanitize_storage_path(f"receipts/{payment_id}/")
        res = client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
        contents = res.get("Contents", [])
        keep_key = sanitize_storage_path(keep_ref)
        for item in contents:
            if item["Key"] != keep_key:
                try:
                    client.delete_object(Bucket=self.bucket_name, Key=item["Key"])
                except Exception:
                    pass


def get_file_storage() -> FileStorageService:
    """Factory helper to obtain the configured storage provider."""
    storage_backend = os.environ.get("STORAGE_BACKEND", "local").lower()
    if storage_backend == "s3":
        return S3FileStorage()
    return LocalFileStorage()


def get_receipt_dir(payment_id: Union[uuid.UUID, str], base_dir: Optional[Path] = None) -> Path:
    """Get secure storage directory for a client payment receipt (LocalFileStorage helper)."""
    storage = LocalFileStorage(receipts_dir=base_dir)
    return storage._get_receipt_dir(payment_id)


def save_receipt_file(
    payment_id: Union[uuid.UUID, str],
    file_bytes: bytes,
    original_filename: str,
    content_type: Optional[str] = None,
    base_dir: Optional[Path] = None,
) -> Tuple[Path, str]:
    """
    Validates and stores a payment receipt in secure private storage (outside static /uploads).
    Local helper preserving backward compatibility.
    """
    storage = LocalFileStorage(receipts_dir=base_dir)
    return storage._save_receipt_sync(
        payment_id=payment_id,
        file_bytes=file_bytes,
        original_filename=original_filename,
        content_type=content_type,
    )


def get_receipt_file_path(
    payment_id: Union[uuid.UUID, str],
    base_dir: Optional[Path] = None,
    storage_ref: Optional[str] = None,
) -> Optional[Tuple[Path, str]]:
    """
    Locates an existing receipt file for a payment from private storage.
    Returns (path, mime) or None if not found.
    Raises AmbiguousReceiptStorageError if multiple files exist and storage_ref is missing or legacy.
    """
    storage = LocalFileStorage(receipts_dir=base_dir)
    res = storage._get_receipt_sync(payment_id, storage_ref=storage_ref)
    if not res or not res.file_path:
        return None
    return res.file_path, res.media_type
