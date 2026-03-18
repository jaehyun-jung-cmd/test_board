def current_user(request):
    """모든 템플릿에 현재 로그인 사용자 정보를 주입하는 컨텍스트 프로세서"""
    user_id = request.session.get('user_id')
    if user_id:
        return {
            'current_user': {
                'id': user_id,
                'nickname': request.session.get('user_nickname'),
                'email': request.session.get('user_email'),
            }
        }
    return {'current_user': None}
