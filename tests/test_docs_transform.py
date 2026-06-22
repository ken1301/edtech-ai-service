import unittest
from unittest.mock import patch

from application.stateless_services.docs_transform import PDFToMarkdownTransformer
from domain.exceptions import DocumentTransformationError
from domain.models.overall_models.document import PDFDocument


class _FakeRenderedImage:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.save_calls = []

    def save(self, buffer, format: str):
        self.save_calls.append(format)
        buffer.write(self.payload)


class _FakeConverter:
    def __init__(self, artifact_dict):
        self.artifact_dict = artifact_dict
        self.calls = []

    def __call__(self, stream):
        self.calls.append(stream.read())
        return "rendered-document"


class PDFToMarkdownTransformerTests(unittest.IsolatedAsyncioTestCase):
    async def test_execute_converts_pdf_and_builds_markdown_and_images(self):
        pdf_document = PDFDocument(
            id="pdf-1",
            filename="lesson.pdf",
            content=b"%PDF-1.7",
            size_bytes=8,
        )
        fake_converter = _FakeConverter(artifact_dict={"model": "fake"})
        rendered_images = {
            "page-1.png": _FakeRenderedImage(b"img-1"),
            "page-2.png": _FakeRenderedImage(b"img-2"),
        }

        with patch(
            "application.stateless_services.docs_transform.create_model_dict",
            return_value={"model": "fake"},
        ), patch(
            "application.stateless_services.docs_transform.PdfConverter",
            return_value=fake_converter,
        ), patch(
            "application.stateless_services.docs_transform.text_from_rendered",
            return_value=("# Markdown", None, rendered_images),
        ):
            markdown_document, image_set = await PDFToMarkdownTransformer().execute(pdf_document)

        self.assertEqual(fake_converter.artifact_dict, {"model": "fake"})
        self.assertEqual(fake_converter.calls, [b"%PDF-1.7"])
        self.assertEqual(markdown_document.id, "pdf-1")
        self.assertEqual(markdown_document.filename, "lesson.pdf")
        self.assertEqual(markdown_document.content, "# Markdown")
        self.assertEqual(markdown_document.parent_pdf_id, "pdf-1")
        self.assertEqual(len(image_set), 2)
        self.assertEqual(image_set[0].id, "pdf-1_0")
        self.assertEqual(image_set[0].filename, "page-1.png")
        self.assertEqual(image_set[0].content, b"img-1")
        self.assertEqual(image_set[0].parent_pdf_id, "pdf-1")
        self.assertEqual(image_set[1].id, "pdf-1_1")
        self.assertEqual(image_set[1].filename, "page-2.png")
        self.assertEqual(image_set[1].content, b"img-2")
        self.assertEqual(image_set[1].parent_pdf_id, "pdf-1")
        self.assertEqual(rendered_images["page-1.png"].save_calls, ["PNG"])
        self.assertEqual(rendered_images["page-2.png"].save_calls, ["PNG"])

    async def test_execute_wraps_converter_failures(self):
        pdf_document = PDFDocument(
            id="pdf-2",
            filename="broken.pdf",
            content=b"broken",
            size_bytes=6,
        )

        with patch(
            "application.stateless_services.docs_transform.create_model_dict",
            return_value={"model": "fake"},
        ), patch(
            "application.stateless_services.docs_transform.PdfConverter",
            side_effect=RuntimeError("converter init failed"),
        ):
            with self.assertRaises(DocumentTransformationError) as context:
                await PDFToMarkdownTransformer().execute(pdf_document)

        self.assertEqual(str(context.exception), "Failed to transform PDF document to Markdown.")


if __name__ == "__main__":
    unittest.main()