from io import BytesIO

import fitz
import pymupdf4llm

from domain.models.overall_models.document import PDFDocument, MarkdownDocument, ImageDocument

from domain.exceptions import DocumentTransformationError

from infrastructure.logging import logger

class PDFToMarkdownTransformer:
    """Service responsible for transforming PDF documents into Markdown format, including handling of embedded images."""

    def __init__(self):
        pass

    async def execute(self, pdf_document: PDFDocument) -> tuple[MarkdownDocument, list[ImageDocument]]:
        """Main method to transform a PDF document into Markdown format, extracting text and images as needed."""

        try:
            # 1. Load PDF from bytes using PyMuPDF (fitz)
            doc = fitz.open(stream=pdf_document.content, filetype="pdf")

            # 2. Extract markdown text using pymupdf4llm
            markdown_content = pymupdf4llm.to_markdown(doc)
            
            # (Optional) Image extraction can be added later if needed. For now, empty list saves RAM.
            image_set: list[ImageDocument] = []

            markdown_document = MarkdownDocument(
                id=pdf_document.id,
                filename=pdf_document.filename,
                content=markdown_content,
                parent_pdf_id=pdf_document.id,
            )

            logger.info(
                "pdf_to_markdown_transformer.execute.completed",
                log_type="business",
                document_id=pdf_document.id,
                image_count=len(image_set),
            )
            return markdown_document, image_set

        except Exception as e:
            logger.error(
                "pdf_to_markdown_transformer.execute.failed",
                log_type="technical",
                document_id=pdf_document.id,
                error=str(e),
                exc_info=True,
            )
            raise DocumentTransformationError("Failed to transform PDF document to Markdown.") from e
