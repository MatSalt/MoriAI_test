# Storybook API Specification

## Overview
동화책 생성, 조회, 삭제를 위한 RESTful API 명세서입니다.
FastAPI 기반으로 구현되며, TTS API와 연동하여 오디오 생성을 지원합니다.

## Base URL
- Development: `http://localhost:8001`
- Production: `http://storybook-api:8001`

## Data Models

### Book
동화책 전체 데이터 구조

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | 동화책 고유 ID (자동 생성) |
| `coverImage` | String (URL) | Yes | 동화책 커버 이미지 URL |
| `title` | String | Yes | 동화책 제목 |
| `status` | Enum | Yes | 동화책 상태: `process`, `success`, `error` |
| `pages` | List[Page] | Yes | 동화책 페이지 리스트 |
| `createdAt` | DateTime | Yes | 생성 시간 (자동 생성) |

### Page
동화책 페이지 구조

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | 페이지 고유 ID (자동 생성) |
| `index` | Integer | Yes | 페이지 순서 (1부터 시작) |
| `backgroundImage` | String (URL) | Yes | 페이지 배경 이미지 URL |
| `dialogues` | List[Dialogue] | Yes | 대사 리스트 |

### Dialogue
페이지 내 대사 구조

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | 대사 고유 ID (자동 생성) |
| `index` | Integer | Yes | 대사 순서 (1부터 시작) |
| `text` | String | Yes | 대사 텍스트 |
| `partAudioUrl` | String (URL) | Yes | 대사 오디오 파일 URL |

## API Endpoints

---

### 1. 동화책 생성

새로운 동화책을 생성합니다. 이미지와 스토리를 기반으로 TTS 오디오를 생성하고 동화책 데이터를 구성합니다.

**Endpoint:** `POST /storybook/create`

**Content-Type:** `multipart/form-data`

#### Request Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `stories` | String[] | Yes | 각 페이지의 텍스트(스토리 내용) 배열 |
| `images` | File[] | Yes | 각 페이지의 이미지 파일 배열 (stories 순서와 매칭) |
| `title` | String | No | 동화책 제목 (미입력 시 자동 생성) |

#### Request Example

```javascript
const formData = new FormData();
formData.append('title', '우리집 동화책');
formData.append('stories', '낮잠을 잤다.');
formData.append('stories', '점심을 먹었다. 맛있었다.');
formData.append('stories', '저녁을 먹었다.');
formData.append('images', file1); // File object
formData.append('images', file2);
formData.append('images', file3);
```

#### Response

**Status Code:** `201 Created`

```json
{
  "id": "uuid-book-1234",
  "title": "우리집 동화책",
  "coverImage": "/data/image/uuid-book-1234/cover.png",
  "status": "success",
  "pages": [
    {
      "id": "uuid-page-1",
      "index": 1,
      "backgroundImage": "/data/image/uuid-book-1234/uuid-page-1.png",
      "dialogues": [
        {
          "id": "uuid-dialogue-1",
          "index": 1,
          "text": "낮잠을 잤다.",
          "partAudioUrl": "/data/sound/batch-uuid/uuid-dialogue-1.mp3"
        }
      ]
    }
  ],
  "createdAt": "2025-10-21T12:00:00"
}
```

**Status Code:** `500 Internal Server Error` (TTS 실패 시)

```json
{
  "detail": "TTS 생성 중 오류가 발생했습니다"
}
```

---

### 2. 전체 동화책 조회

모든 동화책의 목록을 조회합니다 (간략 정보).

**Endpoint:** `GET /storybook/books`

#### Response

**Status Code:** `200 OK`

```json
{
  "books": [
    {
      "id": "uuid-book-1234",
      "title": "우리집 동화책",
      "coverImage": "/data/image/uuid-book-1234/cover.png",
      "status": "success"
    },
    {
      "id": "uuid-book-5678",
      "title": "모험 이야기",
      "coverImage": "/data/image/uuid-book-5678/cover.png",
      "status": "process"
    }
  ]
}
```

