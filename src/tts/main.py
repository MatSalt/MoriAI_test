"""
FastAPI TTS Service
ElevenLabs 기반 비동기 TTS 생성 API
"""

import os
import logging
import time
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv
from src.tts_generator import TtsGenerator
from fastapi.middleware.cors import CORSMiddleware
# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="MoriAI TTS Service",
    description="ElevenLabs 기반 비동기 TTS 생성 API",
    version="1.0.0",
)
# 허용할 출처 목록
origins = [
    "http://localhost:5173", # 프론트엔드 개발 서버 주소
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# TTS Generator 싱글톤 인스턴스
tts_generator = TtsGenerator()


# === Pydantic Models ===


class TTSRequest(BaseModel):
    """TTS 생성 요청 모델 - texts만 필수, 나머지는 환경변수 기본값 사용"""

    texts: List[List[str]] = Field(
        ...,
        description="중첩 문자열 리스트 (예: [['hello', 'world'], ['test']])",
        example=[["North Korea fired multiple short-range ballistic missiles on Wednesday morning", "just days ahead of the Asia-Pacific Economic Cooperation summit in Gyeongju"], ["It marks the North’s first ballistic missile provocation in five months. Kim In-kyung has this report."]],
    )
    voice_id: Optional[str] = Field(
        default=None,
        description="ElevenLabs 음성 ID (선택 사항, 미입력시 환경변수 기본값 사용)",
        example="TxWD6rImY3v4izkm2VL0",
    )
    model_id: Optional[str] = Field(
        default=None,
        description="TTS 모델 ID (선택 사항)",
        example="eleven_v3",
    )
    language: Optional[str] = Field(
        default="en", description="언어 코드 (ISO 639-1, 선택 사항)", example="en"
    )
    stability: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="안정성 (0.0-1.0, 선택 사항)"
    )
    similarity_boost: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="유사도 부스트 (0.0-1.0, 선택 사항)"
    )
    style: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="스타일 강조 (0.0-1.0, 선택 사항)"
    )

    @validator("texts")
    def validate_texts(cls, v):
        """텍스트 유효성 검사"""
        if not v:
            raise ValueError("texts는 비어있을 수 없습니다.")

        # 모든 그룹이 비어있지 않은지 확인
        for group in v:
            if not group:
                raise ValueError("빈 그룹이 포함되어 있습니다.")

            # 각 텍스트가 문자열인지 확인
            for text in group:
                if not isinstance(text, str) or not text.strip():
                    raise ValueError("빈 문자열이 포함되어 있습니다.")

        return v


class TTSResponse(BaseModel):
    """TTS 생성 응답 모델"""

    success: bool = Field(..., description="성공 여부")
    batch_id: str = Field(..., description="배치 요청 UUID")
    paths: List[List[Optional[str]]] = Field(
        ...,
        description="생성된 MP3 파일 경로 (중첩 리스트)",
        example=[
            [
                "/data/sound/batch-uuid/uuid1.mp3",
                "/data/sound/batch-uuid/uuid2.mp3",
            ],
            ["/data/sound/batch-uuid/uuid3.mp3"],
        ],
    )
    total_count: int = Field(..., description="총 생성된 파일 수")
    success_count: int = Field(..., description="성공한 파일 수")
    failed_count: int = Field(..., description="실패한 파일 수")
    duration_ms: int = Field(..., description="처리 시간 (밀리초)")


class WordTTSResponse(BaseModel):
    """단어 TTS 응답 모델"""

    success: bool = Field(..., description="성공 여부")
    word: str = Field(..., description="변환된 단어")
    file_path: str = Field(
        ..., description="생성된 MP3 파일 경로", example="/data/sound/word/cat.mp3"
    )
    cached: bool = Field(
        ..., description="기존 파일 재사용 여부 (True: 캐시됨, False: 새로 생성)"
    )
    duration_ms: Optional[int] = Field(
        default=None, description="처리 시간 (밀리초, 캐시된 경우 None)"
    )


class StatsResponse(BaseModel):
    """통계 정보 응답 모델"""

    output_dir: str
    max_concurrent_requests: int
    output_dir_exists: bool
    file_count: int


# === API Endpoints ===


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "ok", "service": "MoriAI TTS Service"}


@app.get("/")
async def read_root():
    """루트 엔드포인트"""
    return {"service": "MoriAI TTS Service", "version": "1.0.0", "status": "running"}


