.PHONY: up down logs build rebuild clean help

# Docker Compose 설정
COMPOSE_FILE = docker-compose.yml
COMPOSE = docker compose -f $(COMPOSE_FILE)

# 기본 타겟
.DEFAULT_GOAL := help

## up: 모든 서비스 시작 (detached mode)
up:
	$(COMPOSE) up -d

## down: 모든 서비스 중지 및 볼륨 삭제
down:
	$(COMPOSE) down -v

## logs: 모든 서비스 로그 출력 (실시간)
logs:
	$(COMPOSE) logs -f

## build: 특정 서비스 빌드 (사용법: make build SERVICE=nginx)
build:
	@if [ -z "$(SERVICE)" ]; then \
		echo "Error: SERVICE 파라미터가 필요합니다."; \
		echo "사용법: make build SERVICE=서비스명"; \
		echo "예시: make build SERVICE=nginx"; \
		exit 1; \
	fi
	$(COMPOSE) build $(SERVICE)

## rebuild: 특정 서비스 재빌드 및 재시작 (사용법: make rebuild SERVICE=nginx)
rebuild:
	@if [ -z "$(SERVICE)" ]; then \
		echo "Error: SERVICE 파라미터가 필요합니다."; \
		echo "사용법: make rebuild SERVICE=서비스명"; \
		echo "예시: make rebuild SERVICE=nginx"; \
		exit 1; \
	fi
	$(COMPOSE) up -d --build $(SERVICE)

## build-all: 모든 서비스 빌드
build-all:
	$(COMPOSE) build

## restart: 모든 서비스 재시작
restart:
	$(COMPOSE) restart

## stop: 모든 서비스 중지 (볼륨 유지)
stop:
	$(COMPOSE) stop

## ps: 실행 중인 컨테이너 확인
ps:
	$(COMPOSE) ps

## clean: 중지된 컨테이너, 네트워크, 볼륨, 이미지 정리
clean:
	$(COMPOSE) down -v --rmi all --remove-orphans

## help: Makefile 명령어 도움말
help:
	@echo "==================================================="
	@echo "  MoriAI Docker Compose Makefile"
	@echo "==================================================="
	@echo ""
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/## /  /'
	@echo ""
	@echo "서비스 목록:"
	@echo "  - tts-api"
	@echo "  - frontend-builder"
	@echo "  - nginx"
	@echo ""
