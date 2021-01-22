# pylint: disable=no-member
"""
数据入口，负责对外输出后台数据

不参与数据获取
"""
import math
import threading
import threading
import tqdm
# import pandas as pd
from ginkgo_server.data.stock.baostock_data import bao_instance
from ginkgo_server.data.storage import ginkgo_storage as gs
from ginkgo_server.data.ginkgo_mongo import ginkgo_mongo as gm
from ginkgo_server.libs.ginkgo_logger import ginkgo_logger as gl
from ginkgo_server.libs.thread_manager import thread_manager as tm
from ginkgo_server.data.models.stock_info import StockInfo
from ginkgo_server.data.models.adjust_factor import AdjustFactor
from ginkgo_server.data.models.day_bar import DayBar
from ginkgo_server.data.models.min5_bar import Min5Bar


class DataPortal(object):
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "_instance"):
            with DataPortal._instance_lock:
                if not hasattr(cls, "_instance"):
                    DataPortal._instance = super().__new__(cls)

            return DataPortal._instance

    def upsert_all_cn_stock_info(self):
        """
        更新所有指数代码基本信息,包括指数指数代码、指数名称、交易状态
        """
        # Step1：通过Baostock获取所有指数代码
        result = bao_instance.get_all_stock_code()
        # result = result[:10000]

        # Step2：如果数据不为空进行持久化操作，反之报错
        if result.shape[0] > 0:
            # Step3：通过GinkGO_Storage进行数据持久化，目前先存储至MongoDBDocker，之后考虑本地缓存方法
            stock_info_list = []
            for i in range(result.shape[0]):
                code = result.iloc[i].loc["code"]
                code_name = result.iloc[i].loc["code_name"]
                trade_status = result.iloc[i].loc["tradeStatus"]
                new_stock = StockInfo(
                    code=code, code_name=code_name, trade_status=trade_status
                )
                stock_info_list.append(new_stock)

            gs.insert_stock_info_list(stock_info_list)
        else:
            gl.error("股票指数代码获取为空，请检查代码或日期")

    def upsert_all_cn_adjust_factor(self):
        """
        更新所有指数的复权数据
        """
        stock_list = gs.get_all_stock_code()
        self.upsert_list_adjust_factor(stock_list=stock_list)
    
    def upsert_list_adjust_factor(self,stock_list):
        pbar = tqdm.tqdm(stock_list)
        for i in pbar:
            insert_list = []
            rs = bao_instance.get_adjust_factor(code=i)
            # 如果有复权数据，添加到待插入列表
            if rs.shape[0] > 0:
                for s in range(rs.shape[0]):
                    new_ajust_factor = AdjustFactor(
                        code=rs.iloc[s].loc["code"],
                        divid_operate_date=rs.iloc[s].loc["dividOperateDate"],
                        fore_adjust_factor=rs.iloc[s].loc["foreAdjustFactor"],
                        back_adjust_factor=rs.iloc[s].loc["backAdjustFactor"],
                        adjust_factor=rs.iloc[s].loc["adjustFactor"]
                    )
                    insert_list.append(new_ajust_factor)
            pbar.set_description(f"Getting {i} AdjustFactor")

            if len(insert_list) > 0:
                gs.insert_adjust_factor_list(insert_list)
                pbar.set_description(f"Update  {i} AdjustFactor")

    def upsert_all_cn_adjust_factor_async(self, thread_num=1):
        # 获取指数列表
        bao_instance.login()
        stock_list = gs.get_all_stock_code()
        slice_count = 500
        pieces_count = math.ceil(len(stock_list)/slice_count)

        threads = []
        # 按照Count将stock_list 分割
        for i in range(pieces_count):
            sliced_stock_list = stock_list[slice_count*i:slice_count*(i+1)]
            print(len(sliced_stock_list))
            thread = threading.Thread(name = f'StockList{slice_count*i}-{slice_count*(i+1)}',target=self.upsert_list_adjust_factor,args=(sliced_stock_list,))
            threads.append(thread)
        
        tm.data_portal_thread_register(threads=threads,thread_num=thread_num)
        
        # 全部完成后停止

    def get_adjust_factor(self, code="sh.000001"):
        result = gs.get_adjust_factors(code=code)
        return result

    def upsert_stock_day_bar(self, pbar=None, code="sh.000001"):
        """
        更新某一指数的日交易数据]

        :param pbar: [tqdm的进度条提示实例]], defaults to None
        :type pbar: [type], tqdm
        :param code: [股票代码], defaults to "sh.000001"
        :type code: str, optional
        """        
        # 获取最新数据日期，目前是从baostock获取
        end = bao_instance.get_baostock_last_date()
        # 获取当前最新的数据日期
        try:
            # 尝试从MongoDB查询该指数的最新数据
            last_date = gm.get_latest_date(code=code)
        except Exception as e:
            # 失败则把开始日期设置为初识日期
            last_date = bao_instance.init_date
        bao_instance.login()
        # 获取DataFrame数据
        if pbar is not None:
            pbar.set_description(f"尝试获取{code} {last_date} 至 {end} 数据")
        else:
            gl.info(f"尝试获取{code} {last_date} 至 {end} 数据")
        rs = bao_instance.get_data(
            code=code, data_frequency="d", start_date=last_date, end_date=end
        )
        # rs = rs[:200]
        # 存储数据

        split_unit = 20000
        if pbar is not None:
            pbar.set_description(f"{code}准备插入{rs.shape[0]}条数据")
        else:
            gl.info(f"{code}准备插入{rs.shape[0]}条数据")
            
        if rs.shape[0] > 0:
            split_count = int(rs.shape[0] / split_unit)
            for j in range(split_count + 1):
                df = rs[j * split_unit : (j + 1) * split_unit]
                gm.upsert_day_bar(code=code, data_frame=df)
        if pbar is not None:
            pbar.set_description(f"完成{code}daybar 插入")

    def upsert_all_stock_day_bar(self):
        """
        更新所有指数日交易数据
        """
        # Step.1 获取所有指数代码
        stock_list = gs.get_all_stock_code()
        # Step.2 遍历更新
        self.upsert_list_stock_day_bar(stock_list=stock_list)

    def upsert_list_stock_day_bar(self, stock_list):
        pbar = tqdm.tqdm(stock_list)
        for i in pbar:
            bao_instance.login()
            self.update_stock_day_bar(code=i, pbar=pbar)
            pbar.set_description(f"Update {i} DayBar")

    def upsert_all_stock_day_bar_async(self, thread_num=1):
         # 获取指数列表
        stock_list = gs.get_all_stock_code()
        slice_count = 500
        pieces_count = math.ceil(len(stock_list)/slice_count)
        bao_instance.login()
        threads = []
        # 按照Count将stock_list 分割
        for i in range(pieces_count):
            sliced_stock_list = stock_list[slice_count*i:slice_count*(i+1)]
            thread = threading.Thread(name = f'StockList{slice_count*i}-{slice_count*(i+1)}',target=self.upsert_list_stock_day_bar,args=(sliced_stock_list,))
            threads.append(thread)
        
        tm.data_portal_thread_register(threads=threads,thread_num=thread_num)
        
        # 全部完成后停止



    def upsert_stock_min5_bar(self, pbar=None, code="sh.000001"):
        """
        更新某一指数的5min交易数据
        """
        # 获取最新数据日期，目前是从baostock获取
        end = bao_instance.get_baostock_last_date()
        # 获取当前最新的数据日期
        try:
            # 尝试从MongoDB查询该指数的最新数据
            last_date = gm.get_latest_time(code=code)
        except Exception as e:
            # 失败则把开始日期设置为初识日期
            last_date = bao_instance.init_date
        bao_instance.login()
        # 获取DataFrame数据
        rs = bao_instance.get_data(
            code=code, data_frequency="5", start_date=last_date, end_date=end
        )
        if pbar is not None:
            pbar.set_description(f"获取{code} 数据{rs.shape[0]}条")
        # rs = rs[:200]
        # 存储数据

        split_unit = 20000

        if rs.shape[0] > 0:
            split_count = int(rs.shape[0] / split_unit)
            for j in range(split_count + 1):
                df = rs[j * split_unit : (j + 1) * split_unit]
                gm.upsert_min5(code=code, data_frame=df)
                pbar.set_description(
                    f"获取{code}数据{j * split_unit}-{(j + 1) * split_unit}条"
                )
            if pbar is not None:
                pbar.set_description(f"获取{code} 数据{rs.shape[0]}条")

        else:
            # TODO 修改CodeInfo 的has_min_bar数据
            gs.set_stock_has_min_bar(code=code, has_min_bar=False)

    def upsert_all_min5_bar(self):
        """
        更新所有指数5min交易数据
        """
        # Step.1 获取所有指数代码
        stock_list = gs.get_all_min5_code()
        # Step.2 遍历更新
        pbar = tqdm.tqdm(stock_list)
        for i in pbar:
            bao_instance.login()
            self.update_stock_min5_bar(code=i, pbar=pbar)
            pbar.set_description(f"Update {i} Min5")


data_portal = DataPortal()
