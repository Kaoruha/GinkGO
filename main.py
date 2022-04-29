# from config.setting import *
from src.libs import GINKGOLOGGER as gl
from src.web.server import start_server

# from src.data.ginkgo_mongo import ginkgo_mongo as gm
# from src.data.data_portal import data_portal as gdp
# from src.data.storage import ginkgo_storage as gs


gl.logger.info("Server启动")

# 开启tornado后端服务
start_server()
