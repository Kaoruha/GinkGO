import pandas as pd
import numpy as np
import time
from ginkgo_research.stock_filter import remove_index
import logging
import matplotlib.pyplot as plt
from ginkgo_server.data.ginkgo_mongo import ginkgo_mongo as gm
import scipy.stats as stats
import os
from multiprocessing import Queue, Pool


def cal(code1, name1, code2, name2, start_date, end_date, df1, p):
    print("Run task %s (%s)..." % (code2, os.getpid()))
    print(f"{round(p,3)}%", end="\r")
    start = time.time()
    plt.cla()
    r_rate_base = 0.95

    df2 = gm.query_stock(
        code=code2,
        start_date=start_date,
        end_date=end_date,
        frequency="d",
        adjust_flag=3,
    )
    dff1 = df1["close"].astype("float")
    dff2 = df2["close"].astype("float")
    overall_pearson_r = dff1.corr(dff2)
    print(f"Pandas computed Pearson r: {overall_pearson_r}")
    # # # 输出：使用 Pandas 计算皮尔逊相关结果的 r 值：0.2058774513561943

    _r, p = stats.pearsonr(dff1, dff2)

    plt.rcParams["font.sans-serif"] = ["Arial Unicode MS"]
    plt.title(f"[{name1} : {name2}  r={_r}")
    plt.xticks([])
    plt.plot(df1["date"], dff1, color="red", linewidth=1.0, linestyle="dashed")
    plt.plot(df2["date"], dff2, color="blue", linewidth=2.0, linestyle="solid")
    print(f"Scipy computed Pearson r: {_r} and p-value: {p}")
    if abs(_r) > r_rate_base or abs(overall_pearson_r) > r_rate_base:
        # item = {"code": r["code"], "name": r["code_name"]}
        # df = pd.DataFrame(item, index=[0])
        # high_related = high_related.append(df)
        # queue.put(code2)
        plt.savefig(f"./output/{code1}_{code2}.jpg")
    # df.to_csv(f"./output/{code1}.csv")
    end = time.time()
    print("Task %s runs %0.2f seconds." % (code2, (end - start)))


def long_time_task(name):

    print("Run task %s (%s)..." % (name, os.getpid()))

    start = time.time()

    time.sleep(1)

    end = time.time()

    print("Task %s runs %0.2f seconds." % (name, (end - start)))


if __name__ == "__main__":
    print("Parent process %s." % os.getpid())
    start = time.time()
    stock_list = remove_index()
    code_num = stock_list.shape[0]
    high_related = pd.DataFrame()
    start_date = "2020-01-01"
    end_date = "2021-01-01"
    q = Queue()
    p = Pool(7)
    count = 0
    for i1, r1 in stock_list.iterrows():
        df1 = gm.query_stock(
            code=r1["code"],
            start_date=start_date,
            end_date=end_date,
            frequency="d",
            adjust_flag=3,
        )
        for i2, r2 in stock_list.iterrows():
            count += 1
            # print(f"{count}/{code_num*code_num}")
            percent = count / code_num / code_num * 100
            if i2 <= i1:
                continue
            p.apply_async(
                cal,
                args=(
                    r1["code"],
                    r1["code_name"],
                    r2["code"],
                    r2["code_name"],
                    start_date,
                    end_date,
                    df1,
                    percent,
                ),
            )
    # for i in range(10):
    #     p.apply_async(long_time_task, args=(i,))
    print("Waiting for all subprocesses done...")
    p.close()
    p.join()
    end = time.time()
    print("All subprocesses done. Tasks runs %0.2f seconds." % (end - start))
