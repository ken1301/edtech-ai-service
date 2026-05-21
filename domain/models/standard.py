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

# === Nhóm Pattern (đánh giá sự khác biệt giữa những cách tiếp cận bài tập) ===
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
    DEFINITION      = "definition"       # Khái niệm / định nghĩa
    FORMULA         = "formula"          # Công thức / định lý
    METHOD          = "method"           # Phương pháp / kỹ thuật giải
    PROPERTY        = "property"         # Tính chất
    APPLICATION     = "application"      # Ứng dụng
    COMMON_MISTAKE  = "common_mistake"   # Lỗi sai phổ biến
    VISUALIZATION   = "visualization"    # Hình vẽ / đồ thị minh họa

# === Nhóm đánh giá điểm mạnh yếu của cách tiếp cận bài tập ===
class ApproachStrength(Enum):
    OPTIMAL_COMPLEXITY  = "optimal_complexity"   # Thời gian / không gian tốt nhất có thể
    EASY_TO_IMPLEMENT   = "easy_to_implement"    # Code / trình bày ngắn, ít lỗi
    GENERALIZABLE       = "generalizable"        # Áp dụng được lớp bài rộng
    EXACT_RESULT        = "exact_result"         # Cho kết quả chính xác, không xấp xỉ
    HANDLES_EDGE_CASES  = "handles_edge_cases"   # Xử lý tốt trường hợp biên

class ApproachWeakness(Enum):
    HIGH_TIME_COMPLEXITY    = "high_time_complexity"    # Chậm khi input lớn
    HIGH_SPACE_COMPLEXITY   = "high_space_complexity"   # Tốn bộ nhớ
    HARD_TO_IMPLEMENT       = "hard_to_implement"       # Dễ bug, code phức tạp
    CASE_SPECIFIC           = "case_specific"           # Chỉ đúng với điều kiện hẹp
    APPROXIMATION_ONLY      = "approximation_only"      # Kết quả xấp xỉ, không chính xác
# ---------------------------------------------------------------------------

# Nhóm đánh giá điểm mạnh yếu của học sinh
class StudentStrength(Enum):
    GOOD_LOGIC       = "good_logic"        # Tư duy mạch lạc, hiểu đề nhanh
    CAREFUL          = "careful"           # Cẩn thận, ít làm sai sót vặt
    CREATIVE         = "creative"          # Hay tìm ra cách giải độc đáo
    FAST_EXECUTION   = "fast_execution"    # Trình bày hoặc gõ code rất nhanh

class StudentWeakness(Enum):
    CARELESS         = "careless"          # Hay ẩu, sót trường hợp dễ/biên
    STUCK_EASY       = "stuck_easy"        # Chỉ nghĩ được cách đơn giản, sợ bài khó
    OVER_THINKING    = "over_thinking"     # Hay nghĩ phức tạp hóa vấn đề đơn giản
    SLOW_PACE        = "slow_pace"         # Làm bài chậm, tốn nhiều thời gian
# ---------------------------------------------------------------------------

class ProblemRole(str, Enum):
    """Vai trò của bài tập trong quá trình học tập"""
    REINFORCEMENT = "reinforcement"   # Củng cố kiến thức đã học (pattern cũ)
    CHALLENGE     = "challenge"       # Thử thách với bài tập khó hơn (pattern cũ)
    EXPLORATION   = "exploration"     # Khám phá kiến thức mới (pattern mới vì pattern cũ không còn phù hợp)
    EXTENSION     = "extension"       # Review lại kiến thức mới (pattern mới)

class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"