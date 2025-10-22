"""
Storage Services Package

파일 리소스(이미지, 오디오) 관리를 위한 Storage 추상화 레이어
Repository와 분리하여 확장 가능한 구조 제공
"""

from .base import AbstractStorageService
from .local_storage import LocalStorageService

__all__ = [
    "AbstractStorageService",
    "LocalStorageService",
]
