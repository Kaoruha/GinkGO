# from ..util.restful_api import RestfulAPI
import tornado.web

URL = '/engine'


class TestHandler(tornado.web.RequestHandler):
    url_prefix = URL + '/test'

    def get(self, *args, **kwargs):
        print('yessss')



class TestHandler2(tornado.web.RequestHandler):
    url_prefix = URL + '/test2'

    def get(self, *args, **kwargs):
        print('no')
