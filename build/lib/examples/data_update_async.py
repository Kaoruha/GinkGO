"""
异步数据更新
"""
import os
import time
import tqdm
import multiprocessing
import pandas as pd
from src.data.ginkgo_mongo import ginkgo_mongo as gm
from src.data.stock.baostock_data import bao_instance
from src.data.bitcoin.coin_cap import coin_cap_instance
from multiprocessing import Manager


def update_stock_daybar(queue, code, end_date):
    # print(f"Run task pid:{os.getpid()}...")
    try:
        # 尝试从mongoDB查询该指数的最新数据
        last_date = gm.get_daybar_latestDate_by_mongo(code=code)
    except Exception:
        # 失败则把开始日期设置为初识日期
        last_date = bao_instance.init_date

    if last_date != end_date:
        bao_instance.login()
        rs = bao_instance.get_data(
            code=code,
            data_frequency="d",
            start_date=last_date,
            end_date=end_date,
        )
        bao_instance.logout()
        if rs.shape[0] > 0:
            gm.update_daybar(code, rs)
    queue.get(code)


def daybar_update_async():
    print(f"Main Process {os.getpid()}..")
    start = time.time()
    cpu_core_num = multiprocessing.cpu_count()

    stock_list = gm.get_all_stockcode_by_mongo()
    bao_instance.login()
    end_date = bao_instance.get_baostock_last_date()
    bao_instance.logout()
    print(f"Daybar准备更新至：{end_date}")
    print(f"Stock:{stock_list.shape[0]}")
    q = Manager().Queue(stock_list.shape[0])
    p = multiprocessing.Pool(cpu_core_num - 1)
    print(f"建立了一个 {cpu_core_num - 1} 容量的进程池")

    pbar = tqdm.tqdm(total=stock_list.shape[0])
    pbar.set_description("DayBar Update")

    def p_update(*a):
        pbar.update()

    for i, r in stock_list.iterrows():
        q.put(r["code"])
        p.apply_async(
            update_stock_daybar,
            args=(q, r["code"], end_date),
            callback=p_update,
        )

    print("Waiting for all subprocesses done...")
    p.close()
    p.join()
    end = time.time()
    print(f"{q.qsize()} 条更新失败")
    if q.qsize() > 0:
        error_list = []
        while True:
            try:
                code = q.get(block=False)
                print(code)
                error_list.append(code)
            except Exception as e:
                print(e)
                break

    print("All Daybar subprocesses done. Tasks runs %0.2f seconds." % (end - start))


def update_adjust_factor(queue, code):
    bao_instance.login()
    rs = bao_instance.get_adjust_factor(code=code)
    bao_instance.logout()
    if rs.shape[0] > 0:
        gm.upsert_adjustfactor(data_frame=rs)
    queue.get(code)


def adjust_factor_update_async():
    print(f"Main Process {os.getpid()}.")
    start = time.time()
    cpu_core_num = multiprocessing.cpu_count()

    stock_list = gm.get_all_stockcode_by_mongo()
    print(stock_list.shape[0])
    q = Manager().Queue(stock_list.shape[0])
    p = multiprocessing.Pool(cpu_core_num - 1)
    print(f"建立了一个 {cpu_core_num - 1} 容量的进程池")

    pbar = tqdm.tqdm(total=stock_list.shape[0])
    pbar.set_description("AdjustFactor Update")

    def p_update(*a):
        pbar.update()

    for i, r in stock_list.iterrows():
        q.put(r["code"])
        p.apply_async(
            update_adjust_factor,
            args=(q, r["code"]),
            callback=p_update,
        )
    print("Waiting for all subprocesses done...")
    p.close()
    p.join()
    end = time.time()
    print(
        "All AdjustFactor subprocesses done. Tasks runs %0.2f seconds." % (end - start)
    )


def update_stock_min5(queue, code, end_date):
    # print(f"Run task pid:{os.getpid()}...")
    try:
        # 尝试从mongoDB查询该指数的最新数据
        last_date = gm.get_min5_latestDate_by_mongo(code=code)
    except Exception:
        # 失败则把开始日期设置为初识日期
        last_date = bao_instance.init_date

    if last_date != end_date:
        bao_instance.login()
        rs = bao_instance.get_data(
            code=code,
            data_frequency="5",
            start_date=last_date,
            end_date=end_date,
        )
        bao_instance.logout()
        if rs.shape[0] > 0:
            gm.update_min5(code, rs)
        else:
            gm.set_nomin5(code=code)
    queue.get(code)


