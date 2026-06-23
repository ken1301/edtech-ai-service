from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import AliasChoices, BaseModel, Field

from adapters.inbound.rest.schemas import DocumentExtractionRequest, ExerciseExtractionRequest
from domain.exceptions import LegacyExerciseJobError
from domain.models.overall_models.curriculum import Concept, Subject, Topic
from domain.ports.legacy_exercise_job_port import LegacyExerciseJobPort, ProgressReporter
from infrastructure.logging import logger


class LegacyExerciseJobPayload(BaseModel):
    teacherId: str
    classId: str | None = None
    fileUrl: str = ""
    title: str | None = None
    description: str | None = None
    accessToken: str | None = None
    subject: str
    topic: str
    concept: str
    previous_lessons: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("previous_lessons", "previousLessons"),
    )


class LegacyExerciseJobService(LegacyExerciseJobPort):
    """Translate a legacy BullMQ job into the existing lesson creation use case."""

    def __init__(self, lesson_creation_manager):
        self._lesson_creation_manager = lesson_creation_manager

    async def process_job(
        self,
        *,
        job_id: str,
        payload: Mapping[str, Any],
        progress_reporter: ProgressReporter | None = None,
    ) -> dict[str, Any]:
        job = LegacyExerciseJobPayload.model_validate(payload)
        lesson1_request = self._build_lesson1_request(job_id=job_id, job=job)
        lesson2_request = self._build_lesson2_request(job_id=job_id, job=job)

        if progress_reporter is not None:
            await progress_reporter({"status": "parsing", "progress": 30})

        lesson1_response = await self._lesson_creation_manager.lesson1_run(
            user_id=lesson1_request.user_id,
            lesson_id=lesson1_request.lesson_id,
            document_url=lesson1_request.document_url,
            previous_lessons=lesson1_request.previous_lessons,
            subject=lesson1_request.subject,
            topic=lesson1_request.topic,
            concept=lesson1_request.concept,
        )

        if progress_reporter is not None:
            await progress_reporter({"status": "parsing", "progress": 70})

        lesson2_response = await self._lesson_creation_manager.lesson2_run(
            user_id=lesson2_request.user_id,
            lesson_id=lesson2_request.lesson_id,
            document_url=lesson2_request.document_url,
            subject=lesson2_request.subject,
            topic=lesson2_request.topic,
            concept=lesson2_request.concept,
        )

        lesson1_dump = lesson1_response.model_dump(mode="json")
        lesson2_dump = lesson2_response.model_dump(mode="json")
        theory_markdown = self._build_theory_markdown(lesson1_dump.get("output", {}).get("knowledge"))

        result = {
            "teacherId": job.teacherId,
            "classId": job.classId,
            "title": job.title or "Bài tập AI tự động",
            "description": theory_markdown or job.description or "Sinh ra từ file đính kèm",
            "subject": lesson1_request.subject.value,
            "topic": lesson1_request.topic.value,
            "concept": lesson1_request.concept.value,
            "lesson_id": job_id,
            "lesson1_exercise_id": lesson1_response.exercise_id,
            "lesson2_exercise_id": lesson2_response.exercise_id,
            "lesson1_summary": lesson1_dump.get("output", {}).get("summary"),
            "lesson2_summary": lesson2_dump.get("output", {}).get("summary"),
            "problem_list": lesson2_dump.get("output", {}).get("exercise", {}).get("problem_list", []),
            "extracted_questions": lesson1_dump.get("output", {}).get("exercises", []),
            "lesson1": lesson1_dump,
            "lesson2": lesson2_dump,
            "theory_markdown": theory_markdown,
        }

        logger.info(
            "legacy_exercise_job_service.completed",
            log_type="business",
            teacher_id=job.teacherId,
            lesson_id=job_id,
            subject=lesson1_request.subject.value,
            topic=lesson1_request.topic.value,
            concept=lesson1_request.concept.value,
        )
        return result

    def _build_lesson1_request(
        self,
        *,
        job_id: str,
        job: LegacyExerciseJobPayload,
    ) -> DocumentExtractionRequest:
        subject, topic, concept = self._resolve_curriculum(job)
        previous_lessons = self._resolve_previous_lessons(job.previous_lessons)
        return DocumentExtractionRequest(
            user_id=job.teacherId,
            lesson_id=job_id,
            document_url=job.fileUrl,
            previous_lessons=previous_lessons,
            subject=subject,
            topic=topic,
            concept=concept,
        )

    def _build_lesson2_request(
        self,
        *,
        job_id: str,
        job: LegacyExerciseJobPayload,
    ) -> ExerciseExtractionRequest:
        subject, topic, concept = self._resolve_curriculum(job)
        return ExerciseExtractionRequest(
            user_id=job.teacherId,
            lesson_id=job_id,
            document_url=job.fileUrl,
            subject=subject,
            topic=topic,
            concept=concept,
        )

    @staticmethod
    def _resolve_curriculum(job: LegacyExerciseJobPayload) -> tuple[Subject, Topic, Concept]:
        try:
            subject = Subject(job.subject)
            topic = Topic(job.topic)
            concept = Concept(job.concept)
        except ValueError as exc:
            raise LegacyExerciseJobError("Legacy exercise job contains invalid curriculum values.") from exc

        if topic.subject != subject:
            raise LegacyExerciseJobError(
                f"Topic '{topic.value}' does not belong to subject '{subject.value}'."
            )
        if concept.topic != topic:
            raise LegacyExerciseJobError(
                f"Concept '{concept.value}' does not belong to topic '{topic.value}'."
            )

        return subject, topic, concept

    @staticmethod
    def _resolve_previous_lessons(previous_lessons: list[str]) -> list[Concept]:
        resolved_previous_lessons: list[Concept] = []
        for lesson in previous_lessons:
            try:
                resolved_previous_lessons.append(Concept(lesson))
            except ValueError as exc:
                raise LegacyExerciseJobError(
                    f"Previous lesson '{lesson}' is not a valid concept."
                ) from exc

        return resolved_previous_lessons

    @staticmethod
    def _build_theory_markdown(knowledge: dict[str, Any] | None) -> str:
        if not knowledge:
            return ""

        sections: list[str] = []
        concept_name = knowledge.get("concept_name") or ""
        if concept_name:
            sections.append(f"# {concept_name}")

        hook = knowledge.get("hook")
        if hook:
            sections.append(f"## Đặt vấn đề\n{hook}")

        items = knowledge.get("items") or []
        if items:
            lines = ["## Lý thuyết bài học"]
            for item in items:
                title = item.get("title") or ""
                content = item.get("content") or ""
                lines.append(f"### {title}\n{content}")
            sections.append("\n\n".join(lines))

        return "\n\n".join(section for section in sections if section)