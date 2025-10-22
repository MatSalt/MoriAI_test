# MoriAI Storybook Service

동화책 생성, 조회, 삭제를 위한 FastAPI 기반 백엔드 서비스입니다.

## 프로젝트 구조

```
src/storybook/
├── main.py                         # FastAPI 애플리케이션 진입점
├── models.py                       # Pydantic 데이터 모델 (Book, Page, Dialogue)
├── schemas.py                      # API Request/Response 스키마
├── file_manager.py                 # 파일 저장/로드/삭제 유틸리티
├── services.py                     # 비즈니스 로직 (TTS 연동)
├── repositories/
│   ├── __init__.py                 # Repository 패키지
│   ├── base.py                     # 추상 Repository 인터페이스
│   ├── file_repository.py          # 파일 기반 영구 저장
│   └── memory_repository.py        # 인메모리 캐싱 + 파일 백업
├── requirements.txt                # Python 의존성
└── README.md                       # 이 파일
```

## 아키텍처 설계

### Repository 패턴

**3-Layer 아키텍처:**
1. **Controller Layer**: `main.py` - FastAPI 엔드포인트
2. **Service Layer**: `services.py` - 비즈니스 로직 (TTS 연동)
3. **Data Access Layer**: `repositories/` - 데이터 저장/조회

**Repository 계층:**
- `AbstractBookRepository`: 추상 인터페이스 (추후 DB 전환 용이)
- `FileBookRepository`: 파일 시스템 영구 저장
- `InMemoryBookRepository`: 캐싱 레이어 (Write-Through Cache)

### 캐싱 전략 (Write-Through Cache)

**서버 시작 시:**
- 파일 시스템 전체 스캔 (`/app/data/book/`)
- 모든 Book JSON 로드하여 인메모리 캐시 워밍업

**런타임:**
- **읽기**: 캐시 우선, 미스 시 파일 로드 후 캐싱
- **쓰기**: 캐시 저장 + 파일 저장 (동시)
- **삭제**: 캐시 삭제 + 파일 삭제 (동시)

**장점:**
- 빠른 읽기 성능 (메모리에서 직접 반환)
- 데이터 일관성 보장 (캐시와 파일 동시 업데이트)
- 서버 재시작 시 데이터 복구 가능 (파일 백업)

## API 엔드포인트

### 1. 동화책 생성
```
POST /storybook/create
Content-Type: multipart/form-data

Body:
  - title: string (optional, default: "새로운 동화책")
  - stories: string[] (각 페이지 텍스트)
  - images: File[] (각 페이지 이미지, stories와 순서 매칭)

Response: 201 Created
{
  "id": "uuid",
  "title": "동화책 제목",
  "cover_image": "/data/image/uuid/cover.png",
  "status": "success",
  "pages": [...],
  "created_at": "2025-10-21T12:00:00"
}
```

### 2. 전체 동화책 목록 조회
```
GET /storybook/books

Response: 200 OK
{
  "books": [
    {
      "id": "uuid",
      "title": "동화책 제목",
      "cover_image": "/data/image/uuid/cover.png",
      "status": "success"
    }
  ]
}
```

### 3. 특정 동화책 상세 조회
```
GET /storybook/books/{book_id}

Response: 200 OK
{
  "id": "uuid",
  "title": "동화책 제목",
  "cover_image": "/data/image/uuid/cover.png",
  "status": "success",
  "pages": [
    {
      "id": "page-uuid",
      "index": 1,
      "background_image": "/data/image/uuid/page-uuid.png",
      "dialogues": [
        {
          "id": "dialogue-uuid",
          "index": 1,
          "text": "대사 텍스트",
          "part_audio_url": "/data/sound/batch-uuid/dialogue-uuid.mp3"
        }
      ]
    }
  ],
  "created_at": "2025-10-21T12:00:00"
}
```

### 4. 동화책 삭제
```
DELETE /storybook/books/{book_id}

Response: 200 OK
{
  "success": true,
  "message": "Book deleted successfully",
  "book_id": "uuid"
}
```

### 5. 디버그 엔드포인트

