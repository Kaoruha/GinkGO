# from config.setting import *
from ginkgo.libs.ginkgo_logger import ginkgo_logger as gl
from ginkgo.web.server import start_server

# from ginkgo.data.ginkgo_mongo import ginkgo_mongo as gm
# from ginkgo.data.data_portal import data_portal as gdp
# from ginkgo.data.storage import ginkgo_storage as gs


gl.info("Server开始启动")

# 开启tornado后端服务
start_server()
