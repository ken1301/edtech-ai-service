from io import BytesIO

from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered

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
            # 1. Convert PDF bytes using marker's expected converter configuration.
            converter = PdfConverter(artifact_dict=create_model_dict())
            rendered_document = converter(BytesIO(pdf_document.content))

            # 2. Extract markdown text and rendered images from the converted document.
            markdown_content, _, rendered_images = text_from_rendered(rendered_document)
            image_set: list[ImageDocument] = []
            for index, (image_name, image) in enumerate(rendered_images.items()):
                image_buffer = BytesIO()
                image.save(image_buffer, format="PNG")
                image_set.append(
                    ImageDocument(
                        id=f"{pdf_document.id}_{index}",
                        filename=image_name,
                        content=image_buffer.getvalue(),
                        parent_pdf_id=pdf_document.id,
                    )
                )

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
