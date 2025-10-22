"""
Storybook Repositories Package

Repository 패턴을 사용한 데이터 접근 레이어
추후 DB 전환 시 쉽게 교체 가능하도록 추상화
"""

from .base import AbstractBookRepository
from .file_repository import FileBookRepository
from .memory_repository import InMemoryBookRepository

__all__ = [
    "AbstractBookRepository",
    "FileBookRepository",
    "InMemoryBookRepository",
]
