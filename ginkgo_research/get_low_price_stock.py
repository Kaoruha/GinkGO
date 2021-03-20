import datetime
import time
import pandas as pd
from ginkgo_server.data.ginkgo_mongo import ginkgo_mongo as gm
import multiprocessing
import queue
import os
import signal

def signal_handler():
    


def check_low(code):
    print("Run task %s (%s)..." % (code, os.getpid()))
    start = time.time()
    df = gm.query_stock(
        code=code,
        start_date="2021-03-18",
        end_date="2021-03-18",
        frequency="d",
        adjust_flag=3,
    )
    db_time = time.time()
    if df.shape[0] == 0:
        return
    if float(df.close) <= 10:
        low_stock = {
            "code": row["code"],
            "name": row["code_name"],
            "price": float(df.close),
        }
        q.put(low_stock)
    list_time = time.time()
    print(
        f"{index}/{stock_list.shape[0]}  查询耗时:{round(db_time-start, 3)}s  处理耗时:{round(list_time-db_time, 3)}s  收盘价:{float(df.close)}",
        end="\r",
    )


if __name__ == "__main__":
    print("Parent process %s." % os.getpid())
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    start = time.time()
    stock_list = gm.get_all_stockcode_by_mongo()
    low_list = []
    q = queue.Queue()
    p = multiprocessing.Pool(7)
    begin_time = time.time()
    for index, row in stock_list.iterrows():
        p.apply_async(
            check_low,
            args=[
                row["code"],
            ],
        )
    print("Waiting for all subprocesses done...")
    p.close()
    p.join()
    end = time.time()
    print("All subprocesses done. Tasks runs %0.2f seconds." % (end - start))
    df = pd.DataFrame()
    while True:
        try:
            info = q.get(block=False)  # 获取消息的阻塞时间
            print(info)
            df = df.append({"code": info})
        except queue.Empty:
            # 事件列表为空时，输出现在的时间
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\rData_list is Empty!! {now}", end="")
    # print('尝试存储')
    df.to_csv(path_or_buf="./low_price.csv", encoding="utf_8_sig")
    # print('存储成功')