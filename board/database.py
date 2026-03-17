import contextlib

from django.conf import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


# SQLAlchemy ORM의 기본 모델 클래스 - 모든 모델이 이 클래스를 상속받음
class Base(DeclarativeBase):
    pass


# DB 엔진 생성 - pool_pre_ping으로 끊긴 연결 자동 감지
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,  # 연결 유효성 사전 확인
    echo=settings.DEBUG,  # DEBUG 모드일 때 SQL 쿼리 로깅
)

# 세션 팩토리 - autocommit/autoflush 비활성화하여 수동 제어
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """모든 SQLAlchemy 모델을 기반으로 DB 테이블 생성"""
    from . import models  # noqa: F401 - 모델 임포트로 Base에 테이블 등록
    Base.metadata.create_all(bind=engine)


@contextlib.contextmanager
def get_db():
    """
    뷰에서 사용할 DB 세션 컨텍스트 매니저

    사용법:
        with get_db() as db:
            db.query(...)

    - 정상 종료 시 자동 commit
    - 예외 발생 시 자동 rollback
    - 항상 세션 close 보장
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
