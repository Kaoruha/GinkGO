from pytdx.hq import TdxHq_API
import pandas as pd
import time
from pytdx.config.hosts import hq_hosts
import datetime


api = TdxHq_API(heartbeat=True)


def get_history_transaction_data():
    market = 1
    nodata_count = 0
    code = "600300"
    slice_count = 1000
    start = 0
    date = datetime.datetime.now()
    # while True:
    # import pdb

    # pdb.set_trace()
    while True:
        if nodata_count >= 50:
            break
        datenum = date.strftime("%Y%m%d")
        datenum = int(datenum)
        print(datenum)
        rs = []
        while True:
            data = api.get_history_transaction_data(
                market, code, start, slice_count, datenum
            )
            if data is None:
                break
            if len(data) == 0:
                break
            elif len(data) < slice_count:
                rs += data
                break
            else:
                rs += data
                start += slice_count

        if len(rs) == 0:
            nodata_count += 1
        else:
            df = api.to_df(rs)
            df = df.sort_values("time", ascending=True)
            df = df.reset_index(drop=True)
            print(df)
            start = 0
            end = slice_count
            nodata_count = 0

            # TODO Save the data
        date = date + datetime.timedelta(days=-1)


with api.connect("119.147.212.81", 7709):
    t0 = datetime.datetime.now()
    ### History

    # # 历史分时行情
    # data = api.to_df(api.get_history_minute_time_data(1, "600300", 20161209))

    # # 历史分笔成交
    # data = api.to_df(api.get_history_transaction_data(1, "600300", 0, 2000, 20230731))

    # # 查询分时行情
    # data = api.to_df(api.get_minute_time_data(1, "600300"))

    # # 获取实时行情
    # data = api.to_df(api.get_security_quotes([(0, "000001"), (1, "600300")]))

    # # 除权除息信息 Have no idea how to read
    # data = api.to_df(api.get_xdxr_info(1, "600300"))

    # # 查询公司信息目录 Not Work
    # data = api.to_df(api.get_company_info_content(1, "600300", "600300.txt", 0, 100))

    # # notwork
    # data = api.to_df(api.get_k_data("600300", "2017-07-03", "2017-07-10"))

    # print(data)
    get_history_transaction_data()
    t1 = datetime.datetime.now()
    print(f"Cost: {t1-t0}")
