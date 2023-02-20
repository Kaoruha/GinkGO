# 在这里定义异常报错的基类
from flask import request, json
from werkzeug.exceptions import HTTPException


class APIException(HTTPException):
    code = 500
    msg = "Sorry, we made a mistake. >_<|||"
    error_code = 999

    def __init__(self, code=None, msg=None, error_code=None, headers=None):
        if code:
            self.code = code
        if msg:
            self.msg = msg
        if error_code:
            self.code = error_code
        super(APIException, self).__init__(msg, None)

    def get_body(self, environ=None):
        body = dict(
            msg=self.msg,
            error_code=self.error_code,
            request=request.method + ' ' + self.get_url_no_param()
        )
        text = json.dumps(body)
        return text

    @staticmethod
    def get_url_no_param():
        full_path = str(request.full_path)
        main_path = full_path.split('?')
        return main_path[0]

    def get_headers(self, environ=None):
        """Get a list of headers."""
        return [("Content-Type", "application/json")]


class NoException(HTTPException):
    code = 200
    msg = "Everything goes well. >-<|||"
    data = {}
    # error_code = 200

    def __init__(self, code=None, msg=None, data=None, headers=None):
        if code:
            self.code = code
        if msg:
            self.msg = msg
        if data:
            self.data = data
        super(NoException, self).__init__(msg, None)

    def get_body(self, environ=None):
        body = dict(
            msg=self.msg,
            data=self.data,
            request=request.method + ' ' + self.get_url_no_param()
        )
        text = json.dumps(body)
        return text

    @staticmethod
    def get_url_no_param():
        full_path = str(request.full_path)
        main_path = full_path.split('?')
        return main_path[0]

    def get_headers(self, environ=None):
        """Get a list of headers."""
        return [("Content-Type", "application/json")]