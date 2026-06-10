from copy import deepcopy
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence, Tuple

from domain.models.lesson2_models.exercise import Exercise, Problem, Lesson2Exercises
from domain.models.overall_models.common import BloomLevel, DifficultyLevel, ProblemRole
from domain.models.overall_models.profile import StudentPreference, LearningDetail, StudentProfile, LearningStyle, SessionSummary

from domain.exceptions import ProblemSelectionAnalysisError, UpdateStudentProfileError

from infrastructure.logging import logger

class AdaptiveLearningService:

    _ROLE_ORDER: tuple[ProblemRole, ...] = (
        ProblemRole.REINFORCEMENT,
        ProblemRole.CHALLENGE,
        ProblemRole.EXPLORATION,
        ProblemRole.EXTENSION,
    )

    _BLOOM_SCORES: Dict[BloomLevel, float] = {
        BloomLevel.REMEMBER: 0.15,
        BloomLevel.UNDERSTAND: 0.30,
        BloomLevel.APPLY: 0.50,
        BloomLevel.ANALYZE: 0.70,
        BloomLevel.EVALUATE: 0.85,
        BloomLevel.CREATE: 1.00,
    }

    _ROLE_TARGET_BLOOM: Dict[ProblemRole, float] = {
        ProblemRole.REINFORCEMENT: 0.28,
        ProblemRole.CHALLENGE: 0.52,
        ProblemRole.EXPLORATION: 0.76,
        ProblemRole.EXTENSION: 0.68,
    }

    _DIFFICULTY_SHIFT: Dict[DifficultyLevel, float] = {
        DifficultyLevel.EASY: -0.08,
        DifficultyLevel.MEDIUM: 0.00,
        DifficultyLevel.HARD: 0.08,
    }

    def __init__(self):
        pass

    @staticmethod
    def _clone_model(model):
        if hasattr(model, "model_copy"):
            return model.model_copy(deep=True)
        return deepcopy(model)

    @staticmethod
    def _enum_key(item):
        return getattr(item, "value", item)

    @classmethod
    def _unique_items(cls, primary: Sequence, secondary: Sequence) -> List:
        merged: List = []
        seen = set()

        for item in list(primary) + list(secondary):
            marker = cls._enum_key(item)
            if marker in seen:
                continue
            seen.add(marker)
            merged.append(item)

        return merged

    @staticmethod
    def _resolve_mapping_key(mapping: dict, candidate):
        if candidate in mapping:
            return candidate

        candidate_value = getattr(candidate, "value", candidate)
        for existing_key in mapping:
            if getattr(existing_key, "value", existing_key) == candidate_value:
                return existing_key

        return candidate

    @classmethod
    def _average_bloom_score(cls, problem: Problem) -> float:
        if not problem.approach_list:
            return 0.50

        scores = [cls._BLOOM_SCORES.get(approach.bloom_level, 0.50) for approach in problem.approach_list]
        return sum(scores) / len(scores)

    @staticmethod
    def _style_overlap(learning_style: Optional[LearningStyle], problem: Problem) -> float:
        if learning_style is None:
            return 0.0

        student_ops = set(learning_style.cognitive_operation)
        student_reps = set(learning_style.representation)
        if not student_ops and not student_reps:
            return 0.0

        best_overlap = 0.0
        for approach in problem.approach_list:
            approach_ops = set(approach.pattern.cognitive_operation)
            approach_reps = set(approach.pattern.representation)

            op_overlap = 0.0
            rep_overlap = 0.0

            if student_ops and approach_ops:
                op_overlap = len(student_ops & approach_ops) / len(student_ops | approach_ops)
            if student_reps and approach_reps:
                rep_overlap = len(student_reps & approach_reps) / len(student_reps | approach_reps)

            best_overlap = max(best_overlap, (op_overlap + rep_overlap) / 2)

        return best_overlap

    @classmethod
    def _score_problem(cls, problem: Problem, student_profile: StudentProfile, role: ProblemRole) -> float:
        preference = student_profile.preferences
        difficulty_shift = cls._DIFFICULTY_SHIFT.get(preference.preferred_difficulty, 0.0)
        target_bloom = max(0.0, min(1.0, cls._ROLE_TARGET_BLOOM[role] + difficulty_shift))
        average_bloom = cls._average_bloom_score(problem)

        score = 1.0 - abs(average_bloom - target_bloom)

        if problem.open_approach:
            score += 0.12 if role in {ProblemRole.EXPLORATION, ProblemRole.EXTENSION} else -0.05
        else:
            score += 0.08 if role in {ProblemRole.REINFORCEMENT, ProblemRole.CHALLENGE} else -0.03

        score += min(len(problem.approach_list), 4) * 0.025
        score += cls._style_overlap(preference.learning_style, problem) * 0.20

        if role == ProblemRole.REINFORCEMENT:
            score += 0.05 if average_bloom <= 0.35 else 0.0
        elif role == ProblemRole.CHALLENGE:
            score += 0.05 if 0.30 <= average_bloom <= 0.60 else 0.0
        elif role == ProblemRole.EXPLORATION:
            score += 0.05 if average_bloom >= 0.60 else 0.0
        elif role == ProblemRole.EXTENSION:
            score += 0.05 if average_bloom >= 0.55 else 0.0

        return score

    @classmethod
    def _merge_learning_style(
        cls,
        old_style: Optional[LearningStyle],
        new_style: Optional[LearningStyle],
    ) -> Optional[LearningStyle]:
        if old_style is None and new_style is None:
            return None
        if old_style is None:
            return cls._clone_model(new_style)
        if new_style is None:
            return cls._clone_model(old_style)

        return LearningStyle(
            cognitive_operation=cls._unique_items(old_style.cognitive_operation, new_style.cognitive_operation),
            representation=cls._unique_items(old_style.representation, new_style.representation),
        )

    @classmethod
    def _merge_preferences(
        cls,
        old_preferences: StudentPreference,
        new_preferences: StudentPreference,
    ) -> StudentPreference:
        merged_preferences = cls._clone_model(old_preferences)

        if new_preferences.summary and new_preferences.summary.strip():
            merged_preferences.summary = new_preferences.summary.strip()

        merged_preferences.strengths = cls._unique_items(old_preferences.strengths, new_preferences.strengths)
        merged_preferences.weaknesses = cls._unique_items(old_preferences.weaknesses, new_preferences.weaknesses)
        merged_preferences.learning_style = cls._merge_learning_style(
            old_preferences.learning_style,
            new_preferences.learning_style,
        )

        if new_preferences.preferred_difficulty is not None:
            merged_preferences.preferred_difficulty = new_preferences.preferred_difficulty

        merged_preferences.other_preferences = {
            **old_preferences.other_preferences,
            **new_preferences.other_preferences,
        }

        return merged_preferences

    @classmethod
    def _merge_learning_detail(
        cls,
        old_detail: LearningDetail,
        new_detail: LearningDetail,
    ) -> LearningDetail:
        avg_score = (old_detail.avg_score + new_detail.avg_score) / 2
        last_practiced = max(old_detail.last_practiced, new_detail.last_practiced)

        mastering_at = cls._unique_items(old_detail.mastering_at, new_detail.mastering_at)
        struggling_at = cls._unique_items(old_detail.struggling_at, new_detail.struggling_at)
        mastered_markers = {cls._enum_key(item) for item in mastering_at}
        struggling_at = [item for item in struggling_at if cls._enum_key(item) not in mastered_markers]

        finished_exercise = {
            **old_detail.finished_exercise,
            **new_detail.finished_exercise,
        }

        return LearningDetail(
            avg_score=avg_score,
            last_practiced=last_practiced,
            mastering_at=mastering_at,
            struggling_at=struggling_at,
            finished_exercise=finished_exercise,
        )

    @classmethod
    def _merge_knowledge_map(cls, old_map, new_map):
        merged_map = cls._clone_model(old_map)

        for subject, topics in new_map.items():
            subject_key = cls._resolve_mapping_key(merged_map, subject)
            subject_bucket = merged_map.setdefault(subject_key, {})

            for topic, concepts in topics.items():
                topic_key = cls._resolve_mapping_key(subject_bucket, topic)
                topic_bucket = subject_bucket.setdefault(topic_key, {})

                for concept, new_detail in concepts.items():
                    concept_key = cls._resolve_mapping_key(topic_bucket, concept)
                    old_detail = topic_bucket.get(concept_key)

                    if old_detail is None:
                        topic_bucket[concept_key] = cls._clone_model(new_detail)
                    else:
                        topic_bucket[concept_key] = cls._merge_learning_detail(old_detail, new_detail)

        return merged_map

    @staticmethod
    def _summarize_path(subject, topic, concept) -> str:
        return f"{getattr(subject, 'value', subject)}/{getattr(topic, 'value', topic)}/{getattr(concept, 'value', concept)}"

    @classmethod
    def _knowledge_highlights(cls, student_profile: StudentProfile) -> tuple[List[str], List[str]]:
        mastered: List[tuple[float, str]] = []
        struggling: List[tuple[float, str]] = []

        for subject, topics in student_profile.knowledge_map.items():
            for topic, concepts in topics.items():
                for concept, detail in concepts.items():
                    path = cls._summarize_path(subject, topic, concept)
                    if detail.avg_score >= 0.75 or detail.mastering_at:
                        mastered.append((detail.avg_score, path))
                    if detail.avg_score <= 0.45 or detail.struggling_at:
                        struggling.append((detail.avg_score, path))

        mastered.sort(key=lambda item: (-item[0], item[1]))
        struggling.sort(key=lambda item: (item[0], item[1]))

        mastered_items = [path for _, path in mastered[:2]]
        struggling_items = [path for _, path in struggling[:2]]
        return mastered_items, struggling_items

    @staticmethod
    def _format_enum_list(items: Sequence) -> str:
        values = [getattr(item, "value", str(item)) for item in items if item is not None]
        return ", ".join(values) if values else "none"

    async def problem_select(
        self,
        student_profile: StudentProfile,
        exercise: Exercise
    ) -> Lesson2Exercises:
        """Phân tích và chọn bài tập phù hợp dựa trên hồ sơ học sinh và bài tập đã cho."""
        try:
            selected_problem_set: Dict[ProblemRole, List[Problem]] = {role: [] for role in self._ROLE_ORDER}

            remaining_problems = list(exercise.problem_list)

            for role in self._ROLE_ORDER:
                if not remaining_problems:
                    break

                role_candidates = [
                    problem
                    for problem in remaining_problems
                    if problem.recommended_problem_role == role
                ]
                if not role_candidates:
                    role_candidates = list(remaining_problems)

                chosen_problem = max(
                    role_candidates,
                    key=lambda problem: (
                        self._score_problem(problem=problem, student_profile=student_profile, role=role),
                        -problem.problem_id,
                    ),
                )

                selected_problem_set[role] = [chosen_problem]
                remaining_problems = [problem for problem in remaining_problems if problem.problem_id != chosen_problem.problem_id]

            logger.info(
                "adaptive_learning_service.problem_select.completed",
                log_type="business",
                student_id=student_profile.student_id,
            )

            return Lesson2Exercises(problem_set=selected_problem_set)
        
        except (ValueError, TypeError, Exception) as e:
            logger.error(
                "adaptive_learning_service.problem_select.failed",
                log_type="technical",
                error=str(e),                
                exc_info=True,
            )
            raise ProblemSelectionAnalysisError("Failed to analyze and select problems.") from e

    async def update_student_profile(
        self,
        session_summary: SessionSummary,
        student_profile: StudentProfile,
    ) -> Tuple[StudentPreference, LearningDetail]:
        """Cập nhật hồ sơ học sinh dựa trên thông tin mới thu thập được sau khi học sinh hoàn thành bài tập."""
        try:
            now = datetime.now(timezone.utc)

            summary_preferences = StudentPreference(
                summary=session_summary.summary.strip() if session_summary.summary and session_summary.summary.strip() else None,
                strengths=session_summary.strengths,
                weaknesses=session_summary.weaknesses,
                learning_style=session_summary.learning_style,
                preferred_difficulty=session_summary.preferred_difficulty,
            )
            merged_preferences = self._merge_preferences(student_profile.preferences, summary_preferences)

            finished_exercise = self._clone_model(session_summary.finished_exercise)
            avg_score = (
                sum(performance.score for performance in finished_exercise.values()) / len(finished_exercise)
                if finished_exercise
                else 0.50
            )

            mastering_at = self._unique_items([], session_summary.mastering_at)
            struggling_at = self._unique_items([], session_summary.struggling_at)
            mastered_markers = {self._enum_key(item) for item in mastering_at}
            struggling_at = [item for item in struggling_at if self._enum_key(item) not in mastered_markers]

            session_detail = LearningDetail(
                avg_score=avg_score,
                last_practiced=now,
                mastering_at=mastering_at,
                struggling_at=struggling_at,
                finished_exercise=finished_exercise,
            )

            latest_detail = None
            latest_practiced = None
            for topics in student_profile.knowledge_map.values():
                for concepts in topics.values():
                    for detail in concepts.values():
                        if latest_detail is None or detail.last_practiced > latest_practiced:
                            latest_detail = detail
                            latest_practiced = detail.last_practiced

            merged_learning_detail = (
                self._merge_learning_detail(latest_detail, session_detail)
                if latest_detail is not None
                else session_detail
            )

            logger.info(
                "adaptive_learning_service.update_student_profile.completed",
                log_type="business",
                student_id=student_profile.user_id,
            )

            return merged_preferences, merged_learning_detail
        
        except (ValueError, TypeError, Exception) as e:
            logger.error(
                "adaptive_learning_service.update_student_profile.failed",
                log_type="technical",
                error=str(e),                
                exc_info=True,
            )
            raise UpdateStudentProfileError("Failed to update student profile with new information.") from e

    async def summarize_student_profile(
        self,
        student_profile: StudentProfile
    ) -> str:
        """Tóm tắt hồ sơ học sinh thành một đoạn văn ngắn gọn để sử dụng trong prompt cho LLM."""
        if not student_profile:
            return "No student profile is available yet."

        preferences = student_profile.preferences
        mastered, struggling = self._knowledge_highlights(student_profile)

        parts: List[str] = [
            f"Student {student_profile.full_name}, grade {student_profile.grade}.",
        ]

        if preferences.summary and preferences.summary.strip():
            parts.append(preferences.summary.strip())
        else:
            preference_bits: List[str] = []
            if preferences.preferred_difficulty is not None:
                preference_bits.append(f"prefers {preferences.preferred_difficulty.value} difficulty")

            if preferences.learning_style is not None:
                style_bits: List[str] = []
                if preferences.learning_style.cognitive_operation:
                    style_bits.append(f"cognitive ops: {self._format_enum_list(preferences.learning_style.cognitive_operation)}")
                if preferences.learning_style.representation:
                    style_bits.append(f"representations: {self._format_enum_list(preferences.learning_style.representation)}")
                if style_bits:
                    preference_bits.append("learning style: " + "; ".join(style_bits))

            if preferences.strengths:
                preference_bits.append(f"strengths: {self._format_enum_list(preferences.strengths)}")
            if preferences.weaknesses:
                preference_bits.append(f"weaknesses: {self._format_enum_list(preferences.weaknesses)}")

            if preference_bits:
                parts.append("; ".join(preference_bits))

        if mastered or struggling:
            knowledge_bits: List[str] = []
            if mastered:
                knowledge_bits.append(f"mastered: {', '.join(mastered)}")
            if struggling:
                knowledge_bits.append(f"struggling: {', '.join(struggling)}")
            parts.append("Knowledge signals - " + "; ".join(knowledge_bits))

        session_count = int(student_profile.metadata.get("total_sessions", 0) or 0)
        if session_count:
            parts.append(f"Total sessions: {session_count}.")

        summary = " ".join(parts).replace("  ", " ").strip()
        return summary