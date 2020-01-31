# 定义具体的异常报错
from app.libs.error import APIException


class TestError(APIException):
    code = 400
    description = (
        'this is error description'
    )


class ServerError(APIException):
    code = 500
    error_code = 999
