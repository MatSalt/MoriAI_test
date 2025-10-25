"""
Middleware Configuration Module
CORS 및 기타 미들웨어 설정
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings


def setup_middleware(app: FastAPI) -> None:
    """미들웨어 설정"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
