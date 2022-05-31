import tornado.web
import tornado.websocket

URL = '/api/engine'


class TestHandler(tornado.web.RequestHandler):
    url_prefix = URL + '/test'

    def get(self, *args, **kwargs):
        print('yessss')


class TestHandler2(tornado.web.RequestHandler):
    url_prefix = URL + '/test2'

    def get(self, *args, **kwargs):
        print('no')


class ConnectHandler(tornado.websocket.WebSocketHandler):
    url_prefix = URL + '/sockets'

    def check_origin(self, origin):
        '''重写同源检查 解决跨域问题'''
        return True

    def open(self):
        '''新的websocket连接后被调动'''
        print('NEW CONNECTION', self)
        self.write_message('Welcome')

    def on_close(self):
        '''websocket连接关闭后被调用'''
        print('LOSE CONNECTION', self)

    def on_message(self, message):
        '''接收到客户端消息时被调用'''
        self.write_message('new message :' + message)  # 向客服端发送
        print(message)