---

### 3. 특정 동화책 상세 조회

특정 동화책의 전체 데이터를 조회합니다 (페이지, 대사 포함).

**Endpoint:** `GET /storybook/books/{book_id}`

#### Path Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `book_id` | UUID | Yes | 조회할 동화책 ID |

#### Response

**Status Code:** `200 OK`

```json
{
  "id": "uuid-book-1234",
  "coverImage": "/data/image/uuid-book-1234/cover.png",
  "title": "우리집 동화책",
  "status": "success",
  "pages": [
    {
      "id": "uuid-page-1",
      "index": 1,
      "backgroundImage": "/data/image/uuid-book-1234/uuid-page-1.png",
      "dialogues": [
        {
          "id": "uuid-dialogue-1",
          "index": 1,
          "text": "낮잠을 잤다.",
          "partAudioUrl": "/data/sound/batch-uuid/uuid-dialogue-1.mp3"
        }
      ]
    },
    {
      "id": "uuid-page-2",
      "index": 2,
      "backgroundImage": "/data/image/uuid-book-1234/uuid-page-2.png",
      "dialogues": []
    }
  ],
  "createdAt": "2025-10-21T12:00:00"
}
```

**Status Code:** `404 Not Found`

```json
{
  "detail": "Book not found"
}
```

---

### 4. 동화책 삭제

특정 동화책을 삭제합니다 (메타데이터, 이미지, 오디오 파일 포함).

**Endpoint:** `DELETE /storybook/books/{book_id}`

#### Path Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `book_id` | UUID | Yes | 삭제할 동화책 ID |

#### Response

**Status Code:** `200 OK`

```json
{
  "success": true,
  "message": "Book deleted successfully",
  "book_id": "uuid-book-1234"
}
```

**Status Code:** `404 Not Found`

```json
{
  "detail": "Book not found"
}
```

---

## Error Handling

### Common Error Response Format

```json
{
  "detail": "Error message description"
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | OK - 요청 성공 |
| 201 | Created - 리소스 생성 성공 |
| 400 | Bad Request - 잘못된 요청 파라미터 |
| 404 | Not Found - 리소스를 찾을 수 없음 |
| 500 | Internal Server Error - 서버 내부 오류 |
| 503 | Service Unavailable - TTS API 연결 실패 |

---

## File Storage Structure

```
/app/data/
├── book/
│   └── {book_id}/
│       └── metadata.json          # Book 전체 데이터
├── image/
│   └── {book_id}/
│       ├── cover.png               # 커버 이미지 (첫 페이지 이미지)
│       └── {page_id}.png           # 각 페이지 배경 이미지
└── sound/
    └── {batch_id}/
        └── {dialogue_id}.mp3       # TTS 생성 오디오 파일
```

---

## TTS Integration

### TTS API 호출 흐름

1. 사용자가 `POST /storybook/create` 요청
2. Storybook API가 stories 배열을 TTS API 형식으로 변환
3. `POST http://tts-api:8000/tts/generate` 호출
4. TTS API가 오디오 파일 생성 후 경로 반환
5. Storybook API가 반환된 경로를 `partAudioUrl`에 매핑

### TTS 요청 변환 예시

**Input (Storybook API 수신):**
```javascript
stories: ["낮잠을 잤다.", "점심을 먹었다. 맛있었다."]
```

**Output (TTS API 전송):**
```json
{
  "texts": [
    ["낮잠을 잤다."],
    ["점심을 먹었다. 맛있었다."]
  ]
}
```

---

## Notes

- **MVP 특성**: 인메모리 저장소 사용으로 서버 재시작 시 데이터 유실
- **파일 백업**: JSON 파일로 백업되어 있어 추후 복구 가능
- **비동기 처리**: TTS 생성은 비동기로 처리되며, 실패 시에도 Book 생성 (status='error')
- **Auto-generated IDs**: 모든 ID는 UUID v4로 자동 생성
- **Index 관리**: 페이지와 대사의 index는 1부터 시작
