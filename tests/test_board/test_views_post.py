"""
게시글 뷰 보호 테스트 - 로그인 필요 및 소유권 체크
"""
import pytest
from unittest.mock import patch

from board.models import Post
from tests.conftest import make_mock_get_db


class TestPostLoginRequired:
    """게시글 작성/수정/삭제 login_required 테스트"""

    def test_미로그인_게시글_작성_redirect(self, client):
        """로그인 안 한 사용자가 post_create 접근 시 로그인 페이지로 redirect"""
        response = client.get('/post/create/')
        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']
        assert 'next=/post/create/' in response['Location']

    def test_미로그인_게시글_수정_redirect(self, client):
        """로그인 안 한 사용자가 post_edit 접근 시 로그인 페이지로 redirect"""
        response = client.get('/post/1/edit/')
        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']

    def test_미로그인_게시글_삭제_redirect(self, client):
        """로그인 안 한 사용자가 post_delete 시도 시 로그인 페이지로 redirect"""
        response = client.post('/post/1/delete/')
        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']


class TestPostOwnership:
    """게시글 소유권 테스트"""

    def _create_post(self, db_session, user):
        """테스트용 게시글 생성"""
        post = Post(
            title='테스트 게시글',
            content='테스트 내용',
            author=user.nickname,
            user_id=user.id,
        )
        db_session.add(post)
        db_session.flush()
        return post

    def test_로그인_후_게시글_작성_성공(self, logged_in_client, db_session, test_user):
        """로그인 후 게시글 작성 시 성공"""
        with patch('board.views.get_db', make_mock_get_db(db_session)):
            response = logged_in_client.post('/post/create/', {
                'title': '새 게시글',
                'content': '내용입니다',
            })

        assert response.status_code == 302
        # DB에 게시글 저장 확인
        post = db_session.query(Post).filter(Post.title == '새 게시글').first()
        assert post is not None
        assert post.user_id == test_user.id
        assert post.author == test_user.nickname

    def test_다른_사용자_게시글_수정_불가(self, client, db_session, test_user, another_user):
        """다른 사람의 게시글 수정 시도 시 403 또는 redirect"""
        post = self._create_post(db_session, another_user)

        # test_user로 로그인
        session = client.session
        session['user_id'] = test_user.id
        session['user_nickname'] = test_user.nickname
        session['user_email'] = test_user.email
        session.save()

        with patch('board.views.get_db', make_mock_get_db(db_session)):
            response = client.get(f'/post/{post.id}/edit/')

        # 권한 없으므로 상세 페이지로 redirect
        assert response.status_code == 302
        assert f'/post/{post.id}/' in response['Location']

    def test_본인_게시글_삭제_성공(self, logged_in_client, db_session, test_user):
        """본인 게시글 삭제 성공"""
        post = self._create_post(db_session, test_user)

        with patch('board.views.get_db', make_mock_get_db(db_session)):
            response = logged_in_client.post(f'/post/{post.id}/delete/')

        assert response.status_code == 302
        # DB에서 삭제 확인
        deleted = db_session.query(Post).filter(Post.id == post.id).first()
        assert deleted is None
