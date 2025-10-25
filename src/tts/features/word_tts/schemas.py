"""
Word TTS Schemas
단어 TTS 생성 관련 Pydantic 모델
"""

from typing import Optional
from pydantic import BaseModel, Field


class WordTTSResponse(BaseModel):
    """단어 TTS 응답 모델"""

    success: bool = Field(..., description="성공 여부")
    word: str = Field(..., description="변환된 단어")
    file_path: str = Field(
        ..., description="생성된 MP3 파일 경로", example="/data/sound/word/cat.mp3"
    )
    cached: bool = Field(
        ..., description="기존 파일 재사용 여부 (True: 캐시됨, False: 새로 생성)"
    )
    duration_ms: Optional[int] = Field(
        default=None, description="처리 시간 (밀리초, 캐시된 경우 None)"
    )
