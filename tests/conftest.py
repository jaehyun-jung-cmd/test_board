"""
pytest 픽스처 설정 - SQLAlchemy 테스트용 세션 구성

테스트 DB 전략:
- SQLite in-memory 사용 (PostgreSQL 없이 독립 실행 가능)
- 각 테스트 함수마다 중첩 트랜잭션(Savepoint)으로 데이터 격리
- views 테스트 시 get_db를 패치하여 테스트 세션 주입
"""
from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from django.conf import settings as django_settings
from django.test import Client


@pytest.fixture(scope='session')
def test_engine():
    """테스트용 SQLite in-memory 엔진 (세션 범위)"""
    # board, accounts 모델을 모두 Base에 등록
    from board.database import Base
    import board.models   # noqa: F401
    import accounts.models  # noqa: F401

    engine = create_engine(
        'sqlite:///:memory:',
        connect_args={'check_same_thread': False},
    )
    # SQLite 외래 키 제약조건 활성화
    @event.listens_for(engine, 'connect')
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.close()

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    """각 테스트용 DB 세션 - 중첩 트랜잭션으로 데이터 격리 후 롤백"""
    connection = test_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client():
    """Django 테스트 클라이언트"""
    return Client()


@pytest.fixture
def test_user(db_session):
    """테스트용 회원 생성"""
    from django.contrib.auth.hashers import make_password
    from accounts.models import User

    user = User(
        email='test@example.com',
        password=make_password('Test1234'),
        nickname='테스터',
        name='테스트유저',
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def another_user(db_session):
    """다른 회원 생성 (소유권 체크 테스트용)"""
    from django.contrib.auth.hashers import make_password
    from accounts.models import User

    user = User(
        email='other@example.com',
        password=make_password('Test1234'),
        nickname='다른유저',
        name='다른사람',
    )
    db_session.add(user)
    db_session.flush()
    return user


def make_mock_get_db(session):
    """
    views의 get_db를 테스트 세션으로 대체하는 컨텍스트 매니저 팩토리.

    Savepoint(중첩 트랜잭션)를 사용하여 뷰 내부의 변경사항이 외부 트랜잭션에서
    보이도록 하면서, 테스트 종료 시 전체 트랜잭션 롤백으로 DB 격리를 유지.
    """
    @contextmanager
    def mock_get_db():
        # 뷰의 변경사항을 외부 트랜잭션에 반영하기 위해 savepoint 사용
        nested = session.begin_nested()
        try:
            yield session
            nested.commit()  # savepoint 커밋 (외부 트랜잭션은 유지됨)
        except Exception:
            nested.rollback()
            raise

    return mock_get_db


@pytest.fixture
def logged_in_client(client, test_user):
    """
    로그인 상태의 테스트 클라이언트 반환.

    signed_cookies 세션 백엔드에서는 session.save() 후 session.session_key를
    직접 쿠키에 설정해야 다음 요청에서 세션이 유지됨.
    """
    session = client.session
    session['user_id'] = test_user.id
    session['user_nickname'] = test_user.nickname
    session['user_email'] = test_user.email
    session.save()
    # signed_cookies: session_key가 인코딩된 세션 데이터 - 쿠키에 직접 설정
    client.cookies[django_settings.SESSION_COOKIE_NAME] = session.session_key
    return client
