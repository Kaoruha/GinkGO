import numpy as np
import pandas as pd
import datetime
import os
import time
import math
import multiprocessing
from src.data.ginkgo_mongo import ginkgo_mongo as gm


def GetQueueIndex(
    is_signal: bool,
    is_bull: bool,
    signal_current: int,
    observe_current: int,
    observe_iter_count: int,
    rate_current: int,
    rate_iter_count: int,
) -> int:
    epoch = 1 + observe_iter_count * 2
    round = signal_current * rate_iter_count + rate_current
    basic = epoch * round
    if is_signal:
        return basic
    iter = basic + 1 + 2 * observe_current
    if is_bull:
        return iter
    else:
        return iter + 1


def check(config):
    stock_queue = config["stock_queue"]
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
    rate_max = rate_iter_count * rate_epoch + rate_min
    stocks = config["codes"]
    q = config["q"]
    for index, row in stocks.iterrows():
        stock = row["code"]
        df = gm.get_dayBar_by_mongo(code=stock)
        count = df.shape[0]
        if count < (signal_max + observe_max + 2):
            # 如果这个股票的数据数量小于最大信号天数+最大观察天数+2，直接看下一个股票
            stock_queue.put(stock)
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

                    if signal_1 / signal_0 < current_rate + 1:
                        continue

                    # 确认一个信号
                    signal_index = GetQueueIndex(
                        is_signal=True,
                        is_bull=True,
                        signal_current=s,
                        observe_current=0,
                        observe_iter_count=observe_iter_count,
                        rate_current=r,
                        rate_iter_count=rate_iter_count,
                    )
                    # print(f"insert_index {signal_index}")
                    q[signal_index].put(df.iloc[i].date)
                    # print(f"insert done")

                    for o in range(observe_iter_count):
                        observe_period = o * observe_epoch + observe_min
                        # print(f'observe {stock} , {observe_period}')
                        observe_0 = float(df.iloc[i + signal_period + 1].close)
                        observe_1 = float(
                            df.iloc[i + signal_period + observe_period + 1].close
                        )
                        observe_rate = (observe_1 - observe_0) / observe_0

                        observe_index = GetQueueIndex(
                            is_signal=False,
                            is_bull=observe_rate > 0,
                            signal_current=s,
                            observe_current=o,
                            observe_iter_count=observe_iter_count,
                            rate_current=r,
                            rate_iter_count=rate_iter_count,
                        )
                        q[observe_index].put(observe_rate)
        stock_queue.put(stock)
        p_update(config)


