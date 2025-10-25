"""
TTS Generation Service
TTS 배치 생성 비즈니스 로직
"""

import os
import time
from typing import Dict, Any
from src.tts_generator import TtsGenerator
from core.config import settings
from core.logging import get_logger
from features.tts_generation.schemas import TTSRequest

logger = get_logger(__name__)


class TTSGenerationService:
    """TTS 배치 생성 서비스"""

    def __init__(self, tts_generator: TtsGenerator):
        self.tts_generator = tts_generator

    async def generate_batch(self, request: TTSRequest) -> Dict[str, Any]:
        """
        TTS 배치 생성

        Args:
            request: TTS 생성 요청

        Returns:
            생성 결과 (batch_id, paths, 통계)

        Raises:
            ValueError: voice_id가 없을 때
            Exception: TTS 생성 실패 시
        """
        start_time = time.time()

        # voice_id 환경변수에서 가져오기 (필수)
        voice_id = request.voice_id or settings.tts_default_voice_id
        if not voice_id:
            raise ValueError(
                "voice_id가 제공되지 않았고, TTS_DEFAULT_VOICE_ID 환경변수도 설정되지 않았습니다."
            )

        logger.info(
            f"TTS 생성 요청 수신 - "
            f"voice_id: {voice_id}, "
            f"texts: {sum(len(g) for g in request.texts)}개"
        )

        # TTS 생성 파라미터 구성
        params = {"texts": request.texts, "voice_id": voice_id}

        # None이 아닌 값만 추가
        if request.model_id is not None:
            params["model_id"] = request.model_id
        if request.language is not None:
            params["language"] = request.language
        if request.stability is not None:
            params["stability"] = request.stability
        if request.similarity_boost is not None:
            params["similarity_boost"] = request.similarity_boost
        if request.style is not None:
            params["style"] = request.style

        # TTS 생성
        result = await self.tts_generator.generate_batch(**params)

        # 통계 계산
        batch_id = result["batch_id"]
        paths = result["paths"]
        flat_paths = [p for group in paths for p in group]
        total_count = len(flat_paths)
        success_count = sum(1 for p in flat_paths if p is not None)
        failed_count = total_count - success_count
        duration_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"TTS 생성 완료 - "
            f"batch_id: {batch_id}, "
            f"성공: {success_count}/{total_count}, "
            f"처리 시간: {duration_ms}ms"
        )

        return {
            "batch_id": batch_id,
            "paths": paths,
            "total_count": total_count,
            "success_count": success_count,
            "failed_count": failed_count,
            "duration_ms": duration_ms,
        }

    def get_stats(self) -> Dict[str, Any]:
        """통계 정보 조회"""
        return self.tts_generator.get_stats()
