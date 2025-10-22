"""
Storybook Business Logic Services

동화책 생성, TTS 연동 등의 비즈니스 로직을 담당하는 서비스 레이어
"""

import logging
import os
from typing import List
from pathlib import Path
from fastapi import UploadFile
import httpx
from google import genai
from google.genai import types
from PIL import Image

from io import BytesIO

import asyncio

from .models import Book, Page, Dialogue
from .prompts.generate_story_prompt import GenerateStoryPrompt
from .prompts.generate_image_prompt import GenerateImagePrompt
from .prompts.generate_video_prompt import GenerateVideoPrompt
from .schemas import StoriesListResponse, create_stories_response_schema
from .storage import AbstractStorageService

logger = logging.getLogger(__name__)


class BookService:
    """
    동화책 생성 및 관리를 위한 비즈니스 로직 서비스

    책임:
    - TTS API 연동
    - 이미지 업로드 조율 (StorageService 사용)
    - Book 객체 조립
    - 복잡한 비즈니스 로직 처리
    """

    def __init__(
        self,
        storage_service: AbstractStorageService,
        tts_api_url: str = None,
        image_data_dir: str = None,
        video_data_dir: str = None,
        http_client: httpx.AsyncClient = None,
        genai_client: genai.Client = None,
    ):
        """
        BookService 초기화

        Args:
            storage_service: 파일 스토리지 서비스
            tts_api_url: TTS API URL (환경변수에서 로드 가능)
            image_data_dir: 이미지 저장 디렉토리
            video_data_dir: 비디오 저장 디렉토리
            http_client: 재사용 가능한 HTTP 클라이언트 (선택, 없으면 자동 생성)
            genai_client: GenAI 클라이언트 (선택, 없으면 자동 생성)
        """
        self.storage = storage_service
        self.tts_api_url = tts_api_url or os.getenv(
            "TTS_API_URL", "http://tts-api:8000"
        )
        self.image_data_dir = image_data_dir or os.getenv(
            "IMAGE_DATA_DIR", "./data/image/"
        )
        self.video_data_dir = video_data_dir or os.getenv(
            "VIDEO_DATA_DIR", "./data/video/"
        )

        # HTTP 클라이언트 설정 (재사용 가능)
        if http_client:
            self.http_client = http_client
            self._owns_client = False  # 외부 주입 클라이언트는 외부에서 관리
            logger.info(f"BookService initialized with injected HTTP client")
        else:
            # 자체 클라이언트 생성 (base_url 없이 - 테스트 호환성)
            self.http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0, read=300.0),  # 기본 타임아웃
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            )
            self._owns_client = True  # 자체 생성 클라이언트는 직접 관리
            logger.info(
                f"BookService initialized with self-managed HTTP client - TTS API: {self.tts_api_url}"
            )

        logger.info(
            f"^&*^*&^&*^*&^*&^GOOGLE_API_KEY: {'set' if os.getenv('GOOGLE_API_KEY') else 'not set'}"
        )
        if genai_client:
            self.genai_client = genai_client
            self._owns_genai_client = False
            logger.info("BookService initialized with injected GenAI client")
        else:
            # Google API Key 확인
            google_api_key = os.getenv("GOOGLE_API_KEY")
            if google_api_key:
                self.genai_client = genai.Client(api_key=google_api_key)
                self._owns_genai_client = True
                logger.info("BookService initialized with self-managed GenAI client")
            else:
                self.genai_client = None
                self._owns_genai_client = False
                logger.warning("GenAI client not initialized - GOOGLE_API_KEY not set")
        logger.info("BookService initialized successfully")

    async def close(self):
        """
        서비스 종료 시 HTTP 클라이언트 정리

        주의: 외부 주입 클라이언트는 외부에서 관리해야 함
        """
        if self._owns_client and self.http_client:
            await self.http_client.aclose()
            logger.info("BookService HTTP client closed")

        # GenAI Client 명시적 close 필요 없음
        if self._owns_genai_client and self.genai_client:
            self.genai_client = None
            logger.info("BookService GenAI client released")

    # ================================================================
    # 동화책 생성 (TTS 연동)
    # ================================================================

    async def create_book_with_tts(
        self, stories: List[str], images: List[dict], book_id: str = None
    ) -> Book:
        """
        동화책 생성 및 TTS 오디오 생성

        Args:
            stories: 각 페이지의 텍스트 배열
            images: 각 페이지의 이미지 파일 배열 (stories와 순서 매칭)
            book_id: 기존 Book ID (선택, BackgroundTasks에서 사용)

        Returns:
            Book: 생성된 Book 객체 (status='success' or 'error')

        Raises:
            ValueError: stories와 images 길이가 다를 경우
            Exception: 처리 중 오류 발생 시
        """
        # 입력 검증
        if not stories or not images:
            raise ValueError("At least one page is required")

        if len(stories) != len(images):
            raise ValueError(
                f"Stories and images count mismatch: {len(stories)} vs {len(images)}"
            )

        # Book 객체 초기화 (status='process')
        if book_id:
            # 기존 Book ID 사용 (BackgroundTasks에서 호출 시)
            book = Book(
                id=book_id,
                title="",  # 기본 제목 (나중에 업데이트 가능)
                cover_image="",
                status="process",
                pages=[],
            )
        else:
            # 새 Book 생성 (일반 호출 시)
            book = Book(title="", cover_image="", status="process", pages=[])
        try:
            stories = await self._generate_story_with_ai(stories)
            logger.info(f"Generated stories: {stories}")
            if stories is None or len(stories) == 0:
                logger.warning("[BookService] No stories generated")
                book.status = "error"
                return book

            # 1️⃣ TTS 생성 태스크
            tts_task = asyncio.create_task(self._generate_tts_audio(stories))

            # 2️⃣ 이미지 병렬 생성
            image_tasks = [
                asyncio.create_task(
                    self._generate_storybook_page(i, story, img, book.id)
                )
                for i, (story, img) in enumerate(zip(stories, images))
            ]

            # 3️⃣ 병렬 처리 결과 수집
            tts_results, page_results = await asyncio.gather(
                tts_task, asyncio.gather(*image_tasks)
            )
            logger.info(f"generate_tts_audio() results: {tts_results}")
            logger.info(f"generate_storybook_page() results: {page_results}")

            # 4️⃣ TTS 결과를 각 Page의 Dialogue로 추가
            for page_idx, (page, story_dialogues, tts_urls) in enumerate(
                zip(page_results, stories, tts_results)
            ):
                # 각 대사마다 Dialogue 객체 생성
                for dialogue_idx, (text, audio_url) in enumerate(
                    zip(story_dialogues, tts_urls if tts_urls else [])
                ):
                    dialogue = Dialogue(
                        index=dialogue_idx + 1,
                        text=text,
                        part_audio_url=audio_url if audio_url else "",
                    )
                    page.dialogues.append(dialogue)

                logger.info(
                    f"[BookService] Page {page_idx + 1}: {len(page.dialogues)} dialogues added"
                )

            # 5️⃣ Book 객체 조합
            book.pages = page_results

            # 첫 번째 페이지의 이미지를 커버로 설정
            if page_results and page_results[0].content:
                # video 타입이면 fallback_image를 커버로 사용
                if page_results[0].type == "video" and page_results[0].fallback_image:
                    book.cover_image = page_results[0].fallback_image
                else:
                    book.cover_image = page_results[0].content

            book.status = "success"
            logger.info(
                f"[BookService] Book creation completed successfully: {book.id}"
            )
            return book

        except Exception as e:
            logger.error(f"[BookService] Book creation failed: {e}", exc_info=True)
            book.status = "error"

            # 롤백: 업로드된 파일 삭제 시도
            logger.warning(
                f"[BookService] Attempting rollback: deleting book directory {book.id}..."
            )
            try:
                await self.storage.delete_book_directory(book.id)
                logger.info(f"[BookService] Rollback completed: book directory deleted")
            except Exception as rollback_error:
                logger.error(f"[BookService] Rollback failed: {rollback_error}")

            raise

    # ================================================================
    # TTS API 연동
    # ================================================================

    async def _generate_tts_audio(self, dialogs: List[List[str]]) -> List[List[str]]:
        """
        TTS API 호출하여 오디오 파일 생성

        Args:
            stories: 텍스트 배열

        Returns:
            List[str]: 생성된 오디오 파일 URL 리스트 (실패 시 None)
        """

        if not dialogs:
            logger.warning("[BookService] Empty stories list for TTS generation")
            return []

        try:

            logger.info(
                f"[BookService] Calling TTS API: {self.tts_api_url}/tts/generate"
            )
            logger.debug(f"[BookService] TTS request data: {dialogs}")

            # TTS API 호출 (비동기)
            # 타임아웃: 페이지당 10초 + 기본 30초 (최소 60초)
            timeout_seconds = max(120.0, len(dialogs) * 10.0)

            # 재사용 가능한 클라이언트 사용 + 요청별 타임아웃 오버라이드
            response = await self.http_client.post(
                f"{self.tts_api_url}/tts/generate",
                json={"texts": dialogs},
                timeout=timeout_seconds,
            )
            logger.info(
                f"&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&\n[BookService] TTS API call completed: {response}"
            )

            response.raise_for_status()
            result = response.json()
            logger.info(
                f"&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&\n[BookService] TTS API call completed: {result}"
            )

            logger.debug(f"[BookService] TTS API raw response: {result}")

            # 결과에서 오디오 URL 추출
            # TTS API 응답: {"paths": [["/path/to/audio1.mp3"], ["/path/to/audio2.mp3"]], ...}
            paths = result.get("paths", [])

            if not paths:
                logger.error("[BookService] TTS API returned empty paths")
                return [[None] * len(page_dialogs) for page_dialogs in dialogs]

            # TTS API 응답 구조: {"paths": [[url1, url2], [url3, url4]], ...} (2차원 배열)
            # paths는 이미 dialogs와 동일한 2차원 구조로 반환됨
            audio_urls = []

            for page_idx, page_paths in enumerate(paths):
                page_urls = []

                # page_paths가 리스트인지 확인
                if isinstance(page_paths, list):
                    for dialog_idx, audio_url in enumerate(page_paths):
                        if audio_url:
                            # /app 접두사 제거 (컨테이너 내부 경로 → 외부 접근 경로)
                            cleaned_url = (
                                audio_url.removeprefix("/app")
                                if isinstance(audio_url, str)
                                else audio_url
                            )
                            page_urls.append(cleaned_url)
                            logger.debug(
                                f"[BookService] Page {page_idx + 1}, Dialog {dialog_idx + 1}: {cleaned_url}"
                            )
                        else:
                            page_urls.append(None)
                            logger.warning(
                                f"[BookService] Page {page_idx + 1}, Dialog {dialog_idx + 1}: No audio URL"
                            )
                else:
                    # 예상치 못한 형식
                    logger.error(
                        f"[BookService] Unexpected path format for page {page_idx + 1}: {type(page_paths)}"
                    )
                    page_urls = (
                        [None] * len(dialogs[page_idx])
                        if page_idx < len(dialogs)
                        else []
                    )

                audio_urls.append(page_urls)

            # 페이지 수 검증
            if len(audio_urls) != len(dialogs):
                logger.warning(
                    f"[BookService] TTS API page count mismatch: "
                    f"expected {len(dialogs)}, got {len(audio_urls)}"
                )
                # 부족한 페이지 추가
                while len(audio_urls) < len(dialogs):
                    audio_urls.append([None] * len(dialogs[len(audio_urls)]))

            # 각 페이지의 대사 수 검증 및 조정
            for page_idx, (expected_dialogs, actual_urls) in enumerate(
                zip(dialogs, audio_urls)
            ):
                if len(actual_urls) != len(expected_dialogs):
                    logger.warning(
                        f"[BookService] Page {page_idx + 1} dialog count mismatch: "
                        f"expected {len(expected_dialogs)}, got {len(actual_urls)}"
                    )
                    # 부족한 만큼 None 추가
                    while len(actual_urls) < len(expected_dialogs):
                        actual_urls.append(None)
                    # 초과분 제거
                    if len(actual_urls) > len(expected_dialogs):
                        audio_urls[page_idx] = actual_urls[: len(expected_dialogs)]

            # 총 성공한 URL 개수 계산
            success_count = sum(
                1 for page_urls in audio_urls for url in page_urls if url
            )
            total_expected = sum(len(page_dialogs) for page_dialogs in dialogs)

            logger.info(
                f"[BookService] TTS API returned {success_count}/{total_expected} audio files across {len(audio_urls)} pages"
            )

            return audio_urls

        except httpx.TimeoutException as e:
            logger.error(f"[BookService] TTS API timeout after {timeout_seconds}s: {e}")
            return [[None] * len(page_dialogs) for page_dialogs in dialogs]
        except httpx.HTTPStatusError as e:
            logger.error(
                f"[BookService] TTS API HTTP error: {e.response.status_code} - {e.response.text}"
            )
            return [[None] * len(page_dialogs) for page_dialogs in dialogs]
        except httpx.RequestError as e:
            logger.error(f"[BookService] TTS API connection error: {e}")
            return [[None] * len(page_dialogs) for page_dialogs in dialogs]
        except Exception as e:
            logger.error(f"[BookService] TTS API unexpected error: {e}", exc_info=True)
            return [[None] * len(page_dialogs) for page_dialogs in dialogs]

    # ================================================================
    # 동화책 삭제 (파일 리소스)
    # ================================================================

    async def delete_book_assets(self, book: Book) -> bool:
        """
        Book에 속한 모든 파일 리소스 삭제

        StorageService를 사용하여 이미지 파일 삭제
        Repository는 메타데이터만 삭제하므로, Service가 파일 삭제 조율

        Args:
            book: 파일을 삭제할 Book 객체

        Returns:
            bool: 삭제 성공 여부
        """
        try:
            result = await self.storage.delete_book_assets(book)

            if result:
                logger.info(f"Book assets deleted: {book.id}")
            else:
                logger.warning(f"Failed to delete some assets: {book.id}")

            return result

        except Exception as e:
            logger.error(f"Failed to delete book assets: {e}")
            return False

    # ================================================================
    # 동화책 시나리오 생성 (GenAI 연동)
    # ================================================================
    async def _generate_story_with_ai(self, input_texts: list[str]) -> list[list[str]]:
        """
        GenAI API를 호출하여 동화책 시나리오 생성

        입력 텍스트 개수에 따라 자동으로 페이지 수와 대사 수 제한을 설정합니다.

        Args:
            input_texts: 시나리오 생성을 위한 입력 텍스트 리스트

        Returns:
            list[list[str]]: 생성된 시나리오 리스트
        """
        if not self.genai_client:
            logger.error("GenAI client is not initialized")
            return [[] for _ in input_texts]

        try:
            # 입력 텍스트 개수를 기반으로 자동으로 max_pages 설정
            max_pages = len(input_texts)

            # 페이지당 최대 대사 수 설정 (고정값 또는 동적 계산 가능)
            max_dialogues_per_page = 3  # 필요에 따라 조정 가능

            # 동적 스키마 생성
            response_schema = create_stories_response_schema(
                max_pages=max_pages, max_dialogues_per_page=max_dialogues_per_page
            )

            prompt = GenerateStoryPrompt(diary_entries=input_texts).render()
            logger.info(
                f"Calling GenAI API for story generation (max_pages={max_pages}, "
                f"max_dialogues_per_page={max_dialogues_per_page})"
            )
            logger.debug(f"Prompt: {prompt}")

            response = await self.genai_client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": response_schema,
                },
            )
            logger.info(f"GenAI API call completed: {response}")
            parsed = response.parsed
            return parsed.stories

        except Exception as e:
            logger.error(f"GenAI story generation failed: {e}", exc_info=True)
            return [[] for _ in input_texts]

    # ================================================================
    # 동화책 이미지 생성
    # ================================================================
    async def _generate_storybook_page(
        self, index: int, story: List[str], image: dict, book_id: str
    ) -> Page:
        """
        페이지 시나리오에 대한 이미지 및 비디오 생성 및 업로드

        Args:
            index: 페이지 인덱스
            story: 페이지 시나리오 텍스트 배열
            image: 업로드할 이미지 파일
            book_id: Book ID

        Returns:
            Page: 생성된 페이지 객체
        """
        if not self.genai_client:
            logger.error("GenAI client is not initialized")
            return Page(
                index=index + 1,
                type="image",
                content="",
                fallback_image="",
                dialogues=[],
            )

        try:
            # 1. 이미지 생성 및 업로드 (fallback용)
            image_url = await self._generate_storybook_page_image(
                index, story, image, book_id, f"page_{index + 1}"
            )

            # 2. 비디오 생성 및 업로드
            video_url = await self._generate_storybook_page_video(
                index, story, image_url, book_id, f"page_{index + 1}"
            )
            # video_url = ""  # 비디오 생성 비활성화

            # 3. 페이지 객체 생성
            if video_url:
                # 비디오 생성 성공 시 - video 타입 페이지
                page = Page(
                    index=index + 1,
                    type="video",
                    content=video_url,
                    fallback_image=image_url,
                    dialogues=[],
                )
                logger.info(
                    f"[BookService] Page {index + 1} generated - Type: video, Content: {video_url}, Fallback: {image_url}"
                )
            else:
                # 비디오 생성 실패 시 - image 타입 페이지
                page = Page(
                    index=index + 1,
                    type="image",
                    content=image_url,
                    fallback_image="",
                    dialogues=[],
                )
                logger.info(
                    f"[BookService] Page {index + 1} generated - Type: image, Content: {image_url}"
                )

            return page

        except Exception as e:
            logger.error(
                f"[BookService] Page generation failed for page {index + 1}: {e}",
                exc_info=True,
            )
            # 에러 발생 시 빈 이미지 페이지 반환
            return Page(
                index=index + 1,
                type="image",
                content="",
                fallback_image="",
                dialogues=[],
            )

    async def _generate_storybook_page_image(
        self, index: int, story: List[str], input_img: dict, book_id: str, page_id: str
    ) -> str:
        """
        페이지 시나리오에 대한 이미지 생성 및 업로드

        Args:
            story: 페이지 시나리오 텍스트 배열
            image: 업로드할 이미지 파일

        Returns:
        """
        logger.info(f"[BookService] Generating storybook page image {index + 1}")
        if not self.genai_client:
            logger.error("GenAI client is not initialized")
            return ""
        try:
            img = types.Part.from_bytes(
                data=input_img["content"], mime_type=input_img["content_type"]
            )
            prompt = GenerateImagePrompt(
                stories=story, style_keyword="cartoon"
            ).render()
            response = self.genai_client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=[prompt, img],
                config=types.GenerateContentConfig(
                    image_config=types.ImageConfig(
                        aspect_ratio="4:3",
                    )
                ),
            )
            image_parts = [
                part.inline_data.data
                for part in response.candidates[0].content.parts
                if part.inline_data
            ]

            if image_parts:
                upload_file = UploadFile(
                    file=BytesIO(image_parts[0]),
                    filename=str(index) + "_" + page_id + ".png",
                    headers={"content-type": "image/png"},
                )
                result = await self.storage.upload_image(
                    file=upload_file, book_id=book_id, filename=upload_file.filename
                )
                return result
            else:
                logger.info(f"no image_parts")
                return None

        except Exception as e:
            logger.error(
                f"[BookService] Image generation failed for page {index + 1}: {e}"
            )
            return "<image_url>"

    async def _generate_storybook_page_video(
        self, index: int, story: List[str], image_url: str, book_id: str, page_id: str
    ) -> str:
        """
        페이지 시나리오에 대한 비디오 생성 및 업로드

        Args:
            index: 페이지 인덱스
            story: 페이지 시나리오 텍스트 배열
            image_url: 생성된 이미지 URL (로컬 경로)
            book_id: Book ID
            page_id: Page ID

        Returns:
            str: 업로드된 비디오 URL (성공 시) 또는 빈 문자열 (실패 시)
        """
        if not self.genai_client:
            logger.error("GenAI client is not initialized")
            return ""

        logger.info(f"[BookService] Generating storybook page video {index + 1}")

        try:
            # 1. 이미지 URL을 로컬 파일 경로로 변환
            # image_url: "/data/image/{book_id}/{filename}" -> "./data/image/{book_id}/{filename}"
            image_path = str(
                Path(self.image_data_dir) / image_url.replace("/data/image/", "")
            )

            # 2. 이미지를 GenAI 형식으로 로드
            image_part = genai.types.Image.from_file(
                location=image_path, mime_type="image/png"
            )

            # 3. 비디오 생성 프롬프트
            prompt = GenerateVideoPrompt(stories=story).render()

            # 4. GenAI 비디오 생성 요청 (동기 호출)
            operation = self.genai_client.models.generate_videos(
                model="veo-3.1-generate-preview",
                prompt=prompt,
                image=image_part,
                config=types.GenerateVideosConfig(
                    last_frame=image_part,
                    # duration_seconds=4,
                ),
            )

            # 5. 비디오 생성 완료 대기
            while not operation.done:
                logger.info(
                    f"[BookService] Waiting for video generation to complete... (page {index + 1})"
                )
                await asyncio.sleep(10)
                operation = self.genai_client.operations.get(operation)

            # 6. 비디오 다운로드 (동기 호출, bytes 반환)
            video = operation.response.generated_videos[0]
            video_bytes = self.genai_client.files.download(file=video.video)

            # 7. UploadFile 객체 생성
            video_file = UploadFile(
                file=BytesIO(video_bytes),
                filename=f"{page_id}.mp4",
                headers={"content-type": "video/mp4"},
            )

            # 8. Storage Service로 업로드
            video_url = await self.storage.upload_file(
                file=video_file,
                book_id=book_id,
                filename=video_file.filename,
                media_type="video",
            )

            logger.info(f"[BookService] Video uploaded successfully: {video_url}")
            return video_url

        except Exception as e:
            logger.error(
                f"[BookService] Video generation failed for page {index + 1}: {e}",
                exc_info=True,
            )
            return ""
