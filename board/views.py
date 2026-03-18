import math

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render

from .database import get_db
from .models import Comment, Post
from accounts.decorators import login_required


class PageObj:
    """
    SQLAlchemy 쿼리 결과를 위한 페이지네이션 헬퍼 클래스

    Django 기본 Paginator 대신 사용 - SQLAlchemy offset/limit 기반으로
    실제 DB 레벨에서 페이징 처리 후 이 클래스로 감싸서 템플릿에 전달
    """

    def __init__(self, items, page, per_page, total):
        self.object_list = items    # 현재 페이지의 데이터 목록
        self.number = page          # 현재 페이지 번호
        self.per_page = per_page    # 페이지당 항목 수
        self.total = total          # 전체 항목 수
        self.num_pages = math.ceil(total / per_page) if total > 0 else 1  # 전체 페이지 수

    def __iter__(self):
        return iter(self.object_list)

    @property
    def has_previous(self):
        # 이전 페이지 존재 여부
        return self.number > 1

    @property
    def has_next(self):
        # 다음 페이지 존재 여부
        return self.number < self.num_pages

    @property
    def has_other_pages(self):
        # 페이지네이션 표시 필요 여부
        return self.num_pages > 1

    @property
    def previous_page_number(self):
        return self.number - 1

    @property
    def next_page_number(self):
        return self.number + 1

    def page_range(self, delta=2):
        # 현재 페이지 기준 앞뒤 delta개 페이지 번호 반환
        start = max(1, self.number - delta)
        end = min(self.num_pages, self.number + delta)
        return range(start, end + 1)


def post_list(request):
    """게시글 목록 - 페이징 및 제목 검색 지원"""
    try:
        page = max(1, int(request.GET.get('page', 1)))
    except (ValueError, TypeError):
        page = 1

    search = request.GET.get('search', '').strip()
    per_page = settings.POSTS_PER_PAGE

    with get_db() as db:
        query = db.query(Post)

        # 검색어가 있으면 제목 LIKE 필터 적용
        if search:
            query = query.filter(Post.title.ilike(f'%{search}%'))

        # 최신글 순 정렬
        query = query.order_by(Post.created_at.desc())

        total = query.count()
        # DB 레벨에서 페이징 처리
        posts = query.offset((page - 1) * per_page).limit(per_page).all()

        # 세션 종료 전에 필요한 데이터만 dict로 변환 (지연 로딩 방지)
        post_data = [
            {
                'id': p.id,
                'title': p.title,
                'author': p.author,
                'view_count': p.view_count,
                'created_at': p.created_at,
                'comment_count': len(p.comments),  # 댓글 수 (배지 표시용)
            }
            for p in posts
        ]

    page_obj = PageObj(post_data, page, per_page, total)

    return render(request, 'board/list.html', {
        'page_obj': page_obj,
        'search': search,
    })


def post_detail(request, post_id):
    """게시글 상세 조회 - 조회수 증가 및 댓글 목록 포함"""
    with get_db() as db:
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            messages.error(request, '게시글을 찾을 수 없습니다.')
            return redirect('board:post_list')

        # 조회수 증가 후 flush (commit은 컨텍스트 매니저 종료 시 자동)
        post.view_count += 1
        db.flush()

        # 댓글을 작성일 오름차순으로 조회
        comments = (
            db.query(Comment)
            .filter(Comment.post_id == post_id)
            .order_by(Comment.created_at.asc())
            .all()
        )

        # 세션 종료 전 dict 변환 (user_id 포함 - 소유권 체크에 사용)
        post_data = {
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'author': post.author,
            'view_count': post.view_count,
            'created_at': post.created_at,
            'updated_at': post.updated_at,
            'user_id': post.user_id,
        }
        comment_data = [
            {
                'id': c.id,
                'content': c.content,
                'author': c.author,
                'created_at': c.created_at,
                'user_id': c.user_id,  # 소유권 체크에 사용
            }
            for c in comments
        ]

    return render(request, 'board/detail.html', {
        'post': post_data,
        'comments': comment_data,
    })


@login_required
def post_create(request):
    """게시글 작성 - 로그인 필요. 작성자는 로그인 사용자 닉네임 자동 설정."""
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        # 작성자는 세션의 닉네임 자동 사용 (입력 불필요)
        author = request.session.get('user_nickname', '')

        errors = {}
        if not title:
            errors['title'] = '제목을 입력해주세요.'
        if not content or content in ('<p><br></p>', '<p></p>'):
            errors['content'] = '내용을 입력해주세요.'

        if not errors:
            with get_db() as db:
                post = Post(
                    title=title,
                    content=content,
                    author=author,
                    user_id=request.session.get('user_id'),
                )
                db.add(post)
                db.flush()
                post_id = post.id
            messages.success(request, '게시글이 작성되었습니다.')
            return redirect('board:post_detail', post_id=post_id)

        return render(request, 'board/create.html', {
            'errors': errors,
            'form_data': {'title': title, 'content': content},
        })

    return render(request, 'board/create.html')


