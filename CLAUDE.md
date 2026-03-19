# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup & Run Commands

```bash
# 1. 가상 환경 생성 및 패키지 설치 (Windows)
setup.bat

# 또는 수동으로:
C:\Users\tjgud\AppData\Local\Programs\Python\Python311\python.exe -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 2. PostgreSQL 컨테이너 시작
docker-compose up -d

# 3. DB 테이블 생성 (최초 1회)
python manage.py init_db

# 4. 개발 서버 실행
python manage.py runserver

# 5. 테스트 실행
pytest
```

## Architecture

Django를 웹 프레임워크로만 사용하고, DB 작업은 SQLAlchemy로 처리하는 구조다. Django ORM은 비활성화(`DATABASES = {}`).

```
config/          Django 프로젝트 설정 (settings, urls, wsgi)
board/
  database.py    SQLAlchemy engine, SessionLocal, Base, get_db() 컨텍스트 매니저
  models.py      SQLAlchemy ORM 모델 (Post, Comment)
  views.py       뷰 함수 + PageObj 페이지네이션 헬퍼 클래스
  urls.py        URL 라우팅
  management/commands/init_db.py   테이블 생성 커맨드
accounts/
  models.py      SQLAlchemy ORM 모델 (User, PasswordResetToken)
  views.py       회원가입, 로그인, 로그아웃, 비밀번호 찾기/재설정
  decorators.py  login_required 데코레이터
  context_processors.py  current_user 전역 주입
  utils.py       토큰 생성, 만료 검사
  urls.py        accounts URL 라우팅
templates/
  base.html      Bootstrap 4 + Summernote CDN 포함
  board/         list, detail, create, edit, comment_edit 템플릿
  accounts/      signup, login, find_account, reset_password 템플릿
  includes/      alerts.html, pagination.html 공통 컴포넌트
tests/
  conftest.py    pytest fixtures (test_engine, db_session, logged_in_client 등)
  test_accounts/ 회원 인증 테스트 (모델, 뷰, 데코레이터)
  test_board/    게시글/댓글 뷰 테스트
```

## Key Patterns

**DB 세션**: 모든 뷰에서 `with get_db() as db:` 컨텍스트 매니저 사용. commit/rollback/close 자동 처리.

**페이지네이션**: Django Paginator 대신 커스텀 `PageObj` 클래스 (`views.py`) 사용. SQLAlchemy `.offset().limit()`으로 실제 DB 레벨 페이징.

**메시지**: `django.contrib.messages` + `CookieStorage` 사용 (세션/DB 불필요).

**세션**: `signed_cookies` 백엔드 (DB 불필요). 3시간 유지. 로그인 시 `user_id`, `user_nickname`, `user_email` 저장.

**인증**: `@login_required` 데코레이터 (`accounts/decorators.py`). 미로그인 시 `/accounts/login/?next=<원래경로>` 리디렉트. 게시글/댓글 작성·수정·삭제에 적용.

**비밀번호 해싱**: Argon2 (`argon2-cffi`). `django.contrib.auth.hashers.make_password` / `check_password` 사용.

**소유권 검사**: 게시글/댓글 수정·삭제 시 `post.user_id == session['user_id']` 확인. 댓글 비밀번호 인증 방식 제거.

**비밀번호 재설정**: `secrets.token_urlsafe(32)` raw 토큰 이메일 발송, SHA-256 해시를 DB 저장. 1시간 만료, `used` 플래그로 재사용 방지.

**전역 사용자 주입**: `accounts.context_processors.current_user` — 모든 템플릿에 `current_user` dict 주입 (`id`, `nickname`, `email`).

**에디터**: Summernote (Bootstrap 4 기반, CDN). create/edit 템플릿의 `#content` textarea에 초기화됨.

## DB Schema

```
users:                 id, email(UNIQUE), password, nickname(UNIQUE), name, phone,
                       is_active, last_login_at, created_at, updated_at
posts:                 id, title, content(HTML), author, view_count,
                       user_id(FK→users), created_at, updated_at
comments:              id, post_id(FK→posts), content, author,
                       user_id(FK→users), created_at, updated_at
password_reset_tokens: id, user_id(FK→users), token_hash(UNIQUE), created_at, used
```

## Testing

SQLite in-memory DB로 pytest 실행. PostgreSQL 없이 독립 실행 가능.

```bash
pytest                          # 전체 테스트 (44개)
pytest tests/test_accounts/     # 회원 인증 테스트
pytest tests/test_board/        # 게시판 테스트
pytest -v                       # 상세 출력
```

**테스트 격리**: 각 테스트는 `begin_nested()` (SAVEPOINT)로 격리. 테스트 종료 시 자동 롤백.

**세션 픽스처**: `signed_cookies` 백엔드 특성상 `session.save()` 후 `client.cookies[SESSION_COOKIE_NAME] = session.session_key` 직접 설정 필요.

## Environment

`.env` 파일로 설정 관리.

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `SECRET_KEY` | `django-insecure-fallback-key` | Django 시크릿 키 |
| `DEBUG` | `True` | 디버그 모드 |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | 허용 호스트 |
| `DB_HOST` | `localhost` | PostgreSQL 호스트 |
| `DB_PORT` | `5432` | PostgreSQL 포트 |
| `DB_NAME` | `bulletin_board` | DB 이름 |
| `DB_USER` | `postgres` | DB 사용자 |
| `DB_PASSWORD` | `password123` | DB 비밀번호 |
| `EMAIL_HOST_USER` | — | Gmail 계정 (운영 환경) |
| `EMAIL_HOST_PASSWORD` | — | Gmail 앱 비밀번호 (운영 환경) |

이메일: `DEBUG=True`이면 터미널 출력, `DEBUG=False`이면 Gmail SMTP 발송.

## GitHub 업로드 금지 파일

다음 파일들은 보안상 GitHub에 절대 업로드하지 않는다:

- `.env` — DB 접속 정보, 시크릿 키 등 민감한 환경변수
- `venv/` — 가상 환경 디렉토리
- `*.pem`, `*.key`, `*.crt` — SSL/TLS 인증서 및 개인 키
- `*.p12`, `*.pfx` — 인증서 번들
- `id_rsa`, `id_ed25519` 등 SSH 키 파일

`.gitignore`에 반드시 포함되어야 할 항목:

```
.env
venv/
*.pem
*.key
*.crt
*.p12
*.pfx
id_rsa
id_ed25519
```
