# Nginx Static File Access Issue - 트러블슈팅 문서

## 문제 상황

브라우저에서 `https://localhost/data/image/{book_id}/{filename}.png`로 접근 시 **404 Not Found** 에러 발생

### 환경
- Docker Compose 기반 Nginx 컨테이너
- 볼륨 마운팅: `./data:/data:ro`
- 파일 실제 존재 여부: ✅ 확인됨
- Nginx 컨테이너 내부 파일 존재: ✅ 확인됨

## 원인 분석

### 1. Nginx Location 우선순위 문제

#### 기존 설정 (문제 있음)
```nginx
# Static data folder access
location /data/ {
    alias /data/;
    autoindex on;
    add_header Cache-Control "no-cache";
}

# Cache static assets
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

#### 문제점
Nginx의 location 우선순위 규칙:
1. **Exact match** (`=`)
2. **Preferential prefix** (`^~`)
3. **Regular expression** (`~`, `~*`) ⬅️ **이것이 우선!**
4. **Prefix match** (단순 `/data/`)

**결과:**
- `/data/image/xxx.png` 요청 시
- 정규식 location `~* \.(png|...)$`이 먼저 매칭됨
- `root /usr/share/nginx/html`에서 파일 검색
- `/usr/share/nginx/html/data/image/xxx.png` 경로에서 찾으려 시도 → **404**

#### Nginx 에러 로그
```
[error] open() "/usr/share/nginx/html/data/image/6ffcffde-a6c1-4a9a-9292-f78f6d9b86e1/0_page_1.png"
failed (2: No such file or directory)
```

### 2. HTTP → HTTPS 리다이렉트 포트 불일치

#### 기존 설정 (문제 있음)
```nginx
server {
    listen 80;
    server_name localhost;
    return 301 https://$server_name:3443$request_uri;  # ❌ 잘못된 포트
}

server {
    listen 443 ssl;  # 실제 HTTPS 포트는 443
    ...
}
```

#### 문제점
- HTTP(80) → HTTPS(3443)으로 리다이렉트
- 실제 HTTPS는 443 포트에서 리스닝
- 결과: 리다이렉트 후 연결 실패 가능

## 해결 방안

### 1. Location 우선순위 제어 (`^~` modifier 사용)

#### 수정된 설정
```nginx
# Static data folder access (use ^~ to prevent regex matching)
location ^~ /data/ {
    alias /data/;
    autoindex on;
    autoindex_exact_size off;
    autoindex_localtime on;
    add_header Cache-Control "no-cache";
}

# Cache static assets for app files
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
    root /usr/share/nginx/html;
    expires 1y;
    add_header Cache-Control "public, immutable";
}

# React SPA routing
location / {
    try_files $uri $uri/ /index.html;
}
```

#### 핵심 변경사항
- `location /data/` → `location ^~ /data/`
- `^~` modifier: **"정규식보다 우선순위가 높은 prefix match"**
- 이제 `/data/`로 시작하는 모든 요청은 정규식 location을 거치지 않고 바로 처리됨

### 2. HTTP 리다이렉트 포트 수정

#### 수정된 설정
```nginx
server {
    listen 80;
    server_name localhost;
    return 301 https://$server_name$request_uri;  # ✅ 포트 번호 제거
}
```

## 적용 방법

### 1. 설정 파일 수정
```bash
# docker/nginx/nginx.conf 수정
vim docker/nginx/nginx.conf
```

### 2. Docker 이미지 재빌드 및 재시작
```bash
# Nginx 이미지 재빌드 (설정 파일이 이미지에 포함되므로 필수)
docker-compose build nginx

# Nginx 컨테이너 재시작
docker-compose up -d nginx
```

**주의:** `docker restart nginx-server`만으로는 설정 변경이 적용되지 않습니다!
설정 파일이 Docker 빌드 시 이미지에 복사되므로 **반드시 재빌드 필요**

### 3. 테스트
```bash
# 파일 접근 테스트
curl -k -I https://localhost/data/image/{book_id}/{filename}.png

# 예상 결과
HTTP/1.1 200 OK
Content-Type: image/png
Content-Length: 2419800
```

## 검증 체크리스트

- [ ] 파일이 호스트에 존재하는가? (`ls ./data/image/`)
- [ ] Docker 볼륨이 올바르게 마운트되었는가? (`docker exec nginx-server ls /data/`)
- [ ] Nginx 설정이 올바른가? (`docker exec nginx-server cat /etc/nginx/conf.d/default.conf`)
- [ ] Nginx 설정 문법 검사 통과? (`docker exec nginx-server nginx -t`)
- [ ] Docker 이미지 재빌드 완료? (`docker-compose build nginx`)
- [ ] 브라우저/curl 테스트 성공? (`curl -k -I https://localhost/data/...`)

## Nginx Location 우선순위 참고

| Modifier | 설명 | 우선순위 | 예시 |
|----------|------|---------|------|
| `=` | Exact match | 1 (최우선) | `location = /exact` |
| `^~` | Preferential prefix | 2 | `location ^~ /data/` |
| `~`, `~*` | Regular expression | 3 | `location ~* \.png$` |
| (없음) | Prefix match | 4 (최하위) | `location /` |

**핵심:** 정규식 location은 prefix location보다 우선순위가 높으므로,
특정 경로를 정규식에서 제외하려면 `^~`를 사용해야 합니다.

## 관련 파일

- Nginx 설정: `docker/nginx/nginx.conf`
- Docker Compose: `docker-compose.yml`
- Storage Service: `src/storybook/storage/local_storage.py`

## 참고 자료

- [Nginx Location Directive Documentation](http://nginx.org/en/docs/http/ngx_http_core_module.html#location)
- [Nginx Location Priority Explanation](https://nginx.org/en/docs/http/request_processing.html)
