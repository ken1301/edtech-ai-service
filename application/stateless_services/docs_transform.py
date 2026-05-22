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

        try:
            # 1. Convert PDF to an intermediate format (e.g., using marker library)
            converter = PdfConverter()
            rendered_pages = converter.convert(pdf_document.file_path)

            # 2. Extract text content and images from the rendered pages
            markdown_content = ""
            image_set = []
            for page in rendered_pages:
                markdown_content += text_from_rendered(page)

                for element in page.elements:
                    if isinstance(element, Image.Image):
                        image_doc = ImageDocument(
                            filename=f"{pdf_document.document_id}_{len(image_set)}.png",
                            content=element
                        )
                        image_set.append(image_doc)

            markdown_document = MarkdownDocument(
                document_id=pdf_document.document_id,
                content=markdown_content
            )

            logger.info(
                "pdf_to_markdown_transformer.execute.completed",
                log_type="business",
                document_id=pdf_document.document_id,
                image_count=len(image_set),
            )
            return markdown_document, image_set

        except Exception as e:
            logger.error(
                "pdf_to_markdown_transformer.execute.failed",
                log_type="technical",
                document_id=pdf_document.document_id,
                error=str(e),
                exc_info=True,
            )
            raise DocumentTransformationError("Failed to transform PDF document to Markdown.") from e
