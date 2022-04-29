import functools
from ..libs.error_code import AuthorizationException
from src.config.setting import TOKEN_EXPIRATION
from src.config.secure import SECRET_KEY
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired, BadSignature
from ..models.user import User
from ..validators.forms import TokenForm

# from flask import request


def creat_token(uid):
    """
    创建Token
    :param uid: 用户ID
    :return: 该用户此次获取的Token
    """
    s = Serializer(SECRET_KEY, expires_in=TOKEN_EXPIRATION)
    token = s.dumps({"uid": uid}).decode("ascii")
    return token


def verify_token(token):
    d = {"token": token}
    form = TokenForm(data=d)
    s = Serializer(SECRET_KEY)

    try:
        data = s.loads(form.token.data)
    except SignatureExpired:
        raise AuthorizationException(msg="Token已过期")
    except BadSignature:
        raise AuthorizationException(msg="非法Token")
    user = User.query.filter_by(id=data["uid"]).first()
    return user.account


def login_required(view_func):
    @functools.wraps(view_func)
    def verify_t(*args, **kwargs):
        # 1、从请求头上拿到token
        try:
            token = request.headers["Authorization"]
        except Exception:
            # 1.1、如果没拿到，返回没有权限
            raise AuthorizationException()
        # 1.2、如果拿到Token，开始校验Token有效性
        s = Serializer(SECRET_KEY)
        d = {"token": token}
        form = TokenForm(data=d)
        try:
            data = s.loads(form.token.data)
        except SignatureExpired:
            raise AuthorizationException(msg="Token已过期")
        except BadSignature:
            raise AuthorizationException(msg="非法Token")
        return view_func(*args, **kwargs)

    return verify_t


def get_account_by_token():
    try:
        token = request.headers["Authorization"]
    except Exception:
        # 1.1、如果没拿到，返回没有权限
        raise AuthorizationException()
    t = verify_token(token)
    return t
