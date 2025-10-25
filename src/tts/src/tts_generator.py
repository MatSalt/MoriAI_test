"""
TTS Generator with ElevenLabs API
비동기 배치 처리 및 중첩 리스트 구조 보존
"""

import os
import uuid
import base64
import asyncio
import logging
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv
from elevenlabs import ElevenLabs


# 환경 변수 로드
load_dotenv()

# 로거 설정
logger = logging.getLogger(__name__)


class TtsGenerator:
    """ElevenLabs TTS 비동기 생성기 (싱글톤)"""

    _instance: Optional["TtsGenerator"] = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """TTS Generator 초기화"""
        # 중복 초기화 방지
        if hasattr(self, "_initialized"):
            return

        # ElevenLabs API 키 로드
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            raise ValueError(
                "ELEVENLABS_API_KEY가 설정되지 않았습니다. " ".env 파일을 확인하세요."
            )

        # ElevenLabs 클라이언트 초기화
        self.client = ElevenLabs(api_key=api_key)

        # 설정 로드
        self.output_dir = Path(os.getenv("TTS_OUTPUT_DIR", "/app/data/sound"))
        self.max_concurrent = int(os.getenv("TTS_MAX_CONCURRENT_REQUESTS", "5"))

        # 출력 디렉토리 생성
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 세마포어 (동시 요청 제한)
        self.semaphore = asyncio.Semaphore(self.max_concurrent)

        self._initialized = True
        logger.info(
            f"TtsGenerator 초기화 완료 - "
            f"출력 경로: {self.output_dir}, "
            f"최대 동시 요청: {self.max_concurrent}"
        )

    async def generate_batch(
        self,
        texts: List[List[str]],
        voice_id: str = "TxWD6rImY3v4izkm2VL0",
        model_id: str = "eleven_v3",
        language: str = "en",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
    ) -> dict:
        """
        중첩 리스트 배치 TTS 생성

        Args:
            texts: 중첩 문자열 리스트 (예: [["hello", "this"], ["is"], ["me", "too"]])
            voice_id: ElevenLabs 음성 ID
            model_id: TTS 모델 ID
            language: 언어 코드 (ISO 639-1)
            stability: 안정성 (0.0-1.0)
            similarity_boost: 유사도 부스트 (0.0-1.0)
            style: 스타일 강조 (0.0-1.0)

        Returns:
            dict: {"batch_id": str, "paths": List[List[str]]}
        """
        # 배치 요청 UUID 생성 및 폴더 생성
        batch_uuid = str(uuid.uuid4())
        batch_dir = self.output_dir / batch_uuid
        batch_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"배치 TTS 생성 시작 - "
            f"batch_id: {batch_uuid}, "
            f"voice_id: {voice_id}, "
            f"model: {model_id}"
        )

        # 1. 평탄화: 중첩 리스트를 1차원으로 변환하면서 구조 정보 저장
        flat_texts = []
        structure = []  # 각 그룹의 길이 저장

        for group in texts:
            structure.append(len(group))
            flat_texts.extend(group)

        logger.info(f"총 {len(flat_texts)}개 텍스트 처리 시작 (구조: {structure})")

        # 2. 모든 텍스트를 병렬로 처리
        tasks = [
            self._generate_single(
                text=text,
                batch_dir=batch_dir,
                voice_id=voice_id,
                model_id=model_id,
                language=language,
                stability=stability,
                similarity_boost=similarity_boost,
                style=style,
            )
            for text in flat_texts
        ]

        # 병렬 실행 (일부 실패 허용)
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 3. 에러 처리 및 경로 추출
        flat_paths = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"텍스트 '{flat_texts[idx]}' 처리 실패: {result}")
                flat_paths.append(None)  # 실패 시 None
            else:
                flat_paths.append(result)

        # 4. 재구조화: 원래 중첩 구조로 복원
        nested_paths = []
        start_idx = 0

        for group_size in structure:
            group_paths = flat_paths[start_idx : start_idx + group_size]
            nested_paths.append(group_paths)
            start_idx += group_size

        # 성공/실패 통계
        success_count = sum(1 for p in flat_paths if p is not None)
        logger.info(
            f"배치 TTS 생성 완료 - "
            f"batch_id: {batch_uuid}, "
            f"성공: {success_count}/{len(flat_paths)}"
        )

        return {"batch_id": batch_uuid, "paths": nested_paths}

    async def _generate_single(
        self,
        text: str,
        batch_dir: Path,
        voice_id: str = "TxWD6rImY3v4izkm2VL0",
        model_id: str = "eleven_v3",
        language: str = "en",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
    ) -> str:
        """
        단일 텍스트 TTS 생성

        Args:
            text: 변환할 텍스트
            voice_id: ElevenLabs 음성 ID
            model_id: TTS 모델 ID
            language: 언어 코드
            stability: 안정성
            similarity_boost: 유사도 부스트
            style: 스타일 강조

        Returns:
            생성된 MP3 파일 경로 (예: "/data/sound/uuid.mp3")

        Raises:
            Exception: TTS 생성 실패 시
        """
        # 세마포어로 동시 요청 수 제한
        async with self.semaphore:
            try:
                logger.debug(f"TTS 생성 시작: '{text[:30]}...'")

                # 음성 설정
                voice_settings = {
                    "stability": stability,
                    "similarity_boost": similarity_boost,
                    "style": style,
                }

                # ElevenLabs API 호출 (동기 함수를 비동기 실행)
                loop = asyncio.get_event_loop()
                audio_generator = await loop.run_in_executor(
                    None,
                    lambda: self.client.text_to_speech.convert_with_timestamps(
                        text=text,
                        voice_id=voice_id,
                        model_id=model_id,
                        voice_settings=voice_settings,
                        language_code=language,
                    ),
                )

                # Base64 디코딩
                audio_data = audio_generator.audio_base_64
                if not audio_data:
                    raise ValueError("오디오 데이터가 비어있습니다.")

                decoded_audio = base64.b64decode(audio_data)

                # UUID 생성 및 파일 경로 (배치 폴더 내)
                file_uuid = str(uuid.uuid4())
                file_path = batch_dir / f"{file_uuid}.mp3"

                # 파일 저장 (비동기)
                await self._save_audio_file(file_path, decoded_audio)

                logger.debug(f"TTS 생성 완료: {file_path}")

                # 컨테이너 내 절대 경로 반환 (/app 제거)
                return str(file_path).removeprefix("/app")

            except Exception as e:
                logger.error(f"TTS 생성 실패 ('{text[:30]}...'): {e}")
                raise

    async def _save_audio_file(self, file_path: Path, audio_data: bytes) -> None:
        """
        오디오 파일 비동기 저장

        Args:
            file_path: 저장할 파일 경로
            audio_data: 오디오 바이트 데이터
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: file_path.write_bytes(audio_data))

    async def generate_word(
        self,
        word: str,
        voice_id: Optional[str] = "TxWD6rImY3v4izkm2VL0",
        model_id: Optional[str] = "eleven_v3",
        language: Optional[str] = "en",
        stability: Optional[float] = 0.5,
        similarity_boost: Optional[float] = 0.75,
        style: Optional[float] = 0.0,
    ) -> str:
        """
        단어 단위 TTS 생성 (캐싱 지원)

        파일이 이미 존재하면 기존 파일 경로를 반환하고,
        없으면 새로 생성합니다.

        Args:
            word: 변환할 단어
            voice_id: ElevenLabs 음성 ID (Optional, 환경변수 기본값 사용)
            model_id: TTS 모델 ID (Optional, 환경변수 기본값 사용)
            language: 언어 코드 (Optional, 환경변수 기본값 사용)
            stability: 안정성 (Optional, 환경변수 기본값 사용)
            similarity_boost: 유사도 부스트 (Optional, 환경변수 기본값 사용)
            style: 스타일 강조 (Optional, 환경변수 기본값 사용)

        Returns:
            생성된 또는 캐시된 MP3 파일 경로 (예: "/data/sound/word/cat.mp3")

        Raises:
            Exception: TTS 생성 실패 시
        """
        # word 디렉토리 생성
        word_dir = self.output_dir / "word"
        word_dir.mkdir(parents=True, exist_ok=True)

        # 파일 경로 설정
        file_path = word_dir / f"{word}.mp3"

        # 캐시된 파일이 있으면 재사용
        if file_path.exists():
            logger.info(f"캐시된 파일 재사용: {word}.mp3")
            return str(file_path).removeprefix("/app")

        # 환경변수 기본값 처리
        voice_id = voice_id or os.getenv("TTS_DEFAULT_VOICE_ID", "TxWD6rImY3v4izkm2VL0")
        model_id = model_id or os.getenv("TTS_DEFAULT_MODEL_ID", "eleven_v3")
        language = language or os.getenv("TTS_DEFAULT_LANGUAGE", "en")
        stability = (
            stability
            if stability is not None
            else float(os.getenv("TTS_DEFAULT_STABILITY", "0.5"))
        )
        similarity_boost = (
            similarity_boost
            if similarity_boost is not None
            else float(os.getenv("TTS_DEFAULT_SIMILARITY_BOOST", "0.75"))
        )
        style = (
            style if style is not None else float(os.getenv("TTS_DEFAULT_STYLE", "0.0"))
        )

        logger.info(f"새 단어 TTS 생성: {word} (voice: {voice_id}, model: {model_id})")

        try:
            # 음성 설정
            voice_settings = {
                "stability": stability,
                "similarity_boost": similarity_boost,
                "style": style,
            }

            # ElevenLabs API 호출
            loop = asyncio.get_event_loop()
            audio_generator = await loop.run_in_executor(
                None,
                lambda: self.client.text_to_speech.convert_with_timestamps(
                    text=word,
                    voice_id=voice_id,
                    model_id=model_id,
                    voice_settings=voice_settings,
                    language_code=language,
                ),
            )

            # Base64 디코딩
            audio_data = audio_generator.audio_base_64
            if not audio_data:
                raise ValueError("오디오 데이터가 비어있습니다.")

            decoded_audio = base64.b64decode(audio_data)

            # 파일 저장
            await self._save_audio_file(file_path, decoded_audio)

            logger.info(f"단어 TTS 생성 완료: {file_path}")
            return str(file_path).removeprefix("/app")

        except Exception as e:
            logger.error(f"단어 TTS 생성 실패 ('{word}'): {e}")
            raise

    def get_stats(self) -> dict:
        """
        TTS Generator 통계 정보 반환

        Returns:
            dict: 설정 및 통계 정보
        """
        return {
            "output_dir": str(self.output_dir),
            "max_concurrent_requests": self.max_concurrent,
            "output_dir_exists": self.output_dir.exists(),
            "file_count": (
                len(list(self.output_dir.glob("*.mp3")))
                if self.output_dir.exists()
                else 0
            ),
        }

    async def get_clone_voice_list(self):
        """
        클론 보이스 목록 조회

        Returns:
            List[dict]: 보이스 목록 [{"voice_label": str, "voice_id": str}, ...]
        """
        # ElevenLabs API 호출 (동기 함수를 비동기로 실행)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.voices.get_all(show_legacy=False)
        )

        voices = []
        for x in response.voices:
            if x.category in "cloned":
                voices.append(
                    {
                        "voice_label": x.name,
                        "voice_id": x.voice_id,
                        'description': x.description or '',
                        'category': x.category if hasattr(x, 'category') else 'unknown',
                        'preview_url': x.preview_url if hasattr(x, 'preview_url') else None,
                        'labels': x.labels if hasattr(x, 'labels') and x.labels else {},
                    }
                )
        return voices
