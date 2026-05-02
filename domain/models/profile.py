from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from enum import Enum

class Subject(str, Enum):
    MATH = "MATH"
    IT = "IT"

# 1. Chi tiết năng lực theo từng chủ đề (Ví dụ: Toán -> Đạo hàm)
class TopicMastery(BaseModel):
    score: float = 0.0  # Từ 0.0 đến 1.0
    last_practiced: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    misconceptions: List[str] = []  # Các lỗ hổng kiến thức AI phát hiện được

# 2. DTO chính cho Student Profile
class StudentProfile(BaseModel):
    student_id: str = Field(..., alias="_id")  # Dùng Student UUID từ NestJS
    full_name: str
    grade: int

    # Cá nhân hóa để AI "biết người biết ta"
    preferences: Dict[str, Any] = {}

    # Bản đồ kiến thức (Đây là phần quan trọng nhất cho Socratic AI)
    # Ví dụ: {"math": {"derivative": TopicMastery, "integral": TopicMastery}}
    knowledge_map: Dict[str, Dict[str, TopicMastery]] = {}

    metadata: Dict[str, Any] = Field(default_factory=lambda: {"total_sessions": 0})
    last_active: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True