# BackgroundTasks와 UploadFile 처리 가이드

## 📌 문제 상황

FastAPI의 BackgroundTasks를 사용할 때 UploadFile을 그대로 전달하면 **파일 내용을 읽을 수 없는** 문제가 발생합니다.

## 🔍 UploadFile의 특성

### UploadFile은 스트림(Stream)

```python
from fastapi import UploadFile

async def endpoint(file: UploadFile = File(...)):
    # 첫 번째 읽기
    content = await file.read()  # ✅ 성공
    print(len(content))  # 예: 50000 bytes

    # 두 번째 읽기 (같은 파일)
    content2 = await file.read()  # ❌ 빈 데이터!
    print(len(content2))  # 0 bytes (이미 소진됨)
```

**핵심**:
- UploadFile은 네트워크에서 오는 데이터를 **한 번만** 읽을 수 있는 스트림
- 파일을 읽으면 "포인터"가 끝으로 이동
- 다시 읽으려면 `seek(0)`으로 되돌려야 함

---

## ⚠️ BackgroundTasks에서의 문제

### 문제 발생 메커니즘

```python
@app.post("/upload")
async def upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    # BackgroundTasks에 UploadFile 전달
    background_tasks.add_task(process_file, file)

    return {"status": "ok"}
    # ===== 응답 전송 =====

async def process_file(file: UploadFile):
    # ❌ 에러 또는 빈 데이터!
    content = await file.read()
```

**왜 작동하지 않는가?**

1. FastAPI는 응답 전송 후 **요청 컨텍스트를 정리**
2. UploadFile의 스트림도 **자동으로 닫힘** (close)
3. BackgroundTasks는 **응답 전송 후** 실행
4. BackgroundTasks 실행 시점에는 **이미 스트림이 닫힌 상태**
5. `await file.read()` → **IOError 또는 빈 데이터 (0 bytes)**

---

## ✅ 해결 방법

### 방법 1: 메모리에 미리 읽기 (추천)

```python
@app.post("/upload")
async def upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    # ✅ 응답 전송 전에 미리 읽어서 메모리에 저장
    file_data = {
        'filename': file.filename,
        'content': await file.read(),  # bytes 형태로 저장
        'content_type': file.content_type
    }

    # BackgroundTasks에 bytes 전달 (UploadFile 아님!)
    background_tasks.add_task(process_file_data, file_data)

    return {"status": "ok"}


async def process_file_data(file_data: dict):
    # ✅ bytes에서 UploadFile 재구성
    from io import BytesIO
    from fastapi import UploadFile

    file_obj = BytesIO(file_data['content'])
    upload_file = UploadFile(
        file=file_obj,
        filename=file_data['filename'],
        headers={'content-type': file_data['content_type']}
    )

    # 이제 정상 작동!
    content = await upload_file.read()
    print(f"Read {len(content)} bytes")
```

**장점**:
- ✅ 구현 간단
- ✅ 빠른 처리
- ✅ 추가 파일 관리 불필요

**단점**:
- ❌ 메모리 사용량 증가 (큰 파일 위험)

**적합한 경우**:
- 이미지 파일 (보통 수 MB 이하)
- 작은 파일 업로드

---

### 방법 2: 임시 파일 저장

```python
import tempfile
import shutil
import os

@app.post("/upload")
async def upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    # ✅ 임시 파일로 저장
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    shutil.copyfileobj(file.file, temp_file)
    temp_file.close()

    temp_info = {
        'path': temp_file.name,
        'filename': file.filename,
        'content_type': file.content_type
    }

    # BackgroundTasks에 파일 경로 전달
    background_tasks.add_task(process_temp_file, temp_info)

    return {"status": "ok"}


async def process_temp_file(temp_info: dict):
    try:
        # 임시 파일에서 UploadFile 재구성
        file_obj = open(temp_info['path'], 'rb')
        upload_file = UploadFile(
            file=file_obj,
            filename=temp_info['filename'],
            headers={'content-type': temp_info['content_type']}
        )

        # 파일 처리
        content = await upload_file.read()
        print(f"Read {len(content)} bytes")

    finally:
        # 임시 파일 정리
        try:
            os.unlink(temp_info['path'])
        except:
            pass
```

**장점**:
- ✅ 메모리 절약 (큰 파일에 유리)
- ✅ 디스크 기반 처리

