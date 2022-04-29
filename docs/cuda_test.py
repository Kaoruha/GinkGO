"""
Author: Suny
Date: 2021-09-09 16:36:39
LastEditors: Suny
LastEditTime: 2021-09-09 17:44:56
Description: This is an app for iot digital twin. In the future will use auto construction modeling tech to make the world more real.
"""
import time
import datetime
import numpy as np
import pandas as pd
import math
from numba import cuda
from ginkgo.data.ginkgo_mongo import ginkgo_mongo as gm

# Configuration
TPB = 32
signal_min = 2
signal_epoch = 1
signal_iter_count = 10
observe_min = 2
observe_epoch = 1
observe_iter_count = 10
rate_min = 0.2
rate_epoch = 0.5
rate_iter_count = 10
url = "./docs/volume_research/volume_research_cuda"
threadsperblock = (TPB * 10, 1)


# 0 open
# 1 high
# 2 low
# 3 close
# 4 pre_close
# 5 volume
# 6 amount
# 7 turn
# 8 pct_change
#     open  high   low  close  pre_close      volume       amount       turn  pct_change
# 0   9.00  9.39  8.88   9.20       7.80  20538936.0  187416592.0  45.642078   17.948709
# 1   9.08  9.15  8.71   8.93       9.20   8569085.0   76443984.0  19.042412   -2.930000
# 2   8.89  9.82  8.82   9.82       8.93  11553022.0  108926936.0  25.673382    9.970000
# 3   9.88  9.88  9.46   9.48       9.82  12853352.0  123780464.0  28.563004   -3.460000
# 4   9.45  9.55  9.12   9.38       9.48   7218816.0   67312552.0  16.041813   -1.050000
# 5   9.38  9.39  9.10   9.28       9.38   3776984.0   34936920.0   8.393298   -1.070000
# 6   9.28  9.39  9.08   9.29       9.28   3194653.0   29544990.0   7.099229    0.110000
# 7   9.28  9.28  8.73   8.81       9.29   5186779.0   46308992.0  11.526176   -5.170000
# 8   8.74  8.74  8.25   8.39       8.81   4428764.0   37232832.0   9.841698   -4.770000
# 9   8.30  8.54  8.26   8.30       8.39   2488364.0   20873140.0   5.529698   -1.070000
# 10  8.30  8.38  7.96   8.11       8.30   2295640.0   18623816.0   5.101422   -2.290000
# 11  8.11  8.18  7.89   8.09       8.11   1738656.0   14001976.0   3.863680   -0.250000
# 12  8.06  8.20  7.88   7.89       8.09   2073638.0   16696763.0   4.608084   -2.470000
# 13  7.80  7.96  7.70   7.93       7.89   1450827.0   11411731.0   3.224060    0.510000

# GPU Code
@cuda.jit
def process_gpu(df, result_global) -> None:
    tx = cuda.blockIdx.x * cuda.blockDim.x + cuda.threadIdx.x
    # 超出每一行长度的线程，返回
    # 不然数据会挤到下一行，虽然不知道为什么会这样
    # TODO 针对GPU优化
    if tx > df.shape[0]:
        return

    # 数据长度小于信号天数+观察天数的，不看了直接返回
    if (
        df.shape[0]
        < signal_iter_count * signal_epoch
        + signal_min
        + observe_min
        + observe_epoch * observe_iter_count
    ):
        return

    # Iteration with signal days and observe days
    for s in range(signal_iter_count):
        signal = s * signal_epoch + signal_min
        if tx < signal:
            return
        # 判断是否有信号，如果有就遍历Observe计算收益
        has_signal = 1
        for i in range(signal):
            today = df[tx - i][3]
            yesterday = df[tx - i - 1][3]
            gap = today - yesterday
            has_signal = has_signal * gap

        for i in range(rate_iter_count):
            rate = rate_min + i * rate_epoch
            rate_compare = df[tx - i][3] - (rate + 1) * df[tx - signal][3]
            has_signal = has_signal * rate_compare
            if has_signal < 0:
                continue
            # TODO 带上Rate计算最后一天的成交量是最开始的rate倍

            for o in range(observe_iter_count):
                observe = o * observe_epoch + observe_min
                row = o + s * observe_iter_count

                if tx > df.shape[0] - observe:
                    return
                profit = df[tx + observe][3] - df[tx + 1][3]
                result_global[row, tx, i] = profit / df[tx + 1][3]