**캐시 통계 조회:**
```
GET /storybook/debug/cache-stats

Response:
{
  "cached_books": 10,
  "book_ids": ["uuid1", "uuid2", ...]
}
```

**캐시 재로드:**
```
POST /storybook/debug/refresh-cache

Response:
{
  "success": true,
  "message": "Cache refreshed",
  "stats": {...}
}
```

## 파일 저장 구조

```
/app/data/
├── book/
│   └── {book_id}/
│       └── metadata.json          # Book 전체 데이터 (JSON)
├── image/
│   └── {book_id}/
│       ├── {page_id}.png          # 각 페이지 배경 이미지
│       └── ...
└── sound/                          # TTS API와 공유
    └── {batch_id}/
        └── {dialogue_id}.mp3       # TTS 생성 오디오
```

## TTS 연동 플로우

1. 사용자가 `POST /storybook/create` 요청 (stories + images)
2. `BookService`가 이미지 저장 (`FileManager`)
3. `BookService`가 TTS API 호출 (`POST http://tts-api:8000/tts/generate`)
   - Input: `stories = ["text1", "text2"]`
   - TTS Format: `{"texts": [["text1"], ["text2"]]}`
4. TTS API가 오디오 파일 생성 후 경로 반환
5. `BookService`가 Book 객체 조립 (Pages + Dialogues)
6. `InMemoryBookRepository`가 캐시 + 파일 저장

## 실행 방법

### Docker Compose (권장)

```bash
# 전체 서비스 시작
make up

# Storybook API만 재빌드
make rebuild storybook-api

# 로그 확인
docker logs -f storybook-fastapi
```

### 로컬 개발 (Python 환경)

```bash
cd src/storybook

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
export TTS_API_URL=http://localhost:8000

# FastAPI 실행
uvicorn main:app --reload --port 8001
```

## 환경 변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `TTS_API_URL` | TTS API 엔드포인트 | `http://tts-api:8000` |

## 의존성

- **fastapi**: 웹 프레임워크
- **pydantic**: 데이터 검증 및 모델
- **uvicorn**: ASGI 서버
- **httpx**: 비동기 HTTP 클라이언트 (TTS API 호출)
- **python-multipart**: multipart/form-data 처리
- **aiofiles**: 비동기 파일 I/O

## 추후 개선 사항

### DB 전환 (PostgreSQL/MongoDB)

현재는 파일 기반 저장이지만, Repository 패턴 덕분에 쉽게 DB로 전환 가능:

1. `DatabaseBookRepository` 구현 (`AbstractBookRepository` 상속)
2. `main.py`에서 의존성 교체:
   ```python
   # 기존
   file_repository = FileBookRepository()

   # 변경
   db_repository = DatabaseBookRepository(db_session)
   book_repository = InMemoryBookRepository(file_repository=db_repository)
   ```

### Redis 캐싱

인메모리 캐시를 Redis로 교체하여 여러 서버 간 캐시 공유:

```python
redis_repository = RedisBookRepository(redis_client)
book_repository = redis_repository  # 또는 계층화
```

### 비동기 작업 큐 (Celery)

TTS 생성을 백그라운드 작업으로 처리:
- Book 생성 시 `status='process'`로 즉시 반환
- Celery Worker가 TTS 생성 후 `status='success'` 업데이트

## 개발 팁

### API 문서 확인

FastAPI 자동 생성 문서:
- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`

### 로그 레벨 조정

`main.py`에서 로그 레벨 변경:
```python
logging.basicConfig(level=logging.DEBUG)  # 더 자세한 로그
```

### 테스트 요청 예시

```bash
# 동화책 생성 (curl)
curl -X POST "http://localhost:8001/storybook/create" \
  -F "title=테스트 동화책" \
  -F "stories=아침을 먹었다" \
  -F "stories=점심을 먹었다" \
  -F "images=@page1.png" \
  -F "images=@page2.png"

# 전체 목록 조회
curl http://localhost:8001/storybook/books

# 특정 동화책 조회
curl http://localhost:8001/storybook/books/{book_id}

# 동화책 삭제
curl -X DELETE http://localhost:8001/storybook/books/{book_id}
```

## 라이선스

MIT
