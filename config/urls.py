from django.urls import path, include

urlpatterns = [
    # board 앱의 URL을 루트 경로에 연결
    path('', include('board.urls')),
]
