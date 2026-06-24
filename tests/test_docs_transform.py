import unittest
from unittest.mock import sentinel, patch

from application.stateless_services.docs_transform import PDFToMarkdownTransformer
from domain.exceptions import DocumentTransformationError
from domain.models.overall_models.document import PDFDocument


class PDFToMarkdownTransformerTests(unittest.IsolatedAsyncioTestCase):
    async def test_execute_converts_pdf_and_builds_markdown_and_images(self):
        pdf_document = PDFDocument(
            id="pdf-1",
            filename="lesson.pdf",
            content=b"%PDF-1.7",
            size_bytes=8,
        )

        with patch(
            "application.stateless_services.docs_transform.fitz.open",
            return_value=sentinel.doc,
        ) as open_pdf, patch(
            "application.stateless_services.docs_transform.pymupdf4llm.to_markdown",
            return_value="# Markdown",
        ) as to_markdown:
            markdown_document, image_set = await PDFToMarkdownTransformer().execute(pdf_document)

        open_pdf.assert_called_once_with(stream=b"%PDF-1.7", filetype="pdf")
        to_markdown.assert_called_once_with(sentinel.doc)
        self.assertEqual(markdown_document.id, "pdf-1")
        self.assertEqual(markdown_document.filename, "lesson.pdf")
        self.assertEqual(markdown_document.content, "# Markdown")
        self.assertEqual(markdown_document.parent_pdf_id, "pdf-1")
        self.assertEqual(image_set, [])

    async def test_execute_wraps_converter_failures(self):
        pdf_document = PDFDocument(
            id="pdf-2",
            filename="broken.pdf",
            content=b"broken",
            size_bytes=6,
        )

        with patch(
            "application.stateless_services.docs_transform.fitz.open",
            side_effect=RuntimeError("converter init failed"),
        ):
            with self.assertRaises(DocumentTransformationError) as context:
                await PDFToMarkdownTransformer().execute(pdf_document)

        self.assertEqual(str(context.exception), "Failed to transform PDF document to Markdown.")


if __name__ == "__main__":
    unittest.main()