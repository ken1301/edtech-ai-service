from domain.ports.cloud_port import CloudPort
from domain.models.document import PDFDocument, ImageDocument

from domain.exceptions import CloudAdapterError

from infrastructure.logging import logger

class S3Adapter(CloudPort):

    def __init__(self):
        # Initialize S3 client here (e.g., using boto3)
        pass
    
    async def upload_pdf(self, document: PDFDocument) -> bool:
        pass

    async def download_pdf(self, document_id: str) -> PDFDocument:
        pass

    async def upload_image(self, document: ImageDocument) -> bool:
        pass

    async def download_image(self, document_id: str) -> ImageDocument:
        pass

    async def delete_document(self, document_id: str) -> bool:
        pass