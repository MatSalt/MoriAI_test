# Storybook API Architecture

## 📐 3계층 아키텍처 (3-Tier Architecture)

Storybook API는 **프로덕션급 3계층 아키텍처**를 사용하여 명확한 책임 분리와 확장 가능성을 제공합니다.

```
┌─────────────────────────────────────────────────────────────┐
│                   Presentation Layer                         │
│                     (FastAPI Endpoints)                      │
│                        main.py                               │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Business Layer                            │
│                      BookService                             │
│              (비즈니스 로직 조율자)                              │
│   ┌──────────────────┐     ┌────────────────────┐           │
│   │  TTS API 연동    │     │  복잡한 로직 처리   │           │
│   └──────────────────┘     └────────────────────┘           │
└──────────┬───────────────────────────┬────────────────────┘
           │                           │
           ▼                           ▼
┌──────────────────────┐    ┌──────────────────────────┐
│   Data Layer         │    │   Storage Layer          │
│  BookRepository      │    │  StorageService          │
│  (구조화된 데이터)     │    │  (비구조화된 파일)        │
│                      │    │                          │
│  - metadata.json     │    │  - 이미지 파일            │
│  - DB (향후)         │    │  - 오디오 파일            │
└──────────┬───────────┘    └──────────┬───────────────┘
           │                           │
           ▼                           ▼
      ┌─────────┐              ┌──────────────┐
      │  JSON   │              │ File System  │
      │  Files  │              │ (S3/GCS 향후)│
      └─────────┘              └──────────────┘
```

---

## 🎯 계층별 책임 (Separation of Concerns)

### 1️⃣ **Repository Layer** (데이터 계층)

**책임**: Book 엔티티의 **구조화된 데이터** 영속성 관리

```python
class AbstractBookRepository(ABC):
    async def create(self, book: Book) -> Book
    async def get(self, book_id: str) -> Optional[Book]
    async def get_all(self) -> List[Book]
    async def update(self, book_id: str, book: Book) -> Book
    async def delete(self, book_id: str) -> bool
```

**구현체**:
- `FileBookRepository`: JSON 파일 기반 (현재)
- `PostgreSQLBookRepository`: PostgreSQL (향후)
- `MongoDBBookRepository`: MongoDB (향후)

**관리 대상**:
- ✅ Book 메타데이터 (id, title, status, created_at)
- ✅ Page 구조 (index, dialogues)
- ✅ 이미지/오디오 **URL 참조** (실제 파일 X)

**파일 구조**:
```
./data/book/
└── {book_id}/
    └── metadata.json    # Book 전체 데이터
```

---

### 2️⃣ **Storage Layer** (스토리지 계층)

**책임**: **비구조화된 파일 리소스** 관리

```python
class AbstractStorageService(ABC):
    async def upload_image(file, book_id, filename) -> str
    async def delete_image(image_url: str) -> bool
    async def delete_book_assets(book: Book) -> bool
```

**구현체**:
- `LocalStorageService`: 로컬 파일 시스템 (현재)
- `S3StorageService`: AWS S3 (향후)
- `GCSStorageService`: Google Cloud Storage (향후)

**관리 대상**:
- ✅ 이미지 파일 (.png, .jpg 등)
- ✅ 오디오 파일 (.mp3, .wav 등)
- ✅ 영상 파일 (.mp4 등 - 향후)

**파일 구조**:
```
./data/image/
└── {book_id}/
    ├── {page_id_1}.png
    ├── {page_id_2}.png
    └── ...
```

---

### 3️⃣ **Service Layer** (비즈니스 계층)

**책임**: 복잡한 비즈니스 로직 **조율 (Orchestration)**

```python
class BookService:
    def __init__(
        self,
        storage_service: AbstractStorageService,
        tts_api_url: str
    )

    async def create_book_with_tts(...) -> Book
    async def delete_book_assets(book: Book) -> bool
```

