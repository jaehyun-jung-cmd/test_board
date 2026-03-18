"""
로그인/로그아웃 뷰 테스트
"""
import pytest
from unittest.mock import patch

from tests.conftest import make_mock_get_db


class TestLoginView:
    """로그인 뷰 테스트"""

    def test_GET_로그인_폼_표시(self, client):
        """GET 요청 시 로그인 폼 200 OK"""
        response = client.get('/accounts/login/')
        assert response.status_code == 200

    def test_POST_올바른_자격증명_로그인_성공(self, client, db_session, test_user):
        """올바른 이메일+비밀번호로 로그인 시 세션 설정 후 redirect"""
        with patch('accounts.views.get_db', make_mock_get_db(db_session)):
            response = client.post('/accounts/login/', {
                'email': 'test@example.com',
                'password': 'Test1234',
            })

        assert response.status_code == 302
        # 세션에 user_id가 설정됨
        assert client.session.get('user_id') == test_user.id
        assert client.session.get('user_nickname') == test_user.nickname

    def test_POST_잘못된_비밀번호_로그인_실패(self, client, db_session, test_user):
        """틀린 비밀번호로 로그인 시 오류 메시지 표시"""
        with patch('accounts.views.get_db', make_mock_get_db(db_session)):
            response = client.post('/accounts/login/', {
                'email': 'test@example.com',
                'password': 'WrongPassword1',
            })

        assert response.status_code == 200
        assert '올바르지 않습니다' in response.content.decode()

    def test_POST_존재하지_않는_이메일_로그인_실패(self, client, db_session):
        """존재하지 않는 이메일로 로그인 시 오류"""
        with patch('accounts.views.get_db', make_mock_get_db(db_session)):
            response = client.post('/accounts/login/', {
                'email': 'notexist@example.com',
                'password': 'Test1234',
            })

        assert response.status_code == 200
        assert '올바르지 않습니다' in response.content.decode()

    def test_next_파라미터_로그인_후_redirect(self, client, db_session, test_user):
        """?next= 파라미터가 있으면 로그인 성공 후 해당 URL로 redirect"""
        with patch('accounts.views.get_db', make_mock_get_db(db_session)):
            response = client.post('/accounts/login/?next=/post/create/', {
                'email': 'test@example.com',
                'password': 'Test1234',
                'next': '/post/create/',
            })

        assert response.status_code == 302
        assert response['Location'] == '/post/create/'

    def test_이미_로그인한_사용자_접근시_redirect(self, logged_in_client):
        """이미 로그인된 사용자가 로그인 페이지 접근 시 게시글 목록으로 redirect"""
        response = logged_in_client.get('/accounts/login/')
        assert response.status_code == 302


class TestLogoutView:
    """로그아웃 뷰 테스트"""

    def test_POST_로그아웃_세션_삭제(self, logged_in_client):
        """POST 요청으로 로그아웃 시 세션 삭제 후 게시글 목록으로 redirect"""
        assert logged_in_client.session.get('user_id') is not None

        response = logged_in_client.post('/accounts/logout/')

        assert response.status_code == 302
        # 로그아웃 후 세션에 user_id 없음
        assert logged_in_client.session.get('user_id') is None

    def test_GET_로그아웃_허용_안됨(self, logged_in_client):
        """GET으로 로그아웃 시도 시 세션 유지 (CSRF 보호)"""
        response = logged_in_client.get('/accounts/logout/')
        # GET은 세션을 삭제하지 않고 redirect만 함
        assert logged_in_client.session.get('user_id') is not None
