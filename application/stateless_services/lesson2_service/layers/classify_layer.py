from application.stateless_services.prompt_builder import PromptBuilder
from application.stateless_services.llm_manager import LLMManager

from domain.models.lesson2_models.classify import (
    ClassifyInput,
    ClassifyOutput,
    EmotionalSignal,
    Intent,
    Routing,
)
from domain.models.lesson2_models.common import Lesson2LayerUsage

from domain.exceptions import Lesson2LayerError, LLMManagerError, LLMManagerStructuredOutputError

from infrastructure.logging import logger

class ClassifyLayer:
    """Layer responsible for classifying the user's message and determining the appropriate response based on the content and context of the message."""

    def __init__(self, prompt_builder: PromptBuilder, llm_manager: LLMManager):
        self._prompt_builder = prompt_builder
        self._llm_manager = llm_manager

    @staticmethod
    def _safe_default_output(input: ClassifyInput) -> ClassifyOutput:
        user_msg = ClassifyLayer._extract_user_msg(input)
        abuse_flags: list[str] = []

        if any(marker in user_msg for marker in ["ignore previous", "system prompt", "jailbreak"]):
            abuse_flags.append("jailbreak")
            intent = Intent.JAILBREAK_ATTEMPT
            routing = Routing.FAST_PATH_REPLY
            learning_relevance = 0.0
        elif any(marker in user_msg for marker in ["give me the answer", "just the answer", "answer only"]):
            abuse_flags.append("extract_answer")
            intent = Intent.ANSWER_EXTRACTION
            routing = Routing.FAST_PATH_REPLY
            learning_relevance = 0.0
        elif any(marker in user_msg for marker in ["hurt myself", "kill myself", "emergency", "suicide"]):
            intent = Intent.EMOTIONAL_EXPRESSION
            routing = Routing.SAFETY_DIVERT
            learning_relevance = 0.0
        else:
            has_text = bool(user_msg.strip())
            intent = Intent.LEARNING_DISCUSSION if has_text else Intent.UNINTELLIGIBLE
            routing = Routing.FULL_PIPELINE if has_text else Routing.FAST_PATH_REPLY
            learning_relevance = 0.5 if has_text else 0.0

        return ClassifyOutput(
            intent=intent,
            intent_confidence=0.2,
            emotional=EmotionalSignal(
                valence=0.5,
                frustration=0.3,
                confusion=0.3,
                confidence_tone=0.5,
            ),
            learning_relevance=learning_relevance,
            references_problem_id=input.current_problem_id,
            abuse_flags=abuse_flags,
            routing=routing,
        )

    @staticmethod
    def _extract_user_msg(input: ClassifyInput) -> str:
        if hasattr(input, 'user_msg') and getattr(input, 'user_msg'):
            return str(getattr(input, 'user_msg')).lower()

        if input.recent_messages:
            last_message = input.recent_messages[-1]
            content = getattr(last_message, 'content', '') or ''
            return str(content).lower()

        return ''

    async def execute(self, input: ClassifyInput) -> Lesson2LayerUsage:
        try:
            logger.debug(
                "classify_layer.called",
                log_type="debug",
            )

            prompt = await self._prompt_builder.lesson2_classify_prompt(**input.model_dump())

            llm_response = await self._llm_manager.generate_response(
                system_prompt=prompt,
                messages=input.recent_messages,
                response_model=ClassifyOutput,
            )

            return Lesson2LayerUsage(output=llm_response.content, usage=llm_response.usage)

        except LLMManagerStructuredOutputError as e:
            logger.warning(
                "classify_layer.structured_output_degraded",
                log_type="technical",
                error=str(e),
            )
            return Lesson2LayerUsage(output=self._safe_default_output(input), usage=[])

        except LLMManagerError as e:
            raise Lesson2LayerError("LLM Manager failed to generate classification.") from e

        except Exception as e:
            logger.error(
                "classify_layer.unexpected.failed",
                log_type="error",
                error=str(e),
                exc_info=True,
            )
            raise Lesson2LayerError("Failed to classify user message.") from e
    
        
    
    
    
    

    