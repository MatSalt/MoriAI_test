"""
Storybook Data Models
Pydantic 모델을 사용한 동화책 데이터 구조 정의
"""

from datetime import datetime
from typing import List, Literal
from uuid import uuid4
from pydantic import BaseModel, Field


class Dialogue(BaseModel):
    """
    페이지 내 대사 모델

    Attributes:
        id: 대사 고유 ID (UUID)
        index: 대사 순서 (1부터 시작)
        text: 대사 텍스트
        part_audio_url: 대사 오디오 파일 URL
    """

    id: str = Field(default_factory=lambda: str(uuid4()), description="대사 고유 ID")
    index: int = Field(..., ge=1, description="대사 순서 (1부터 시작)")
    text: str = Field(..., min_length=1, description="대사 텍스트")
    part_audio_url: str = Field(..., description="대사 오디오 파일 URL")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "uuid-dialogue-1",
                "index": 1,
                "text": "아침을 먹었다.",
                "part_audio_url": "/data/sound/batch-uuid/uuid-dialogue-1.mp3",
            }
        }


class Page(BaseModel):
    """
    동화책 페이지 모델

    Attributes:
        id: 페이지 고유 ID (UUID)
        index: 페이지 순서 (1부터 시작)
        type: 페이지 컨텐츠 타입 ('image' 또는 'video')
        content: 페이지 컨텐츠 URL (이미지 또는 비디오)
        dialogues: 페이지에 포함된 대사 리스트
        fallback_image: 비디오 타입일 때 로딩 실패 시 대체 이미지 URL (비디오 타입에만 필수)
    """

    id: str = Field(default_factory=lambda: str(uuid4()), description="페이지 고유 ID")
    index: int = Field(..., ge=1, description="페이지 순서 (1부터 시작)")
    type: Literal["image", "video"] = Field(..., description="페이지 컨텐츠 타입")
    content: str = Field(..., description="페이지 컨텐츠 URL")
    dialogues: List[Dialogue] = Field(default_factory=list, description="대사 리스트")
    fallback_image: str = Field(default="", description="비디오 실패 시 대체 이미지 URL")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "uuid-page-1",
                "index": 1,
                "type": "video",
                "content": "/data/video/book-uuid/uuid-page-1.mp4",
                "fallback_image": "/data/image/book-uuid/uuid-page-1.png",
                "dialogues": [
                    {
                        "id": "uuid-dialogue-1",
                        "index": 1,
                        "text": "아침을 먹었다.",
                        "part_audio_url": "/data/sound/batch-uuid/uuid-dialogue-1.mp3",
                    }
                ],
            }
        }


class Book(BaseModel):
    """
    동화책 모델

    Attributes:
        id: 동화책 고유 ID (UUID)
        title: 동화책 제목
        cover_image: 동화책 커버 이미지 URL
        status: 동화책 상태 (process, success, error)
        pages: 동화책 페이지 리스트
        created_at: 생성 시간
    """

    id: str = Field(default_factory=lambda: str(uuid4()), description="동화책 고유 ID")
    title: str = Field(..., description="동화책 제목")
    cover_image: str = Field(..., description="동화책 커버 이미지 URL")
    status: Literal["process", "success", "error"] = Field(
        default="process", description="동화책 상태"
    )
    pages: List[Page] = Field(default_factory=list, description="동화책 페이지 리스트")
    created_at: datetime = Field(default_factory=datetime.now, description="생성 시간")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "uuid-book-1234",
                "title": "우리집 동화책",
                "cover_image": "/data/image/uuid-book-1234/cover.png",
                "status": "success",
                "pages": [
                    {
                        "id": "uuid-page-1",
                        "index": 1,
                        "type": "video",
                        "content": "/data/video/uuid-book-1234/uuid-page-1.mp4",
                        "fallback_image": "/data/image/uuid-book-1234/uuid-page-1.png",
                        "dialogues": [
                            {
                                "id": "uuid-dialogue-1",
                                "index": 1,
                                "text": "아침을 먹었다.",
                                "part_audio_url": "/data/sound/batch-uuid/uuid-dialogue-1.mp3",
                            }
                        ],
                    }
                ],
                "created_at": "2025-10-21T12:00:00",
            }
        }
