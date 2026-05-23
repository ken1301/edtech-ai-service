from domain.models.exercise import Exercise, ExerciseForPurpose
from domain.models.profile import StudentProfile



class AdaptiveLearningService:

    def __init__(self):
        pass

    async def problem_select(
        self,
        student_profile: StudentProfile,
        exercise: Exercise
    ) -> ExerciseForPurpose:
        """Phân tích và chọn bài tập phù hợp dựa trên hồ sơ học sinh và bài tập đã cho."""
        pass

    async def update_student_profile(
        self,
        old_student_profile: StudentProfile,
        new_student_profile: StudentProfile,
    ) -> StudentProfile:
        """Cập nhật hồ sơ học sinh dựa trên thông tin mới thu thập được sau khi học sinh hoàn thành bài tập."""
        pass

    async def summarize_student_profile(
        self,
        student_profile: StudentProfile
    ) -> str:
        """Tóm tắt hồ sơ học sinh thành một đoạn văn ngắn gọn để sử dụng trong prompt cho LLM."""
        pass