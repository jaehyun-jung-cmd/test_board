import hashlib
import re
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.shortcuts import redirect, render

from board.database import get_db
from .models import PasswordResetToken, User
from .utils import generate_reset_token, is_token_expired, send_reset_email


def _validate_password(password):
    """비밀번호 유효성 검사 - 최소 8자, 영문+숫자 조합 필수"""
    if len(password) < 8:
        return '비밀번호는 최소 8자 이상이어야 합니다.'
    if not re.search(r'[a-zA-Z]', password):
        return '비밀번호는 영문자를 포함해야 합니다.'
    if not re.search(r'[0-9]', password):
        return '비밀번호는 숫자를 포함해야 합니다.'
    return None


def _validate_email(email):
    """이메일 형식 서버 사이드 유효성 검사"""
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return '올바른 이메일 형식이 아닙니다.'
    return None


def signup(request):
    """회원가입"""
    # 이미 로그인한 사용자는 게시글 목록으로 redirect
    if request.session.get('user_id'):
        return redirect('board:post_list')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        nickname = request.POST.get('nickname', '').strip()
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')

        errors = {}

        # 이메일 유효성 검사
        if not email:
            errors['email'] = '이메일을 입력해주세요.'
        else:
            email_error = _validate_email(email)
            if email_error:
                errors['email'] = email_error

        # 닉네임 유효성 검사
        if not nickname:
            errors['nickname'] = '닉네임을 입력해주세요.'
        elif len(nickname) > 50:
            errors['nickname'] = '닉네임은 50자 이내로 입력해주세요.'

        # 이름 유효성 검사
        if not name:
            errors['name'] = '이름을 입력해주세요.'

        # 전화번호 유효성 검사 (선택 입력)
        if phone and not re.match(r'^[\d\-]+$', phone):
            errors['phone'] = '전화번호는 숫자와 하이픈(-)만 입력 가능합니다.'

        # 비밀번호 유효성 검사
        if not password:
            errors['password'] = '비밀번호를 입력해주세요.'
        else:
            pw_error = _validate_password(password)
            if pw_error:
                errors['password'] = pw_error
            elif password != password_confirm:
                errors['password_confirm'] = '비밀번호가 일치하지 않습니다.'

        if not errors:
            with get_db() as db:
                # 이메일 중복 확인
                if db.query(User).filter(User.email == email).first():
                    errors['email'] = '이미 사용 중인 이메일입니다.'
                # 닉네임 중복 확인
                elif db.query(User).filter(User.nickname == nickname).first():
                    errors['nickname'] = '이미 사용 중인 닉네임입니다.'
                else:
                    user = User(
                        email=email,
                        password=make_password(password),
                        nickname=nickname,
                        name=name,
                        phone=phone if phone else None,
                    )
                    db.add(user)
                    db.flush()

        if not errors:
            messages.success(request, '회원가입이 완료되었습니다. 로그인해주세요.')
            return redirect('accounts:login')

        return render(request, 'accounts/signup.html', {
            'errors': errors,
            'form_data': {
                'email': email,
                'nickname': nickname,
                'name': name,
                'phone': phone,
            },
        })

    return render(request, 'accounts/signup.html')


def login(request):
    """로그인 - 이메일 + 비밀번호 인증, 성공 시 세션에 user_id/nickname/email 저장"""
    # 이미 로그인한 사용자는 게시글 목록으로 redirect
    if request.session.get('user_id'):
        return redirect('board:post_list')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        next_url = request.POST.get('next', '')

        errors = {}

        if not email:
            errors['email'] = '이메일을 입력해주세요.'
        if not password:
            errors['password'] = '비밀번호를 입력해주세요.'

        if not errors:
            with get_db() as db:
                user = db.query(User).filter(
                    User.email == email,
                    User.is_active == True,
                ).first()

                if not user or not check_password(password, user.password):
                    errors['general'] = '이메일 또는 비밀번호가 올바르지 않습니다.'
                else:
                    # 로그인 성공 - 세션 설정
                    request.session['user_id'] = user.id
                    request.session['user_nickname'] = user.nickname
                    request.session['user_email'] = user.email

                    # 마지막 로그인 시간 업데이트
                    user.last_login_at = datetime.utcnow()

                    messages.success(request, f'{user.nickname}님, 환영합니다!')

                    # next 파라미터가 있으면 해당 URL로, 없으면 게시글 목록으로
                    if next_url and next_url.startswith('/'):
                        return redirect(next_url)
                    return redirect('board:post_list')

        return render(request, 'accounts/login.html', {
            'errors': errors,
            'email': email,
            'next': next_url,
        })

    next_url = request.GET.get('next', '')
    return render(request, 'accounts/login.html', {'next': next_url})


