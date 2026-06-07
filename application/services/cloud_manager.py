from domain.ports.cloud_port import CloudPort

from domain.models.overall_models.document import PDFDocument, ImageDocument

from domain.exceptions import CloudAdapterError, CloudManagerError

from infrastructure.logging import logger

class CloudManager:
    """Service responsible for managing interactions with cloud storage, including uploading and retrieving documents."""

    def __init__(self, cloud_port: CloudPort):
        self._cloud_port = cloud_port

    async def fetch_pdf_document(self, document_url: str) -> PDFDocument:
        """Fetch a PDF document from cloud storage using its unique identifier."""
        try:
            pdf_document = await self._cloud_port.download_pdf(document_url=document_url)
            
            logger.info(
                "cloud_manager.fetch_pdf_document.completed",
                log_type="business",
                document_url=document_url
            )
            return pdf_document

        except CloudAdapterError as e:
            raise CloudManagerError("Failed to fetch PDF document from cloud storage.") from e
        
        except Exception as e:
            logger.error(
                "cloud_manager.fetch_pdf_document.unexpected.failed",
                log_type="technical",
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise CloudManagerError("Unexpected error while fetching PDF document from cloud storage.") from e

    async def upload_image_document(self, image_document: ImageDocument) -> str:
        """Upload an image document to cloud storage and return its accessible URL."""
        try:
            image_url = await self._cloud_port.upload_image(document=image_document)
            
            logger.info(
                "cloud_manager.upload_image_document.completed",
                log_type="business",
                document_url=image_document.url
            )
            return image_url

        except CloudAdapterError as e:
            raise CloudManagerError("Failed to upload image document to cloud storage.") from e

        except Exception as e:
            logger.error(
                "cloud_manager.upload_image_document.unexpected.failed",
                log_type="technical",
                document_url=image_document.url,
                error=str(e),
                exc_info=True,
            )
            raise CloudManagerError("Unexpected error while uploading image document to cloud storage.") from e