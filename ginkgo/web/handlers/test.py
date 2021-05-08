import tornado.web

URL = '/api/test'


class FlutterTestHandler(tornado.web.RequestHandler):
    url_prefix = URL + '/flutter'

    def get(self, *args, **kwargs):
        print('yes111')