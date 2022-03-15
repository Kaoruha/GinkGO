from multiprocessing.pool import RUN
import numpy as np
import pandas as pd
import datetime
import os
import time
import math
import multiprocessing
from src.data.ginkgo_mongo import ginkgo_mongo as gm


def check(config):
    stocks = config["codes"]
    stock_queue = config["stock_queue"]
    signal_queue = config["signal_queue"]
    bull_queue = config["bull_queue"]
    bear_queue = config["bear_queue"]
    signal_period = config["signal_period"]
    observe_period = config["observe_period"]
    signal_rate = config["signal_rate"]
    for index, row in stocks.iterrows():
        stock = row["code"]
        df = gm.get_dayBar_by_mongo(code=stock)
        count = df.shape[0]
        if count < (signal_period + observe_period + 2):
            stock_queue.put(stock)
            continue
        for i in range(count - signal_period - observe_period - 2):
            if df.iloc[i].volume == "":
                continue
            signal_0 = int(df.iloc[i].volume)
            if signal_0 == 0:
                continue
            is_ok = True
            for j in range(1, signal_period):
                try:
                    signal_j = int(df.iloc[i + j].volume)
                    signal_p = int(df.iloc[i + j - 1].volume)
                except:
                    is_ok = False
                    break
                if signal_j < signal_p:
                    is_ok = False
                    break

            if not is_ok:
                continue

            try:
                signal_1 = int(df.iloc[i + signal_period].volume)
            except:
                signal_1 = 0

            if signal_1 / signal_0 < signal_rate + 1:
                continue

            signal_queue.put(1)
            observe_0 = float(df.iloc[i + signal_period + 1].close)
            observe_1 = float(df.iloc[i + signal_period + observe_period + 1].close)
            observe_rate = (observe_1 - observe_0) / observe_0

            if observe_rate > 0:
                bull_queue.put(observe_rate)
            else:
                bear_queue.put(observe_rate)
        stock_queue.put(stock)
        p_update(config)


# check(signal_period=10, observer_period=5, stock_list=stock_list, signal_rate=4)
def p_update(config):
    stock_queue = config["stock_queue"]
    signal_queue = config["signal_queue"]
    bull_queue = config["bull_queue"]
    stock_num = config["stock_num"]
    bear_queue = config["bear_queue"]
    signal_period = config["signal_period"]
    observe_period = config["observe_period"]
    signal_rate = config["signal_rate"]
    bull_rate = []
    bear_rate = []
    bear_rate_mean = 0
    bull_rate_mean = 0
    now = datetime.datetime.now().strftime("%y-%m-%d %H:%M:%S")
    msg = f"{now}  (SP:{signal_period}, OP:{observe_period}, SR:{signal_rate})  "
    msg += f"进度: {round(stock_queue.qsize()/stock_num*100,2)}%  "
    msg += f"信号: {signal_queue.qsize()}  "
    if signal_queue.qsize() > 0:
        bull_pct = bull_queue.qsize() / signal_queue.qsize()
        bear_pct = bear_queue.qsize() / signal_queue.qsize()
    else:
        bull_pct = 0
        bear_pct = 0
    msg += f"上涨: {bull_queue.qsize()}[{round(bull_pct*100,2)}%]  "
    msg += f"下跌: {bear_queue.qsize()}[{round(bear_pct*100,2)}%]  "
    if stock_queue.qsize() == stock_num:
        while bull_queue.qsize() > 0:
            bull_rate.append(bull_queue.get())
        while bear_queue.qsize() > 0:
            bear_rate.append(bear_queue.get())
        
        if signal_queue.qsize() > 0:
            if len(bull_rate) > 0:
                bull_rate_mean = np.mean(np.array(bull_rate))
                msg += f"上涨均幅: {round(bull_rate_mean*100,2)}% "

            if len(bear_rate) > 0:
                bear_rate_mean = np.mean(np.array(bear_rate))
                msg += f"下跌均幅: {round(bear_rate_mean*100,2)}% "
            msg += (
                f"期望收益: {round((bull_rate_mean*bull_pct+bear_rate_mean*bear_pct)*100,4)}%"
            )
    print(msg)
    if stock_queue.qsize() == stock_num:
        dict = {
            "create_time": datetime.datetime.now().strftime("%y-%m-%d %H:%M"),
            "expection": round(
                bull_rate_mean * bull_pct + bear_rate_mean * bear_pct, 6
            ),
            "sample_count": signal_queue.qsize(),
            "signal_period": signal_period,
            "ovserve_period": observe_period,
            "bull_num": len(bull_rate),
            "bull_rate": bull_rate_mean,
            "bear_num": len(bear_rate),
            "bear_rate": bear_rate_mean,
            "rate": signal_rate,
        }
        df = pd.DataFrame(dict, index=[0])
        try:
            result = pd.read_csv("./docs/volume_research.csv", index_col=0)
            print("读到数据")
            print(result)
        except:
            result = pd.DataFrame()
        result = result.append(df)
        print("准备保存")
        result = result.sort_values("expection", ascending=False)
        result = result.reset_index(drop=True)
        print(result)
        result.to_csv("./docs/volume_research.csv")
        print("csv更新成功")


def RunRun(sp: int, op: int, rate_: float):
    print(f"Main Process {os.getpid()}..")

    start = time.time()
    cpu_core_num = multiprocessing.cpu_count()
    thread_num = cpu_core_num - 1
    # thread_num = 4
    stock_list = gm.get_all_stockcode_by_mongo()
    stock_num = stock_list.shape[0]
    print(f"Stock:{stock_num}")
    print(f"建立了一个 {thread_num} 容量的进程池")

    p = multiprocessing.Pool(thread_num)
    stock_queue = multiprocessing.Manager().Queue()
    signal_queue = multiprocessing.Manager().Queue()
    bull_queue = multiprocessing.Manager().Queue()
    bear_queue = multiprocessing.Manager().Queue()
    signal_period = sp
    observe_period = op
    rate = rate_
    epoch_num = math.floor(stock_num / thread_num)

    stock_lists = []
    for i in range(thread_num):
        if i < thread_num - 1:
            df_tem = stock_list[epoch_num * i : epoch_num * (i + 1)]
        else:
            df_tem = stock_list[epoch_num * i :]
        stock_lists.append(df_tem)

    for r in stock_lists:
        config = {
            "stock_queue": stock_queue,
            "signal_queue": signal_queue,
            "bull_queue": bull_queue,
            "bear_queue": bear_queue,
            "stock_num": stock_num,
            "signal_period": signal_period,
            "observe_period": observe_period,
            "signal_rate": rate,
            "codes": r,
        }
        p.apply_async(
            check,
            args=(config,),
            # callback=p_update,
        )

    print("Waiting for all subprocesses done...")
    p.close()
    p.join()
    end = time.time()
    print("All Daybar subprocesses done. Tasks runs %0.2f seconds." % (end - start))


if __name__ == "__main__":
    signal_max = 10
    observe_max = 20
    rate_epoch = 0.5
    rate_iter_max = 20
    for i in range(1, signal_max+1,2):
        for j in range(1, observe_max+1,2):
            for k in range(rate_iter_max+1):
                rate = k * rate_epoch
                RunRun(i, j, rate)