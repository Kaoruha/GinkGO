# from config.setting import *
from ginkgo_server.libs.ginkgo_logger import ginkgo_logger as gl
from ginkgo_server.web.server import start_server

gl.info('Server开始启动')

# 开启tornado后端服务
start_server()
