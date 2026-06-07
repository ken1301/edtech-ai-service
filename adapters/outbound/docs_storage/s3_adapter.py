import asyncio
import os
from typing import Any
from urllib.parse import quote, unquote, urlparse

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from domain.ports.cloud_port import CloudPort
from domain.models.overall_models.document import PDFDocument, ImageDocument

from domain.exceptions import CloudAdapterError

from infrastructure.logging import logger


class S3Adapter(CloudPort):

    def __init__(self, s3_client: Any | None = None, bucket_name: str | None = None):
        self.s3_client = s3_client or boto3.client("s3")
        self._bucket_name = bucket_name or os.getenv("MINIO_BUCKET_NAME") or os.getenv("S3_BUCKET_NAME") or "documents"

    def _ensure_bucket_exists(self) -> None:
        try:
            self.s3_client.head_bucket(Bucket=self._bucket_name)
        except ClientError:
            self.s3_client.create_bucket(Bucket=self._bucket_name)

    def _document_key(self, document_type: str, document_id: str, filename: str) -> str:
        return f"{document_type}/{document_id}/{quote(filename, safe='')}"

    def _extract_key(self, document_url: str) -> str:
        parsed = urlparse(document_url)
        key = parsed.path.lstrip("/") or document_url.lstrip("/")
        if key.startswith(f"{self._bucket_name}/"):
            key = key[len(self._bucket_name) + 1 :]
        return key

    @staticmethod
    def _split_key(key: str) -> tuple[str, str]:
        parts = [part for part in key.split("/") if part]
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

    async def upload_pdf(self, document: PDFDocument) -> str:
        try:
            logger.debug(
                "s3_adapter.upload_pdf.completed",
                log_type="debug",
                document_id=document.id,
                filename=document.filename,
            )
            return await asyncio.to_thread(self._upload_document, document, "pdfs", "application/pdf")     
        except (BotoCoreError, ClientError) as e:
            logger.error(
                "s3_adapter.upload_pdf.failed",
                log_type="technical",
                document_id=document.id,
                filename=document.filename,
                error=str(e),
            )
            raise CloudAdapterError(f"Failed to upload PDF document '{document.filename}' to cloud storage.") from e
        except Exception as e:
            logger.error(
                "s3_adapter.upload_pdf.unexpected_error",
                log_type="technical",
                document_id=document.id,
                filename=document.filename,
                error=str(e),
            )
            raise CloudAdapterError("An unexpected error occurred while uploading a PDF document.") from e

    async def download_pdf(self, document_url: str) -> PDFDocument:
        try:
            logger.debug(
                "s3_adapter.download_pdf.completed",
                log_type="debug",
                document_url=document_url,
            )
            return await asyncio.to_thread(self._download_pdf, document_url)
        except (BotoCoreError, ClientError) as e:
            logger.error(
                "s3_adapter.download_pdf.failed",
                log_type="technical",
                document_url=document_url,
                error=str(e),
            )
            raise CloudAdapterError(f"Failed to download PDF document from '{document_url}'.") from e
        except Exception as e:
            logger.error(
                "s3_adapter.download_pdf.unexpected_error",
                log_type="technical",
                document_url=document_url,
                error=str(e),
            )
            raise CloudAdapterError("An unexpected error occurred while downloading a PDF document.") from e

    async def upload_image(self, document: ImageDocument) -> str:
        try:
            logger.debug(
                "s3_adapter.upload_image.completed",
                log_type="debug",
                document_id=document.id,
                filename=document.filename,
            )
            return await asyncio.to_thread(self._upload_document, document, "images", "image/*")
        except (BotoCoreError, ClientError) as e:
            logger.error(
                "s3_adapter.upload_image.failed",
                log_type="technical",
                document_id=document.id,
                filename=document.filename,
                error=str(e),
            )
            raise CloudAdapterError(f"Failed to upload image document '{document.filename}' to cloud storage.") from e
        except Exception as e:
            logger.error(
                "s3_adapter.upload_image.unexpected_error",
                log_type="technical",
                document_id=document.id,
                filename=document.filename,
                error=str(e),
            )
            raise CloudAdapterError("An unexpected error occurred while uploading an image document.") from e

    async def download_image(self, document_url: str) -> ImageDocument:
        try:
            logger.debug(
                "s3_adapter.download_image.completed",
                log_type="debug",
                document_url=document_url,
            )
            return await asyncio.to_thread(self._download_image, document_url)
        except (BotoCoreError, ClientError) as e:
            logger.error(
                "s3_adapter.download_image.failed",
                log_type="technical",
                document_url=document_url,
                error=str(e),
            )
            raise CloudAdapterError(f"Failed to download image document from '{document_url}'.") from e
        except Exception as e:
            logger.error(
                "s3_adapter.download_image.unexpected_error",
                log_type="technical",
                document_url=document_url,
                error=str(e),
            )
            raise CloudAdapterError("An unexpected error occurred while downloading an image document.") from e

    async def delete_document(self, document_url: str) -> bool:
        try:
            logger.debug(
                "s3_adapter.delete_document.completed",
                log_type="debug",
                document_url=document_url,
            )
            await asyncio.to_thread(self._delete_document, document_url)
            return True
        except (BotoCoreError, ClientError) as e:
            logger.error(
                "s3_adapter.delete_document.failed",
                log_type="technical",
                document_url=document_url,
                error=str(e),
            )
            raise CloudAdapterError(f"Failed to delete document '{document_url}' from cloud storage.") from e
        except Exception as e:
            logger.error(
                "s3_adapter.delete_document.unexpected_error",
                log_type="technical",
                document_url=document_url,
                error=str(e),
            )
            raise CloudAdapterError("An unexpected error occurred while deleting a document.") from e

    def _upload_document(self, document: PDFDocument | ImageDocument, document_type: str, content_type: str) -> str:
        self._ensure_bucket_exists()
        key = self._document_key(document_type, document.id, document.filename)
        self.s3_client.put_object(
            Bucket=self._bucket_name,
            Key=key,
            Body=document.content,
            ContentType=content_type,
            Metadata={
                "document_id": document.id,
                "filename": document.filename,
            },
        )
        return self._object_url(key)

    def _download_pdf(self, document_url: str) -> PDFDocument:
        self._ensure_bucket_exists()
        key = self._extract_key(document_url)
        response = self.s3_client.get_object(Bucket=self._bucket_name, Key=key)
        content = response["Body"].read()
        document_id, filename = self._split_key(key)
        return PDFDocument(
            id=document_id,
            filename=filename,
            content=content,
            size_bytes=response.get("ContentLength", len(content)),
        )

    def _download_image(self, document_url: str) -> ImageDocument:
        self._ensure_bucket_exists()
        key = self._extract_key(document_url)
        response = self.s3_client.get_object(Bucket=self._bucket_name, Key=key)
        content = response["Body"].read()
        document_id, filename = self._split_key(key)
        return ImageDocument(
            id=document_id,
            filename=filename,
            content=content,
            parent_pdf_id=response.get("Metadata", {}).get("parent_pdf_id"),
        )

    def _delete_document(self, document_url: str) -> None:
        self._ensure_bucket_exists()
        key = self._extract_key(document_url)
        self.s3_client.delete_object(Bucket=self._bucket_name, Key=key)