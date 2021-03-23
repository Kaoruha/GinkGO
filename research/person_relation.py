import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import scipy.stats as stats
from ginkgo_server.data.ginkgo_mongo import ginkgo_mongo as gm


def run():
    relate = 0.8
    date_start = "2021-02-01"
    date_end = "2021-03-01"
    df1 = gm.query_stock(
        code="sh.000001",
        start_date=date_start,
        end_date=date_end,
        frequency="d",
        adjust_flag=3,
    )["close"].astype("float")

    stock_list = gm.get_all_stockcode_by_mongo()
    high_relation = pd.DataFrame()

    for i, r in stock_list.iterrows():
        print(r.code)
        df2 = gm.query_stock(
            code=r.code,
            start_date=date_start,
            end_date=date_end,
            frequency="d",
            adjust_flag=3,
        )["close"].astype("float")
        if df2.shape[0] is not df1.shape[0]:
            continue
        overall_pearson_r = df1.corr(df2)
        print(f"{r.code}Pandas Pearson r: {overall_pearson_r}")
        # # # 输出：使用 Pandas 计算皮尔逊相关结果的 r 值：0.2058774513561943
        _r, p = stats.pearsonr(df1, df2)
        print(f"{r.code}Scipy Pearson r: {_r} and p-value: {p}")
        # # 输出：使用 Scipy 计算皮尔逊相关结果的 r 值：0.20587745135619354，以及 p-value：3.7902989479463397e-51
        if abs(overall_pearson_r) > relate or abs(_r) > relate:
            item = {"code": r.code, "name": r.code_name, "r": _r}
            high_relation = high_relation.append(item, ignore_index=True)

    print(high_relation)
    high_relation.to_csv(
        f"high_relation{date_start}_{date_end}.csv", encoding="utf_8_sig"
    )

    # # # 计算滑动窗口同步性
    # f, ax = plt.subplots(figsize=(7, 3))
    # df1.rolling(window=20, center=True).median().plot(ax=ax)
    # ax.set(xlabel="Time", ylabel="Pearson r")
    # ax.set(title=f"Overall Pearson r = {np.round(overall_pearson_r,2)}")
    # plt.show()