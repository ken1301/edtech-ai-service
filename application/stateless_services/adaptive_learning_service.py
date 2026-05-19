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