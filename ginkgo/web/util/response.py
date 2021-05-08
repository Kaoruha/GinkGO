"""
Restful API 响应封装
"""
from tornado.web import RequestHandler
from werkzeug.exceptions import HTTPException
import datetime


class APIException(HTTPException):
    msg = "Sorry, we made a mistake. >_<|||"
    error_code = 999

    def __init__(self, msg=None, error_code=None, headers=None):
        if msg:
            self.msg = msg
        if error_code:
            self.error_code = error_code
        super(APIException, self).__init__(msg, None)

    def get_body(self, environ=None):
        body = dict(
            code=self.error_code,
            description=self.msg,
            # request=request.method + ' ' + self.get_url_no_param(),
            request=RequestHandler.get_arguments(),
            time_stamp=datetime.datetime.now().strftime('%Y-%m-%d,%H:%M:%S')
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


class APIResponse(object):
    msg = "It Works Well!!"
    error_code = 200
    data = ''

    def __init__(self, msg=None, error_code=None, headers=None, data=None):
        if msg:
            self.msg = msg
        if error_code:
            self.error_code = error_code
        if data:
            self.data = data

    def get_body(self, environ=None):
        body = dict(
            code=self.error_code,
            description=self.msg,
            request=request.method + ' ' + self.get_url_no_param(),
            time_stamp=datetime.datetime.now().strftime('%Y-%m-%d,%H:%M:%S'),
            data=self.data
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