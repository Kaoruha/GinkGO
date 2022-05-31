# from ..util.restful_api import RestfulAPI
import tornado.web

URL = '/api/user'


class TestHandler(tornado.web.RequestHandler):
    url_prefix = URL + '/test'

    def get(self, *args, **kwargs):
        print('yes111')


class TestHandler2(tornado.web.RequestHandler):
    url_prefix = URL + '/test2'

    def get(self, *args, **kwargs):
        print('no111')
