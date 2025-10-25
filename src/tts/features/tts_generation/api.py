"""
TTS Generation API
TTS 배치 생성 엔드포인트
"""

from fastapi import APIRouter, HTTPException, Depends
from features.tts_generation.schemas import (
    TTSRequest,
    TTSResponse,
    StatsResponse,
)
from features.tts_generation.service import TTSGenerationService
from shared.dependencies import get_tts_generator
from src.tts_generator import TtsGenerator
from core.registry import RouterRegistry

router = APIRouter(prefix="/tts", tags=["TTS Generation"])

# Router 자동 등록
RouterRegistry.register(
    router,
    priority=50,  # 일반 기능
    tags=["tts", "generation", "core"],
    name="tts_generation",
)


def get_tts_service(
    tts_generator: TtsGenerator = Depends(get_tts_generator),
) -> TTSGenerationService:
    """TTSGenerationService 의존성 주입"""
    return TTSGenerationService(tts_generator)


@router.post("/generate", response_model=TTSResponse)
async def generate_tts(
    request: TTSRequest,
    service: TTSGenerationService = Depends(get_tts_service),
):
    """
    TTS 배치 생성 엔드포인트

    중첩 리스트 구조를 유지하면서 각 텍스트를 TTS로 변환합니다.

    Args:
        request: TTS 생성 요청
        service: TTS 생성 서비스 (DI)

    Returns:
        TTSResponse: 생성된 파일 경로 및 통계

    Raises:
        HTTPException: TTS 생성 실패 시 400/500 에러
    """
    try:
        result = await service.generate_batch(request)
        return TTSResponse(success=True, **result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"TTS 생성 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/stats", response_model=StatsResponse)
async def get_stats(service: TTSGenerationService = Depends(get_tts_service)):
    """
    TTS Generator 통계 정보 조회

    Returns:
        StatsResponse: 현재 설정 및 통계 정보
    """
    try:
        stats = service.get_stats()
        return StatsResponse(**stats)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"통계 조회 중 오류가 발생했습니다: {str(e)}"
        )