# @cuda.jit
# def matmul_shared_mem(A, B, C):
#     sA = cuda.shared.array(shape=(TPB, TPB), dtype=float32)
#     sB = cuda.shared.array(shape=(TPB, TPB), dtype=float32)
#     x, y = cuda.grid(2)
#     tx = cuda.threadIdx.x
#     ty = cuda.threadIdx.y
#     if x >= C.shape[0] or y >= C.shape[1]:
#         return

#     tmp = 0.0
#     for i in range(int(A.shape[1] / TPB)):
#         sA[tx, ty] = A[x, ty + i * TPB]
#         sB[tx, ty] = B[tx + i * TPB, y]
#         cuda.syncthreads()
#         for j in range(TPB):
#             tmp += sA[tx, j] * sB[j, ty]

#     C[x, y] = tmp


if __name__ == "__main__":
    code_list = gm.get_all_stockcode_by_mongo()
    max_count = code_list.shape[0]
    done = 0
    start_gpu = time.time()
    for i, r in code_list.iterrows():
        code = r.code
        df_raw = gm.get_dayBar_by_mongo(code=code)
        df_raw = df_raw.head(20)
        df = df_raw.drop(
            ["_id", "code", "is_st", "adjust_flag", "trade_status", "date"], axis=1
        )
        # some data is null or '', need repair.
        for i in df.columns:
            df[df[i] == ""] = 0.0

        df = df.astype("float32")
        df = np.array(df)
        blockspergrid_x = int(math.ceil(df.shape[0] / threadsperblock[0]))
        blockspergrid_y = 1
        blockspergrid = (blockspergrid_x, blockspergrid_y)
        observe_signal = observe_iter_count * signal_iter_count
        result = np.full(
            (observe_signal, df.shape[0], rate_iter_count), 0.0, dtype=np.float32
        )

        # Start in GPU
        # Transfer Data to Device
        df_gpu = cuda.to_device(df)

        # print("Start processing in GPU")
        process_gpu[blockspergrid, threadsperblock](df_gpu, result)
        cuda.synchronize()

        result_final = pd.DataFrame(columns=df_raw["date"].values)
        for r in range(rate_iter_count):
            rate = rate_min + r * rate_epoch

            piece = result[:, :, r]
            result_df = pd.DataFrame(piece)
            result_df.columns = df_raw["date"].values
            indexs = []
            for s in range(signal_iter_count):
                signal = s * signal_epoch + signal_min
                for o in range(observe_iter_count):
                    observe = o * observe_epoch + observe_min
                    indexs.append(f"s{signal}_o{observe}_r{round(rate,2)}")
            result_df.index = indexs
            result_final = result_final.append(result_df)

        signal_situation = result_final[result_final != 0]
        print(signal_situation)
        signal_situation = signal_situation.count(axis=1)
        win = result_final[result_final > 0]
        lose = result_final[result_final < 0]
        end_gpu = time.time()
        signal_situation["SUM"] = result_final.apply(lambda x: x.sum(), axis=1)
        print(signal_situation)
        done += 1
        time_gpu = end_gpu - start_gpu
        print("GPU time(global memory):" + str(time_gpu))
        tar_url = url + code + ".csv"
        # result_final.to_csv(tar_url)
        print("csv save complete.")
        eta = time_gpu / done * max_count
        eta_show = datetime.timedelta(seconds=eta)
        print(f"预计剩余: {str(eta_show)}")

    # print("Start processing in GPU (shared memory)")
    # start_gpu = time.time()
    # matmul_shared_mem[blockspergrid, threadsperblock](
    #     A_global_mem, B_global_mem, C_global_mem
    # )
    # cuda.synchronize()
    # end_gpu = time.time()
    # time_gpu = end_gpu - start_gpu
    # print("GPU time(shared memory):" + str(time_gpu))
    # C_shared_gpu = C_shared_mem.copy_to_host
