from enum import Enum


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class BloomLevel(str, Enum):
    REMEMBER = "remember"
    UNDERSTAND = "understand"
    APPLY = "apply"
    ANALYZE = "analyze"
    EVALUATE = "evaluate"
    CREATE = "create"


class CognitiveOperation(str, Enum):
    """Loại hình tư duy cần áp dụng"""
    RECALL = "recall"
    APPLY = "apply"
    ANALYZE = "analyze"
    TRANSFER = "transfer"
    CONSTRUCT = "construct"


class Representation(str, Enum):
    """Cách thức biểu diễn kiến thức"""
    SYMBOLIC = "symbolic"
    VIRTUAL = "virtual"
    VERBAL = "verbal"
    NUMERIC = "numeric"
    PROCEDURAL = "procedural"


class Constraint(str, Enum):
    """Ràng buộc làm thay đổi cách tiếp cận"""
    DOMAIN = "domain"
    TOOL = "tool"
    PERSPECTIVE = "perspective"
    COMPOSITION = "composition"
    NONE = "none"


class ConceptType(Enum):
    DEFINITION      = "definition"
    FORMULA         = "formula"
    METHOD          = "method"
    PROPERTY        = "property"
    APPLICATION     = "application"
    COMMON_MISTAKE  = "common_mistake"
    VISUALIZATION   = "visualization"


class ApproachStrength(Enum):
    OPTIMAL_COMPLEXITY  = "optimal_complexity"
    EASY_TO_IMPLEMENT   = "easy_to_implement"
    GENERALIZABLE       = "generalizable"
    EXACT_RESULT        = "exact_result"
    HANDLES_EDGE_CASES  = "handles_edge_cases"


class ApproachWeakness(Enum):
    HIGH_TIME_COMPLEXITY    = "high_time_complexity"
    HIGH_SPACE_COMPLEXITY   = "high_space_complexity"
    HARD_TO_IMPLEMENT       = "hard_to_implement"
    CASE_SPECIFIC           = "case_specific"
    APPROXIMATION_ONLY      = "approximation_only"


class StudentStrength(Enum):
    GOOD_LOGIC       = "good_logic"
    CAREFUL          = "careful"
    CREATIVE         = "creative"
    FAST_EXECUTION   = "fast_execution"


class StudentWeakness(Enum):
    CARELESS         = "careless"
    STUCK_EASY       = "stuck_easy"
    OVER_THINKING    = "over_thinking"
    SLOW_PACE        = "slow_pace"


class ProblemRole(str, Enum):
    """Vai trò của bài tập trong quá trình học tập"""
    REINFORCEMENT = "reinforcement"
    CHALLENGE     = "challenge"
    EXPLORATION   = "exploration"
    EXTENSION     = "extension"


class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
