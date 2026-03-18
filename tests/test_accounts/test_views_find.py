"""
비밀번호 찾기/재설정 뷰 테스트
"""
import hashlib
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from accounts.models import PasswordResetToken
from accounts.utils import generate_reset_token
from tests.conftest import make_mock_get_db


class TestFindAccountView:
    """비밀번호 찾기 뷰 테스트"""

    def test_GET_비밀번호_찾기_폼_표시(self, client):
        """GET 요청 시 이메일 입력 폼 200 OK"""
        response = client.get('/accounts/find/')
        assert response.status_code == 200

    def test_POST_존재하는_이메일_토큰_생성(self, client, db_session, test_user):
        """유효한 이메일 입력 시 토큰 생성 및 이메일 발송"""
        with patch('accounts.views.get_db', make_mock_get_db(db_session)):
            with patch('accounts.views.send_reset_email') as mock_mail:
                response = client.post('/accounts/find/', {
                    'email': test_user.email,
                })

        assert response.status_code == 302
        # 이메일 발송 호출 확인
        assert mock_mail.called

    def test_POST_존재하지_않는_이메일_동일_성공_메시지(self, client, db_session):
        """존재하지 않는 이메일도 동일한 성공 메시지 (사용자 열거 방지)"""
        with patch('accounts.views.get_db', make_mock_get_db(db_session)):
            response = client.post('/accounts/find/', {
                'email': 'notexist@example.com',
            })

        # 존재 여부와 무관하게 302 redirect
        assert response.status_code == 302


class TestResetPasswordView:
    """비밀번호 재설정 뷰 테스트"""

    def _create_token(self, db_session, user):
        """테스트용 유효 토큰 생성"""
        raw_token, token_hash = generate_reset_token()
        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
        )
        db_session.add(reset_token)
        db_session.flush()
        return raw_token, reset_token

    def test_GET_유효_토큰_폼_표시(self, client, db_session, test_user):
        """유효한 토큰으로 GET 요청 시 새 비밀번호 입력 폼 표시"""
        raw_token, _ = self._create_token(db_session, test_user)

        with patch('accounts.views.get_db', make_mock_get_db(db_session)):
            response = client.get(f'/accounts/reset-password/{raw_token}/')

        assert response.status_code == 200

    def test_GET_만료_토큰_find_redirect(self, client, db_session, test_user):
        """만료된 토큰으로 접근 시 비밀번호 찾기 페이지로 redirect"""
        raw_token, reset_token = self._create_token(db_session, test_user)
        # 2시간 전으로 조작
        reset_token.created_at = datetime.utcnow() - timedelta(hours=2)
        db_session.flush()

        with patch('accounts.views.get_db', make_mock_get_db(db_session)):
            response = client.get(f'/accounts/reset-password/{raw_token}/')

        assert response.status_code == 302
        assert '/accounts/find/' in response['Location']

    def test_POST_새_비밀번호_변경_성공(self, client, db_session, test_user):
        """유효 토큰 + 올바른 비밀번호로 POST 시 비밀번호 변경 후 login redirect"""
        raw_token, _ = self._create_token(db_session, test_user)

        with patch('accounts.views.get_db', make_mock_get_db(db_session)):
            response = client.post(f'/accounts/reset-password/{raw_token}/', {
                'password': 'NewPass99',
                'password_confirm': 'NewPass99',
            })

        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']

    def test_POST_사용된_토큰_재사용_불가(self, client, db_session, test_user):
        """이미 사용된 토큰으로 재설정 시도 시 find 페이지로 redirect"""
        raw_token, reset_token = self._create_token(db_session, test_user)
        reset_token.used = True
        db_session.flush()

        with patch('accounts.views.get_db', make_mock_get_db(db_session)):
            response = client.get(f'/accounts/reset-password/{raw_token}/')

        assert response.status_code == 302
        assert '/accounts/find/' in response['Location']
