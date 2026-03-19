# Project Context

## 프로젝트 개요

로그인 없이 누구나 글을 쓰고 댓글을 달 수 있는 익명 게시판에서 출발하여,
현재 **회원가입/로그인 기반 인증 시스템**을 추가한 상태다.
로그인한 사용자만 게시글·댓글을 작성할 수 있고, 수정/삭제는 본인 소유만 가능하다.

## 기술 스택

| 구분 | 기술 |
|------|------|
| 웹 프레임워크 | Django 4.2 (라우팅·템플릿·메시지·세션만 사용, ORM 미사용) |
| DB ORM | SQLAlchemy 2.0 |
| DB | PostgreSQL (Docker 컨테이너) |
| 프론트엔드 | Bootstrap 4, Summernote 에디터, Chart.js 4 (CDN) |
| 환경변수 | python-dotenv (.env 파일) |
| Python | 3.11 |
| 비밀번호 해시 | Argon2 (`argon2-cffi`) |
| 세션 | Django signed_cookies 백엔드 (DB 불필요) |
| 테스트 | pytest + pytest-django, SQLite in-memory |
| 외부 데이터 | `requests` (Naver Finance API), `yfinance` (미국 주식) |

## 설계 의도

- **Django ORM 비활성화**: `DATABASES = {}` 설정. Django는 URL 라우팅·템플릿·메시지·세션 역할만 담당하고, DB 접근은 전적으로 SQLAlchemy로 처리한다.
- **signed_cookies 세션**: DB 없이 동작하는 세션 백엔드. 페이로드: `user_id`, `user_nickname`, `user_email`. 유지 시간 3시간.
- **Argon2 비밀번호 해시**: 2015 PHC 우승 알고리즘. `PASSWORD_HASHERS` 설정으로 기존 `make_password`/`check_password` API 그대로 사용.
- **DB 레벨 페이지네이션**: 커스텀 `PageObj` 클래스 + SQLAlchemy `offset/limit`.
- **세션 안전성**: 모든 뷰에서 `with get_db() as db:` 컨텍스트 매니저로 commit·rollback·close 자동 처리.

## 현재 브랜치 및 작업 상태

- **브랜치**: `feature/stock-viewer`
- **상태**: 주식조회 기능 구현 완료 + 버그 수정 진행 중
- **main 병합**: 미완료 (사용자 확인 후 진행)

## TDD 개발 방식

Red → Green → Refactor 사이클로 개발한다.

1. **Red**: 테스트 먼저 작성 → 실패 확인
2. **Green**: 테스트를 통과하는 최소 구현 작성
3. **Refactor**: 코드 정리 (테스트는 계속 통과 유지)

외부 API 테스트는 `unittest.mock.patch`로 `requests.get` / `yfinance.Ticker`를 모킹하여 실제 네트워크 없이 실행.

## URL 구조

```
GET  /                                          게시글 목록 (검색, 페이징)
GET  /post/create/                              게시글 작성 폼 (로그인 필요)
POST /post/create/                              게시글 저장
GET  /post/<id>/                                게시글 상세 + 댓글 목록
GET  /post/<id>/edit/                           게시글 수정 폼 (로그인 + 본인 필요)
POST /post/<id>/edit/                           게시글 수정 저장
POST /post/<id>/delete/                         게시글 삭제 (로그인 + 본인 필요)
POST /post/<id>/comment/create/                 댓글 작성 (로그인 필요)
GET  /post/<id>/comment/<cid>/edit/             댓글 수정 폼 (로그인 + 본인 필요)
POST /post/<id>/comment/<cid>/edit/             댓글 수정 저장
POST /post/<id>/comment/<cid>/delete/           댓글 삭제 (로그인 + 본인 필요)

GET  /accounts/signup/                          회원가입 폼
POST /accounts/signup/                          회원가입 처리
GET  /accounts/login/                           로그인 폼
POST /accounts/login/                           로그인 처리
POST /accounts/logout/                          로그아웃 (POST 전용, CSRF 보호)
GET  /accounts/find/                            비밀번호 찾기 이메일 입력
POST /accounts/find/                            재설정 링크 발송
GET  /accounts/reset-password/<token>/          새 비밀번호 입력 폼
POST /accounts/reset-password/<token>/          비밀번호 재설정 처리

GET  /stocks/                                   주식조회 검색 페이지
GET  /stocks/api/search/?q=<쿼리>              KR 종목 자동완성 JSON
GET  /stocks/api/quote/?market=KR&code=<코드>  한국 주식 시세·차트·뉴스 JSON
GET  /stocks/api/quote/?market=US&code=<티커>  미국 주식 시세·차트·뉴스 JSON
```

## DB 스키마

```
users:                  id, email(UNIQUE), password(Argon2), nickname(UNIQUE), name,
                        phone(nullable), is_active, last_login_at, created_at, updated_at
password_reset_tokens:  id, user_id(FK→users), token_hash(SHA-256), created_at, used
posts:                  id, title, content(HTML), author, view_count, created_at, updated_at,
                        user_id(FK→users) ← 신규
comments:               id, post_id(FK→posts), content, author, created_at, updated_at,
                        user_id(FK→users) ← 신규  /  password ← 제거
```

