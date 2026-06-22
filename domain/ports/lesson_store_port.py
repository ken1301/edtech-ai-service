from abc import ABC, abstractmethod
from typing import List

from domain.models.lesson2_models.exercise import Exercise
from domain.models.overall_models.lesson1 import CreateLessonMetadata

class LessonStorePort(ABC):

    # === Lesson creation metadata ===
    @abstractmethod
    async def save_lesson_creation_metadata(
        self,
        lesson_id: str,
        user_id: str,
        metadata: CreateLessonMetadata
    ) -> bool:
        """Lưu metadata liên quan đến việc tạo bài học và trả về True nếu thành công, False nếu thất bại."""
        pass

    @abstractmethod
    async def get_lesson_creation_metadata(self, lesson_id: str, user_id: str) -> CreateLessonMetadata:
        """Lấy metadata liên quan đến việc tạo bài học dựa trên ID và trả về đối tượng CreateLessonMetadata."""
        pass
    
    # === Exercise Management ===
    @abstractmethod
    async def save_exercise(self, exercise_id: str, user_id: str, exercise: Exercise) -> bool:
        """Lưu một danh sách bài tập vào kho lưu trữ và trả về True nếu thành công, False nếu thất bại."""
        pass

    @abstractmethod
    async def get_exercise(self, exercise_id: str, user_id: str) -> Exercise:
        """Lấy một bài tập dựa trên ID và trả về đối tượng Exercise."""
        pass

    @abstractmethod
    async def delete_exercise(self, exercise_id: str, user_id: str) -> bool:
        """Xóa một bộ bài tập dựa trên ID và trả về True nếu thành công, False nếu thất bại."""
        pass

    