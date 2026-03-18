"""
accounts 모델 단위 테스트

RED → GREEN → REFACTOR 사이클:
1. 이 테스트를 먼저 실행 (RED - 모델 없으면 실패)
2. accounts/models.py 구현 (GREEN)
3. 필요 시 리팩토링
"""
import pytest
from django.contrib.auth.hashers import check_password, make_password

from accounts.models import PasswordResetToken, User
from accounts.utils import generate_reset_token, is_token_expired


class TestUserModel:
    """User 모델 단위 테스트"""

    def test_사용자_생성(self, db_session):
        """기본 필드로 User 생성 성공"""
        user = User(
            email='new@example.com',
            password=make_password('Test1234'),
            nickname='새유저',
            name='새사람',
        )
        db_session.add(user)
        db_session.flush()

        assert user.id is not None
        assert user.email == 'new@example.com'
        assert user.nickname == '새유저'
        assert user.is_active is True  # 기본값
        assert user.phone is None      # 선택 필드 기본값

    def test_비밀번호_해시_검증(self, db_session):
        """저장된 비밀번호는 Argon2 해시이며 check_password로 검증 가능"""
        raw_password = 'Test1234'
        user = User(
            email='hash@example.com',
            password=make_password(raw_password),
            nickname='해시유저',
            name='해시사람',
        )
        db_session.add(user)
        db_session.flush()

        # 올바른 비밀번호 검증
        assert check_password(raw_password, user.password) is True
        # 틀린 비밀번호 검증
        assert check_password('WrongPassword1', user.password) is False

    def test_이메일_유일성(self, db_session):
        """동일 이메일로 두 번 가입 시 IntegrityError 발생"""
        from sqlalchemy.exc import IntegrityError

        user1 = User(email='dup@example.com', password='hash', nickname='유저1', name='이름1')
        db_session.add(user1)
        db_session.flush()

        user2 = User(email='dup@example.com', password='hash', nickname='유저2', name='이름2')
        db_session.add(user2)
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_닉네임_유일성(self, db_session):
        """동일 닉네임으로 두 번 가입 시 IntegrityError 발생"""
        from sqlalchemy.exc import IntegrityError

        user1 = User(email='nick1@example.com', password='hash', nickname='같은닉네임', name='이름1')
        db_session.add(user1)
        db_session.flush()

        user2 = User(email='nick2@example.com', password='hash', nickname='같은닉네임', name='이름2')
        db_session.add(user2)
        with pytest.raises(IntegrityError):
            db_session.flush()


class TestPasswordResetTokenModel:
    """PasswordResetToken 모델 단위 테스트"""

    def test_토큰_생성(self, db_session, test_user):
        """토큰 생성 및 DB 저장 성공"""
        raw_token, token_hash = generate_reset_token()

        reset_token = PasswordResetToken(
            user_id=test_user.id,
            token_hash=token_hash,
        )
        db_session.add(reset_token)
        db_session.flush()

        assert reset_token.id is not None
        assert reset_token.used is False  # 기본값
        assert reset_token.token_hash == token_hash

    def test_토큰_만료_확인(self, db_session, test_user):
        """생성된 지 1시간이 넘은 토큰은 만료됨"""
        from datetime import datetime, timedelta

        raw_token, token_hash = generate_reset_token()
        reset_token = PasswordResetToken(
            user_id=test_user.id,
            token_hash=token_hash,
        )
        # 2시간 전에 생성된 것으로 설정
        reset_token.created_at = datetime.utcnow() - timedelta(hours=2)
        db_session.add(reset_token)
        db_session.flush()

        assert is_token_expired(reset_token) is True

    def test_유효_토큰_만료_아님(self, db_session, test_user):
        """방금 생성된 토큰은 만료되지 않음"""
        raw_token, token_hash = generate_reset_token()
        reset_token = PasswordResetToken(
            user_id=test_user.id,
            token_hash=token_hash,
        )
        db_session.add(reset_token)
        db_session.flush()

        assert is_token_expired(reset_token) is False
