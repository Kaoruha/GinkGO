# from config.setting import *
from ginkgo_server.libs.ginkgo_logger import ginkgo_logger as gl
from ginkgo_server.web.server import start_server
from ginkgo_server.data.ginkgo_mongo import ginkgo_mongo as gm
from ginkgo_server.data.data_portal import data_portal as gdp
from ginkgo_server.data.storage import ginkgo_storage as gs


# gl.info('Server开始启动')

# 开启tornado后端服务
start_server()


# gs.add_stock_info(code='hhhh')
# gs.test()
# gs.get_day_bar_last_date(code='sh.0000021')


# gdp.update_all_cn_stock_info()
# gdp.upsert_all_cn_adjust_factor_async(thread_num=10)
# gs.get_all_stock_code()

# gdp.update_stock_day_bar(code="sz.000822")

# gdp.update_all_stock_day_bar()

# gdp.update_stock_min5_bar(code="sh.600000")

# gm.get_all_stock_code()

# gm.update_adjust_factor()


# def update_all():
#     gm.update_stockinfo()
#     gm.update_adjustfactor()
#     gm.update_daybar_async(thread_num=4)
#     gm.update_min5_async(thread_num=2)


# update_all()
