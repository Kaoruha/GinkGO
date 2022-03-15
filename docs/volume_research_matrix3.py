from pandas.core.frame import DataFrame

# from src.backtest.enums import EventType
# import numpy as np
import pandas as pd
import datetime
import os

# import numba
import time

# import math
import multiprocessing
from src.data.ginkgo_mongo import ginkgo_mongo as gm


class QEvent(object):
    def __init__(
        self,
        code: str,
        event_type: str,
        rate: float,
        signal: int,
        obserse: int = 1,
        profit: float = 0,
    ) -> None:
        super().__init__()
        self.code = code
        self.event_type = event_type  # s or o
        self.rate = rate
        self.signal = signal
        self.observe = obserse
        self.profit = profit


def merge_df(df):
    return df.sum()


def save_csv(df: DataFrame, config):
    url = "./docs/volume_research.csv"
    observe_min = config["observe_min"]
    observe_epoch = config["observe_epoch"]
    observe_iter_count = config["observe_iter_count"]
    columns_deal = []
    columns_deal.append("signal_count")
    for i in range(observe_iter_count):
        columns_deal.append("observe_" + str(observe_min + observe_epoch * i))
        columns_deal.append("profit_" + str(observe_min + observe_epoch * i))
    result = df.groupby(["rate", "signal_day"])[columns_deal].apply(merge_df)
    for i in range(observe_iter_count):
        o = observe_min + i * observe_epoch
        index = "expection_" + str(o)
        profit_index = "profit_" + str(o)
        result[index] = result[profit_index] / result["signal_count"]
    result = result.reset_index(drop=False)
    print(result)
    result.to_csv(url)
    return result


def check_one_stock(config):
    stock_queue = config["stock_queue"]
    stocks_done = config["stock_done"]
    signal_min = config["signal_min"]
    signal_epoch = config["signal_epoch"]
    signal_iter_count = config["signal_iter_count"]
    signal_max = signal_iter_count * signal_epoch + signal_min
    observe_min = config["observe_min"]
    observe_epoch = config["observe_epoch"]
    observe_iter_count = config["observe_iter_count"]
    observe_max = observe_iter_count * observe_epoch + observe_min
    rate_min = config["rate_min"]
    rate_epoch = config["rate_epoch"]
    rate_iter_count = config["rate_iter_count"]
    # rate_max = rate_iter_count * rate_epoch + rate_min
    column_names = config["df_columns"]
    q = config["q"]
    df_q = pd.DataFrame(columns=column_names)

    while stock_queue.qsize() > 0:
        code_now = stock_queue.get(block=False)
        df = gm.get_dayBar_by_mongo(code=code_now)
        count = df.shape[0]
        if count < (signal_max + observe_max + 2):
            # 如果这个股票的数据数量小于最大信号天数+最大观察天数+2，直接看下一个股票
            stocks_done.put(code_now)
            continue
        for i in range(count - signal_max - observe_max - 2):
            # 每一天的数据
            if df.iloc[i].volume == "":
                # 如果成交量为空，说明数据有问题，也直接返回，看下一个交易日的数据
                continue
            # 初始信号
            signal_0 = int(df.iloc[i].volume)
            if signal_0 == 0:
                # 如果初始信号成交量为0，直接看下一个交易日的数据
                continue
            # 如果初始信号成交量不为0，则开始查看指定信号区间内是否有信号产生
            # 先遍历每一个信号观察周期
            for s in range(signal_iter_count):
                signal_period = s * signal_epoch + signal_min
                # 再遍历每一个rate
                for r in range(rate_iter_count):
                    current_rate = r * rate_epoch + rate_min
                    # print(f'rate {stock} , {current_rate}')
                    is_ok = True
                    for j in range(1, signal_period):
                        try:
                            signal_j = int(df.iloc[i + j].volume)
                            signal_p = int(df.iloc[i + j - 1].volume)
                        except Exception as e:
                            print(e)
                            is_ok = False
                            break
                        if signal_j < signal_p:
                            is_ok = False
                            break
                    if not is_ok:
                        continue

                    try:
                        signal_1 = int(df.iloc[i + signal_period].volume)
                    except Exception as e:
                        print(e)
                        signal_1 = 0

                    if signal_1 / signal_0 < current_rate + 1:
                        continue

                    # 确认一个信号
                    item = {
                        "rate": current_rate,
                        "signal_day": signal_period,
                        "signal_count": 1,
                    }
                    df_q = df_q.append(item, ignore_index=True).fillna(0)

                    for o in range(observe_iter_count):
                        observe_period = o * observe_epoch + observe_min
                        # print(f'observe {stock} , {observe_period}')
                        observe_0 = float(df.iloc[i + signal_period + 1].close)
                        observe_1 = float(
                            df.iloc[i + signal_period + observe_period + 1].close
                        )
                        profit = (observe_1 - observe_0) / observe_0

                        item = {
                            "rate": current_rate,
                            "signal_day": signal_period,
                        }
                        item["observe_" + str(observe_period)] = 1 if profit > 0 else 0
                        item["profit_" + str(observe_period)] = profit
                        df_q = df_q.append(item, ignore_index=True).fillna(0)

                    if df_q.shape[0] > 1000:
                        q.put(df_q)
                        df_q = pd.DataFrame(columns=column_names)

        # 处理完一个
        q.put(df_q)
        df_q = pd.DataFrame(columns=column_names)
        stocks_done.put(code_now)

    print(f"Sub Process {os.getpid()} Complete.")


