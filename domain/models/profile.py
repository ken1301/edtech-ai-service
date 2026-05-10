from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from enum import Enum

class Subject(str, Enum):
    MATH = "math"
    IT = "it"

# 1. Chi tiết năng lực theo từng chủ đề (Ví dụ: Toán -> Đạo hàm)
class TopicMastery(BaseModel):
    score: float = 0.0  # Từ 0.0 đến 1.0
    last_practiced: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    misconceptions: List[str] = []  # Các lỗ hổng kiến thức AI phát hiện được
    summary: str  # Tóm tắt ngắn gọn về năng lực của học sinh trong chủ đề này

class StudentPreference(BaseModel):
    strengths: List[str] = []  # Điểm mạnh của học sinh
    weaknesses: List[str] = []  # Điểm yếu của học sinh
    learning_style: Optional[str] = None  # Ví dụ: "visual", "auditory", "kinesthetic"
    preferred_difficulty: Optional[str] = None  # Ví dụ: "easy", "medium", "hard"
    other_preferences: Dict[str, Any] = Field(default_factory=dict)  # Các sở thích khác (ví dụ: thời gian học, loại bài tập yêu thích, v.v.)

class SessionSummary(BaseModel):
    student_preference: StudentPreference
    topic_mastery: TopicMastery

# 2. DTO chính cho Student Profile
class StudentProfile(BaseModel):
    student_id: str = Field(..., alias="_id")  # Dùng Student UUID từ NestJS
    full_name: str
    grade: int

    # Cá nhân hóa để AI "biết người biết ta" (điểm mạnh, điểm yếu tổng thế, sở thích học tập, v.v.)
    preferences: StudentPreference = Field(default_factory=StudentPreference)

    # Bản đồ kiến thức 
    # Ví dụ: {"math": {"derivative": TopicMastery, "integral": TopicMastery}}
    knowledge_map: Dict[str, Dict[str, TopicMastery]] = {}

    metadata: Dict[str, Any] = Field(default_factory=lambda: {"total_sessions": 0})
    last_active: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True