def logout(request):
    """로그아웃 - POST 전용 (GET 로그아웃은 CSRF 취약점)"""
    if request.method == 'POST':
        request.session.flush()
        messages.success(request, '로그아웃되었습니다.')
    return redirect('board:post_list')


def find_account(request):
    """비밀번호 찾기 - 이메일 입력 후 재설정 링크 발송. 사용자 열거 방지를 위해 이메일 존재 여부와 무관하게 동일 메시지 표시."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()

        if email:
            with get_db() as db:
                user = db.query(User).filter(
                    User.email == email,
                    User.is_active == True,
                ).first()

                if user:
                    # 기존 미사용 토큰 모두 무효화
                    db.query(PasswordResetToken).filter(
                        PasswordResetToken.user_id == user.id,
                        PasswordResetToken.used == False,
                    ).update({'used': True})

                    # 새 토큰 생성 및 DB 저장 (해시만 저장)
                    raw_token, token_hash = generate_reset_token()
                    reset_token = PasswordResetToken(
                        user_id=user.id,
                        token_hash=token_hash,
                    )
                    db.add(reset_token)
                    db.flush()

                    # 원본 토큰을 이메일로 발송
                    try:
                        send_reset_email(user.email, user.nickname, raw_token, request)
                    except Exception:
                        pass  # 이메일 발송 실패 시 사용자에게 노출 안 함

        # 이메일 존재 여부와 무관하게 동일한 성공 메시지 (사용자 열거 방지)
        messages.success(request, '입력한 이메일로 비밀번호 재설정 링크를 발송했습니다. (이메일이 존재하는 경우)')
        return redirect('accounts:find_account')

    return render(request, 'accounts/find_account.html')


def reset_password(request, token):
    """비밀번호 재설정 - 토큰 검증 후 새 비밀번호 설정"""
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    # 토큰 유효성 검사
    with get_db() as db:
        reset_token = db.query(PasswordResetToken).filter(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used == False,
        ).first()

        if not reset_token or is_token_expired(reset_token):
            messages.error(request, '유효하지 않거나 만료된 링크입니다. 다시 요청해주세요.')
            return redirect('accounts:find_account')

        user_id = reset_token.user_id

    if request.method == 'POST':
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')

        errors = {}
        if not password:
            errors['password'] = '비밀번호를 입력해주세요.'
        else:
            pw_error = _validate_password(password)
            if pw_error:
                errors['password'] = pw_error
            elif password != password_confirm:
                errors['password_confirm'] = '비밀번호가 일치하지 않습니다.'

        if not errors:
            with get_db() as db:
                # 토큰 재검증 (동시 요청 방지)
                reset_token = db.query(PasswordResetToken).filter(
                    PasswordResetToken.token_hash == token_hash,
                    PasswordResetToken.used == False,
                ).first()

                if reset_token and not is_token_expired(reset_token):
                    user = db.query(User).filter(User.id == reset_token.user_id).first()
                    if user:
                        user.password = make_password(password)
                        reset_token.used = True

            messages.success(request, '비밀번호가 변경되었습니다. 새 비밀번호로 로그인해주세요.')
            return redirect('accounts:login')

        return render(request, 'accounts/reset_password.html', {
            'token': token,
            'errors': errors,
        })

    return render(request, 'accounts/reset_password.html', {'token': token})
