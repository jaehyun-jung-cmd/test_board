from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    # 회원가입
    path('signup/', views.signup, name='signup'),
    # 로그인
    path('login/', views.login, name='login'),
    # 로그아웃 (POST 전용)
    path('logout/', views.logout, name='logout'),
    # 비밀번호 찾기 (이메일 입력)
    path('find/', views.find_account, name='find_account'),
    # 비밀번호 재설정 (토큰 검증 후 새 비밀번호 입력)
    path('reset-password/<str:token>/', views.reset_password, name='reset_password'),
]
