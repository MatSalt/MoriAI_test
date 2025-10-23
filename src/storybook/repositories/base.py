"""
Base Repository Interface

추상 베이스 클래스를 사용하여 Repository 인터페이스 정의
추후 DB 전환 시 이 인터페이스를 구현하는 새로운 Repository를 만들면 됨
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from ..models import Book


class AbstractBookRepository(ABC):
    """
    동화책 Repository 추상 인터페이스

    Repository 패턴을 통해 데이터 접근 로직을 추상화
    구현체: FileBookRepository, InMemoryBookRepository, DatabaseBookRepository (추후)
    """

    @abstractmethod
    async def create(self, book: Book) -> Book:
        """
        새로운 동화책 생성

        Args:
            book: 생성할 Book 객체

        Returns:
            Book: 생성된 Book 객체

        Raises:
            Exception: 생성 실패 시
        """
        pass

    @abstractmethod
    async def get(self, book_id: str) -> Optional[Book]:
        """
        특정 동화책 조회

        Args:
            book_id: 조회할 동화책 ID

        Returns:
            Optional[Book]: 조회된 Book 객체, 없으면 None

        Raises:
            Exception: 조회 실패 시
        """
        pass

    @abstractmethod
    async def get_all(self) -> List[Book]:
        """
        모든 동화책 조회

        Returns:
            List[Book]: 모든 Book 객체 리스트

        Raises:
            Exception: 조회 실패 시
        """
        pass

    @abstractmethod
    async def update(self, book_id: str, book: Book) -> Book:
        """
        동화책 정보 업데이트

        Args:
            book_id: 업데이트할 동화책 ID
            book: 업데이트할 Book 객체

        Returns:
            Book: 업데이트된 Book 객체

        Raises:
            Exception: 업데이트 실패 시 또는 동화책이 없을 시
        """
        pass

    @abstractmethod
    async def delete(self, book_id: str) -> bool:
        """
        동화책 삭제

        Args:
            book_id: 삭제할 동화책 ID

        Returns:
            bool: 삭제 성공 여부

        Raises:
            Exception: 삭제 실패 시
        """
        pass

    @abstractmethod
    async def exists(self, book_id: str) -> bool:
        """
        동화책 존재 여부 확인

        Args:
            book_id: 확인할 동화책 ID

        Returns:
            bool: 존재 여부

        Raises:
            Exception: 확인 실패 시
        """
        pass
