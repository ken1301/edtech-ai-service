from abc import abstractmethod, ABC

from domain.models.overall_models.document import PDFDocument, ImageDocument, MarkdownDocument

class CloudPort(ABC):
    @abstractmethod
    async def upload_document(
        self,
        document: PDFDocument | ImageDocument | MarkdownDocument
    ) -> str:
        """Tải lên một tài liệu (PDF, hình ảnh hoặc Markdown) và trả về URL truy cập nếu thành công, None nếu thất bại."""
        pass

    @abstractmethod
    async def download_document(
        self,
        document_url: str
    ) -> PDFDocument | ImageDocument | MarkdownDocument:
        """Tải xuống một tài liệu (PDF, hình ảnh hoặc Markdown) và trả về đối tượng tương ứng."""
        pass

    @abstractmethod
    async def delete_document(
        self,
        document_url: str
    ) -> bool:
        """Xóa một tài liệu khỏi lưu trữ đám mây và trả về True nếu thành công, False nếu thất bại."""
        pass