"""File storage service abstraction with local filesystem and pluggable S3 support."""

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO, Optional, Set, Union

from app.core.config import settings

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

ALLOWED_IMAGE_MIME_TYPES: Set[str] = {
    "image/jpeg",
    "image/png",
    "image/webp",
}


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


def detect_mime_type_from_bytes(data: bytes) -> Optional[str]:
    """Detect image MIME type from binary magic bytes (pure Python)."""
    if len(data) >= 3 and data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
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


class LocalFileStorage(FileStorageService):
    """Local filesystem storage implementation for development."""

    def __init__(
        self,
        base_dir: Optional[Union[str, Path]] = None,
        base_url: str = "/uploads",
    ):
        if base_dir is None:
            self.base_dir = Path("uploads").resolve()
        else:
            self.base_dir = Path(base_dir).resolve()

        self.base_url = base_url.rstrip("/")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_target_path(self, relative_path: str) -> Path:
        clean_rel = sanitize_storage_path(relative_path)
        target = (self.base_dir / clean_rel).resolve()
        if not str(target).startswith(str(self.base_dir)):
            raise FileStorageError("Access outside of base directory is forbidden")
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


def get_file_storage() -> FileStorageService:
    """Factory helper to obtain the configured storage provider."""
    storage_backend = os.environ.get("STORAGE_BACKEND", "local").lower()
    if storage_backend == "s3":
        return S3FileStorage()
    return LocalFileStorage()