def min5_update_async():
    print(f"Main Process {os.getpid()}.")
    start = time.time()
    cpu_core_num = multiprocessing.cpu_count()

    stock_list = gm.get_all_stockcode_by_mongo()
    insert_list = []

    for i, r in stock_list.iterrows():
        if gm.check_stock_min5(code=r["code"]):
            insert_list.append(r["code"])
    print(f"Stock:{stock_list.shape[0]}, HasMin5:{len(insert_list)}")
    bao_instance.login()
    end_date = bao_instance.get_baostock_last_date()
    bao_instance.logout()
    print(f"Min5准备更新至：{end_date}")
    q = Manager().Queue(stock_list.shape[0])
    p = multiprocessing.Pool(cpu_core_num - 1)
    print(f"建立了一个 {cpu_core_num - 1} 容量的进程池")

    pbar = tqdm.tqdm(total=len(insert_list))
    pbar.set_description("更新Min5")

    def p_update(*a):
        pbar.update()

    for i in insert_list:
        q.put(i)
        p.apply_async(
            update_stock_min5,
            args=(q, i, end_date),
            callback=p_update,
        )
    print("Waiting for all subprocesses done...")
    p.close()
    p.join()
    end = time.time()
    print(f"{q.qsize()} 条更新失败")
    if q.qsize() > 0:
        error_list = []
        while True:
            try:
                code = q.get(block=False)
                print(code)
                error_list.append(code)
            except Exception as e:
                print(e)
                break

    print("All Min5 subprocesses done. Tasks runs %0.2f seconds." % (end - start))


def update_coin_min1(queue, code):
    if not gm.is_coin_exist:
        print("虚拟币不在更新列表内，请检查代码")
        return
    # 从后往后更新
    end_time = gm.get_coin_tail_time_by_mongo(coin_id=code)
    forward_go = True
    start_time = end_time - coin_cap_instance.one_day_sec
    empty_count = 0
    insert_df = pd.DataFrame()
    split_count = 10000
    while forward_go:
        start_time += coin_cap_instance.one_day_sec
        rs = coin_cap_instance.get_min_data_by_time(
            coin_id=code, interval="m1", time_start=start_time
        )
        if rs.shape[0] == 0:
            empty_count += 1
            print(f"空数据{empty_count}次")
            forward_go = False if empty_count >= 2 else True
        else:
            insert_df = insert_df.append(rs)
            if insert_df.shape[0] > split_count:
                gm.upsert_coin_m1(coin_id=code, df=insert_df)
                insert_df = pd.DataFrame()

    # 从前往前更新
    backward_go = True
    start_time = (
        gm.get_coin_head_time_by_mongo(coin_id=code) + coin_cap_instance.one_day_sec
    )

    while backward_go:
        start_time -= coin_cap_instance.one_day_sec
        rs = coin_cap_instance.get_min_data_by_time(
            coin_id=code, interval="m1", time_start=start_time
        )
        if rs.shape[0] == 0:
            empty_count += 1
            print(f"空数据{empty_count}次")
            backward_go = False if empty_count >= 2 else True
        else:
            insert_df = insert_df.append(rs)
            if insert_df.shape[0] > split_count:
                gm.upsert_coin_m1(coin_id=code, df=insert_df)
                insert_df = pd.DataFrame()
    if insert_df.shape[0] > 0:
        gm.upsert_coin_m1(coin_id=code, df=insert_df)
    queue.get(code)


def coin_udpate_async():
    print(f"Main Process {os.getpid()}.")
    start = time.time()
    cpu_core_num = multiprocessing.cpu_count()

    coin_list = gm.get_coin_list_by_mongo()
    print(coin_list)
    q = Manager().Queue(coin_list.shape[0])
    p = multiprocessing.Pool(cpu_core_num - 1)
    print(f"建立了一个 {cpu_core_num - 1} 容量的进程池")

    pbar = tqdm.tqdm(total=coin_list.shape[0])
    pbar.set_description("更新Coin")

    def p_update(*a):
        pbar.update()

    for i, r in coin_list.iterrows():
        q.put(r["id"])
        p.apply_async(
            update_coin_min1,
            args=(q, r["id"]),
            callback=p_update,
        )

    print("Waiting for all subprocesses done...")
    p.close()
    p.join()
    end = time.time()
    print(f"{q.qsize()} 条更新失败")
    if q.qsize() > 0:
        error_list = []
        while True:
            try:
                code = q.get(block=False)
                print(code)
                error_list.append(code)
            except Exception as e:
                print(e)
                break

    print("All Coin subprocesses done. Tasks runs %0.2f seconds." % (end - start))


if __name__ == "__main__":
    gm.update_stockinfo()
    adjust_factor_update_async()
    daybar_update_async()
    min5_update_async()
