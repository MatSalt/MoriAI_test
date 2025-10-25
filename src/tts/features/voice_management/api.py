"""
Voice Management API
보이스 관리 엔드포인트
"""

from fastapi import APIRouter, HTTPException, Depends
from features.voice_management.schemas import VoiceIdResponseList
from features.voice_management.service import VoiceService
from shared.dependencies import get_tts_generator
from src.tts_generator import TtsGenerator
from core.registry import RouterRegistry

router = APIRouter(prefix="/tts/voices", tags=["Voice Management"])

# Router 자동 등록
RouterRegistry.register(
    router,
    priority=30,  # 일반 기능
    tags=["tts", "voice", "management"],
    name="voice_management",
)


def get_voice_service(
    tts_generator: TtsGenerator = Depends(get_tts_generator),
) -> VoiceService:
    """VoiceService 의존성 주입"""
    return VoiceService(tts_generator)


@router.get("", response_model=VoiceIdResponseList)
async def get_voices(service: VoiceService = Depends(get_voice_service)):
    """생성된 클론 보이스 목록 반환"""
    try:
        voices = await service.get_clone_voice_list()
        return VoiceIdResponseList(voices=voices)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Voice List 반환 오류가 발생했습니다: {str(e)}"
        )
