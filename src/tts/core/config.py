"""
Core Configuration Module
환경변수 및 앱 설정 관리
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # API 기본 정보
    app_title: str = "MoriAI TTS Service"
    app_description: str = "ElevenLabs 기반 비동기 TTS 생성 API"
    app_version: str = "1.0.0"

    # TTS 기본 설정
    tts_default_voice_id: Optional[str] = os.getenv("TTS_DEFAULT_VOICE_ID")
    tts_default_model_id: str = "eleven_turbo_v2_5"
    tts_default_language: str = "en"

    # CORS 설정
    cors_origins: list[str] = ["http://localhost:5173"]

    # 파일 경로 설정
    output_dir: str = "/app/data/sound"
    word_dir: str = "/app/data/sound/word"

    class Config:
        env_file = ".env"
        case_sensitive = False


# 싱글톤 인스턴스
settings = Settings()
