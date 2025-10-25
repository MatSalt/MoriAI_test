FROM python:3.12-alpine

WORKDIR /app

# wget 설치 (헬스체크용)
RUN apk add --no-cache wget

# requirements.txt 복사 및 의존성 설치
COPY src/tts/requirements.txt /app/tts/requirements.txt
RUN pip install --no-cache-dir -r /app/tts/requirements.txt

# 소스 코드 복사 (Feature-First 구조)
COPY src/tts/main.py /app/tts/main.py
COPY src/tts/core /app/tts/core
COPY src/tts/shared /app/tts/shared
COPY src/tts/features /app/tts/features
COPY src/tts/src /app/tts/src

# 작업 디렉토리 설정
WORKDIR /app/tts

# 포트 노출
EXPOSE 8000

# FastAPI 앱 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
