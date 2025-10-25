"""
Voice Management Service
보이스 관리 비즈니스 로직
"""

from typing import List
from src.tts_generator import TtsGenerator
from core.logging import get_logger

logger = get_logger(__name__)


class VoiceService:
    """보이스 관리 서비스"""

    def __init__(self, tts_generator: TtsGenerator):
        self.tts_generator = tts_generator

    async def get_clone_voice_list(self) -> List[dict]:
        """클론 보이스 목록 조회"""
        try:
            voices = await self.tts_generator.get_clone_voice_list()
            logger.info(f"클론 보이스 {len(voices)}개 조회 성공")
            return voices
        except Exception as e:
            logger.error(f"클론 보이스 조회 실패: {e}")
            raise
