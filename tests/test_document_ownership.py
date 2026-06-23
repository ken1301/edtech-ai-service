import unittest

from domain.exceptions import CloudAdapterError
from adapters.outbound.docs_storage.s3_adapter import S3Adapter
from domain.models.overall_models.document import ImageDocument, PDFDocument


class _FakeBody:
    def read(self):
        return b"pdf"


class _FakeS3Client:
    def __init__(self):
        self.get_object_calls = []
        self.put_object_calls = []
        self.content_type = "application/pdf"
        self.content_length = 3

    def head_bucket(self, Bucket):
        return None

    def get_object(self, Bucket, Key):
        self.get_object_calls.append((Bucket, Key))
        return {
            "Body": _FakeBody(),
            "ContentLength": self.content_length,
            "ContentType": self.content_type,
            "Metadata": {},
        }

    def put_object(self, **kwargs):
        self.put_object_calls.append(kwargs)


class DocumentOwnershipTests(unittest.TestCase):
    def test_download_uses_shared_default_bucket_name(self):
        client = _FakeS3Client()
        adapter = S3Adapter(s3_client=client)

        document = adapter._download_pdf(
            "http://localhost:9000/edtech/users/user-1/file.pdf",
            "user-1",
        )

        self.assertEqual(document.id, "user-1")
        self.assertEqual(client.get_object_calls, [("edtech", "users/user-1/file.pdf")])

    def test_download_rejects_other_user_prefix(self):
        adapter = S3Adapter(s3_client=_FakeS3Client(), bucket_name="edtech")

        with self.assertRaises(CloudAdapterError):
            adapter._download_pdf("http://localhost:9000/edtech/users/user-2/file.pdf", "user-1")

    def test_download_accepts_matching_user_prefix(self):
        client = _FakeS3Client()
        adapter = S3Adapter(s3_client=client, bucket_name="edtech")

        document = adapter._download_pdf(
            "http://localhost:9000/edtech/users/user-1/pdfs/doc-1/file.pdf",
            "user-1",
        )

        self.assertEqual(document.id, "doc-1")
        self.assertEqual(client.get_object_calls, [("edtech", "users/user-1/pdfs/doc-1/file.pdf")])

    def test_download_accepts_legacy_uploads_prefix_for_matching_user(self):
        client = _FakeS3Client()
        adapter = S3Adapter(s3_client=client, bucket_name="edtech")

        document = adapter._download_pdf(
            "http://localhost:9000/edtech/uploads/users/user-1/pdfs/doc-1/file.pdf",
            "user-1",
        )

        self.assertEqual(document.id, "doc-1")
        self.assertEqual(client.get_object_calls, [("edtech", "users/user-1/pdfs/doc-1/file.pdf")])

    def test_download_rejects_mismatched_pdf_content_type(self):
        client = _FakeS3Client()
        client.content_type = "image/png"
        adapter = S3Adapter(s3_client=client, bucket_name="edtech")

        with self.assertRaises(CloudAdapterError):
            adapter._download_pdf(
                "http://localhost:9000/edtech/users/user-1/pdfs/doc-1/file.pdf",
                "user-1",
            )

    def test_upload_rejects_filename_with_path_segments(self):
        adapter = S3Adapter(s3_client=_FakeS3Client(), bucket_name="edtech")
        document = PDFDocument(
            id="doc-1",
            filename="../file.pdf",
            content=b"pdf",
            size_bytes=3,
        )

        with self.assertRaises(CloudAdapterError):
            adapter._resolve_upload_spec(document)

    def test_upload_rejects_oversized_document_payload(self):
        adapter = S3Adapter(s3_client=_FakeS3Client(), bucket_name="edtech")
        adapter._max_document_bytes = 2
        document = PDFDocument(
            id="doc-1",
            filename="file.pdf",
            content=b"pdf",
            size_bytes=3,
        )

        with self.assertRaises(CloudAdapterError):
            adapter._upload_document(document, "user-1", "pdfs", "application/pdf")

    def test_upload_sets_specific_image_content_type(self):
        client = _FakeS3Client()
        adapter = S3Adapter(s3_client=client, bucket_name="edtech")
        document = ImageDocument(
            id="img-1",
            filename="diagram.png",
            content=b"png-bytes",
            parent_pdf_id="doc-1",
        )

        document_type, content_type = adapter._resolve_upload_spec(document)
        url = adapter._upload_document(document, "user-1", document_type, content_type)

        self.assertEqual(content_type, "image/png")
        self.assertEqual(url, "https://edtech.s3.amazonaws.com/users/user-1/images/img-1/diagram.png")
        self.assertEqual(client.put_object_calls[0]["ContentType"], "image/png")
        self.assertEqual(client.put_object_calls[0]["Key"], "users/user-1/images/img-1/diagram.png")


if __name__ == "__main__":
    unittest.main()