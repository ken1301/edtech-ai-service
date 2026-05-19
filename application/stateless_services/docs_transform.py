from PIL import Image
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered

from domain.models.document import PDFDocument, MarkdownDocument, ImageDocument

from domain.exceptions import DocumentTransformationError

from infrastructure.logging import logger

class PDFToMarkdownTransformer:
    """Service responsible for transforming PDF documents into Markdown format, including handling of embedded images."""

    def __init__(self):
        pass

    async def execute(self, pdf_document: PDFDocument) -> tuple[MarkdownDocument, list[ImageDocument]]:
        """Main method to transform a PDF document into Markdown format, extracting text and images as needed."""

        pass
