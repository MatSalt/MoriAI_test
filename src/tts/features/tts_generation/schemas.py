"""
TTS Generation Schemas
TTS 배치 생성 관련 Pydantic 모델
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class TTSRequest(BaseModel):
    """TTS 생성 요청 모델 - texts만 필수, 나머지는 환경변수 기본값 사용"""

    texts: List[List[str]] = Field(
        ...,
        description="중첩 문자열 리스트 (예: [['hello', 'world'], ['test']])",
        example=[
            [
                "North Korea fired multiple short-range ballistic missiles on Wednesday morning",
                "just days ahead of the Asia-Pacific Economic Cooperation summit in Gyeongju",
            ],
            [
                "It marks the North's first ballistic missile provocation in five months. Kim In-kyung has this report."
            ],
        ],
    )
    voice_id: Optional[str] = Field(
        default=None,
        description="ElevenLabs 음성 ID (선택 사항, 미입력시 환경변수 기본값 사용)",
        example="TxWD6rImY3v4izkm2VL0",
    )
    model_id: Optional[str] = Field(
        default=None,
        description="TTS 모델 ID (선택 사항)",
        example="eleven_v3",
    )
    language: Optional[str] = Field(
        default="en", description="언어 코드 (ISO 639-1, 선택 사항)", example="en"
    )
    stability: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="안정성 (0.0-1.0, 선택 사항)"
    )
    similarity_boost: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="유사도 부스트 (0.0-1.0, 선택 사항)"
    )
    style: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="스타일 강조 (0.0-1.0, 선택 사항)"
    )

    @field_validator("texts")
    @classmethod
    def validate_texts(cls, v: List[List[str]]) -> List[List[str]]:
        """텍스트 유효성 검사"""
        if not v:
            raise ValueError("texts는 비어있을 수 없습니다.")

        # 모든 그룹이 비어있지 않은지 확인
        for group in v:
            if not group:
                raise ValueError("빈 그룹이 포함되어 있습니다.")

            # 각 텍스트가 문자열인지 확인
            for text in group:
                if not isinstance(text, str) or not text.strip():
                    raise ValueError("빈 문자열이 포함되어 있습니다.")

        return v


class TTSResponse(BaseModel):
    """TTS 생성 응답 모델"""

    success: bool = Field(..., description="성공 여부")
    batch_id: str = Field(..., description="배치 요청 UUID")
    paths: List[List[Optional[str]]] = Field(
        ...,
        description="생성된 MP3 파일 경로 (중첩 리스트)",
        example=[
            [
                "/data/sound/batch-uuid/uuid1.mp3",
                "/data/sound/batch-uuid/uuid2.mp3",
            ],
            ["/data/sound/batch-uuid/uuid3.mp3"],
        ],
    )
    total_count: int = Field(..., description="총 생성된 파일 수")
    success_count: int = Field(..., description="성공한 파일 수")
    failed_count: int = Field(..., description="실패한 파일 수")
    duration_ms: int = Field(..., description="처리 시간 (밀리초)")


class StatsResponse(BaseModel):
    """통계 정보 응답 모델"""

    output_dir: str
    max_concurrent_requests: int
    output_dir_exists: bool
    file_count: int
