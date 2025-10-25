"""
Router Registry Module
중앙 집중식 Router 등록 및 관리 시스템
"""

from typing import List, Dict, Any, Optional
from fastapi import FastAPI, APIRouter
from core.logging import get_logger

logger = get_logger(__name__)


class RouterRegistry:
    """
    Router 중앙 레지스트리

    Features:
    - 자동 router 등록 및 로딩
    - Priority 기반 로딩 순서 제어
    - Tag 기반 router 분류
    - 런타임 router 추가/제거
    - 등록된 router 조회 및 필터링
    """

    _routers: List[Dict[str, Any]] = []
    _loaded: bool = False

    @classmethod
    def register(
        cls,
        router: APIRouter,
        priority: int = 0,
        tags: Optional[List[str]] = None,
        name: Optional[str] = None,
        enabled: bool = True,
    ) -> APIRouter:
        """
        Router를 레지스트리에 등록

        Args:
            router: 등록할 APIRouter 인스턴스
            priority: 로딩 순서 (높을수록 먼저 로딩)
            tags: Router 분류용 태그
            name: Router 식별 이름 (미입력시 자동 생성)
            enabled: 활성화 여부

        Returns:
            등록된 APIRouter (데코레이터로 사용 가능)

        Example:
            ```python
            router = APIRouter(prefix="/api")
            RouterRegistry.register(router, priority=10, tags=["api", "v1"])
            ```
        """
        # Router 이름 자동 생성
        if name is None:
            name = router.prefix or f"router_{len(cls._routers)}"

        entry = {
            "router": router,
            "priority": priority,
            "tags": tags or [],
            "name": name,
            "enabled": enabled,
        }

        cls._routers.append(entry)
        logger.debug(
            f"📝 Router registered: {name} (priority: {priority}, tags: {tags})"
        )

        return router

    @classmethod
    def load_all(cls, app: FastAPI, filter_tags: Optional[List[str]] = None) -> int:
        """
        등록된 모든 Router를 FastAPI 앱에 로딩

        Args:
            app: FastAPI 애플리케이션 인스턴스
            filter_tags: 특정 태그를 가진 router만 로딩 (선택)

        Returns:
            로딩된 router 개수

        Example:
            ```python
            app = FastAPI()
            loaded_count = RouterRegistry.load_all(app)
            # 또는 특정 태그만: RouterRegistry.load_all(app, filter_tags=["api"])
            ```
        """
        if cls._loaded:
            logger.warning("⚠️  Routers already loaded. Skipping duplicate load.")
            return 0

        # Priority 순으로 정렬 (높은 숫자가 먼저)
        sorted_routers = sorted(cls._routers, key=lambda x: x["priority"], reverse=True)

        loaded_count = 0
        for entry in sorted_routers:
            # 비활성화된 router는 스킵
            if not entry["enabled"]:
                logger.info(f"⏭️  Skipped (disabled): {entry['name']}")
                continue

            # 태그 필터링
            if filter_tags and not any(tag in entry["tags"] for tag in filter_tags):
                logger.debug(f"⏭️  Skipped (tag filter): {entry['name']}")
                continue

            try:
                app.include_router(entry["router"])
                loaded_count += 1
                logger.info(
                    f"✅ Router loaded: {entry['name']} "
                    f"(priority: {entry['priority']}, tags: {entry['tags']})"
                )
            except Exception as e:
                logger.error(f"❌ Failed to load router '{entry['name']}': {e}")

        cls._loaded = True
        logger.info(f"🎉 Total routers loaded: {loaded_count}/{len(sorted_routers)}")
        return loaded_count

    @classmethod
    def get_registered(
        cls, tags: Optional[List[str]] = None, enabled_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        등록된 Router 목록 조회

        Args:
            tags: 특정 태그를 가진 router만 조회
            enabled_only: 활성화된 router만 조회

        Returns:
            Router 정보 리스트
        """
        routers = cls._routers

        if enabled_only:
            routers = [r for r in routers if r["enabled"]]

        if tags:
            routers = [r for r in routers if any(tag in r["tags"] for tag in tags)]

        return routers

    @classmethod
    def unregister(cls, name: str) -> bool:
        """
        특정 Router를 레지스트리에서 제거

        Args:
            name: 제거할 router 이름

        Returns:
            제거 성공 여부
        """
        initial_count = len(cls._routers)
        cls._routers = [r for r in cls._routers if r["name"] != name]

        if len(cls._routers) < initial_count:
            logger.info(f"🗑️  Router unregistered: {name}")
            return True

        logger.warning(f"⚠️  Router not found: {name}")
        return False

    @classmethod
    def clear(cls) -> None:
        """모든 등록된 Router 초기화 (주로 테스트용)"""
        cls._routers.clear()
        cls._loaded = False
        logger.info("🧹 Registry cleared")

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """레지스트리 통계 정보 반환"""
        enabled_count = sum(1 for r in cls._routers if r["enabled"])
        all_tags = set()
        for r in cls._routers:
            all_tags.update(r["tags"])

        return {
            "total_routers": len(cls._routers),
            "enabled_routers": enabled_count,
            "disabled_routers": len(cls._routers) - enabled_count,
            "loaded": cls._loaded,
            "unique_tags": sorted(list(all_tags)),
        }
