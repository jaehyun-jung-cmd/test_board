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
templates/
  base.html      Bootstrap 4 + Summernote CDN 포함
  board/         list, detail, create, edit, comment_edit 템플릿
```

## Key Patterns

**DB 세션**: 모든 뷰에서 `with get_db() as db:` 컨텍스트 매니저 사용. commit/rollback/close 자동 처리.

**페이지네이션**: Django Paginator 대신 커스텀 `PageObj` 클래스 (`views.py`) 사용. SQLAlchemy `.offset().limit()`으로 실제 DB 레벨 페이징.

**메시지**: `django.contrib.messages` + `CookieStorage` 사용 (세션/DB 불필요).

**댓글 비밀번호**: `django.contrib.auth.hashers.make_password` / `check_password`로 해싱 (auth 앱 설치 불필요).

**에디터**: Summernote (Bootstrap 4 기반, CDN). create/edit 템플릿의 `#content` textarea에 초기화됨.

## DB Schema

```
posts:    id, title, content(HTML), author, view_count, created_at, updated_at
comments: id, post_id(FK→posts), content, author, password(hashed), created_at, updated_at
```

## Environment

`.env` 파일로 설정 관리. `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` 환경변수로 DB 연결.

## GitHub 업로드 금지 파일

다음 파일들은 보안상 GitHub에 절대 업로드하지 않는다:

- `.env` — DB 접속 정보, 시크릿 키 등 민감한 환경변수
- `config/settings.py` — `SECRET_KEY`, `DEBUG`, DB 설정 포함 가능
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
