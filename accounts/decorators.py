from functools import wraps

from django.shortcuts import redirect


def login_required(view_func):
    """로그인이 필요한 뷰에 적용하는 데코레이터. 미로그인 시 /accounts/login/?next=<원래 URL>로 redirect."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('user_id'):
            return redirect(f'/accounts/login/?next={request.path}')
        return view_func(request, *args, **kwargs)

    return wrapper
