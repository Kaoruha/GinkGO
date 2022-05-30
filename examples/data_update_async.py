import os
import time
import datetime
import math
import tqdm
import threading
import multiprocessing
import pandas as pd
from ginkgo.data.ginkgo_mongo import ginkgo_mongo as gm
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.data.stock.baostock_data import bao_instance
from ginkgo.data.bitcoin.coin_cap import coin_cap_instance
from multiprocessing import Manager


def update_stock_daybar(queue_get, queue_put, codesdf, end_date):
    gl.logger.warn(f"Sub Process {os.getpid()}..")
    for i, r in codesdf.iterrows():
        code = r["code"]
        try:
            # 尝试从mongoDB查询该指数的最新数据
            last_date = gm.get_daybar_latestDate_by_mongo(code=code)
        except Exception:
            # 失败则把开始日期设置为初识日期
            last_date = bao_instance.init_date

        if last_date != end_date:
            rs = bao_instance.get_data(
                code=code,
                data_frequency="d",
                start_date=last_date,
                end_date=end_date,
            )
            if rs.shape[0] > 0:
                gm.update_daybar(code, rs)

        queue_put.put(code)
        queue_get.get()


def process_pct(queue_get, queue_put, pbar):
    t = datetime.datetime.now()
    t = t.strftime("%H:%M:%S")
    pbar.set_description(f"{t} DayBar Update")
    while True:
        try:
            e = queue_put.get(block=False)
            pbar.update()
        except Exception as e:
            if queue_get.qsize() == 0:
                break


def daybar_update_async():
    gl.logger.critical(f"Main Process {os.getpid()}..")
    start = time.time()
    cpu_core_num = multiprocessing.cpu_count()
    process_num = 12

    stock_list = gm.get_all_stockcode_by_mongo()
    stock_list = stock_list[1000:1100]

    stock_num = len(stock_list)
    end_date = bao_instance.get_baostock_last_date()

    gl.logger.info(f"Daybar准备更新至：{end_date}")
    gl.logger.info(f"Stock:{stock_list.shape[0]}")

    q_put = Manager().Queue(stock_list.shape[0])
    q_get = Manager().Queue(stock_list.shape[0])
    p = multiprocessing.Pool(process_num)

    for i in range(stock_num):
        q_get.put(1)

    gl.logger.info(f"建立了一个 {process_num} 容量的进程池")
    split_count = math.ceil(stock_num / process_num)

    pbar = tqdm.tqdm(total=stock_list.shape[0])
    pbar.set_description("DayBar Update")
    # 启一个监控的线程
    gl.logger.info(f"启动监控线程")
    controller = threading.Thread(target=process_pct, args=(q_get, q_put, pbar))
    controller.start()

    # 启动进程池
    for i in range(process_num):
        a = i * split_count
        b = stock_num if i == process_num - 1 else (i + 1) * split_count
        # slist = stock_list[a:b].values.tolist()
        slist = stock_list[a:b]

        p.apply_async(
            update_stock_daybar,
            args=(q_get, q_put, slist, end_date),
        )

    gl.logger.info("Waiting for all subprocesses done...")
    p.close()
    p.join()
    controller.join()
    end = time.time()
    gl.logger.critical(
        "All Daybar subprocesses done. Tasks runs %0.2f seconds." % (end - start)
    )


def update_stock_min5(queue_get, queue_put, codesdf, end_date):
    gl.logger.warning(f"Sub pid:{os.getpid()}...")
    for i in codesdf:
        code = i
        try:
            # 尝试从mongoDB查询该指数的最新数据
            last_date = gm.get_min5_latestDate_by_mongo(code=code)
        except Exception:
            # 失败则把开始日期设置为初识日期
            last_date = bao_instance.init_date

        if last_date != end_date:
            rs = bao_instance.get_data(
                code=code,
                data_frequency="5",
                start_date=last_date,
                end_date=end_date,
            )
            if rs.shape[0] > 0:
                gm.update_min5(code, rs)
            else:
                gm.set_nomin5(code=code)
        queue_put.put(code)
        queue_get.get()


def min5_update_async():
    gl.logger.critical(f"Main Process {os.getpid()}.")
    start = time.time()
    cpu_core_num = multiprocessing.cpu_count()
    process_num = 12

    stock_list = gm.get_all_stockcode_by_mongo()
    stock_list = stock_list[500:525]

    stock_num = len(stock_list)
    end_date = bao_instance.get_baostock_last_date()

    insert_list = []

    for i, r in stock_list.iterrows():
        if gm.check_stock_min5(code=r["code"]):
            insert_list.append(r["code"])
    gl.logger.warn(f"Stock:{stock_list.shape[0]}, HasMin5:{len(insert_list)}")
    gl.logger.debug(f"Min5准备更新至：{end_date}")
    q_put = Manager().Queue(len(insert_list))
    q_get = Manager().Queue(len(insert_list))
    p = multiprocessing.Pool(process_num)

    gl.logger.info(f"建立了一个 {process_num} 容量的进程池")

    for i in range(len(insert_list)):
        q_get.put(1)
    pbar = tqdm.tqdm(total=len(insert_list))
    pbar.set_description("更新Min5")

    # 启一个监控的线程
    gl.logger.info(f"启动监控线程")
    controller = threading.Thread(target=process_pct, args=(q_get, q_put, pbar))
    controller.start()

    split_count = math.ceil(stock_num / process_num)
    # 启动进程池
    for i in range(process_num):
        a = i * split_count
        b = stock_num if i == process_num - 1 else (i + 1) * split_count
        slist = insert_list[a:b]
        p.apply_async(
            update_stock_min5,
            args=(q_get, q_put, slist, end_date),
        )
    gl.logger.debug("Waiting for all subprocesses done...")
    p.close()
    p.join()
    controller.join()
    end = time.time()

    gl.logger.critical(
        "All Min5 subprocesses done. Tasks runs %0.2f seconds." % (end - start)
    )


if __name__ == "__main__":
    gm.update_stockinfo()
    gm.update_adjustfactor()
    daybar_update_async()
    min5_update_async()
