"""
File-based Book Repository

파일 시스템을 사용하여 Book 데이터를 영구 저장하는 Repository
캐싱 없이 순수 파일 I/O만 담당
"""

import logging
from typing import List, Optional
from .base import AbstractBookRepository
from ..file_manager import FileManager
from ..models import Book

logger = logging.getLogger(__name__)


class FileBookRepository(AbstractBookRepository):
    """
    파일 기반 Book Repository

    JSON 파일로 Book 데이터를 영구 저장
    캐싱 레이어 없이 순수 파일 I/O만 수행
    InMemoryBookRepository가 이 클래스를 감싸서 캐싱 제공
    """

    def __init__(
        self,
        book_data_dir: str = "/app/data/book",
        image_data_dir: str = "/app/data/image"
    ):
        """
        FileBookRepository 초기화

        Args:
            book_data_dir: Book 메타데이터 저장 디렉토리
            image_data_dir: 이미지 파일 저장 디렉토리
        """
        self.file_manager = FileManager(
            book_data_dir=book_data_dir,
            image_data_dir=image_data_dir
        )
        logger.info("FileBookRepository initialized")

    async def create(self, book: Book) -> Book:
        """
        새로운 동화책 생성 (파일 저장)

        Args:
            book: 생성할 Book 객체

        Returns:
            Book: 생성된 Book 객체

        Raises:
            Exception: 파일 저장 실패 시
        """
        await self.file_manager.save_book_metadata(book)
        logger.info(f"Book created in file system: {book.id}")
        return book

    async def get(self, book_id: str) -> Optional[Book]:
        """
        특정 동화책 조회 (파일 로드)

        Args:
            book_id: 조회할 동화책 ID

        Returns:
            Optional[Book]: 조회된 Book 객체, 없으면 None
        """
        book = await self.file_manager.load_book_metadata(book_id)
        if book:
            logger.info(f"Book loaded from file system: {book_id}")
        return book

    async def get_all(self) -> List[Book]:
        """
        모든 동화책 조회 (전체 파일 스캔)

        Returns:
            List[Book]: 모든 Book 객체 리스트
        """
        books = await self.file_manager.scan_all_books()
        logger.info(f"Loaded {len(books)} books from file system")
        return books

    async def update(self, book_id: str, book: Book) -> Book:
        """
        동화책 정보 업데이트 (파일 덮어쓰기)

        Args:
            book_id: 업데이트할 동화책 ID
            book: 업데이트할 Book 객체

        Returns:
            Book: 업데이트된 Book 객체

        Raises:
            ValueError: 동화책이 존재하지 않을 시
            Exception: 파일 저장 실패 시
        """
        # 존재 여부 확인
        existing_book = await self.get(book_id)
        if not existing_book:
            raise ValueError(f"Book not found: {book_id}")

        # Book ID 일치 확인
        if book.id != book_id:
            raise ValueError(f"Book ID mismatch: {book.id} != {book_id}")

        # 파일 덮어쓰기
        await self.file_manager.save_book_metadata(book)
        logger.info(f"Book updated in file system: {book_id}")
        return book

    async def delete(self, book_id: str) -> bool:
        """
        동화책 메타데이터 삭제

        주의: 이미지 파일은 StorageService가 담당
        Repository는 오직 메타데이터(metadata.json)만 삭제

        Args:
            book_id: 삭제할 동화책 ID

        Returns:
            bool: 삭제 성공 여부
        """
        result = await self.file_manager.delete_book_metadata(book_id)
        if result:
            logger.info(f"Book metadata deleted from file system: {book_id}")
        return result

    async def exists(self, book_id: str) -> bool:
        """
        동화책 존재 여부 확인

        Args:
            book_id: 확인할 동화책 ID

        Returns:
            bool: 존재 여부
        """
        book = await self.get(book_id)
        return book is not None
