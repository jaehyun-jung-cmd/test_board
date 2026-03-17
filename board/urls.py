from django.urls import path

from . import views

app_name = 'board'

urlpatterns = [
    # 게시글 목록 (검색, 페이징)
    path('', views.post_list, name='post_list'),

    # 게시글 작성
    path('post/create/', views.post_create, name='post_create'),

    # 게시글 상세 조회
    path('post/<int:post_id>/', views.post_detail, name='post_detail'),

    # 게시글 수정
    path('post/<int:post_id>/edit/', views.post_edit, name='post_edit'),

    # 게시글 삭제
    path('post/<int:post_id>/delete/', views.post_delete, name='post_delete'),

    # 댓글 작성
    path('post/<int:post_id>/comment/create/', views.comment_create, name='comment_create'),

    # 댓글 수정 (비밀번호 인증)
    path('post/<int:post_id>/comment/<int:comment_id>/edit/', views.comment_edit, name='comment_edit'),

    # 댓글 삭제 (비밀번호 인증)
    path('post/<int:post_id>/comment/<int:comment_id>/delete/', views.comment_delete, name='comment_delete'),
]
