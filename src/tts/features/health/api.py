"""
Health Check Feature
헬스체크 및 서비스 상태 확인 엔드포인트
"""

from fastapi import APIRouter
from core.registry import RouterRegistry

router = APIRouter(tags=["Health"])

# Router 자동 등록
RouterRegistry.register(
    router,
    priority=100,  # 헬스체크는 최우선 로딩
    tags=["health", "system"],
    name="health",
)


@router.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "ok", "service": "MoriAI TTS Service"}


@router.get("/")
async def read_root():
    """루트 엔드포인트"""
    return {"service": "MoriAI TTS Service", "version": "1.0.0", "status": "running"}
