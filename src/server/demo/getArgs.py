import tornado.web
import tornado.ioloop

class FormHandler(tornado.web.RequestHandler):
    def get(self, *args, **kwargs):
        user_name = self.get_argument('user_name')
        password= self.get_argument('password')
        print(user_name, password)

# 设置路由
app = tornado.web.Application([(r'/login/', FormHandler)])

# 绑定监听端口
app.listen(8080)

# 启动监听
tornado.ioloop.IOLoop.instance().start()