**역할**:
- ✅ Repository + Storage 조합
- ✅ TTS API 연동
- ✅ 복잡한 비즈니스 규칙 처리
- ✅ 트랜잭션 관리

---

## 🔄 데이터 흐름 (Data Flow)

### **CREATE: 동화책 생성**

```
1. [API] POST /storybook/create
   ├─ stories: ["텍스트1", "텍스트2"]
   └─ images: [file1, file2]
       │
       ▼
2. [BookService] create_book_with_tts()
   │
   ├─→ (a) StorageService.upload_image()
   │   └─→ 📁 ./data/image/{book_id}/{page_id}.png
   │   └─→ 반환: "/data/image/{book_id}/{page_id}.png"
   │
   ├─→ (b) TTS API 호출
   │   └─→ 반환: "/data/sound/batch-id/audio.mp3"
   │
   ├─→ (c) Book 객체 조립
   │   └─→ Book {
   │          id: "book-123",
   │          pages: [
   │            {
   │              background_image: "/data/image/...",  ← URL만!
   │              dialogues: [{part_audio_url: "/data/sound/..."}]
   │            }
   │          ]
   │       }
   │
   └─→ (d) BookRepository.create(book)
       └─→ 📄 ./data/book/{book_id}/metadata.json

✅ 결과: 메타데이터(JSON) + 파일(이미지) 분리 저장
```

---

### **DELETE: 동화책 삭제**

```
1. [API] DELETE /storybook/books/{book_id}
   │
   ├─→ (a) BookRepository.get(book_id)
   │   └─→ Book 객체 조회 (URL 정보 포함)
   │
   ├─→ (b) BookService.delete_book_assets(book)
   │   └─→ StorageService.delete_book_assets(book)
   │       ├─→ 📁 page1.png 삭제
   │       ├─→ 📁 page2.png 삭제
   │       └─→ 📁 ...
   │
   └─→ (c) BookRepository.delete(book_id)
       └─→ 📄 metadata.json 삭제

✅ 결과: 파일 먼저 삭제 → 메타데이터 삭제 (안전한 순서)
```

---

## 🎨 설계 원칙

### **1. 단일 책임 원칙 (Single Responsibility Principle)**

```
Repository  → "Book 데이터는 어디에 저장되어 있는가?"
Storage     → "파일은 어디에 저장되어 있는가?"
Service     → "Book 생성/삭제 로직은 어떻게 되는가?"
```

### **2. 의존성 역전 원칙 (Dependency Inversion Principle)**

```python
# Service는 추상화에 의존
class BookService:
    def __init__(self, storage: AbstractStorageService):
        self.storage = storage  # 구현체가 아닌 인터페이스!

# 주입 (Dependency Injection)
book_service = BookService(
    storage_service=LocalStorageService()  # 쉽게 교체 가능!
)
```

### **3. 개방-폐쇄 원칙 (Open-Closed Principle)**

```python
# 확장에는 열려있고 (새로운 Storage 추가)
class S3StorageService(AbstractStorageService):
    async def upload_image(...): ...

# 수정에는 닫혀있음 (BookService 변경 불필요)
book_service = BookService(
    storage_service=S3StorageService()  # 코드 변경 없이 교체!
)
```

---

## 🚀 확장 시나리오

### **시나리오 1: S3로 전환**

**Before (로컬)**:
```python
storage = LocalStorageService(image_data_dir="./data/image")
```

**After (S3)**:
```python
# storage/s3_storage.py 추가
class S3StorageService(AbstractStorageService):
    def __init__(self, bucket_name, region):
        self.s3_client = boto3.client('s3', region_name=region)
        self.bucket = bucket_name

    async def upload_image(self, file, book_id, filename) -> str:
        key = f"{book_id}/{filename}"
        await self.s3_client.upload_fileobj(file.file, self.bucket, key)
        return f"https://{self.bucket}.s3.amazonaws.com/{key}"

# main.py - 한 줄만 변경!
storage = S3StorageService(bucket_name="my-books", region="us-east-1")
```

