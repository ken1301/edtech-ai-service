from abc import abstractmethod, ABC

from domain.models.document import PDFDocument, ImageDocument

class CloudPort(ABC):
    
    @abstractmethod
    async def upload_pdf(self, document: PDFDocument) -> bool:
        """Tải lên một tài liệu PDF và trả về True nếu thành công, False nếu thất bại."""
        pass

    @abstractmethod
    async def download_pdf(self, document_id: str) -> PDFDocument:
        """Tải xuống một tài liệu PDF và trả về đối tượng PDFDocument."""
        pass

    @abstractmethod
    async def upload_image(self, document: ImageDocument) -> bool:
        """Tải lên một hình ảnh và trả về True nếu thành công, False nếu thất bại."""
        pass

    @abstractmethod
    async def download_image(self, document_id: str) -> ImageDocument:
        """Tải xuống một hình ảnh và trả về đối tượng ImageDocument."""
        pass

    @abstractmethod
    async def delete_document(self, document_id: str) -> bool:
        """Xóa một tài liệu dựa trên ID và trả về True nếu thành công, False nếu thất bại."""
        pass