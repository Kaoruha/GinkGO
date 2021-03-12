import datetime
import time
import pandas as pd
from ginkgo_server.data.ginkgo_mongo import ginkgo_mongo as gm


if __name__ == "__main__":
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    stock_list = gm.get_all_stockcode_by_mongo()[300:400]
    low_list = []
    begin_time = time.time()
    for index, row in stock_list.iterrows():
        start = time.time()
        df = gm.query_stock(
            code=row["code"],
            start_date="2021-03-10",
            end_date="2021-03-10",
            frequency="d",
            adjust_flag=3,
        )
        db_time = time.time()
        if df.shape[0] == 0:
            continue
        if float(df.close) <= 10:
            low_stock = {
                "code": row["code"],
                "name": row["code_name"],
                "price": float(df.close),
            }
            low_list.append(low_stock)
        list_time = time.time()
        print(
            f"{index}/{stock_list.shape[0]}  查询耗时:{round(db_time-start, 3)}s  处理耗时:{round(list_time-db_time, 3)}s  收盘价:{float(df.close)}",
            end="\r",
        )
    print("\n")
    filter_time = time.time()
    _df = pd.DataFrame(low_list)
    end_time = time.time()
    print(stock_list.shape[0])
    print(
        f"查询耗时:{round(filter_time-begin_time, 3)}s  处理耗时:{round(end_time-filter_time, 3)}s  总耗时:{round(end_time-begin_time, 3)}s   平均耗时:{round((end_time-begin_time)/stock_list.shape[0], 3)}s"
    )
    # print('尝试存储')
    # _df.to_csv(path_or_buf='./low_price.csv', encoding='utf_8_sig')
    # print('存储成功')
