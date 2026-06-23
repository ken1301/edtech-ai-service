import base64
import asyncio
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlparse

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from domain.ports.cloud_port import CloudPort
from domain.models.overall_models.document import PDFDocument, ImageDocument, MarkdownDocument

from domain.exceptions import CloudAdapterError

from infrastructure.logging import logger


class S3Adapter(CloudPort):
    _USER_PREFIX = "users"
    _DEFAULT_MAX_DOCUMENT_BYTES = 15 * 1024 * 1024
    _IMAGE_CONTENT_TYPES = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".svg": "image/svg+xml",
    }

    def __init__(self, s3_client: Any | None = None, bucket_name: str | None = None):
        self.s3_client = s3_client or boto3.client("s3")
        self._bucket_name = bucket_name or os.getenv("MINIO_BUCKET_NAME") or os.getenv("S3_BUCKET_NAME") or "edtech"
        self._max_document_bytes = int(
            os.getenv("AI_SERVICE_MAX_DOCUMENT_BYTES", str(self._DEFAULT_MAX_DOCUMENT_BYTES))
        )

    def _ensure_bucket_exists(self) -> None:
        try:
            self.s3_client.head_bucket(Bucket=self._bucket_name)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "404" or error_code == "NoSuchBucket":
                try:
                    self.s3_client.create_bucket(Bucket=self._bucket_name)
                except ClientError:
                    pass  # Ignore creation errors, might be permission issues
            else:
                pass  # Ignore other errors like 403 Forbidden from restrictive tokens

    def _document_key(self, user_id: str, document_type: str, document_id: str, filename: str) -> str:
        return f"{self._USER_PREFIX}/{quote(user_id, safe='')}/{document_type}/{document_id}/{quote(filename, safe='')}"

    def _extract_key(self, document_url: str) -> str:
        parsed = urlparse(document_url)

        if parsed.netloc and "download-shared-object" in parsed.path:
            encoded_url = parsed.path.rsplit("/", 1)[-1]
            padding = (-len(encoded_url)) % 4
            if padding:
                encoded_url += "=" * padding
            try:
                document_url = base64.urlsafe_b64decode(encoded_url).decode("utf-8")
            except Exception:
                pass

        parsed = urlparse(document_url)
        key = parsed.path.lstrip("/") or document_url.lstrip("/")
        
        if key.startswith(f"{self._bucket_name}/"):
            key = key[len(self._bucket_name) + 1 :]
        else:
            parts = key.split("/")
            if len(parts) > 1 and parts[1] == self._USER_PREFIX:
                key = "/".join(parts[1:])

        if key.startswith("uploads/"):
            key = key[len("uploads/") :]
        return key

    def _assert_user_scope(self, key: str, user_id: str) -> None:
        if key.startswith("uploads/"):
            key = key[len("uploads/") :]
        expected_prefix = f"{self._USER_PREFIX}/{quote(user_id, safe='')}/"
        if not key.startswith(expected_prefix):
            raise CloudAdapterError(f"Document key does not belong to the authenticated user. Key: '{key}', Expected Prefix: '{expected_prefix}', Bucket Name: '{self._bucket_name}'")

    @staticmethod
    def _split_key(key: str) -> tuple[str, str]:
        parts = [part for part in key.split("/") if part]
        if len(parts) >= 5 and parts[0] == S3Adapter._USER_PREFIX:
            document_id = unquote(parts[3])
            filename = unquote("/".join(parts[4:]))
            return document_id, filename

        if len(parts) >= 3:
            document_id = unquote(parts[1])
            filename = unquote("/".join(parts[2:]))
            return document_id, filename

        if len(parts) == 2:
            return unquote(parts[0]), unquote(parts[1])

        if len(parts) == 1:
            return unquote(parts[0]), unquote(parts[0])

        raise ValueError("Document key is empty.")

    def _object_url(self, key: str) -> str:
        endpoint_url = getattr(getattr(self.s3_client, "meta", None), "endpoint_url", None) or os.getenv("MINIO_ENDPOINT_URL")
        if endpoint_url:
            return f"{endpoint_url.rstrip('/')}/{self._bucket_name}/{key}"
        return f"https://{self._bucket_name}.s3.amazonaws.com/{key}"

    @staticmethod
    def _validate_filename(filename: str) -> None:
        if not filename:
            raise CloudAdapterError("Document filename must not be empty.")

        path = Path(filename)
        if path.name != filename or any(part == ".." for part in path.parts):
            raise CloudAdapterError("Document filename must not contain path segments.")

    def _validate_document_size(self, size_bytes: int) -> None:
        if size_bytes <= 0:
            raise CloudAdapterError("Document content must not be empty.")
        if size_bytes > self._max_document_bytes:
            raise CloudAdapterError("Document exceeds the maximum allowed size.")

    def _resolve_upload_spec(self, document: PDFDocument | ImageDocument | MarkdownDocument) -> tuple[str, str]:
        self._validate_filename(document.filename)

        if isinstance(document, PDFDocument):
            return "pdfs", "application/pdf"

        if isinstance(document, ImageDocument):
            suffix = Path(document.filename).suffix.lower()
            content_type = self._IMAGE_CONTENT_TYPES.get(suffix)
            if content_type is None:
                raise CloudAdapterError("Unsupported image content type for upload.")
            return "images", content_type

        return "markdown", "text/markdown; charset=utf-8"

    def _validate_download_response(self, document_type: str, response: dict[str, Any]) -> None:
        content_length = int(response.get("ContentLength") or 0)
        self._validate_document_size(content_length)

        content_type = str(response.get("ContentType") or "").lower()
        if not content_type:
            return

        if document_type == "pdf" and content_type != "application/pdf":
            raise CloudAdapterError("Downloaded document content type does not match PDF expectation.")
        if document_type == "markdown" and not content_type.startswith("text/markdown"):
            raise CloudAdapterError("Downloaded document content type does not match Markdown expectation.")
        if document_type == "image" and not content_type.startswith("image/"):
            raise CloudAdapterError("Downloaded document content type does not match image expectation.")

    async def upload_document(self, document: PDFDocument | ImageDocument | MarkdownDocument, user_id: str) -> str:
        document_type, content_type = self._resolve_upload_spec(document)

        try:
            logger.debug(
                "s3_adapter.upload_document.completed",
                log_type="debug",
                document_id=document.id,
                filename=document.filename,
                document_type=document_type,
                user_id=user_id,
            )
            return await asyncio.to_thread(self._upload_document, document, user_id, document_type, content_type)
        except (BotoCoreError, ClientError) as e:
            logger.error(
                "s3_adapter.upload_document.failed",
                log_type="technical",
                document_id=document.id,
                filename=document.filename,
                user_id=user_id,
                error=str(e),
            )
            raise CloudAdapterError(f"Failed to upload document '{document.filename}' to cloud storage.") from e
        except Exception as e:
            logger.error(
                "s3_adapter.upload_document.unexpected_error",
                log_type="technical",
                document_id=document.id,
                filename=document.filename,
                user_id=user_id,
                error=str(e),
            )
            raise CloudAdapterError("An unexpected error occurred while uploading a document.") from e

    async def download_document(self, document_url: str, user_id: str) -> PDFDocument | ImageDocument | MarkdownDocument:
        document_type = self._infer_document_type(document_url)
        if document_type == "markdown":
            return await asyncio.to_thread(self._download_markdown, document_url, user_id)
        if document_type == "image":
            return await asyncio.to_thread(self._download_image, document_url, user_id)
        return await asyncio.to_thread(self._download_pdf, document_url, user_id)

    async def delete_document(self, document_url: str, user_id: str) -> bool:
        try:
            logger.debug(
                "s3_adapter.delete_document.completed",
                log_type="debug",
                document_url=document_url,
                user_id=user_id,
            )
            await asyncio.to_thread(self._delete_document, document_url, user_id)
            return True
        except (BotoCoreError, ClientError) as e:
            logger.error(
                "s3_adapter.delete_document.failed",
                log_type="technical",
                document_url=document_url,
                user_id=user_id,
                error=str(e),
            )
            raise CloudAdapterError(f"Failed to delete document '{document_url}' from cloud storage.") from e
        except Exception as e:
            logger.error(
                "s3_adapter.delete_document.unexpected_error",
                log_type="technical",
                document_url=document_url,
                user_id=user_id,
                error=str(e),
            )
            raise CloudAdapterError("An unexpected error occurred while deleting a document.") from e

    def _upload_document(self, document: PDFDocument | ImageDocument | MarkdownDocument, user_id: str, document_type: str, content_type: str) -> str:
        self._ensure_bucket_exists()
        payload = document.content.encode("utf-8") if isinstance(document.content, str) else document.content
        self._validate_document_size(len(payload))
        key = self._document_key(user_id, document_type, document.id, document.filename)
        self.s3_client.put_object(
            Bucket=self._bucket_name,
            Key=key,
            Body=payload,
            ContentType=content_type,
            Metadata={
                "document_id": document.id,
                "filename": document.filename,
            },
        )
        return self._object_url(key)

    def _infer_document_type(self, document_url: str) -> str:
        key = self._extract_key(document_url)
        suffix = Path(key).suffix.lower()
        if suffix in {".md", ".markdown"}:
            return "markdown"
        if suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}:
            return "image"
        return "pdf"

    def _download_pdf(self, document_url: str, user_id: str) -> PDFDocument:
        self._ensure_bucket_exists()
        key = self._extract_key(document_url)
        self._assert_user_scope(key, user_id)
        response = self.s3_client.get_object(Bucket=self._bucket_name, Key=key)
        self._validate_download_response("pdf", response)
        content = response["Body"].read()
        document_id, filename = self._split_key(key)
        return PDFDocument(
            id=document_id,
            filename=filename,
            content=content,
            size_bytes=response.get("ContentLength", len(content)),
        )

    def _download_markdown(self, document_url: str, user_id: str) -> MarkdownDocument:
        self._ensure_bucket_exists()
        key = self._extract_key(document_url)
        self._assert_user_scope(key, user_id)
        response = self.s3_client.get_object(Bucket=self._bucket_name, Key=key)
        self._validate_download_response("markdown", response)
        content = response["Body"].read().decode("utf-8")
        document_id, filename = self._split_key(key)
        return MarkdownDocument(
            id=document_id,
            filename=filename,
            content=content,
            parent_pdf_id=response.get("Metadata", {}).get("parent_pdf_id"),
        )

    def _download_image(self, document_url: str, user_id: str) -> ImageDocument:
        self._ensure_bucket_exists()
        key = self._extract_key(document_url)
        self._assert_user_scope(key, user_id)
        response = self.s3_client.get_object(Bucket=self._bucket_name, Key=key)
        self._validate_download_response("image", response)
        content = response["Body"].read()
        document_id, filename = self._split_key(key)
        return ImageDocument(
            id=document_id,
            filename=filename,
            content=content,
            parent_pdf_id=response.get("Metadata", {}).get("parent_pdf_id"),
        )

    def _delete_document(self, document_url: str, user_id: str) -> None:
        self._ensure_bucket_exists()
        key = self._extract_key(document_url)
        self._assert_user_scope(key, user_id)
        self.s3_client.delete_object(Bucket=self._bucket_name, Key=key)