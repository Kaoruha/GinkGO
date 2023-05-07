import os
import time
import multiprocessing
import pandas as pd
import scipy.stats as stats
import matplotlib.pyplot as plt
from src.util.stock_filter import remove_index
from src.data.ginkgo_mongo import ginkgo_mongo as gm


def cal(q, code1, code2, start_date, end_date):
    print(f"Run task {code1}-{code2}  pid:{os.getpid()}...")
    start = time.time()
    plt.cla()
    # relation_rate = 0.85
    # no_relation_rate = 0.05
    confirm_rate = -0.1

    df1 = gm.query_stock(
        code=code1,
        start_date=start_date,
        end_date=end_date,
        frequency="d",
        adjust_flag=3,
    )
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
    q.put(_r)
    condition1 = confirm_rate < _r and _r < 0
    condition2 = confirm_rate < overall_pearson_r and overall_pearson_r < 0
    if condition1 or condition2:
        plt.set_loglevel("info")
        title = ""
        title += f"Pandas R = {round(overall_pearson_r,6)}"
        title += f"    Scipy R = {round(_r,6)}"
        plt.title(title)
        plt.rcParams["font.sans-serif"] = ["Arial Unicode MS"]  # Mac
        # plt.rcParams["font.sans-serif"] = ["SimHei"]  # Win
        plt.xticks([])
        plt.xlabel(f"{start_date} to {end_date}")
        plt.ylabel("price")
        plt.plot(
            df1["date"],
            dff1,
            color="red",
            linewidth=0.5,
            linestyle="solid",
            label=f"{code1}",
        )
        plt.plot(
            df2["date"],
            dff2,
            color="blue",
            linewidth=0.5,
            linestyle="solid",
            label=f"{code2}",
        )
        plt.legend(loc="upper left")
        plt.savefig(f"./output/{code1}_{code2}.jpg")
    end = time.time()
    print("Task %s runs %0.2f seconds." % (code2, (end - start)))


def combination(n, c, com=1, limit=0, per=[]):
    for pos in range(limit, n):
        t = per + [pos]
        if len(set(t)) == len(t):
            if len(t) == c:
                yield [
                    pos,
                ]
            else:
                for result in combination(
                    n,
                    c,
                    com,
                    com * pos,
                    per
                    + [
                        pos,
                    ],
                ):
                    yield [
                        pos,
                    ] + result


class comb(object):
    def __init__(self, score, combination):
        self.score = score
        self.combination = combination


if __name__ == "__main__":
    no_relation_count = 4  # 股票组合的总数
    combition22count = 0
    for i in range(no_relation_count):
        combition22count += i
    combination_head = 100  # 最后组合取前多少
    holding_stock = []
    result = pd.DataFrame()
    start_date = "2020-01-01"
    end_date = "2021-04-01"
    volume_first_count = 100  # 全股票池留成交量前XX
    cpu_core_num = multiprocessing.cpu_count()
    stock_list = remove_index()
    stock_count = stock_list.shape[0]
    target_list = pd.DataFrame()
    sort_progress = 0
    for i, r in stock_list.iterrows():
        sort_progress += 1
        df = gm.query_stock(r["code"], start_date, end_date, "d", 3)
        if df.shape[0] != 0:
            _new = {
                "code": df.iloc[0].code,
                "volumn": df["volume"].astype("float").sum(),
            }
            target_list = target_list.append(pd.DataFrame(_new, index=[0]))
            print(f"按成交量排序：{sort_progress}/{stock_count}", end="\r")
    target_list = target_list.sort_values(by=["volumn"], ascending=False).head(
        volume_first_count
    )
    target_list = target_list.reset_index(drop=True)
    for res in combination(target_list.shape[0], no_relation_count):
        start = time.time()
        # 遍历目标股票数内的持有N支股票的组合
        target_pair = []
        print(res)
        for i1 in res:
            code1 = target_list.loc[i1].code
            for i2 in res:
                if i2 <= i1:
                    continue
                code2 = target_list.loc[i2].code
                target_pair.append([code1, code2])
        # p = multiprocessing.Pool(cpu_core_num - 1)
        p = multiprocessing.Pool(int(cpu_core_num * 2 / 3))
        q = multiprocessing.Manager().Queue(len(target_pair))
        for i in target_pair:
            p.apply_async(
                cal,
                args=(
                    q,
                    i[0],
                    i[1],
                    start_date,
                    end_date,
                ),
            )
        print("Waiting for all subprocesses done...")
        p.close()
        p.join()
        end = time.time()
        score = 0
        perfect_count = 0
        min_r = 1
        while q.qsize() > 0:
            item = q.get()
            if item < 0 and item > -0.1:
                perfect_count += 1
            if abs(item) < min_r:
                min_r = item
            score += abs(item)
        codes = ""
        for i in res:
            codes += target_list.loc[i].code + ", "
        new_df = pd.DataFrame(
            {
                "score": score,
                "perfect": perfect_count,
                "min": min_r,
                "mean": score / combition22count,
                "combination": codes,
            },
            index=[0],
        )
        result = result.append(new_df)
        result = result.sort_values(by=["score"], ascending=True).head(combination_head)
        result = result.reset_index(drop=True)
        print(result)
        path = f"./output/C({volume_first_count},{no_relation_count}) no_relation.csv"
        result.to_csv(path)
        print("All subprocesses done. Tasks runs %0.2f seconds." % (end - start))
