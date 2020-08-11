"""
数据入口，负责对外输出后台数据

不参与数据获取
"""
import threading
import pandas as pd
from ginkgo.config.setting import STOCK_URL


class DataPortal(object):
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            with DataPortal._instance_lock:
                if not hasattr(cls, '_instance'):
                    DataPortal._instance = super().__new__(cls)

            return DataPortal._instance

    def query_stock(self,
                    code,
                    start_date,
                    end_date,
                    frequency,
                    adjust_flag=3):
        # 如果code不存在列表内，直接返回
        if not self.__check_code_exist(code=code):
            print('股票代码不存在股票列表内')
            return
        else:
            # 获取股票原始数据
            raw = self.__get_data(code=code, frequency=frequency)
            # 获取复权因子数据
            adjust_factor = self.__get_adjust_factor(code=code)
            # 复权计算
            adjust = self.__adjust_cal(raw=raw,
                                       adjust_factor=adjust_factor,
                                       adjust_flag=adjust_flag,
                                       frequency=frequency)
            # 根据start_date与end_date返回数据
            if start_date > end_date:
                print('start should before end')
                return
            condition = adjust['date'] >= start_date
            condition2 = adjust['date'] <= end_date
            return adjust[condition & condition2]

    def __check_code_exist(self, code):
        # 查询all_stock.csv中是否存在与code匹配
        try:
            code_df = pd.read_csv(STOCK_URL + 'all_stock.csv',
                                  usecols=['code'])
            count = code_df.count().code
            if count == 0:
                print('指数代码为空，请检查代码')
                return False
            else:
                is_code_in_list = code in code_df['code'].values
                return is_code_in_list
        except Exception as e:
            raise e

    def __get_data(self, code, frequency):
        try:
            if frequency == 'd':
                url = 'day/'
            elif frequency == '5':
                if self.__is_code_in_min_ignore(code=code):
                    print(f'{code} 没有分钟交易数据')
                    return
                url = 'min/'
            else:
                print('Frequency should be d or 5.')

            df = pd.read_csv(STOCK_URL + url + code + '.csv')
            return df
        except Exception as e:
            raise e

    def __is_code_in_min_ignore(self, code):
        try:
            ignore_df = pd.read_csv(STOCK_URL + 'min_ignore.csv',
                                    usecols=['code'])
            is_code_in_min_ignore = code in ignore_df['code'].values
            return is_code_in_min_ignore
        except Exception as e:
            print(e)

    def __get_adjust_factor(self, code):
        try:
            adjust_factor = pd.read_csv(STOCK_URL + 'adjust_factor_data.csv')
            condition = adjust_factor['code'] == code
            filter_adjust = adjust_factor[condition]
            return filter_adjust
        except Exception as e:
            print(e)

    def __adjust_cal(self, raw, adjust_factor, adjust_flag=1, frequency='d'):
        # 没有复权因子
        if adjust_factor.count().code == 0:
            return raw

        # 有复权因子
        # TODO 按照截至日期复权
        adjust_columns = []
        if frequency == 'd':
            adjust_columns = ["open", "high", "low", "close", "preclose"]
        elif frequency == '5':
            adjust_columns = ["open", "high", "low", "close"]
        fore = raw.copy(deep=True)
        back = raw.copy(deep=True)
        for i in range(len(adjust_factor) + 1):
            if i == 0:
                condition = raw['date'] < adjust_factor.iloc[0].dividOperateDate
                condition2 = raw['date'] <= adjust_factor.iloc[
                    0].dividOperateDate

                fore.loc[condition,
                         adjust_columns] *= adjust_factor.iloc[0].foreAdjustFactor
                back.loc[condition2,
                         adjust_columns] *= adjust_factor.iloc[0].backAdjustFactor

            elif i == len(adjust_factor):
                condition = raw['date'] >= adjust_factor.iloc[
                    i - 1].dividOperateDate
                condition2 = raw['date'] > adjust_factor.iloc[
                    i - 1].dividOperateDate
                fore.loc[condition,
                         adjust_columns] *= adjust_factor.iloc[i - 1].foreAdjustFactor
                back.loc[condition2,
                         adjust_columns] *= adjust_factor.iloc[i - 1].backAdjustFactor
            else:
                condition = (
                                    raw['date'] < adjust_factor.iloc[i].dividOperateDate
                            ) & (raw['date'] >= adjust_factor.iloc[i - 1].dividOperateDate)
                condition2 = (
                                     raw['date'] <= adjust_factor.iloc[i].dividOperateDate
                             ) & (raw['date'] > adjust_factor.iloc[i - 1].dividOperateDate)
                fore.loc[condition,
                         adjust_columns] *= adjust_factor.iloc[i].foreAdjustFactor
                back.loc[condition2,
                         adjust_columns] *= adjust_factor.iloc[i].backAdjustFactor

        if adjust_flag == 1:
            return fore
        elif adjust_flag == 2:
            return back
        else:
            return raw


data_portal = DataPortal()

# s = data_portal.query_stock(code='sh.600000',
#                          start_date='1999-01-02',
#                          end_date='1999-01-01',
#                          frequency='d',
#                          adjust_flag=2)
