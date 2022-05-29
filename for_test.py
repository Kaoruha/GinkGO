import baostock as bs
import time
import threading
from ginkgo.data.stock.baostock_data import bao_instance as bi

# code = "bj.430047"
# start_date = "1999-07-26"
# end_date = "2022-05-01"
# dimension = "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,isST"
# bi.login()
# rs = bs.query_history_k_data_plus(
#     code,
#     dimension,
#     start_date=start_date,
#     end_date=end_date,
#     frequency="d",
#     adjustflag="3",
# )
# print(rs.error_code)
# print(rs.error_msg)


from ginkgo.data.ginkgo_mongo import ginkgo_mongo as gm

gm.update_daybar_async()
