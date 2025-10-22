"""
Abstract Storage Service Interface

파일 리소스 관리를 위한 추상 인터페이스
LocalStorage, S3, GCS 등 다양한 구현체 교체 가능
"""

from abc import ABC, abstractmethod
from typing import Optional, Literal
from fastapi import UploadFile

from ..models import Book

# 지원하는 미디어 타입
MediaType = Literal["image", "video", "audio"]


class AbstractStorageService(ABC):
    """
    파일 스토리지 추상 인터페이스

    책임: 비구조화된 파일 리소스(이미지, 비디오, 오디오 등)의 물리적 저장 및 삭제

    구현체:
    - LocalStorageService: 로컬 파일 시스템
    - S3StorageService: AWS S3 (향후)
    - GCSStorageService: Google Cloud Storage (향후)
    """

    @abstractmethod
    async def upload_file(
        self,
        file: UploadFile,
        book_id: str,
        filename: str,
        media_type: MediaType = "image"
    ) -> str:
        """
        파일 업로드 (범용)

        Args:
            file: 업로드할 파일
            book_id: 소속된 Book ID
            filename: 저장할 파일명
            media_type: 미디어 타입 ("image", "video", "audio")

        Returns:
            str: 저장된 파일의 URL/경로

        Raises:
            Exception: 업로드 실패 시
        """
        pass

    @abstractmethod
    async def delete_file(self, file_url: str, media_type: MediaType = "image") -> bool:
        """
        단일 파일 삭제 (범용)

        Args:
            file_url: 삭제할 파일 URL/경로
            media_type: 미디어 타입 ("image", "video", "audio")

        Returns:
            bool: 삭제 성공 여부
        """
        pass

    # 하위 호환성을 위한 이미지 전용 메서드 (deprecated)
    async def upload_image(
        self,
        file: UploadFile,
        book_id: str,
        filename: str
    ) -> str:
        """
        이미지 파일 업로드 (하위 호환성용)

        Note: upload_file 사용을 권장합니다.
        """
        return await self.upload_file(file, book_id, filename, media_type="image")

    async def delete_image(self, image_url: str) -> bool:
        """
        단일 이미지 파일 삭제 (하위 호환성용)

        Note: delete_file 사용을 권장합니다.
        """
        return await self.delete_file(image_url, media_type="image")

    @abstractmethod
    async def delete_book_assets(self, book: Book) -> bool:
        """
        Book에 속한 모든 파일 리소스 삭제

        Book 객체를 순회하며 모든 이미지, 비디오, 오디오 파일 삭제

        Args:
            book: 파일을 삭제할 Book 객체

        Returns:
            bool: 삭제 성공 여부
        """
        pass

    @abstractmethod
    async def delete_book_directory(self, book_id: str) -> bool:
        """
        Book 디렉토리 전체 삭제

        Args:
            book_id: Book ID

        Returns:
            bool: 삭제 성공 여부
        """
        pass

    @abstractmethod
    async def file_exists(self, file_url: str, media_type: MediaType = "image") -> bool:
        """
        파일 존재 여부 확인 (범용)

        Args:
            file_url: 확인할 파일 URL/경로
            media_type: 미디어 타입 ("image", "video", "audio")

        Returns:
            bool: 존재 여부
        """
        pass

    async def image_exists(self, image_url: str) -> bool:
        """
        이미지 파일 존재 여부 확인 (하위 호환성용)

        Note: file_exists 사용을 권장합니다.
        """
        return await self.file_exists(image_url, media_type="image")
