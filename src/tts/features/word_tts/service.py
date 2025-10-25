"""
Word TTS Service
단어 TTS 생성 비즈니스 로직
"""

import time
from pathlib import Path
from typing import Dict, Any
from src.tts_generator import TtsGenerator
from core.logging import get_logger

logger = get_logger(__name__)


class WordTTSService:
    """단어 TTS 생성 서비스"""

    def __init__(self, tts_generator: TtsGenerator):
        self.tts_generator = tts_generator
        self.word_dir = Path("/app/data/sound/word")

    def validate_word(self, word: str) -> None:
        """
        단어 유효성 검증

        Args:
            word: 검증할 단어

        Raises:
            ValueError: 유효하지 않은 단어
        """
        # 단어 길이 검증 (최대 50자)
        if len(word) > 50:
            raise ValueError("단어 길이는 50자를 초과할 수 없습니다.")

        # 빈 문자열 검증
        if not word.strip():
            raise ValueError("단어는 비어있을 수 없습니다.")

        # 특수문자 검증 (경로 조작 문자 차단)
        if any(char in word for char in [".", "/", "\\", ".."]):
            raise ValueError("단어에 경로 조작 문자(., /, \\)를 포함할 수 없습니다.")

    def is_cached(self, word: str) -> bool:
        """캐시된 파일 존재 여부 확인"""
        file_path = self.word_dir / f"{word}.mp3"
        return file_path.exists()

    async def generate_word(self, word: str) -> Dict[str, Any]:
        """
        단어 TTS 생성 (캐싱 지원)

        Args:
            word: 변환할 단어

        Returns:
            생성 결과 (word, file_path, cached, duration_ms)

        Raises:
            ValueError: 유효하지 않은 단어
            Exception: TTS 생성 실패 시
        """
        # 유효성 검증
        self.validate_word(word)

        # 캐시 여부 확인
        is_cached = self.is_cached(word)

        start_time = time.time()

        logger.info(f"단어 TTS 요청: '{word}' (캐시됨: {is_cached})")

        # TTS 생성 또는 캐시된 파일 경로 반환
        result_path = await self.tts_generator.generate_word(word)

        # 처리 시간 계산 (캐시된 경우 None)
        duration_ms = None if is_cached else int((time.time() - start_time) * 1000)

        logger.info(
            f"단어 TTS 완료: '{word}' - "
            f"캐시: {is_cached}, "
            f"경로: {result_path}, "
            f"처리 시간: {duration_ms}ms"
        )

        return {
            "word": word,
            "file_path": result_path,
            "cached": is_cached,
            "duration_ms": duration_ms,
        }
