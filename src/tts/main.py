"""
FastAPI TTS Service - Feature-First Architecture
ElevenLabs 기반 비동기 TTS 생성 API
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from core.config import settings
from core.logging import setup_logging, get_logger
from core.middleware import setup_middleware
from core.registry import RouterRegistry
from shared.dependencies import get_tts_generator

# Feature 라우터 자동 등록을 위한 import (Registry에 등록됨)
import features.health.api  # noqa: F401
import features.tts_generation.api  # noqa: F401
import features.word_tts.api  # noqa: F401
import features.voice_management.api  # noqa: F401

# 로깅 설정
setup_logging()
logger = get_logger(__name__)


# === Lifespan Event Handler ===


@asynccontextmanager
async def lifespan(_: FastAPI):
    """애플리케이션 생명주기 관리"""
    # Startup
    logger.info("=" * 50)
    logger.info(f"{settings.app_title} Starting...")
    logger.info(f"Version: {settings.app_version}")

    # TTS Generator 초기화 확인
    tts_generator = get_tts_generator()
    logger.info(f"TTS Generator Stats: {tts_generator.get_stats()}")

    logger.info("=" * 50)

    yield

    # Shutdown
    logger.info(f"{settings.app_title} Shutting Down...")


# FastAPI 앱 생성
def create_app() -> FastAPI:
    """FastAPI 애플리케이션 팩토리"""
    app = FastAPI(
        title=settings.app_title,
        description=settings.app_description,
        version=settings.app_version,
        lifespan=lifespan,
    )

    # 미들웨어 설정
    setup_middleware(app)

    # Router 자동 로딩 (Registry Pattern)
    loaded_count = RouterRegistry.load_all(app)
    logger.info(f"🚀 Loaded {loaded_count} routers from registry")

    return app


# 앱 인스턴스 생성
app = create_app()
