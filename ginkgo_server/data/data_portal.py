"""
数据入口，负责对外输出后台数据

不参与数据获取
"""
import threading
import pandas as pd
from ginkgo_server.data.stock.baostock_data import bao_instance
from ginkgo_server.data.storage import ginkgo_storage as gs
from ginkgo_server.libs.ginkgo_logger import ginkgo_logger as gl


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
            for i in range(result.shape[0]):
                code = result.iloc[i].loc['code']
                code_name = result.iloc[i].loc['code_name']
                trade_status = int(result.iloc[i].loc['tradeStatus'])
                storage_result = gs.update_stock_info(
                    code=code, code_name=code_name, trade_status=trade_status)
                if storage_result:
                    count += 1
            gl.info(f'CN 股票指数代码更新完成,共更新 {count} 条')

    def update_all_cn_adjust_factor(self):
        """
        更新所有CN指数的复权数据

        """
        stock_list = gs.get_all_stock_code()
        bao_instance.login()
        for i in stock_list:
            adjust_factor_list = bao_instance.get_adjust_factor(code=i)
            if adjust_factor_list.shape[0] == 0:
                gl.info(f'{i} 指数没有复权数据')

            for s in range(adjust_factor_list.shape[0]):
                code = adjust_factor_list.iloc[s].loc['code']
                divid_operate_date = adjust_factor_list.iloc[s].loc[
                    'dividOperateDate']
                fore_adjust_factor = adjust_factor_list.iloc[s].loc[
                    'foreAdjustFactor']
                back_adjust_factor = adjust_factor_list.iloc[s].loc[
                    'backAdjustFactor']
                adjust_factor = adjust_factor_list.iloc[s].loc['adjustFactor']
                gs.update_adjust_factor(code=code,
                                        divid_operate_date=divid_operate_date,
                                        fore_adjust_factor=fore_adjust_factor,
                                        back_adjust_factor=back_adjust_factor,
                                        adjust_factor=adjust_factor)

    # def query_stock(self,
    #                 code,
    #                 start_date,
    #                 end_date,
    #                 frequency,
    #                 adjust_flag=3):
    #     # 如果code不存在列表内，直接返回
    #     if not self.check_code_exist(code=code):
    #         print('股票代码不存在股票列表内')
    #         return
    #     else:
    #         # 获取股票原始数据
    #         raw = self.__get_data(code=code, frequency=frequency)
    #         # 获取复权因子数据
    #         adjust_factor = self.__get_adjust_factor(code=code)
    #         # 复权计算
    #         adjust = self.__adjust_cal(raw=raw,
    #                                    adjust_factor=adjust_factor,
    #                                    adjust_flag=adjust_flag,
    #                                    frequency=frequency)
    #         # 根据start_date与end_date返回数据
    #         if start_date > end_date:
    #             print('start should before end')
    #             return
    #         condition = adjust['date'] >= start_date
    #         condition2 = adjust['date'] <= end_date
    #         return adjust[condition & condition2]

    # def check_code_exist(self, code):
    # 查询all_stock.csv中是否存在与code匹配
    # try:
    #     code_df = pd.read_csv(STOCK_URL + 'all_stock.csv',
    #                           usecols=['code'])
    #     count = code_df.count().code
    #     if count == 0:
    #         print('指数代码为空，请检查代码')
    #         return False
    #     else:
    #         is_code_in_list = code in code_df['code'].values
    #         return is_code_in_list
    # except Exception as e:
    #     raise e

    # def __get_data(self, code, frequency):
    #     try:
    #         if frequency == 'd':
    #             url = 'day/'
    #         elif frequency == '5':
    #             if self.__is_code_in_min_ignore(code=code):
    #                 print(f'{code} 没有分钟交易数据')
    #                 return
    #             url = 'min/'
    #         else:
    #             print('Frequency should be d or 5.')

    #         df = pd.read_csv(STOCK_URL + url + code + '.csv')
    #         return df
    #     except Exception as e:
    #         raise e

    # def __is_code_in_min_ignore(self, code):
    # try:
    #     ignore_df = pd.read_csv(STOCK_URL + 'min_ignore.csv',
    #                             usecols=['code'])
    #     is_code_in_min_ignore = code in ignore_df['code'].values
    #     return is_code_in_min_ignore
    # except Exception as e:
    #     print(e)

    # def __get_adjust_factor(self, code):
    #     try:
    #         adjust_factor = pd.read_csv(STOCK_URL + 'adjust_factor_data.csv')
    #         condition = adjust_factor['code'] == code
    #         filter_adjust = adjust_factor[condition]
    #         return filter_adjust
    #     except Exception as e:
    #         print(e)

    # def __adjust_cal(self, raw, adjust_factor, adjust_flag=1, frequency='d'):
    #     # 没有复权因子
    #     if adjust_factor.count().code == 0:
    #         return raw

    # 有复权因子
    # TODO 按照截至日期复权
    # adjust_columns = []
    # if frequency == 'd':
    #     adjust_columns = ["open", "high", "low", "close", "preclose"]
    # elif frequency == '5':
    #     adjust_columns = ["open", "high", "low", "close"]
    # fore = raw.copy(deep=True)
    # back = raw.copy(deep=True)
    # for i in range(len(adjust_factor) + 1):
    #     if i == 0:
    #         condition = raw['date'] < adjust_factor.iloc[0].dividOperateDate
    #         condition2 = raw['date'] <= adjust_factor.iloc[
    #             0].dividOperateDate

    #         fore.loc[condition,
    #                  adjust_columns] *= adjust_factor.iloc[0].foreAdjustFactor
    #         back.loc[condition2,
    #                  adjust_columns] *= adjust_factor.iloc[0].backAdjustFactor

    #     elif i == len(adjust_factor):
    #         condition = raw['date'] >= adjust_factor.iloc[
    #             i - 1].dividOperateDate
    #         condition2 = raw['date'] > adjust_factor.iloc[
    #             i - 1].dividOperateDate
    #         fore.loc[condition,
    #                  adjust_columns] *= adjust_factor.iloc[i - 1].foreAdjustFactor
    #         back.loc[condition2,
    #                  adjust_columns] *= adjust_factor.iloc[i - 1].backAdjustFactor
    #     else:
    #         condition = (
    #                             raw['date'] < adjust_factor.iloc[i].dividOperateDate
    #                     ) & (raw['date'] >= adjust_factor.iloc[i - 1].dividOperateDate)
    #         condition2 = (
    #                              raw['date'] <= adjust_factor.iloc[i].dividOperateDate
    #                      ) & (raw['date'] > adjust_factor.iloc[i - 1].dividOperateDate)
    #         fore.loc[condition,
    #                  adjust_columns] *= adjust_factor.iloc[i].foreAdjustFactor
    #         back.loc[condition2,
    #                  adjust_columns] *= adjust_factor.iloc[i].backAdjustFactor

    # if adjust_flag == 1:
    #     return fore
    # elif adjust_flag == 2:
    #     return back
    # else:
    #     return raw

    # def get_stock_code(self):
    #     bao_instance.get_all_stock_code()

    # def update_all_stock(self):
    #     bao_instance.update_all_stock()

    # def update_adjust(self):
    #     bao_instance.all_adjust_factor_up_to_date()


data_portal = DataPortal()