# check(signal_period=10, observer_period=5, stock_list=stock_list, signal_rate=4)
def p_update(config):
    stock_queue = config["stock_queue"]
    stock_num = config["stock_num"]
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
    rate_max = rate_iter_count * rate_epoch + rate_min
    q = config["q"]
    now = datetime.datetime.now().strftime("%y-%m-%d %H:%M:%S")
    msg = f"{now}  "
    msg += f"{stock_queue.qsize()}/{stock_num} 进度: {round(stock_queue.qsize()/stock_num*100,2)}%  "
    for s in range(signal_iter_count):
        signal_period = s * signal_epoch + signal_min
        for r in range(rate_iter_count):
            rate = r * rate_epoch + rate_min
            signal_index = GetQueueIndex(
                is_signal=True,
                is_bull=True,
                signal_current=s,
                observe_current=0,
                observe_iter_count=observe_iter_count,
                rate_current=r,
                rate_iter_count=rate_iter_count,
            )
            signal_count = q[signal_index].qsize()
            msg += "\n"
            msg += f"(SP:{signal_period},Rate:{rate}) "
            msg += f"信号数:{signal_count} "
            for o in range(observe_iter_count):
                observe_period = o * observe_epoch + observe_min
                bull_index = GetQueueIndex(
                    is_signal=False,
                    is_bull=True,
                    signal_current=s,
                    observe_current=o,
                    observe_iter_count=observe_iter_count,
                    rate_current=r,
                    rate_iter_count=rate_iter_count,
                )
                bull_count = q[bull_index].qsize()
                msg += f"D{observe_period}: {round(bull_count/signal_count*100,2)}% |"

    print(msg)
    # msg += f"信号: {signal_queue.qsize()}  "
    # if signal_queue.qsize() > 0:
    #     bull_pct = bull_queue.qsize() / signal_queue.qsize()
    #     bear_pct = bear_queue.qsize() / signal_queue.qsize()
    # else:
    #     bull_pct = 0
    #     bear_pct = 0
    # msg += f"上涨: {bull_queue.qsize()}[{round(bull_pct*100,2)}%]  "
    # msg += f"下跌: {bear_queue.qsize()}[{round(bear_pct*100,2)}%]  "
    # if stock_queue.qsize() == stock_num:
    #     while bull_queue.qsize() > 0:
    #         bull_rate.append(bull_queue.get())
    #     while bear_queue.qsize() > 0:
    #         bear_rate.append(bear_queue.get())

    #     if signal_queue.qsize() > 0:
    #         if len(bull_rate) > 0:
    #             bull_rate_mean = np.mean(np.array(bull_rate))
    #             msg += f"上涨均幅: {round(bull_rate_mean*100,2)}% "

    #         if len(bear_rate) > 0:
    #             bear_rate_mean = np.mean(np.array(bear_rate))
    #             msg += f"下跌均幅: {round(bear_rate_mean*100,2)}% "
    #         msg += (
    #             f"期望收益: {round((bull_rate_mean*bull_pct+bear_rate_mean*bear_pct)*100,4)}%"
    #         )
    # print(msg)
    # if stock_queue.qsize() == stock_num:
    #     dict = {
    #         "create_time": datetime.datetime.now().strftime("%y-%m-%d %H:%M"),
    #         "expection": round(
    #             bull_rate_mean * bull_pct + bear_rate_mean * bear_pct, 6
    #         ),
    #         "sample_count": signal_queue.qsize(),
    #         "signal_period": signal_period,
    #         "ovserve_period": observe_period,
    #         "bull_num": len(bull_rate),
    #         "bull_rate": bull_rate_mean,
    #         "bear_num": len(bear_rate),
    #         "bear_rate": bear_rate_mean,
    #         "rate": signal_rate,
    #     }
    #     df = pd.DataFrame(dict, index=[0])
    #     try:
    #         result = pd.read_csv("./docs/volume_research.csv", index_col=0)
    #         print("读到数据")
    #         print(result)
    #     except:
    #         result = pd.DataFrame()
    #     result = result.append(df)
    #     print("准备保存")
    #     result = result.sort_values("expection", ascending=False)
    #     result = result.reset_index(drop=True)
    #     print(result)
    #     result.to_csv("./docs/volume_research.csv")
    #     print("csv更新成功")


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
    thread_num = 4
    stock_list = gm.get_all_stockcode_by_mongo()[:10]
    stock_num = stock_list.shape[0]
    stock_queue = multiprocessing.Manager().Queue()
    print(f"Stock:{stock_num}")
    print(f"建立了一个 {thread_num} 容量的进程池")

    p = multiprocessing.Pool(thread_num)
    q = []
    # 前s*r为信号Queue，后 s*r*2*o为每个信号对应的bullqueue与bearqueue
    q_count = (
        (1 + 2 * (observe_iter_count + 1))
        * (signal_iter_count + 1)
        * (rate_iter_count + 1)
    )
    print(f"待添加通信队列{q_count}个")
    for i in range(q_count):
        q.append(multiprocessing.Manager().Queue())  # 信号Queue
        print(f"添加了{i+1}个Queue", end="\r")

    epoch_num = math.floor(stock_num / thread_num)

    stock_lists = []
    for i in range(thread_num):
        if i < thread_num - 1:
            df_tem = stock_list[epoch_num * i : epoch_num * (i + 1)]
        else:
            df_tem = stock_list[epoch_num * i :]
        stock_lists.append(df_tem)

    for i in stock_lists:
        config = {
            "stock_queue": stock_queue,
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
            "codes": i,
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
    print("All subprocesses done. Tasks runs %0.2f seconds." % (end - start))


if __name__ == "__main__":
    signal_min = 1
    signal_epoch = 1
    signal_iter_count = 2
    observe_min = 1
    observe_epoch = 1
    observe_iter_count = 5
    rate_min = 0.1
    rate_epoch = 0.1
    rate_iter_count = 10
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

# TODO Use single Queue to handle event, includes signal happend, observe bull rate, observe bear rate.
# TODO Reduce multib