# 게시판 (Django + SQLAlchemy)

Django를 웹 프레임워크로, SQLAlchemy를 ORM으로 사용하는 게시판 애플리케이션.
회원가입/로그인 기반 인증과 이메일 비밀번호 재설정 기능을 포함한다.

---

## 기술 스택

| 구분 | 기술 |
|---|---|
| 웹 프레임워크 | Django 4.2 |
| ORM | SQLAlchemy 2.0 |
| DB | PostgreSQL (Docker) |
| 비밀번호 해시 | Argon2 (`argon2-cffi`) |
| 세션 | Django signed_cookies (DB 불필요) |
| 에디터 | Summernote (Bootstrap 4, CDN) |
| 테스트 | pytest + pytest-django |

---

## 빠른 시작

### 1. 환경 설정

```bash
# 가상 환경 생성 및 패키지 설치
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

### 2. 환경변수 설정

프로젝트 루트에 `.env` 파일 생성:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
DB_HOST=localhost
DB_PORT=5432
DB_NAME=bulletin_board
DB_USER=postgres
DB_PASSWORD=password123
```

> 운영 환경에서 이메일 발송이 필요하면 아래 항목도 추가:
> ```env
> EMAIL_HOST_USER=your@gmail.com
> EMAIL_HOST_PASSWORD=gmail-app-password
> ```

### 3. PostgreSQL 컨테이너 시작

```bash
docker-compose up -d
```

### 4. DB 테이블 생성

```bash
python manage.py init_db
```

### 5. 개발 서버 실행

```bash
python manage.py runserver
```

브라우저에서 `http://localhost:8000` 접속.

---

## 프로젝트 구조

```
├── config/
│   ├── settings.py         Django 설정 (세션, Argon2, 이메일 등)
│   ├── urls.py             루트 URL 설정
│   └── wsgi.py
├── board/
│   ├── database.py         SQLAlchemy 엔진, 세션, get_db() 컨텍스트 매니저
│   ├── models.py           Post, Comment 모델 (user_id FK 포함)
│   ├── views.py            게시글/댓글 뷰 (@login_required 적용)
│   ├── urls.py             게시판 URL 라우팅
│   └── management/commands/init_db.py  DB 테이블 생성 커맨드
├── accounts/
│   ├── models.py           User, PasswordResetToken 모델
│   ├── views.py            회원가입, 로그인, 로그아웃, 비밀번호 찾기/재설정
│   ├── urls.py             /accounts/* URL 라우팅
│   ├── decorators.py       @login_required
│   ├── context_processors.py  current_user 전역 주입
│   └── utils.py            토큰 생성, 이메일 발송
├── templates/
│   ├── base.html           공통 레이아웃 (네비바 auth 링크 포함)
│   ├── includes/
│   │   ├── alerts.html     공통 flash 메시지
│   │   └── pagination.html 공통 페이지네이션
│   ├── board/              게시판 템플릿
│   └── accounts/           인증 관련 템플릿
├── tests/
│   ├── conftest.py         SQLite in-memory 픽스처, mock_get_db
│   ├── test_accounts/      인증 관련 테스트
│   └── test_board/         게시판 보호 및 소유권 테스트
├── .env                    환경변수 (Git 제외)
├── requirements.txt
├── pytest.ini
└── docker-compose.yml
```

---

## DB 스키마

```
users
  id, email(UNIQUE), password(Argon2), nickname(UNIQUE), name,
  phone(nullable), is_active, last_login_at, created_at, updated_at

password_reset_tokens
  id, user_id(FK→users), token_hash(SHA-256, UNIQUE), created_at, used

posts
  id, title, content(HTML), author, view_count,
  created_at, updated_at, user_id(FK→users)

comments
  id, post_id(FK→posts), content, author,
  created_at, updated_at, user_id(FK→users)
```

---

## 주요 기능

### 게시판
- 게시글 목록 (제목 검색, 페이지네이션)
- 게시글 작성/수정/삭제 — 로그인 + 본인만 가능
- Summernote 리치 텍스트 에디터
- 댓글 작성/수정/삭제 — 로그인 + 본인만 가능

### 회원 인증
- 회원가입 (이메일 + 닉네임 중복 확인, 비밀번호 복잡도 검사)
- 로그인 / 로그아웃 (세션 3시간 유지)
- 비밀번호 찾기 → 이메일로 재설정 링크 발송 (1시간 유효)

---

## URL 목록

| URL | 설명 |
|---|---|
| `GET /` | 게시글 목록 |
| `GET/POST /post/create/` | 게시글 작성 |
| `GET /post/<id>/` | 게시글 상세 |
| `GET/POST /post/<id>/edit/` | 게시글 수정 |
| `POST /post/<id>/delete/` | 게시글 삭제 |
| `POST /post/<id>/comment/create/` | 댓글 작성 |
| `GET/POST /post/<id>/comment/<cid>/edit/` | 댓글 수정 |
| `POST /post/<id>/comment/<cid>/delete/` | 댓글 삭제 |
| `GET/POST /accounts/signup/` | 회원가입 |
| `GET/POST /accounts/login/` | 로그인 |
| `POST /accounts/logout/` | 로그아웃 |
| `GET/POST /accounts/find/` | 비밀번호 찾기 |
| `GET/POST /accounts/reset-password/<token>/` | 비밀번호 재설정 |

---

## 아키텍처 특이사항

**Django ORM 비활성화** — `DATABASES = {}` 설정. DB 접근은 SQLAlchemy로만 처리하고, Django는 URL 라우팅·템플릿·메시지·세션 역할만 담당한다.

**signed_cookies 세션** — DB 없이 동작하는 세션 백엔드. 세션 데이터(user_id, nickname, email)는 서명된 쿠키에 저장된다.

**get_db() 패턴** — 모든 뷰에서 `with get_db() as db:` 컨텍스트 매니저를 사용. 정상 종료 시 자동 commit, 예외 발생 시 자동 rollback.

**이메일 분기** — `DEBUG=True` 시 터미널 출력(`console.EmailBackend`), `DEBUG=False` 시 Gmail SMTP 발송.

---

## 테스트

```bash
pytest tests/ -v
```

- SQLite in-memory DB로 PostgreSQL 없이 독립 실행
- savepoint(중첩 트랜잭션)으로 테스트 간 데이터 격리
- `make_mock_get_db(session)`: 뷰의 `get_db`를 테스트 세션으로 교체

---

## 환경변수 목록

| 변수 | 설명 | 기본값 |
|---|---|---|
| `SECRET_KEY` | Django 시크릿 키 | `django-insecure-fallback-key` |
| `DEBUG` | 디버그 모드 | `True` |
| `ALLOWED_HOSTS` | 허용 호스트 (쉼표 구분) | `localhost,127.0.0.1` |
| `DB_HOST` | PostgreSQL 호스트 | `localhost` |
| `DB_PORT` | PostgreSQL 포트 | `5432` |
| `DB_NAME` | DB 이름 | `bulletin_board` |
| `DB_USER` | DB 사용자 | `postgres` |
| `DB_PASSWORD` | DB 비밀번호 | `password123` |
| `EMAIL_HOST_USER` | Gmail 주소 (운영) | — |
| `EMAIL_HOST_PASSWORD` | Gmail 앱 비밀번호 (운영) | — |

---

## Git 업로드 금지 파일

`.gitignore`에 반드시 포함:

```
.env
venv/
config/settings.py
*.pem
*.key
*.crt
```
