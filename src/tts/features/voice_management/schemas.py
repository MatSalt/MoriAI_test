"""
Voice Management Schemas
보이스 관리 관련 Pydantic 모델
"""

from typing import List
from pydantic import BaseModel, Field


class Voice(BaseModel):
    """개별 보이스 모델"""

    voice_label: str
    voice_id: str
    description: str
    category: str
    preview_url: str
    labels: dict


class VoiceIdResponseList(BaseModel):
    """보이스 리스트 응답 모델"""

    voices: List[Voice] = Field(..., description="생성된 클론 보이스 목록")
