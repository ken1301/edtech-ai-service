from abc import ABC, abstractmethod
from typing import List

from domain.models.exercise import Exercise

class ExerciseStorePort(ABC):

    @abstractmethod
    async def save_exercise(self, exercise: Exercise) -> bool:
        """Lưu một danh sách bài tập vào kho lưu trữ và trả về True nếu thành công, False nếu thất bại."""
        pass

    @abstractmethod
    async def get_exercise_by_id(self, exercise_id: str) -> Exercise:
        """Lấy một bài tập dựa trên ID và trả về đối tượng Exercise."""
        pass

    @abstractmethod
    async def delete_exercise(self, exercise_id: str) -> bool:
        """Xóa một bộ bài tập dựa trên ID và trả về True nếu thành công, False nếu thất bại."""
        pass