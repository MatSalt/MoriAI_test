"""
Shared Dependencies Module
의존성 주입 및 공통 의존성
"""

from functools import lru_cache
from src.tts_generator import TtsGenerator


@lru_cache()
def get_tts_generator() -> TtsGenerator:
    """TTS Generator 싱글톤 인스턴스 반환"""
    return TtsGenerator()
