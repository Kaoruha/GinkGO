import pandas as pd
import time
from ginkgo_research.stock_filter import remove_index
import matplotlib.pyplot as plt
from ginkgo_server.data.ginkgo_mongo import ginkgo_mongo as gm
import scipy.stats as stats
import os
from multiprocessing import Queue, Pool


def cal(code1, name1, code2, name2, start_date, end_date, df1, percent):
    print(f"Run task {code1}-{code2}  pid:{os.getpid()}...")
    print(f"{round(percent,3)}%", end="\r")
    start = time.time()
    plt.cla()
    relation_rate = 0.85
    no_relation_rate = 0.05

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
    _r, p = stats.pearsonr(dff1, dff2)
    print(f"Scipy computed Pearson r: {_r} and p-value: {p}")

    plt.rcParams["font.sans-serif"] = ["Arial Unicode MS"]
    plt.title(f"[{name1} : {name2}  r={_r}")
    plt.xticks([])
    plt.xlabel(f"{start_date} to {end_date}")
    plt.ylabel("price")
    plt.plot(
        df1["date"],
        dff1,
        color="red",
        linewidth=0.5,
        linestyle="solid",
        label=f"{name1}",
    )
    plt.plot(
        df2["date"],
        dff2,
        color="blue",
        linewidth=0.5,
        linestyle="solid",
        label=f"{name2}",
    )
    plt.legend(loc="upper left")
    condition1 = abs(_r) > relation_rate or abs(overall_pearson_r) > relation_rate
    condition2 = (
        abs(_r) < no_relation_rate and abs(overall_pearson_r) < no_relation_rate
    )
    if condition1 or condition2:
        plt.savefig(f"./output/{code1}_{code2}.jpg")
    end = time.time()
    print("Task %s runs %0.2f seconds." % (code2, (end - start)))


if __name__ == "__main__":
    print("Parent process %s." % os.getpid())
    start = time.time()
    stock_list = remove_index()
    code_num = stock_list.shape[0]
    high_related = pd.DataFrame()
    start_date = "2020-01-01"
    end_date = "2021-01-01"
    q = Queue()
    p = Pool(12)
    loop = 0
    target_list = stock_list[0:500]
    for i1, r1 in target_list.iterrows():
        df1 = gm.query_stock(
            code=r1["code"],
            start_date=start_date,
            end_date=end_date,
            frequency="d",
            adjust_flag=3,
        )
        count = 0
        for i2, r2 in stock_list.iterrows():
            count += 1
            percent = (
                (count + loop * stock_list.shape[0])
                / 2
                / (stock_list.shape[0] * target_list.shape[0])
                * 100
            )
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
        loop += 1
    # for i in range(10):
    #     p.apply_async(long_time_task, args=(i,))
    print("Waiting for all subprocesses done...")
    p.close()
    p.join()
    end = time.time()
    print("All subprocesses done. Tasks runs %0.2f seconds." % (end - start))