# coding=utf-8

import tornado.web
import tornado.ioloop

# 定义处理类
class IndexHandler(tornado.web.RequestHandler):
    # 接受GET方式处理
    def get(self, *args, **kwargs):
        self.write('hello, ginkgo-tornado!')


# 设置路由
app = tornado.web.Application([
    (r'/',IndexHandler)
    ])

# 绑定监听端口
app.listen(8080)


# 启动监听
tornado.ioloop.IOLoop.instance().start()