"""
login_required 데코레이터 테스트

미로그인 시 /accounts/login/?next=<원래 URL>로 redirect 확인
"""
import pytest
from unittest.mock import patch

from django.test import RequestFactory

from accounts.decorators import login_required


class TestLoginRequired:
    """login_required 데코레이터 단위 테스트"""

    def setup_method(self):
        self.factory = RequestFactory()

    def _make_request(self, path='/', session_data=None):
        """테스트용 request 객체 생성"""
        request = self.factory.get(path)
        # 세션 mock
        request.session = session_data or {}
        return request

    def test_미로그인_접근시_로그인_페이지_redirect(self):
        """세션에 user_id가 없으면 /accounts/login/?next=... 로 redirect"""
        @login_required
        def dummy_view(request):
            return 'success'

        request = self._make_request('/post/create/')
        response = dummy_view(request)

        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']
        assert 'next=/post/create/' in response['Location']

    def test_로그인_후_정상_접근(self):
        """세션에 user_id가 있으면 원래 뷰 실행"""
        @login_required
        def dummy_view(request):
            return 'success'

        request = self._make_request('/post/create/')
        request.session = {'user_id': 1}
        result = dummy_view(request)

        assert result == 'success'

    def test_미로그인_next_파라미터_포함(self):
        """redirect URL에 원래 경로가 next 파라미터로 포함"""
        @login_required
        def dummy_view(request):
            return 'success'

        request = self._make_request('/post/42/edit/')
        response = dummy_view(request)

        location = response['Location']
        assert 'next=/post/42/edit/' in location