@app.post("/tts/generate", response_model=TTSResponse)
async def tts_generate(request: TTSRequest):
    """
    TTS 배치 생성 엔드포인트

    중첩 리스트 구조를 유지하면서 각 텍스트를 TTS로 변환합니다.

    Args:
        request: TTS 생성 요청

    Returns:
        TTSResponse: 생성된 파일 경로 및 통계

    Raises:
        HTTPException: TTS 생성 실패 시 500 에러
    """
    start_time = time.time()

    try:
        # voice_id만 환경변수에서 가져오기 (필수)
        voice_id = request.voice_id or os.getenv("TTS_DEFAULT_VOICE_ID")
        if not voice_id:
            raise HTTPException(
                status_code=400,
                detail="voice_id가 제공되지 않았고, TTS_DEFAULT_VOICE_ID 환경변수도 설정되지 않았습니다.",
            )

        logger.info(
            f"TTS 생성 요청 수신 - "
            f"voice_id: {voice_id}, "
            f"texts: {sum(len(g) for g in request.texts)}개"
        )

        # TTS 생성 - None인 파라미터는 함수 기본값 사용
        params = {
            "texts": request.texts,
            "voice_id": voice_id,
        }

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

        result = await tts_generator.generate_batch(**params)

        # 결과에서 batch_id와 paths 추출
        batch_id = result["batch_id"]
        paths = result["paths"]

        # 통계 계산
        flat_paths = [p for group in paths for p in group]
        total_count = len(flat_paths)
        success_count = sum(1 for p in flat_paths if p is not None)
        failed_count = total_count - success_count

        # 처리 시간 계산
        duration_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"TTS 생성 완료 - "
            f"batch_id: {batch_id}, "
            f"성공: {success_count}/{total_count}, "
            f"처리 시간: {duration_ms}ms"
        )

        return TTSResponse(
            success=True,
            batch_id=batch_id,
            paths=paths,
            total_count=total_count,
            success_count=success_count,
            failed_count=failed_count,
            duration_ms=duration_ms,
        )

    except Exception as e:
        logger.error(f"TTS 생성 실패: {e}")
        raise HTTPException(
            status_code=500, detail=f"TTS 생성 중 오류가 발생했습니다: {str(e)}"
        )


@app.get("/tts/{word}", response_model=WordTTSResponse)
async def tts_word(word: str):
    """
    단어 TTS 생성 엔드포인트 (캐싱 지원)

    파일이 이미 존재하면 기존 파일을 재사용하고,
    없으면 ElevenLabs API로 새로 생성합니다.

    Args:
        word: 변환할 단어 (최대 50자)

    Returns:
        WordTTSResponse: 생성된 파일 경로 및 통계

    Raises:
        HTTPException:
            - 400: 유효하지 않은 단어 (길이 초과, 특수문자 포함)
            - 500: TTS 생성 실패
    """
    # 단어 길이 검증 (최대 50자)
    if len(word) > 50:
        raise HTTPException(
            status_code=400, detail="단어 길이는 50자를 초과할 수 없습니다."
        )

    # 빈 문자열 검증
    if not word.strip():
        raise HTTPException(status_code=400, detail="단어는 비어있을 수 없습니다.")

    # 특수문자 검증 (영문, 숫자, 한글, 공백, 하이픈만 허용)
    # 추가적인 보안을 위해 경로 조작 문자 차단
    if any(char in word for char in [".", "/", "\\", ".."]):
        raise HTTPException(
            status_code=400,
            detail="단어에 경로 조작 문자(., /, \\)를 포함할 수 없습니다.",
        )

    # 캐시 여부 확인 (generate_word 호출 전)
    from pathlib import Path

    word_dir = Path("/app/data/sound/word")
    file_path = word_dir / f"{word}.mp3"
    is_cached = file_path.exists()

    start_time = time.time()

    try:
        logger.info(f"단어 TTS 요청: '{word}' (캐시됨: {is_cached})")

        # TTS 생성 또는 캐시된 파일 경로 반환
        result_path = await tts_generator.generate_word(word)

        # 처리 시간 계산 (캐시된 경우 None)
        duration_ms = None if is_cached else int((time.time() - start_time) * 1000)

        logger.info(
            f"단어 TTS 완료: '{word}' - "
            f"캐시: {is_cached}, "
            f"경로: {result_path}, "
            f"처리 시간: {duration_ms}ms"
        )

        return WordTTSResponse(
            success=True,
            word=word,
            file_path=result_path,
            cached=is_cached,
            duration_ms=duration_ms,
        )

    except Exception as e:
        logger.error(f"단어 TTS 생성 실패: '{word}' - {e}")
        raise HTTPException(
            status_code=500, detail=f"TTS 생성 중 오류가 발생했습니다: {str(e)}"
        )


@app.get("/tts/stats", response_model=StatsResponse)
async def get_stats():
    """
    TTS Generator 통계 정보 조회

    Returns:
        StatsResponse: 현재 설정 및 통계 정보
    """
    try:
        stats = tts_generator.get_stats()
        return StatsResponse(**stats)

    except Exception as e:
        logger.error(f"통계 조회 실패: {e}")
        raise HTTPException(
            status_code=500, detail=f"통계 조회 중 오류가 발생했습니다: {str(e)}"
        )


# === Startup Event ===


@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행"""
    logger.info("=" * 50)
    logger.info("MoriAI TTS Service Starting...")
    logger.info(f"TTS Generator Stats: {tts_generator.get_stats()}")
    logger.info("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 실행"""
    logger.info("MoriAI TTS Service Shutting Down...")
