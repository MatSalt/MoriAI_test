import os
from typing import Union
import httpx

from fastapi import FastAPI, HTTPException

app = FastAPI()

# TTS API URL 환경 변수
TTS_API_URL = os.getenv("TTS_API_URL", "http://tts-api:8000")


@app.get("/health")
async def health_check():
    return "ok"


@app.get("/")
async def read_root():
    return {"Hello": "World from Storybook"}


@app.get("/test-tts-connection")
async def test_tts_connection():
    """TTS API와의 연결 테스트"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # TTS health 체크
            health_response = await client.get(f"{TTS_API_URL}/health")

            # TTS root endpoint 호출
            root_response = await client.get(f"{TTS_API_URL}/")

            return {
                "status": "success",
                "tts_api_url": TTS_API_URL,
                "health_check": {
                    "status_code": health_response.status_code,
                    "response": health_response.text
                },
                "root_endpoint": {
                    "status_code": root_response.status_code,
                    "response": root_response.json()
                },
                "message": "TTS API 연결 성공!"
            }
    except httpx.ConnectError as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "message": f"TTS API 연결 실패: {TTS_API_URL}",
                "error": str(e),
                "help": "TTS 컨테이너가 실행 중인지 확인하세요"
            }
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail={
                "status": "error",
                "message": "TTS API 응답 시간 초과",
                "tts_api_url": TTS_API_URL
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "예상치 못한 오류 발생",
                "error": str(e)
            }
        )


@app.get("/call-tts/{item_id}")
async def call_tts_item(item_id: int):
    """TTS API의 items 엔드포인트 호출 예시"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{TTS_API_URL}/items/{item_id}")
            return {
                "status": "success",
                "tts_response": response.json(),
                "called_url": f"{TTS_API_URL}/items/{item_id}"
            }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": str(e)}
        )


@app.get("/items/{item_id}")
async def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}
