import os
from pathlib import Path

from dotenv import load_dotenv

# .env 파일에서 환경변수 로드
load_dotenv()

# 프로젝트 루트 경로
BASE_DIR = Path(__file__).resolve().parent.parent

# 시크릿 키 - 운영 환경에서는 반드시 .env에서 설정
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-fallback-key')

DEBUG = os.environ.get('DEBUG', 'True') == 'True'

# 허용 호스트 - 쉼표 구분으로 여러 개 설정 가능
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Django ORM 관련 앱 제외 - SQLAlchemy를 직접 사용하므로 불필요
INSTALLED_APPS = [
    'django.contrib.staticfiles',
    'django.contrib.messages',
    'board',
    'accounts',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',  # 세션 처리
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',             # CSRF 보호
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # 프로젝트 루트의 templates 디렉토리 사용
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
                'accounts.context_processors.current_user',  # 전역 로그인 사용자 주입
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Django ORM 비활성화 - DB 작업은 SQLAlchemy로만 처리
DATABASES = {}

# DB 연결 정보 - .env에서 로드
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('DB_NAME', 'bulletin_board')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'password123')

# SQLAlchemy 연결 URL
SQLALCHEMY_DATABASE_URL = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# 쿠키 기반 메시지 스토리지 - 세션/DB 없이 flash 메시지 동작
MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'

# 세션 설정 - signed_cookies 백엔드 (DB 불필요)
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
SESSION_COOKIE_AGE = 60 * 60 * 3   # 3시간 유지
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # 브라우저 닫아도 3시간 유지
SESSION_SAVE_EVERY_REQUEST = False       # 매 요청마다 세션 갱신 안 함

# Argon2 비밀번호 해시 알고리즘 (업계 최고 권장)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

# 이메일 설정 - 개발/운영 환경 분리
if DEBUG:
    # 로컬 개발: 이메일 내용을 터미널에 출력
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    # 운영: Gmail SMTP 발송
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
    DEFAULT_FROM_EMAIL = os.environ.get('EMAIL_HOST_USER')

LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# 게시글 목록 페이지당 표시 개수
POSTS_PER_PAGE = 10
