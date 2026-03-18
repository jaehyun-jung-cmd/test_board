"""
댓글 뷰 보호 테스트 - 로그인 필요 및 소유권 체크 (비밀번호 인증 제거됨)
"""
import pytest
from unittest.mock import patch

from board.models import Comment, Post
from tests.conftest import make_mock_get_db


class TestCommentLoginRequired:
    """댓글 작성/수정/삭제 login_required 테스트"""

    def test_미로그인_댓글_작성_redirect(self, client):
        """로그인 안 한 사용자가 댓글 작성 시 로그인 페이지로 redirect"""
        response = client.post('/post/1/comment/create/')
        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']

    def test_미로그인_댓글_수정_redirect(self, client):
        """로그인 안 한 사용자가 댓글 수정 시 로그인 페이지로 redirect"""
        response = client.get('/post/1/comment/1/edit/')
        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']

    def test_미로그인_댓글_삭제_redirect(self, client):
        """로그인 안 한 사용자가 댓글 삭제 시 로그인 페이지로 redirect"""
        response = client.post('/post/1/comment/1/delete/')
        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']


class TestCommentOwnership:
    """댓글 소유권 테스트"""

    def _create_post_and_comment(self, db_session, post_user, comment_user):
        """테스트용 게시글 + 댓글 생성"""
        post = Post(
            title='테스트 게시글',
            content='내용',
            author=post_user.nickname,
            user_id=post_user.id,
        )
        db_session.add(post)
        db_session.flush()

        comment = Comment(
            post_id=post.id,
            content='테스트 댓글',
            author=comment_user.nickname,
            user_id=comment_user.id,
        )
        db_session.add(comment)
        db_session.flush()
        return post, comment

    def test_로그인_후_댓글_작성_성공(self, logged_in_client, db_session, test_user):
        """로그인 후 댓글 작성 시 성공 (비밀번호 입력 불필요)"""
        post = Post(
            title='게시글',
            content='내용',
            author=test_user.nickname,
            user_id=test_user.id,
        )
        db_session.add(post)
        db_session.flush()

        with patch('board.views.get_db', make_mock_get_db(db_session)):
            response = logged_in_client.post(f'/post/{post.id}/comment/create/', {
                'content': '새 댓글입니다',
            })

        assert response.status_code == 302
        comment = db_session.query(Comment).filter(Comment.post_id == post.id).first()
        assert comment is not None
        assert comment.user_id == test_user.id
        assert comment.author == test_user.nickname

    def test_다른_사용자_댓글_수정_불가(self, client, db_session, test_user, another_user):
        """다른 사람의 댓글 수정 시도 시 redirect (권한 없음)"""
        post, comment = self._create_post_and_comment(db_session, another_user, another_user)

        # test_user로 로그인
        session = client.session
        session['user_id'] = test_user.id
        session['user_nickname'] = test_user.nickname
        session['user_email'] = test_user.email
        session.save()

        with patch('board.views.get_db', make_mock_get_db(db_session)):
            response = client.get(f'/post/{post.id}/comment/{comment.id}/edit/')

        # 권한 없으므로 게시글 상세 페이지로 redirect
        assert response.status_code == 302

    def test_본인_댓글_삭제_성공(self, logged_in_client, db_session, test_user):
        """본인 댓글 삭제 성공"""
        post, comment = self._create_post_and_comment(db_session, test_user, test_user)

        with patch('board.views.get_db', make_mock_get_db(db_session)):
            response = logged_in_client.post(
                f'/post/{post.id}/comment/{comment.id}/delete/'
            )

        assert response.status_code == 302
        deleted = db_session.query(Comment).filter(Comment.id == comment.id).first()
        assert deleted is None
