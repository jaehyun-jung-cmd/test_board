# Project Context

## 프로젝트 개요

로그인 없이 누구나 글을 쓰고 댓글을 달 수 있는 익명 게시판 웹 애플리케이션이다.
댓글은 작성 시 설정한 비밀번호로만 수정·삭제할 수 있다.

## 기술 스택

| 구분 | 기술 |
|------|------|
| 웹 프레임워크 | Django 4.2 (라우팅·템플릿·메시지만 사용, ORM 미사용) |
| DB ORM | SQLAlchemy 2.0 |
| DB | PostgreSQL (Docker 컨테이너) |
| 프론트엔드 | Bootstrap 4, Summernote 에디터 (CDN) |
| 환경변수 | python-dotenv (.env 파일) |
| Python | 3.11 |

## 설계 의도

- **Django ORM 비활성화**: `DATABASES = {}` 로 설정. Django는 URL 라우팅·템플릿 렌더링·메시지 프레임워크 역할만 담당하고, DB 접근은 전적으로 SQLAlchemy를 통해 처리한다.
- **세션·인증 없음**: 로그인 기능이 없으므로 Django의 세션·auth 미들웨어를 사용하지 않는다. 댓글 수정·삭제 권한은 bcrypt 해시로 저장한 비밀번호 검증으로 대체한다.
- **DB 레벨 페이지네이션**: Django Paginator 대신 커스텀 `PageObj` 클래스와 SQLAlchemy `offset/limit` 조합으로 대용량에서도 효율적인 페이징을 구현한다.
- **세션 안전성**: 모든 뷰에서 `with get_db() as db:` 컨텍스트 매니저를 사용해 commit·rollback·close를 자동 처리한다. SQLAlchemy 지연 로딩 문제를 피하기 위해 세션 종료 전에 필요한 데이터를 dict로 변환한다.

## URL 구조

```
GET  /                                          게시글 목록 (검색, 페이징)
GET  /post/create/                              게시글 작성 폼
POST /post/create/                              게시글 저장
GET  /post/<id>/                                게시글 상세 + 댓글 목록
GET  /post/<id>/edit/                           게시글 수정 폼
POST /post/<id>/edit/                           게시글 수정 저장
POST /post/<id>/delete/                         게시글 삭제
POST /post/<id>/comment/create/                 댓글 작성
GET  /post/<id>/comment/<cid>/edit/             댓글 수정 폼 (비밀번호 입력)
POST /post/<id>/comment/<cid>/edit/             댓글 수정 저장 (비밀번호 검증)
POST /post/<id>/comment/<cid>/delete/           댓글 삭제 (비밀번호 검증)
```

## 데이터 흐름

```
Browser → Django URL Router → View 함수
                                  ↓
                          get_db() 컨텍스트 매니저
                                  ↓
                         SQLAlchemy Session
                                  ↓
                         PostgreSQL (Docker)
```

## 주요 제약사항

- 게시글·댓글 작성자는 인증 없는 임의 문자열(닉네임)이다.
- 게시글 삭제 시 연결된 댓글은 cascade 삭제된다.
- Summernote 에디터로 작성된 게시글 본문은 HTML로 저장되며, 템플릿에서 `|safe` 필터로 렌더링한다.
- 조회수는 상세 페이지 진입 시마다 1씩 증가한다.
