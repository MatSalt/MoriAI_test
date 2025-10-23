"""
File Manager Utility

파일 저장, 로드, 삭제를 담당하는 유틸리티 클래스
이미지 파일 및 Book 메타데이터 JSON 파일 관리
"""

import json
import logging
import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import UploadFile
import aiofiles
from .models import Book

logger = logging.getLogger(__name__)


class FileManager:
    """
    파일 관리 유틸리티 클래스

    책 메타데이터(JSON), 이미지 파일의 저장/로드/삭제를 담당
    """

    def __init__(
        self,
        book_data_dir: str = "/app/data/book",
        image_data_dir: str = "/app/data/image"
    ):
        """
        FileManager 초기화

        Args:
            book_data_dir: Book 메타데이터 저장 디렉토리
            image_data_dir: 이미지 파일 저장 디렉토리
        """
        self.book_data_dir = Path(book_data_dir)
        self.image_data_dir = Path(image_data_dir)

        # 디렉토리 생성
        self.book_data_dir.mkdir(parents=True, exist_ok=True)
        self.image_data_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"FileManager initialized - Book: {self.book_data_dir}, Image: {self.image_data_dir}")

    # ================================================================
    # 이미지 파일 관리
    # ================================================================

    async def save_image(
        self,
        book_id: str,
        file: UploadFile,
        filename: str
    ) -> str:
        """
        이미지 파일 저장

        Args:
            book_id: 동화책 ID
            file: 업로드된 파일 객체
            filename: 저장할 파일명 (예: "cover.png", "page-uuid.png")

        Returns:
            str: 저장된 파일의 상대 경로 (예: "/data/image/book-uuid/cover.png")

        Raises:
            Exception: 파일 저장 실패 시
        """
        try:
            # 책별 이미지 디렉토리 생성
            book_image_dir = self.image_data_dir / book_id
            book_image_dir.mkdir(parents=True, exist_ok=True)

            # 파일 저장 경로
            file_path = book_image_dir / filename

            # 비동기로 파일 쓰기
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)

            # 상대 경로 반환 (Nginx에서 제공할 경로)
            relative_path = f"/data/image/{book_id}/{filename}"

            logger.info(f"Image saved: {relative_path}")
            return relative_path

        except Exception as e:
            logger.error(f"Failed to save image: {e}")
            raise

    async def delete_book_images(self, book_id: str) -> bool:
        """
        특정 동화책의 모든 이미지 파일 삭제

        Args:
            book_id: 동화책 ID

        Returns:
            bool: 삭제 성공 여부
        """
        try:
            book_image_dir = self.image_data_dir / book_id

            if book_image_dir.exists():
                shutil.rmtree(book_image_dir)
                logger.info(f"Book images deleted: {book_id}")
                return True
            else:
                logger.warning(f"Book image directory not found: {book_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete book images: {e}")
            return False

    # ================================================================
    # Book 메타데이터 관리 (JSON)
    # ================================================================

    async def save_book_metadata(self, book: Book) -> Path:
        """
        Book 객체를 JSON 파일로 저장

        Args:
            book: 저장할 Book 객체

        Returns:
            Path: 저장된 파일 경로

        Raises:
            Exception: 파일 저장 실패 시
        """
        try:
            # 책별 메타데이터 디렉토리 생성
            book_dir = self.book_data_dir / book.id
            book_dir.mkdir(parents=True, exist_ok=True)

            # 메타데이터 파일 경로
            metadata_path = book_dir / "metadata.json"

            # Book 객체를 JSON으로 변환 (Pydantic model_dump)
            book_dict = book.model_dump(mode='json')

            # 비동기로 JSON 파일 쓰기
            async with aiofiles.open(metadata_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(book_dict, ensure_ascii=False, indent=2))

            logger.info(f"Book metadata saved: {book.id}")
            return metadata_path

        except Exception as e:
            logger.error(f"Failed to save book metadata: {e}")
            raise

    async def load_book_metadata(self, book_id: str) -> Optional[Book]:
        """
        JSON 파일에서 Book 객체 로드

        Args:
            book_id: 동화책 ID

        Returns:
            Optional[Book]: 로드된 Book 객체, 파일이 없거나 손상되면 None

        Raises:
            Exception: 파일 읽기 실패 시 (파일 손상 등)
        """
        try:
            metadata_path = self.book_data_dir / book_id / "metadata.json"

            if not metadata_path.exists():
                logger.warning(f"Book metadata not found: {book_id}")
                return None

            # 비동기로 JSON 파일 읽기
            async with aiofiles.open(metadata_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                book_dict = json.loads(content)

            # Pydantic 모델로 파싱
            book = Book(**book_dict)

            logger.info(f"Book metadata loaded: {book_id}")
            return book

        except json.JSONDecodeError as e:
            logger.error(f"Corrupted book metadata: {book_id} - {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to load book metadata: {book_id} - {e}")
            raise

    async def delete_book_metadata(self, book_id: str) -> bool:
        """
        Book 메타데이터 파일 삭제

        Args:
            book_id: 동화책 ID

        Returns:
            bool: 삭제 성공 여부
        """
        try:
            book_dir = self.book_data_dir / book_id

            if book_dir.exists():
                shutil.rmtree(book_dir)
                logger.info(f"Book metadata deleted: {book_id}")
                return True
            else:
                logger.warning(f"Book metadata directory not found: {book_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete book metadata: {e}")
            return False

    # ================================================================
    # 초기화 및 스캔
    # ================================================================

    async def scan_all_books(self) -> List[Book]:
        """
        모든 Book 메타데이터 파일을 스캔하여 로드

        서버 시작 시 인메모리 캐시 워밍업에 사용

        Returns:
            List[Book]: 로드된 모든 Book 객체 리스트 (손상된 파일은 제외)
        """
        books = []

        try:
            # book_data_dir의 모든 하위 디렉토리 순회
            if not self.book_data_dir.exists():
                logger.warning("Book data directory does not exist")
                return books

            for book_dir in self.book_data_dir.iterdir():
                if book_dir.is_dir():
                    book_id = book_dir.name
                    book = await self.load_book_metadata(book_id)

                    if book:
                        books.append(book)
                    else:
                        logger.warning(f"Skipping corrupted or missing book: {book_id}")

            logger.info(f"Scanned {len(books)} books from disk")
            return books

        except Exception as e:
            logger.error(f"Failed to scan books: {e}")
            return books

    # ================================================================
    # 완전 삭제 (메타데이터 + 이미지)
    # ================================================================

    async def delete_book_files(self, book_id: str) -> bool:
        """
        특정 동화책의 모든 파일 삭제 (메타데이터 + 이미지)

        Args:
            book_id: 동화책 ID

        Returns:
            bool: 삭제 성공 여부
        """
        metadata_deleted = await self.delete_book_metadata(book_id)
        images_deleted = await self.delete_book_images(book_id)

        return metadata_deleted or images_deleted
