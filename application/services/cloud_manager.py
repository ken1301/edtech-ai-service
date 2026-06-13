from domain.ports.cloud_port import CloudPort

from domain.models.overall_models.document import MarkdownDocument, PDFDocument, ImageDocument

from domain.exceptions import CloudAdapterError, CloudManagerError

from infrastructure.logging import logger

class CloudManager:
    """Service responsible for managing interactions with cloud storage, including uploading and retrieving documents."""

    def __init__(self, cloud_port: CloudPort):
        self._cloud_port = cloud_port

    async def fetch_document(self, document_url: str) -> PDFDocument | ImageDocument | MarkdownDocument:
        """Fetch a document from cloud storage using its unique identifier."""
        try:
            document = await self._cloud_port.download_document(document_url)

            logger.info(
                "cloud_manager.fetch_document.completed",
                log_type="business",
                document_url=document_url
            )

            return document

        except CloudAdapterError as e:
            raise CloudManagerError("Failed to fetch document from cloud storage.") from e

        except Exception as e:
            logger.error(
                "cloud_manager.fetch_document.unexpected.failed",
                log_type="technical",
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise CloudManagerError("Unexpected error while fetching document from cloud storage.") from e

    async def upload_document(self, document: PDFDocument | ImageDocument | MarkdownDocument) -> str:
        """Upload a document to cloud storage and return its accessible URL."""
        try:
            document_url = await self._cloud_port.upload_document(document)
            logger.info(
                "cloud_manager.upload_document.completed",
                log_type="business",
                document_id=document.id,
                filename=document.filename,
            )
            return document_url

        except CloudAdapterError as e:
            raise CloudManagerError("Failed to upload document to cloud storage.") from e

        except Exception as e:
            logger.error(
                "cloud_manager.upload_document.unexpected.failed",
                log_type="technical",
                document_id=document.id,
                filename=document.filename,
                error=str(e),
                exc_info=True,
            )
            raise CloudManagerError("Unexpected error while uploading document to cloud storage.") from e

    async def delete_document(self, document_url: str) -> bool:
        """Delete a document from cloud storage using its URL."""
        try:
            result = await self._cloud_port.delete_document(document_url)
            logger.info(
                "cloud_manager.delete_document.completed",
                log_type="business",
                document_url=document_url,
            )
            return result

        except CloudAdapterError as e:
            raise CloudManagerError("Failed to delete document from cloud storage.") from e

        except Exception as e:
            logger.error(
                "cloud_manager.delete_document.unexpected.failed",
                log_type="technical",
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise CloudManagerError("Unexpected error while deleting document from cloud storage.") from e