> **주의**: 기존 posts/comments 데이터를 전부 삭제한 후 `python manage.py init_db`를 실행해야 한다.

## 데이터 흐름

```
Browser → Django URL Router → View 함수
                                  ↓
                    accounts.decorators.login_required (보호된 뷰)
                                  ↓
                          get_db() 컨텍스트 매니저
                                  ↓
                         SQLAlchemy Session
                                  ↓
                         PostgreSQL (Docker)
```

## 주요 제약사항

- 게시글·댓글 작성자는 로그인 사용자의 닉네임이 자동 설정된다.
- 게시글 삭제 시 연결된 댓글은 cascade 삭제된다.
- Summernote 에디터로 작성된 게시글 본문은 HTML로 저장되며, 템플릿에서 `|safe` 필터로 렌더링한다.
- 조회수는 상세 페이지 진입 시마다 1씩 증가한다.
- 이메일 발송: DEBUG=True 시 터미널 출력, DEBUG=False 시 Gmail SMTP.

## 보안 처리 요약

| 항목 | 처리 방식 |
|---|---|
| 이미 로그인한 사용자 login/signup 접근 | `board:post_list`로 redirect |
| 로그아웃 | POST 전용 (GET 로그아웃은 CSRF 취약점) |
| 비밀번호 복잡도 | 최소 8자, 영문+숫자 조합 |
| 비밀번호 찾기 이메일 | 존재 여부와 무관하게 동일 메시지 (사용자 열거 방지) |
| `?next=` redirect | 내부 URL(`/`로 시작)만 허용 |
| 만료 토큰 정리 | 새 토큰 발급 시 기존 미사용 토큰 모두 `used=True` |

## 테스트

```bash
pytest tests/ -v
# 53/53 통과 (기존 44 + 주식조회 9)
```

테스트 전략:
- SQLite in-memory + savepoint(중첩 트랜잭션) 격리
- `make_mock_get_db(db_session)`: views의 `get_db`를 테스트 세션으로 대체
- signed_cookies 세션: `client.cookies[SESSION_COOKIE_NAME] = session.session_key` 직접 설정

## 실행 방법

```bash
# 패키지 설치 (최초 1회)
pip install -r requirements.txt

# PostgreSQL 컨테이너 시작
docker-compose up -d

# DB 초기화 (기존 데이터 삭제 후 실행)
python manage.py init_db

# 개발 서버
python manage.py runserver
```

## 주식조회 버그 수정 이력 (feature/stock-viewer)

### 수정 1 — 한국 종목 차트 조회 안 됨
- **원인**: Naver Chart API(`/chart/domestic/item/{code}/day`)가 JSON 배열을 직접 반환하는데,
  코드가 `.get('result', {}).get('itemChartPrices', [])` 형태로 파싱해 항상 빈 배열 반환
- **수정**: `items = chart_resp.json()` 으로 직접 파싱
- **추가**: `startDateTime` / `endDateTime` 파라미터 추가 → 3개월치(약 60거래일) 조회 가능

### 수정 2 — 한국 종목 뉴스 노출 안 됨
- **원인**: `https://m.stock.naver.com/api/stock/{code}/news` 엔드포인트가 404 반환 (API 폐기)
- **수정**: `https://finance.naver.com/item/news_news.naver?code={code}` HTML 스크래핑으로 대체
  - `beautifulsoup4` 추가 (`requirements.txt`)
  - EUC-KR 디코딩 후 `<table class="type5">` 파싱
  - URL은 `https://finance.naver.com` + relative href 조합

### 수정 3 — 자동완성 방향키 선택 불가
- **원인**: 자동완성 항목을 마우스 클릭으로만 선택 가능, 키보드 지원 없음
- **수정**: `ArrowDown` / `ArrowUp` 으로 항목 이동, `Enter`로 선택, `Escape`로 목록 닫기
  - 활성 항목에 Bootstrap `.active` 클래스로 하이라이트

### 수정 4 — 미국 종목 뉴스 노출 안 됨
- **원인**: yfinance 0.2.x 업데이트 이후 뉴스 구조 변경
  - 구버전: `item.title` / `item.link` / `item.publisher`
  - 신버전: `item['content'].title` / `item['content'].canonicalUrl.url` / `item['content'].provider.displayName`
- **수정**: `content` 키 우선 파싱, 없으면 구버전 구조 fallback

## 남은 작업

- [ ] `main` 브랜치 병합 (사용자 확인 후)
- [ ] 운영 환경 `.env`에 `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` 추가 (Gmail 앱 비밀번호)
- [ ] PostgreSQL의 기존 posts/comments 테이블 DROP 후 `init_db` 실행
- [ ] `feature/stock-viewer` → `main` 병합 (사용자 확인 후)
