# coding=utf-8
import tornado.web
import tornado.ioloop
import os
from src.libs.ginkgo_logger import ginkgo_logger as gl
from src.server.handlers import get_url_patten


# 启动监听
def start_server():
    # 设置路由
    app = tornado.web.Application(get_url_patten(), debug=True)
    gl.info("路由挂载完成")

    # 绑定监听端口
    port = 8080
    app.listen(port)
    gl.info(f"监听端口：{port}")
    tornado.ioloop.IOLoop.instance().start()
