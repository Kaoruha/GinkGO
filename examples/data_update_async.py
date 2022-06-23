import os
import time
import datetime
import math
import tqdm
import threading
import multiprocessing
import pandas as pd
from ginkgo.data.ginkgo_mongo import ginkgo_mongo as gm
from ginkgo.data.ginkgo_mongo import GinkgoMongo
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.data.stock.baostock_data import bao_instance
from multiprocessing import Manager


def update_stock_daybar(q_stocks, q_result, end_date):
    pid = os.getpid()
    gl.logger.warning(f"Sub Process {pid}..")

    while True:
        if q_stocks.empty():
            gl.logger.critical(f"Pid {pid} End")
            break
        else:
            code = q_stocks.get(block=False)
            # 尝试从mongoDB查询该指数的最新数据
            last_date = gm.get_daybar_latestDate_by_mongo(code=code)

            if last_date != end_date:
                try:
                    rs = bao_instance.get_data(
                        code=code,
                        data_frequency="d",
                        start_date=last_date,
                        end_date=end_date,
                    )
                    if rs.shape[0] > 0:
                        gm.update_daybar(code, rs)
                except Exception as e:
                    # gl.logger.error(e)
                    q_result.put(code)
                    # TODO Need a error queue to store exception code

            q_result.put(code)


def process_pct(q_stocks, q_result, pbar, datatype):
    while True:
        # print(f"Stocck: {q_stocks.qsize()}  Result: {q_result.qsize()}")
        if q_result.empty() and q_stocks.empty():
            gl.logger.critical(f"{datatype} Update End")
            break

        t = datetime.datetime.now()
        t = t.strftime("%H:%M:%S")
        pbar.set_description(f"{t} {datatype} Update")

        try:
            e = q_result.get(block=False)
            pbar.set_description(f"{t} {e} Update")
            pbar.update()
        except Exception as e:
            if q_stocks.qsize() == 0:
                break

        # time.sleep(0.01)


def daybar_update_async():
    gl.logger.critical(f"Main Process {os.getpid()}..")
    start = time.time()
    cpu_core_num = multiprocessing.cpu_count()
    process_num = cpu_core_num

    stock_list = gm.get_all_stockcode_by_mongo()

    stock_num = len(stock_list)

    gl.logger.critical(f"Total Stocks: {stock_num}")
    end_date = bao_instance.get_baostock_last_date()

    gl.logger.info(f"Daybar准备更新至：{end_date}")
    gl.logger.info(f"Stock:{stock_list.shape[0]}")

    q_result = Manager().Queue(stock_list.shape[0])
    q_stocks = Manager().Queue(stock_list.shape[0])
    p = multiprocessing.Pool(process_num)

    for i, r in stock_list.iterrows():
        q_stocks.put(r["code"])

    gl.logger.info(f"建立了一个 {process_num} 容量的进程池")

    pbar = tqdm.tqdm(total=stock_list.shape[0])
    pbar.set_description("DayBar Update")
    # 启一个监控的线程
    gl.logger.info(f"启动监控线程")
    controller = threading.Thread(
        target=process_pct, args=(q_stocks, q_result, pbar, "DayBar")
    )
    controller.start()

    # 启动进程池
    for i in range(process_num):
        p.apply_async(
            update_stock_daybar,
            args=(q_stocks, q_result, end_date),
        )

    gl.logger.info("Waiting for all subprocesses done...")
    p.close()
    p.join()
    end = time.time()
    controller.join()
    gl.logger.critical(
        "All Daybar subprocesses done. Tasks runs %0.2f seconds." % (end - start)
    )


def update_stock_min5(q_stocks, q_result, end_date):
    pid = os.getpid()
    gl.logger.warning(f"Sub Process {pid}..")
    while True:
        if q_stocks.empty():
            gl.logger.critical(f"Pid {pid} End")
            break
        else:
            code = q_stocks.get(block=False)
            # 尝试从mongoDB查询该指数的最新数据
            last_date = gm.get_min5_latestDate_by_mongo(code=code)

            # if last_date != end_date:
            #     try:
            #         pass
            #         rs = bao_instance.get_data(
            #             code=code,
            #             data_frequency="5",
            #             start_date=last_date,
            #             end_date=end_date,
            #         )
            #         if rs.shape[0] > 0:
            #             gm.update_min5(code, rs)
            #         else:
            #             gm.set_nomin5(code=code)
            #     except Exception as e:
            #         print("================================")
            #         gl.logger.error(e)
            #         gl.logger.error(e)
            #         print("================================")
            #         q_result.put(code)

            q_result.put(code)


def min5_update_async():
    gl.logger.critical(f"Main Process {os.getpid()}.")
    start = time.time()
    cpu_core_num = multiprocessing.cpu_count()
    process_num = cpu_core_num

    stock_list = gm.get_all_stockcode_by_mongo()

    end_date = bao_instance.get_baostock_last_date()

    insert_list = []

    for i, r in stock_list.iterrows():
        if gm.check_stock_min5(code=r["code"]):
            insert_list.append(r["code"])

    gl.logger.warning(f"Min5准备更新至：{end_date}")
    stock_num = len(insert_list)
    q_result = Manager().Queue(stock_num)
    q_stocks = Manager().Queue(stock_num)
    p = multiprocessing.Pool(process_num)

    gl.logger.info(f"建立了一个 {process_num} 容量的进程池")

    for i in insert_list:
        q_stocks.put(i)
    pbar = tqdm.tqdm(total=stock_num)
    pbar.set_description("更新Min5")

    # 启一个监控的线程
    gl.logger.info(f"启动监控线程")
    controller = threading.Thread(
        target=process_pct, args=(q_stocks, q_result, pbar, "Min5")
    )
    controller.start()

    # 启动进程池
    for i in range(process_num):
        p.apply_async(
            update_stock_min5,
            args=(q_stocks, q_result, end_date),
        )
    gl.logger.debug("Waiting for all subprocesses done...")
    p.close()
    p.join()
    end = time.time()
    controller.join()

    gl.logger.critical(
        "All Min5 subprocesses done. Tasks runs %0.2f seconds." % (end - start)
    )


if __name__ == "__main__":
    from ginkgo.config.setting import VERSION

    print(VERSION)
    gm.update_stockinfo()
    gm.update_adjustfactor()
    daybar_update_async()
    min5_update_async()
