FROM python:3.12-alpine

WORKDIR /app

# wget 설치 (헬스체크용)
RUN apk add --no-cache wget

# requirements.txt 복사 및 의존성 설치
COPY src/storybook/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 포트 노출
EXPOSE 8001

# FastAPI 앱 실행
CMD ["uvicorn", "storybook.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
