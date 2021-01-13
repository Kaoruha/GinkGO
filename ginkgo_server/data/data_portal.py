"""
数据入口，负责对外输出后台数据

不参与数据获取
"""
import threading
import tqdm
import pandas as pd
from ginkgo_server.data.stock.baostock_data import bao_instance
from ginkgo_server.data.storage import ginkgo_storage as gs
from ginkgo_server.libs.ginkgo_logger import ginkgo_logger as gl
from ginkgo_server.data.models.stock_info import StockInfo
from ginkgo_server.data.models.adjust_factor import AdjustFactor
from ginkgo_server.data.models.day_bar import DayBar


class DataPortal(object):
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            with DataPortal._instance_lock:
                if not hasattr(cls, '_instance'):
                    DataPortal._instance = super().__new__(cls)

            return DataPortal._instance

    def update_all_cn_stock_info(self):
        """
        更新所有指数代码基本信息,包括指数指数代码、指数名称、交易状态

        Step1：通过Baostock获取所有指数代码

        Step2：如果数据不为空进行持久化操作，反之报错

        Step3：通过GinkGO_Storage进行数据持久化，目前先存储至MongoDBDocker，之后考虑本地缓存方法
        """
        count = 0
        # Step1：通过Baostock获取所有指数代码
        result = bao_instance.get_all_stock_code()
        # Step2：如果数据不为空进行持久化操作，反之报错
        if result is None:
            gl.error('股票指数代码获取为空，请检查代码或日期')
        else:
            # Step3：通过GinkGO_Storage进行数据持久化，目前先存储至MongoDBDocker，之后考虑本地缓存方法
            # TODO 后续需要考虑批量插入，现在先单个插入
            stock_info_list = []
            for i in range(result.shape[0]):
                code = result.iloc[i].loc['code']
                code_name = result.iloc[i].loc['code_name']
                trade_status = int(result.iloc[i].loc['tradeStatus'])
                new_stock = StockInfo(code=code,
                                      code_name=code_name,
                                      trade_status=trade_status)
                stock_info_list.append(new_stock)
            gs.insert_stock_info_list(stock_info_list)

    def update_all_cn_adjust_factor(self):
        """
        更新所有CN指数的复权数据
        """
        stock_list = gs.get_all_stock_code()
        bao_instance.login()
        adjust_factor_list = []
        pbar = tqdm.tqdm(stock_list)
        for i in pbar:
            rs = bao_instance.get_adjust_factor(code=i)
            if rs.shape[0] == 0:
                # gl.info(f'{i} 指数没有复权数据')
                pass
            else:
                for s in range(rs.shape[0]):
                    code = rs.iloc[s].loc['code']
                    divid_operate_date = rs.iloc[s].loc['dividOperateDate']
                    fore_adjust_factor = rs.iloc[s].loc['foreAdjustFactor']
                    back_adjust_factor = rs.iloc[s].loc['backAdjustFactor']
                    adjust_factor = rs.iloc[s].loc['adjustFactor']

                    new_ajust_factor = AdjustFactor(
                        code=code,
                        divid_operate_date=divid_operate_date,
                        fore_adjust_factor=fore_adjust_factor,
                        back_adjust_factor=back_adjust_factor,
                        adjust_factor=adjust_factor)
                    
                    adjust_factor_list.append(new_ajust_factor)
                if len(adjust_factor_list)>0:
                    gs.insert_adjust_factor_list(adjust_factor_list)
                    adjust_factor_list = []

            pbar.set_description(f"Getting {i} AdjustFactor")

        

    def get_adjust_factor(self, code='sh.000001'):
        result = gs.get_adjust_factors(code=code)
        return result

    def update_stock_day_bar(self, code='sh.000001'):
        # 获取数据
        end = bao_instance.get_baostock_last_date()
        rs = bao_instance.get_data(code=code, data_frequency='d', end_date=end)
        print(rs.columns)
        # 判断数据Len
        # 存储数据
        if rs.shape[0] > 0:
            for i in range(rs.shape[0]):
                date = rs.iloc[i].date
                open = rs.iloc[i].open
                high = rs.iloc[i].high
                low = rs.iloc[i].low
                close = rs.iloc[i].close
                preclose = rs.iloc[i].preclose
                volume = rs.iloc[i].volume
                amount = rs.iloc[i].amount
                adjust_flag = rs.iloc[i].adjustflag
                turn = rs.iloc[i].turn
                trade_status = rs.iloc[i].tradestatus
                pct_change = rs.iloc[i].pctChg
                is_ST = rs.iloc[i].isST

                gs.update_day_bar(code=code,
                                  date=date,
                                  open=float(open),
                                  high=float(high),
                                  low=float(low),
                                  close=float(close),
                                  preclose=float(preclose),
                                  volume=float(volume),
                                  amount=float(amount),
                                  adjust_flag=adjust_flag,
                                  turn=float(turn),
                                  trade_status=trade_status,
                                  pct_change=float(pct_change),
                                  is_ST=is_ST)

    def update_all_stock_day_bar(self):
        # 获取所有指数代码
        stock_list = gs.get_all_stock_code()
        # 遍历更新
        for i in stock_list:
            self.update_stock_day_bar(code=i)


data_portal = DataPortal()