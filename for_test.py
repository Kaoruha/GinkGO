from ginkgo.data.ginkgo_mongo import ginkgo_mongo as gm
from ginkgo.data.stock.baostock_data import bao_instance

gm.update_stockinfo()
end_date = bao_instance.get_baostock_last_date()
# stock_list = gm.get_all_stockcode_by_mongo()
# print(stock_list)
code0 = "bj.430047"
# try:
#     last_date = gm.get_daybar_latestDate_by_mongo(code=code0)
# except Exception as e:
#     print(e)
#     last_date = bao_instance.init_date

# print(last_date)
# rs = bao_instance.get_data(
#     code=code0,
#     data_frequency="d",
#     start_date=last_date,
#     end_date=end_date,
# )
# print(rs)
# print(rs.shape[0])

stock_list = gm.get_all_stockcode_by_mongo()
print(stock_list)
code = "sh.600838"
try:
    # 尝试从mongoDB查询该指数的最新数据
    last_date = gm.get_min5_latestDate_by_mongo(code=code)
except Exception as e:
    # 失败则把开始日期设置为初识日期
    last_date = bao_instance.init_date

print(last_date)
rs = bao_instance.get_data(
    code=code,
    data_frequency="5",
    start_date=last_date,
    end_date=end_date,
)
print(rs)
if rs.shape[0] > 0:
    gm.update_min5(code, rs)
else:
    gm.set_nomin5(code=code)
