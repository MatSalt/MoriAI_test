"""
Local File System Storage Service

로컬 파일 시스템 기반 스토리지 구현
"""

import logging
import shutil
import aiofiles
from pathlib import Path
from typing import Optional
from fastapi import UploadFile

from .base import AbstractStorageService
from ..models import Book

logger = logging.getLogger(__name__)


class LocalStorageService(AbstractStorageService):
    """
    로컬 파일 시스템 기반 스토리지 서비스

    파일 구조:
    ./data/image/
    └── {book_id}/
        ├── {page_id_1}.png
        ├── {page_id_2}.png
        └── ...
    """

    def __init__(
        self,
        image_data_dir: str = "./data/image",
        video_data_dir: str = "./data/video",
    ):
        """
        LocalStorageService 초기화

        Args:
            image_data_dir: 이미지 저장 디렉토리
            video_data_dir: 비디오 저장 디렉토리
        """
        self.image_data_dir = Path(image_data_dir)
        self.video_data_dir = Path(video_data_dir)
        self.image_data_dir.mkdir(parents=True, exist_ok=True)
        self.video_data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            f"LocalStorageService initialized - Image dir: {self.image_data_dir}, Video dir: {self.video_data_dir}"
        )

    async def upload_file(
        self,
        file: UploadFile,
        book_id: str,
        filename: str,
        media_type: str = "image",
    ) -> str:
        """
        파일을 로컬 파일 시스템에 저장 (범용)

        Args:
            file: 업로드할 파일
            book_id: 소속된 Book ID
            filename: 저장할 파일명
            media_type: 미디어 타입 ("image", "video", "audio")

        Returns:
            str: 저장된 파일 URL (상대 경로)

        Raises:
            Exception: 파일 저장 실패 시
        """
        try:
            # 미디어 타입별 디렉토리 선택
            if media_type == "image":
                base_dir = self.image_data_dir
            elif media_type == "video":
                base_dir = self.video_data_dir
            else:
                raise ValueError(f"Unsupported media type: {media_type}")

            # Book별 디렉토리 생성
            book_media_dir = base_dir / book_id
            book_media_dir.mkdir(parents=True, exist_ok=True)

            # 파일 저장 경로
            file_path = book_media_dir / filename

            # 비동기로 파일 저장
            async with aiofiles.open(file_path, "wb") as f:
                content = await file.read()
                await f.write(content)

            # URL 생성 (실제 저장된 경로 기반)
            file_url = f"/data/{media_type}/{file_path.relative_to(base_dir)}"

            logger.info(f"{media_type.capitalize()} file uploaded: {file_url}")
            return file_url

        except Exception as e:
            logger.error(f"Failed to upload {media_type} file: {e}")
            raise

    async def upload_image(self, file: UploadFile, book_id: str, filename: str) -> str:
        """
        이미지 파일을 로컬 파일 시스템에 저장 (하위 호환성용)

        Note: upload_file 사용을 권장합니다.

        Args:
            file: 업로드할 이미지 파일
            book_id: 소속된 Book ID
            filename: 저장할 파일명

        Returns:
            str: 저장된 이미지 URL (상대 경로)

        Raises:
            Exception: 파일 저장 실패 시
        """
        return await self.upload_file(file, book_id, filename, media_type="image")

    async def delete_file(self, file_url: str, media_type: str = "image") -> bool:
        """
        단일 파일 삭제 (범용)

        Args:
            file_url: 삭제할 파일 URL (예: /data/image/book-id/page-id.png)
            media_type: 미디어 타입 ("image", "video", "audio")

        Returns:
            bool: 삭제 성공 여부
        """
        try:
            # 미디어 타입별 디렉토리 선택
            if media_type == "image":
                base_dir = self.image_data_dir
                prefix = "/data/image/"
            elif media_type == "video":
                base_dir = self.video_data_dir
                prefix = "/data/video/"
            else:
                logger.warning(f"Unsupported media type: {media_type}")
                return False

            # URL에서 로컬 경로 추출
            if file_url.startswith(prefix):
                relative_path = file_url[len(prefix) :]
                file_path = base_dir / relative_path
            else:
                logger.warning(f"Invalid {media_type} URL format: {file_url}")
                return False

            # 파일 존재 확인 및 삭제
            if file_path.exists():
                file_path.unlink()
                logger.info(f"{media_type.capitalize()} deleted: {file_url}")
                return True
            else:
                logger.warning(f"{media_type.capitalize()} not found: {file_url}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete {media_type}: {e}")
            return False

    async def delete_image(self, image_url: str) -> bool:
        """
        단일 이미지 파일 삭제 (하위 호환성용)

        Note: delete_file 사용을 권장합니다.

        Args:
            image_url: 삭제할 이미지 URL (예: /data/image/book-id/page-id.png)

        Returns:
            bool: 삭제 성공 여부
        """
        return await self.delete_file(image_url, media_type="image")

    async def delete_book_assets(self, book: Book) -> bool:
        """
        Book에 속한 모든 파일 리소스 삭제

        Pages의 배경 이미지, 비디오, dialogues의 오디오 파일 모두 삭제

        Args:
            book: 파일을 삭제할 Book 객체

        Returns:
            bool: 삭제 성공 여부
        """
        try:
            success = True

            # 각 페이지의 리소스 삭제
            for page in book.pages:
                # 배경 이미지 삭제
                if page.background_image:
                    result = await self.delete_file(page.background_image, media_type="image")
                    if not result:
                        success = False

                # 비디오 삭제
                if page.video_url:
                    result = await self.delete_file(page.video_url, media_type="video")
                    if not result:
                        success = False

                # 각 대사의 오디오 파일 삭제 (향후 지원)
                # for dialogue in page.dialogues:
                #     if dialogue.part_audio_url:
                #         await self.delete_file(dialogue.part_audio_url, media_type="audio")

            if success:
                logger.info(f"All assets deleted for book: {book.id}")
            else:
                logger.warning(f"Some assets failed to delete for book: {book.id}")

            return success

        except Exception as e:
            logger.error(f"Failed to delete book assets: {e}")
            return False

    async def delete_book_directory(self, book_id: str) -> bool:
        """
        Book 디렉토리 전체 삭제

        Args:
            book_id: Book ID

        Returns:
            bool: 삭제 성공 여부
        """
        try:
            book_dir = self.image_data_dir / book_id

            if book_dir.exists():
                shutil.rmtree(book_dir)
                logger.info(f"Book directory deleted: {book_id}")
                return True
            else:
                logger.warning(f"Book directory not found: {book_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete book directory: {e}")
            return False

    async def file_exists(self, file_url: str, media_type: str = "image") -> bool:
        """
        파일 존재 여부 확인 (범용)

        Args:
            file_url: 확인할 파일 URL
            media_type: 미디어 타입 ("image", "video", "audio")

        Returns:
            bool: 존재 여부
        """
        try:
            # 미디어 타입별 디렉토리 선택
            if media_type == "image":
                base_dir = self.image_data_dir
                prefix = "/data/image/"
            elif media_type == "video":
                base_dir = self.video_data_dir
                prefix = "/data/video/"
            else:
                logger.warning(f"Unsupported media type: {media_type}")
                return False

            # URL에서 로컬 경로 추출
            if file_url.startswith(prefix):
                relative_path = file_url[len(prefix) :]
                file_path = base_dir / relative_path
                return file_path.exists()
            return False

        except Exception as e:
            logger.error(f"Failed to check {media_type} existence: {e}")
            return False

    async def image_exists(self, image_url: str) -> bool:
        """
        이미지 파일 존재 여부 확인 (하위 호환성용)

        Note: file_exists 사용을 권장합니다.

        Args:
            image_url: 확인할 이미지 URL

        Returns:
            bool: 존재 여부
        """
        return await self.file_exists(image_url, media_type="image")
