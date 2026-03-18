"""
회원가입 뷰 테스트

TDD 사이클:
1. 이 테스트 파일 작성 (RED)
2. accounts/views.py signup 구현 (GREEN)
3. 리팩토링
"""
import pytest
from unittest.mock import patch, MagicMock

from tests.conftest import make_mock_get_db


class TestSignupView:
    """회원가입 뷰 테스트"""

    def test_GET_회원가입_폼_표시(self, client):
        """GET 요청 시 회원가입 폼 렌더링 (200 OK)"""
        response = client.get('/accounts/signup/')
        assert response.status_code == 200

    def test_POST_유효한_데이터_회원가입_성공(self, client, db_session):
        """올바른 데이터로 회원가입 시 login 페이지로 redirect"""
        with patch('accounts.views.get_db', make_mock_get_db(db_session)):
            response = client.post('/accounts/signup/', {
                'email': 'newuser@example.com',
                'nickname': '새유저',
                'name': '새사람',
                'password': 'Test1234',
                'password_confirm': 'Test1234',
            })

        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']

    def test_POST_이메일_없으면_오류(self, client, db_session):
        """이메일 미입력 시 errors.email 포함하여 폼 재표시"""
        with patch('accounts.views.get_db', make_mock_get_db(db_session)):
            response = client.post('/accounts/signup/', {
                'email': '',
                'nickname': '유저',
                'name': '사람',
                'password': 'Test1234',
                'password_confirm': 'Test1234',
            })

        assert response.status_code == 200
        assert '이메일을 입력해주세요' in response.content.decode()

    def test_POST_비밀번호_복잡도_미충족_오류(self, client, db_session):
        """비밀번호가 영문+숫자 조합 8자 미만이면 오류"""
        with patch('accounts.views.get_db', make_mock_get_db(db_session)):
            response = client.post('/accounts/signup/', {
                'email': 'test@example.com',
                'nickname': '유저',
                'name': '사람',
                'password': '1234',       # 짧고 영문 없음
                'password_confirm': '1234',
            })

        assert response.status_code == 200
        content = response.content.decode()
        assert '비밀번호' in content

    def test_POST_비밀번호_불일치_오류(self, client, db_session):
        """비밀번호와 확인이 다르면 오류"""
        with patch('accounts.views.get_db', make_mock_get_db(db_session)):
            response = client.post('/accounts/signup/', {
                'email': 'test@example.com',
                'nickname': '유저',
                'name': '사람',
                'password': 'Test1234',
                'password_confirm': 'Different1',
            })

        assert response.status_code == 200
        assert '일치하지 않습니다' in response.content.decode()

    def test_POST_이메일_중복_오류(self, client, db_session, test_user):
        """이미 가입된 이메일로 재가입 시 오류"""
        with patch('accounts.views.get_db', make_mock_get_db(db_session)):
            response = client.post('/accounts/signup/', {
                'email': test_user.email,   # 이미 존재하는 이메일
                'nickname': '다른닉네임',
                'name': '다른이름',
                'password': 'Test1234',
                'password_confirm': 'Test1234',
            })

        assert response.status_code == 200
        assert '이미 사용 중인 이메일' in response.content.decode()

    def test_이미_로그인한_사용자_접근시_redirect(self, logged_in_client):
        """이미 로그인된 사용자가 회원가입 페이지 접근 시 게시글 목록으로 redirect"""
        response = logged_in_client.get('/accounts/signup/')
        assert response.status_code == 302
        assert response['Location'] == '/'
