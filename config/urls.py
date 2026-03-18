from django.urls import path, include

urlpatterns = [
    # accounts 앱 URL (회원가입, 로그인, 로그아웃, 비밀번호 찾기)
    path('accounts/', include('accounts.urls')),
    # board 앱의 URL을 루트 경로에 연결
    path('', include('board.urls')),
]