**변경 범위**:
- ✅ `storage/s3_storage.py` 추가
- ✅ `main.py` 1줄 변경
- ❌ BookService: 변경 없음
- ❌ Repository: 변경 없음
- ❌ API 엔드포인트: 변경 없음

---

### **시나리오 2: 이미지 최적화/CDN**

```python
class CDNStorageService(AbstractStorageService):
    def __init__(self, s3_service, cdn_url):
        self.s3 = s3_service
        self.cdn_url = cdn_url

    async def upload_image(self, file, book_id, filename) -> str:
        # 1. 리사이징
        optimized = await resize_image(file, width=800)

        # 2. S3 업로드
        s3_url = await self.s3.upload_image(optimized, book_id, filename)

        # 3. CDN URL 반환
        return f"{self.cdn_url}/{book_id}/{filename}"
```

---

### **시나리오 3: PostgreSQL 전환**

```python
# repositories/postgres_repository.py
class PostgreSQLBookRepository(AbstractBookRepository):
    def __init__(self, connection_string):
        self.db = create_engine(connection_string)

    async def create(self, book: Book) -> Book:
        async with self.db.begin() as conn:
            await conn.execute(
                "INSERT INTO books (id, title, ...) VALUES (...)"
            )
        return book

    async def delete(self, book_id: str) -> bool:
        async with self.db.begin() as conn:
            await conn.execute("DELETE FROM books WHERE id = ?", book_id)
        return True

# main.py
book_repository = PostgreSQLBookRepository(
    connection_string="postgresql://..."
)
```

---

## 🧪 테스트 전략

### **계층별 독립 테스트**

```python
# test_storage.py - Storage만 테스트
async def test_upload_image(storage_service):
    url = await storage_service.upload_image(file, "book-1", "page.png")
    assert await storage_service.image_exists(url)

# test_repositories.py - Repository만 테스트
async def test_create_book(book_repository):
    book = await book_repository.create(Book(...))
    assert book.id is not None

# test_services.py - Service 테스트 (모킹 사용)
async def test_create_book_with_tts(book_service, mock_storage, mock_tts):
    book = await book_service.create_book_with_tts(...)
    mock_storage.upload_image.assert_called()
    mock_tts.generate.assert_called()
```

---

## 📊 비교표

| 항목 | 이전 (Repository 통합) | 현재 (3계층 분리) |
|------|---------------------|-----------------|
| **Repository 책임** | 메타데이터 + 파일 | 메타데이터만 |
| **파일 관리** | Repository | StorageService |
| **S3 전환** | Repository 전체 수정 | Storage만 교체 |
| **테스트** | Repository + 파일 모킹 | 각 계층 독립 테스트 |
| **확장성** | 낮음 | 높음 |
| **복잡도** | 낮음 (단순) | 중간 (구조화) |
| **실무 적합성** | MVP/프로토타입 | 프로덕션 |

---

## 💡 Key Takeaways

1. **Repository ≠ Storage**
   - Repository: 구조화된 데이터 (Book 엔티티)
   - Storage: 비구조화된 파일 (이미지, 오디오)

2. **URL은 참조(Reference)**
   - Book은 이미지 파일을 **소유하지 않음**
   - URL로 **참조**만 함

3. **Service는 Orchestrator**
   - Repository와 Storage를 **조율**
   - 복잡한 비즈니스 로직 처리

4. **확장성 = 교체 가능성**
   - 추상 인터페이스 사용
   - Dependency Injection
   - 한 계층 변경이 다른 계층에 영향 없음

---

## 📚 참고 자료

- [Clean Architecture (Robert C. Martin)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)
- [Dependency Injection](https://en.wikipedia.org/wiki/Dependency_injection)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