@login_required
def post_edit(request, post_id):
    """게시글 수정 - 로그인 + 본인 게시글만 수정 가능"""
    with get_db() as db:
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            messages.error(request, '게시글을 찾을 수 없습니다.')
            return redirect('board:post_list')

        # 본인 게시글인지 확인
        if post.user_id != request.session.get('user_id'):
            messages.error(request, '수정 권한이 없습니다.')
            return redirect('board:post_detail', post_id=post_id)

        post_data = {
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'author': post.author,
            'user_id': post.user_id,
        }

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()

        errors = {}
        if not title:
            errors['title'] = '제목을 입력해주세요.'
        if not content or content in ('<p><br></p>', '<p></p>'):
            errors['content'] = '내용을 입력해주세요.'

        if not errors:
            with get_db() as db:
                post = db.query(Post).filter(Post.id == post_id).first()
                if post:
                    post.title = title
                    post.content = content
            messages.success(request, '게시글이 수정되었습니다.')
            return redirect('board:post_detail', post_id=post_id)

        return render(request, 'board/edit.html', {
            'post': {**post_data, 'title': title, 'content': content},
            'errors': errors,
        })

    return render(request, 'board/edit.html', {'post': post_data})


@login_required
def post_delete(request, post_id):
    """게시글 삭제 - 로그인 + 본인 게시글만 삭제 가능"""
    if request.method == 'POST':
        with get_db() as db:
            post = db.query(Post).filter(Post.id == post_id).first()
            if not post:
                messages.error(request, '게시글을 찾을 수 없습니다.')
                return redirect('board:post_list')

            # 본인 게시글인지 확인
            if post.user_id != request.session.get('user_id'):
                messages.error(request, '삭제 권한이 없습니다.')
                return redirect('board:post_detail', post_id=post_id)

            db.delete(post)  # cascade 설정으로 댓글도 함께 삭제
        messages.success(request, '게시글이 삭제되었습니다.')
    return redirect('board:post_list')


@login_required
def comment_create(request, post_id):
    """댓글 작성 - 로그인 필요. 작성자는 세션 닉네임 자동 설정."""
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        author = request.session.get('user_nickname', '')

        if content:
            with get_db() as db:
                comment = Comment(
                    post_id=post_id,
                    content=content,
                    author=author,
                    user_id=request.session.get('user_id'),
                )
                db.add(comment)
            messages.success(request, '댓글이 작성되었습니다.')
        else:
            messages.error(request, '댓글 내용을 입력해주세요.')

    return redirect('board:post_detail', post_id=post_id)


@login_required
def comment_edit(request, post_id, comment_id):
    """댓글 수정 - 로그인 + 본인 댓글만 수정 가능 (비밀번호 인증 제거)"""
    with get_db() as db:
        comment = db.query(Comment).filter(
            Comment.id == comment_id,
            Comment.post_id == post_id,
        ).first()
        if not comment:
            messages.error(request, '댓글을 찾을 수 없습니다.')
            return redirect('board:post_detail', post_id=post_id)

        # 본인 댓글인지 확인
        if comment.user_id != request.session.get('user_id'):
            messages.error(request, '수정 권한이 없습니다.')
            return redirect('board:post_detail', post_id=post_id)

        comment_data = {
            'id': comment.id,
            'content': comment.content,
            'author': comment.author,
            'user_id': comment.user_id,
        }

    if request.method == 'POST':
        content = request.POST.get('content', '').strip()

        if not content:
            return render(request, 'board/comment_edit.html', {
                'comment': comment_data,
                'post_id': post_id,
                'error': '내용을 입력해주세요.',
            })

        with get_db() as db:
            comment = db.query(Comment).filter(Comment.id == comment_id).first()
            if comment:
                # 재확인: 본인 댓글인지 (동시 요청 방지)
                if comment.user_id != request.session.get('user_id'):
                    messages.error(request, '수정 권한이 없습니다.')
                    return redirect('board:post_detail', post_id=post_id)
                comment.content = content
        messages.success(request, '댓글이 수정되었습니다.')
        return redirect('board:post_detail', post_id=post_id)

    return render(request, 'board/comment_edit.html', {
        'comment': comment_data,
        'post_id': post_id,
    })


@login_required
def comment_delete(request, post_id, comment_id):
    """댓글 삭제 - 로그인 + 본인 댓글만 삭제 가능 (비밀번호 인증 제거)"""
    if request.method == 'POST':
        with get_db() as db:
            comment = db.query(Comment).filter(
                Comment.id == comment_id,
                Comment.post_id == post_id,
            ).first()
            if not comment:
                messages.error(request, '댓글을 찾을 수 없습니다.')
                return redirect('board:post_detail', post_id=post_id)

            # 본인 댓글인지 확인
            if comment.user_id != request.session.get('user_id'):
                messages.error(request, '삭제 권한이 없습니다.')
                return redirect('board:post_detail', post_id=post_id)

            db.delete(comment)
        messages.success(request, '댓글이 삭제되었습니다.')

    return redirect('board:post_detail', post_id=post_id)
