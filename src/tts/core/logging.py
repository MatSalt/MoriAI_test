"""
Logging Configuration Module
로깅 설정 및 로거 팩토리
"""

import logging
import sys


def setup_logging() -> None:
    """로깅 설정 초기화"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def get_logger(name: str) -> logging.Logger:
    """로거 인스턴스 반환"""
    return logging.getLogger(name)
