from domain.ports.cloud_port import CloudPort

from domain.models.document import PDFDocument, ImageDocument, MarkdownDocument

from domain.exceptions import CloudAdapterError, CloudManagerError

from infrastructure.logging import logger

class CloudManager:
    """Service responsible for managing interactions with cloud storage, including uploading and retrieving documents."""

    def __init__(self, cloud_port: CloudPort):
        self._cloud_port = cloud_port

    async def fetch_pdf_document(self, document_url: str) -> PDFDocument:
        """Fetch a PDF document from cloud storage using its unique identifier."""
        pass

    async def upload_image_document(self, image_document: ImageDocument) -> str:
        """Upload an image document to cloud storage and return its accessible URL."""
        pass