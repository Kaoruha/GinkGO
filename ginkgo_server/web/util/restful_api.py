from tornado import web

class RestfulAPI(web.RequestHandler):
    def __init__(self, url=''):
        self.url = url