"""Validate V1 JWT sessions through the identity service, including live role changes/revocation."""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request as HttpRequest, urlopen
from fastapi import Request


class AuthenticationError(Exception):
    def __init__(self, status, message, code):
        self.status = status
        self.payload = {'message': message, 'code': code}


def require_user(request: Request):
    if request.url.path == '/health':
        return None
    authorization = request.headers.get('Authorization', '')
    if not authorization.startswith('Bearer ') or not authorization[7:].strip():
        raise AuthenticationError(401, '请先登录', 'authentication_required')
    base = os.environ.get('AUTH_SERVICE_URL', 'http://127.0.0.1:5003').rstrip('/')
    call = HttpRequest(base + '/api/v1/auth/user', headers={'Authorization': authorization})
    try:
        with urlopen(call, timeout=5) as response:
            user = json.loads(response.read(65536))
    except HTTPError as exc:
        if exc.code == 401:
            try:
                body = json.loads(exc.read(65536))
            except (ValueError, TypeError):
                body = {}
            if not isinstance(body, dict):
                body = {}
            raise AuthenticationError(401, body.get('message', '登录会话无效'),
                                      body.get('code', 'token_invalid')) from exc
        raise AuthenticationError(503, '身份服务暂不可用，请稍后重试', 'auth_unavailable') from exc
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        raise AuthenticationError(503, '身份服务暂不可用，请稍后重试', 'auth_unavailable') from exc
    if not isinstance(user, dict) or not isinstance(user.get('id'), int) or not user.get('role'):
        raise AuthenticationError(403, '账号尚未分配角色', 'role_required')
    request.state.user = user
    return user
