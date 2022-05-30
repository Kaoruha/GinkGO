import baostock as bs
import math
from ginkgo.data.ginkgo_mongo import ginkgo_mongo as gm
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


# gm.update_stockinfo()
# gm.update_adjustfactor()
# gm.update_min5_async()

if __name__ == "__main__":
    # gm.update_stockinfo()
    # gm.update_min5_async()
    l = []
    for i in range(23):
        l.append(i)

    print(l)
    c = 0
    process_num = 3

    split_count = math.ceil(len(l) / process_num)
    for i in range(process_num):
        a = i * split_count
        b = len(l) if i == process_num - 1 else (i + 1) * split_count
        print(f"{a}-{b}")
        slist = l[a:b]
        for j in slist:
            c += 1
            print(j)

    print("=" * 40)
    print(c)
    print(len(l))
