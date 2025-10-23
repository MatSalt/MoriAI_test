"""
In-Memory Book Repository with Caching

인메모리 캐싱 + 파일 백업을 함께 관리하는 Repository
Write-Through Cache 전략 사용
"""

import asyncio
import logging
from typing import Dict, List, Optional
from .base import AbstractBookRepository
from .file_repository import FileBookRepository
from ..models import Book

logger = logging.getLogger(__name__)


class InMemoryBookRepository(AbstractBookRepository):
    """
    인메모리 캐싱 + 파일 백업 Repository

    전략: Write-Through Cache
    - 읽기: 캐시 우선, 미스 시 파일 로드 후 캐싱
    - 쓰기: 캐시 저장 + 파일 저장 (동시)
    - 삭제: 캐시 삭제 + 파일 삭제 (동시)

    서버 시작 시 파일 시스템 전체 스캔하여 캐시 워밍업
    """

    def __init__(self, file_repository: FileBookRepository):
        """
        InMemoryBookRepository 초기화

        Args:
            file_repository: 파일 저장을 담당하는 FileBookRepository
        """
        self.file_repository = file_repository
        self._cache: Dict[str, Book] = {}
        self._lock = asyncio.Lock()  # 전역 락 (캐시 전체 보호)
        self._book_locks: Dict[str, asyncio.Lock] = {}  # Book별 락 (세밀한 제어)
        logger.info("InMemoryBookRepository initialized with thread-safe locks")

    def _get_book_lock(self, book_id: str) -> asyncio.Lock:
        """
        Book별 Lock 가져오기 (없으면 생성)

        Args:
            book_id: Book ID

        Returns:
            asyncio.Lock: Book별 락
        """
        if book_id not in self._book_locks:
            self._book_locks[book_id] = asyncio.Lock()
        return self._book_locks[book_id]

    async def initialize_cache(self):
        """
        서버 시작 시 파일 시스템 스캔하여 캐시 워밍업

        모든 Book JSON 파일을 로드하여 인메모리 캐시에 저장
        """
        try:
            logger.info("Starting cache warm-up...")
            books = await self.file_repository.get_all()

            async with self._lock:
                for book in books:
                    self._cache[book.id] = book

            logger.info(f"Cache warm-up completed: {len(books)} books loaded")

        except Exception as e:
            logger.error(f"Failed to initialize cache: {e}")
            raise

    # ================================================================
    # CRUD Operations (Write-Through Cache)
    # ================================================================

    async def create(self, book: Book) -> Book:
        """
        새로운 동화책 생성 (캐시 + 파일 저장)

        Args:
            book: 생성할 Book 객체

        Returns:
            Book: 생성된 Book 객체

        Raises:
            Exception: 저장 실패 시
        """
        book_lock = self._get_book_lock(book.id)
        async with book_lock:
            try:
                # 1. 파일 저장 (영구 저장)
                await self.file_repository.create(book)

                # 2. 캐시 저장 (원자적 연산)
                async with self._lock:
                    self._cache[book.id] = book

                logger.info(f"Book created (cache + file): {book.id}")
                return book

            except Exception as e:
                logger.error(f"Failed to create book: {e}")
                # 파일 저장은 성공했지만 캐시 저장 실패 시, 캐시만 복구
                if book.id not in self._cache:
                    try:
                        loaded_book = await self.file_repository.get(book.id)
                        if loaded_book:
                            async with self._lock:
                                self._cache[book.id] = loaded_book
                    except:
                        pass
                raise

    async def get(self, book_id: str) -> Optional[Book]:
        """
        특정 동화책 조회 (캐시 우선, 미스 시 파일 로드)

        Args:
            book_id: 조회할 동화책 ID

        Returns:
            Optional[Book]: 조회된 Book 객체, 없으면 None
        """
        # 1. 캐시 히트 확인 (읽기는 락 불필요, dict 읽기는 thread-safe)
        async with self._lock:
            if book_id in self._cache:
                logger.info(f"Cache HIT: {book_id}")
                return self._cache[book_id]

        # 2. 캐시 미스 - 파일에서 로드 (Book별 락 사용)
        book_lock = self._get_book_lock(book_id)
        async with book_lock:
            # Double-check: 다른 코루틴이 이미 로드했을 수도 있음
            async with self._lock:
                if book_id in self._cache:
                    logger.info(f"Cache HIT (after double-check): {book_id}")
                    return self._cache[book_id]

            logger.info(f"Cache MISS: {book_id}, loading from file...")
            book = await self.file_repository.get(book_id)

            # 3. 로드 성공 시 캐시에 저장
            if book:
                async with self._lock:
                    self._cache[book_id] = book
                logger.info(f"Book loaded and cached: {book_id}")

            return book

    async def get_all(self) -> List[Book]:
        """
        모든 동화책 조회 (캐시에서 반환)

        Returns:
            List[Book]: 모든 Book 객체 리스트
        """
        async with self._lock:
            books = list(self._cache.values())
        logger.info(f"Retrieved {len(books)} books from cache")
        return books

    async def update(self, book_id: str, book: Book) -> Book:
        """
        동화책 정보 업데이트 (캐시 + 파일 갱신)

        Args:
            book_id: 업데이트할 동화책 ID
            book: 업데이트할 Book 객체

        Returns:
            Book: 업데이트된 Book 객체

        Raises:
            ValueError: 동화책이 존재하지 않을 시
            Exception: 업데이트 실패 시
        """
        book_lock = self._get_book_lock(book_id)
        async with book_lock:
            # 존재 여부 확인
            async with self._lock:
                exists = book_id in self._cache

            if not exists:
                existing_book = await self.file_repository.get(book_id)
                if not existing_book:
                    raise ValueError(f"Book not found: {book_id}")

            try:
                # 1. 파일 업데이트
                await self.file_repository.update(book_id, book)

                # 2. 캐시 갱신 (원자적 연산)
                async with self._lock:
                    self._cache[book_id] = book

                logger.info(f"Book updated (cache + file): {book_id}")
                return book

            except Exception as e:
                logger.error(f"Failed to update book: {e}")
                raise

    async def delete(self, book_id: str) -> bool:
        """
        동화책 삭제 (캐시 + 파일 삭제)

        Args:
            book_id: 삭제할 동화책 ID

        Returns:
            bool: 삭제 성공 여부
        """
        book_lock = self._get_book_lock(book_id)
        async with book_lock:
            try:
                # 1. 파일 삭제
                file_deleted = await self.file_repository.delete(book_id)

                # 2. 캐시 삭제 (원자적 연산)
                cache_deleted = False
                async with self._lock:
                    if book_id in self._cache:
                        del self._cache[book_id]
                        cache_deleted = True
                    # Lock 정리 (메모리 누수 방지)
                    if book_id in self._book_locks:
                        del self._book_locks[book_id]

                success = file_deleted or cache_deleted

                if success:
                    logger.info(f"Book deleted (cache + file): {book_id}")
                else:
                    logger.warning(f"Book not found for deletion: {book_id}")

                return success

            except Exception as e:
                logger.error(f"Failed to delete book: {e}")
                raise

    async def exists(self, book_id: str) -> bool:
        """
        동화책 존재 여부 확인 (캐시 우선)

        Args:
            book_id: 확인할 동화책 ID

        Returns:
            bool: 존재 여부
        """
        # 캐시 확인 (원자적 연산)
        async with self._lock:
            if book_id in self._cache:
                return True

        # 파일 확인
        return await self.file_repository.exists(book_id)

    # ================================================================
    # Cache Management
    # ================================================================

    async def get_cache_stats(self) -> dict:
        """
        캐시 통계 정보 조회

        Returns:
            dict: 캐시 통계 (책 개수 등)
        """
        async with self._lock:
            return {
                "cached_books": len(self._cache),
                "book_ids": list(self._cache.keys())
            }

    async def clear_cache(self):
        """
        캐시 완전 초기화 (파일은 유지)

        주의: 이 메서드는 테스트나 디버깅 용도로만 사용
        """
        async with self._lock:
            self._cache.clear()
            self._book_locks.clear()
        logger.warning("Cache cleared (files preserved)")

    async def refresh_cache(self):
        """
        파일 시스템에서 캐시 재로드

        파일과 캐시가 불일치할 경우 사용
        """
        await self.clear_cache()
        await self.initialize_cache()
        logger.info("Cache refreshed from file system")
