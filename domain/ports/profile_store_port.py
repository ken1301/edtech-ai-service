from abc import ABC, abstractmethod
from typing import Optional

from domain.models.profile import StudentProfile


class ProfileStorePort(ABC):
    @abstractmethod
    async def get_student_profile(self, student_id: str) -> Optional[StudentProfile]:
        """Lấy hồ sơ chi tiết của học sinh"""
        pass

    @abstractmethod
    async def update_student_preferences(self, student_id: str, data: dict) -> bool:
        """Cập nhật những tùy chọn của học sinh"""
        pass

    @abstractmethod
    async def update_knowledge_map(self, student_id: str, subject: str, topic: str, data: dict) -> bool:
        """Cập nhật lỗ hổng kiến thức hoặc điểm số sau mỗi buổi học"""
        pass

    @abstractmethod
    async def save_profile(self, profile: StudentProfile) -> bool:
        """Tạo mới hoặc ghi đè toàn bộ profile"""
        pass
