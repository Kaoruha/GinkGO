from tornado.websocket import WebSocketHandler


class WebsocketBase(WebSocketHandler):
    """
    继承WebSocketHandler基类，重写所需实例方法
    """

    url_prefix = ''

    def on_message(self, message):
        """
        接收消息
        """
        raise NotImplementedError("Must implement on_message()")

    def open(self):
        """
        新的websocket连接后被调动
        """
        print('NEW CONNECTION', self)

    def on_close(self):
        """
        websocket连接关闭后被调用
        """
        print('KILL CONNECTION', self)

    def check_origin(self, origin):
        """
        重写同源检查 解决跨域问题
        """
        return True