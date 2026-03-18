import hashlib
import secrets
from datetime import datetime, timedelta

from django.conf import settings
from django.core.mail import send_mail


def generate_reset_token():
    """비밀번호 재설정 토큰 생성. 원본 토큰(이메일 발송용)과 SHA-256 해시(DB 저장용) 반환."""
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    return raw_token, token_hash


def is_token_expired(token, hours=1):
    """토큰 만료 여부 확인 (기본 1시간)"""
    expiry = token.created_at + timedelta(hours=hours)
    return datetime.utcnow() > expiry


def send_reset_email(email, nickname, raw_token, request=None):
    """비밀번호 재설정 이메일 발송"""
    if request:
        base_url = f"{request.scheme}://{request.get_host()}"
    else:
        base_url = 'http://localhost:8000'

    reset_url = f"{base_url}/accounts/reset-password/{raw_token}/"

    subject = '[게시판] 비밀번호 재설정 안내'
    message = f"""안녕하세요, {nickname}님.

비밀번호 재설정을 요청하셨습니다.

아래 링크를 클릭하여 비밀번호를 재설정하세요 (유효시간: 1시간):
{reset_url}

본인이 요청하지 않으셨다면 이 이메일을 무시하세요.

감사합니다.
게시판 운영팀
"""

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')

    send_mail(
        subject=subject,
        message=message,
        from_email=from_email,
        recipient_list=[email],
        fail_silently=False,
    )