**단점**:
- ❌ 디스크 I/O 발생
- ❌ 임시 파일 정리 필요
- ❌ 구현 복잡

**적합한 경우**:
- 대용량 파일 (100MB 이상)
- 영상 파일

---

## 📊 비교표

| 항목 | UploadFile 그대로 | 메모리 미리 읽기 | 임시 파일 |
|------|------------------|----------------|----------|
| **작동 여부** | ❌ 실패 | ✅ 성공 | ✅ 성공 |
| **구현 난이도** | ⭐ 쉬움 | ⭐⭐ 중간 | ⭐⭐⭐ 어려움 |
| **메모리 사용** | - | ⚠️ 높음 | ✅ 낮음 |
| **디스크 I/O** | - | ✅ 없음 | ⚠️ 있음 |
| **파일 정리** | - | ✅ 불필요 | ⚠️ 필요 |
| **적합한 파일** | - | 이미지 (< 10MB) | 영상 (> 100MB) |

---

## 🎯 Storybook API 적용

### 현재 상황

- **이미지 파일**: 보통 1-5MB
- **개수**: 페이지당 1개 (평균 10-20페이지)
- **총 용량**: 10-100MB

### 선택: 메모리에 미리 읽기 (방법 1)

**이유**:
- 이미지 파일 크기가 적당
- 구현 간단
- 디스크 I/O 불필요
- 임시 파일 관리 불필요

---

## 💻 실제 적용 코드

### main.py - create_book 엔드포인트

```python
from fastapi import BackgroundTasks, UploadFile, File, Form
from typing import List
from io import BytesIO

@app.post("/storybook/create")
async def create_book(
    background_tasks: BackgroundTasks,
    stories: List[str] = Form(...),
    images: List[UploadFile] = File(...),
    title: str = Form(default="새로운 동화책"),
):
    try:
        # 1. 입력 검증
        if len(stories) != len(images):
            raise HTTPException(status_code=400, ...)

        # 2. 빈 Book 생성
        book = Book(title=title, status="process", pages=[])
        await book_repository.create(book)

        # 3. ⭐ 이미지를 메모리에 미리 읽기
        images_data = []
        for image in images:
            content = await image.read()
            images_data.append({
                'filename': image.filename,
                'content': content,  # bytes
                'content_type': image.content_type
            })

        # 4. BackgroundTasks 등록 (bytes 전달)
        background_tasks.add_task(
            background_create_full_book,
            book_id=book.id,
            title=title,
            stories=stories,
            images_data=images_data  # ⭐ UploadFile이 아닌 bytes
        )

        # 5. 즉시 응답
        return BookDetailResponse(...)

    except Exception as e:
        logger.error(f"Failed to create book: {e}")
        raise HTTPException(status_code=500, ...)


async def background_create_full_book(
    book_id: str,
    title: str,
    stories: List[str],
    images_data: List[dict]  # bytes 형태
):
    try:
        # ✅ bytes → UploadFile 재구성
        upload_files = []
        for img_data in images_data:
            file_obj = BytesIO(img_data['content'])
            upload_file = UploadFile(
                file=file_obj,
                filename=img_data['filename'],
                headers={'content-type': img_data['content_type']}
            )
            upload_files.append(upload_file)

        # Book 생성 (기존 로직 재사용)
        book = await book_service.create_book_with_tts(
            title=title,
            stories=stories,
            images=upload_files,  # ✅ 재구성된 UploadFile
            book_id=book_id
        )

        # Repository 업데이트
        await book_repository.update(book_id, book)

    except Exception as e:
        logger.error(f"[Background] Failed: {e}")
        # error 상태로 변경
        book = await book_repository.get(book_id)
        if book:
            book.status = "error"
            await book_repository.update(book_id, book)
```

---

## 🚨 주의사항

1. **메모리 사용량 모니터링**
   - 동시 요청이 많으면 메모리 부족 가능
   - 필요 시 Semaphore로 동시 처리 제한

2. **대용량 파일 처리**
   - 영상 파일 등 대용량 파일은 임시 파일 방식 사용

3. **에러 처리**
   - bytes 변환 실패 시 적절한 에러 메시지

---

## 📚 참고 자료

- [FastAPI BackgroundTasks 공식 문서](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [Python Streams 개념](https://docs.python.org/3/library/io.html)
- [FastAPI UploadFile 구현](https://github.com/tiangolo/fastapi/blob/master/fastapi/datastructures.py#L81)
