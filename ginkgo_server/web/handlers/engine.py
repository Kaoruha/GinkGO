import tornado.web
from ginkgo_server.web.util.webSocket_base import WebsocketBase

URL = '/api/engine'


class TestHandler(tornado.web.RequestHandler):
    url_prefix = URL + '/test'

    def get(self, *args, **kwargs):
        print('yessss')


class TestHandler2(tornado.web.RequestHandler):
    url_prefix = URL + '/test2'

    def get(self, *args, **kwargs):
        print('no')


class TrySockets(WebsocketBase):
    url_prefix = URL + '/sockets'

    user = None

    def open(self):
        self.user = self
        print('NEW CONNECTION', self)

    def on_message(self, message):
        print(message)
        msg = f'hello,{self.user},{message}'
        self.user.write_message(msg)

    def on_close(self):
        self.user = None
        print('KILL CONNECTION', self)