# check(signal_period=10, observer_period=5, stock_list=stock_list, signal_rate=4)
def q_handle(config):
    q = config["q"]
    stocks_done = config["stock_done"]
    max_count = config["max_count"]
    start_time = time.time()
    column_names = config["df_columns"]
    df_handle_count = 0
    try:
        result = pd.read_csv("./docs/volume_research.csv", index_col=0)
        print("读到数据")
        print(result)
    except Exception as e:
        print(e)
        result = pd.DataFrame(columns=column_names)

    while stocks_done.qsize() < max_count:
        done_count = stocks_done.qsize()
        msg = f"Event: {q.qsize()}  Stocks Done: [{done_count}/{max_count}]  "
        time_now = time.time()
        elapse = time_now - start_time
        msg += f"Time Cost: {datetime.timedelta(seconds=elapse)}  "
        done = done_count if done_count > 0 else 1
        msg += f"Time Left: {datetime.timedelta(seconds=elapse / done * (max_count-done_count))}"
        print(msg, end="\r")
        while q.qsize() > 0:
            e = q.get(block=False)
            result = result.append(e)
            if df_handle_count <= 10:
                df_handle_count += 1
            else:
                result = save_csv(result, config)
                df_handle_count = 0
            done_count = stocks_done.qsize()
            msg = f"Event: {q.qsize()}  Stocks Done: [{done_count}/{max_count}]  "
            time_now = time.time()
            elapse = time_now - start_time
            msg += f"Time Cost: {datetime.timedelta(seconds=elapse)}  "
            done = done_count if done_count > 0 else 1
            msg += f"Time Left: {datetime.timedelta(seconds=elapse / done * (max_count-done_count))}"
            print(msg, end="\r")
    while q.qsize() > 0:
        e = q.get(block=False)
        result = result.append(e)
    save_csv(result, config)
    print("All Codes Done!")


def RunRunMatrix(
    signal_min: int,
    signal_epoch: int,
    signal_iter_count: int,
    observe_min: int,
    observe_epoch: int,
    observe_iter_count: int,
    rate_min: int,
    rate_epoch: int,
    rate_iter_count: int,
):
    print(f"Main Process {os.getpid()}..")
    start = time.time()
    cpu_core_num = multiprocessing.cpu_count()
    thread_num = cpu_core_num - 1
    # thread_num = 2
    stock_list = gm.get_all_stockcode_by_mongo()[:100]
    stock_num = stock_list.shape[0]
    stock_queue = multiprocessing.Manager().Queue()
    for i, r in stock_list.iterrows():
        stock_queue.put(r["code"])

    print(f"Stock:{stock_num}")
    print(f"建立了一个 {thread_num} 容量的进程池")

    p = multiprocessing.Pool(thread_num)
    q = multiprocessing.Manager().Queue()
    q_done = multiprocessing.Manager().Queue()

    columns = []
    columns.append("rate")
    columns.append("signal_day")
    columns.append("signal_count")
    for i in range(observe_iter_count):
        columns.append("observe_" + str(observe_min + observe_epoch * i))
        columns.append("profit_" + str(observe_min + observe_epoch * i))

    print(columns)
    p.apply_async(
        q_handle,
        args=(
            {
                "stock_done": q_done,
                "max_count": stock_num,
                "stock_queue": stock_queue,
                "q": q,
                "df_columns": columns,
                "observe_min": observe_min,
                "observe_epoch": observe_epoch,
                "observe_iter_count": observe_iter_count,
            },
        ),
    )
    for i in range(thread_num - 1):
        config = {
            "stock_queue": stock_queue,
            "stock_done": q_done,
            "stock_num": stock_num,
            "q": q,
            "signal_min": signal_min,
            "signal_epoch": signal_epoch,
            "signal_iter_count": signal_iter_count,
            "observe_min": observe_min,
            "observe_epoch": observe_epoch,
            "observe_iter_count": observe_iter_count,
            "rate_min": rate_min,
            "rate_epoch": rate_epoch,
            "rate_iter_count": rate_iter_count,
            "df_columns": columns,
        }
        p.apply_async(
            check_one_stock,
            args=(config,),
        )

    print("Waiting for all subprocesses done...")
    p.close()
    p.join()
    end = time.time()
    print("All subprocesses done. Tasks runs %0.2f seconds." % (end - start))


if __name__ == "__main__":
    # s1  r1  o1   80s
    # s1  r1  o5   140s
    # s5  r1  o1   190s
    # s1  r5  o1   200s
    # s5  r1  o5   300s
    # s5  r5  o1   740s
    # s1  r5  o5   350s
    # s5  r5  o5   980s
    # s10 r10 o10  3000s
    signal_min = 3
    signal_epoch = 1
    signal_iter_count = 1
    observe_min = 2
    observe_epoch = 1
    observe_iter_count = 1
    rate_min = 0.2
    rate_epoch = 0.2
    rate_iter_count = 1
    RunRunMatrix(
        signal_min,
        signal_epoch,
        signal_iter_count,
        observe_min,
        observe_epoch,
        observe_iter_count,
        rate_min,
        rate_epoch,
        rate_iter_count,
    )
