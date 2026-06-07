from abc import abstractmethod, ABC

from domain.models.overall_models.document import PDFDocument, ImageDocument, MarkdownDocument

class CloudPort(ABC):
    
    @abstractmethod
    async def upload_pdf(self, document: PDFDocument) -> str:
        """Tải lên một tài liệu PDF và trả về URL truy cập nếu thành công, None nếu thất bại."""
        pass

    @abstractmethod
    async def download_pdf(self, document_url: str) -> PDFDocument:
        """Tải xuống một tài liệu PDF và trả về đối tượng PDFDocument."""
        pass

    @abstractmethod
    async def upload_image(self, document: ImageDocument) -> str:
        """Tải lên một hình ảnh và trả về URL truy cập nếu thành công, None nếu thất bại."""
        pass

    @abstractmethod
    async def download_image(self, document_url: str) -> ImageDocument:
        """Tải xuống một hình ảnh và trả về đối tượng ImageDocument."""
        pass

    @abstractmethod
    async def delete_document(self, document_url: str) -> bool:
        """Xóa một tài liệu dựa trên URL và trả về True nếu thành công, False nếu thất bại."""
        pass