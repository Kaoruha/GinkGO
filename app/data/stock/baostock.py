import threading
import baostock as bs
import sys
import pandas as pd
from app.config.setting import STOCK_URL
import datetime, time
from multiprocessing import Process
from app.data.manager import DataManager

_output = sys.stdout


class BaoStock(object):
    _instance_lock = threading.Lock()
    init_date = '1999-07-26'
    data_split = 10000
    bao_count = 0

    # TODO 文件操作的异常回滚

    def __init__(self):
        pass

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            with BaoStock._instance_lock:
                if not hasattr(cls, '_instance'):
                    BaoStock._instance = super().__new__(cls)

            return BaoStock._instance

    def login(self):
        lg = bs.login(user_id='anonymous', password='123456')
        if lg.error_code == '0':
            return
        else:
            _output.write('\rlogin respond error_code:' + lg.error_code)
            _output.write('\rlogin respond  error_msg:' + lg.error_msg)

    def logout(self):
        bs.logout

    def sleep(self, sleep_second=2):
        for i in range(sleep_second * 2):
            t = sleep_second * 2 - (i + 1)
            _output.write(f'\r还需等待 {t / 2:.1f} 秒' + ' ' + '=' * t)
            time.sleep(.5)
        print('\n')

    def get_data(self, code='sh.600000', data_frequency='d', start_date='init_date', end_date='2006-02-01'):
        daily_query = 'date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,isST'
        min_query = 'date,time,code,open,high,low,close,volume,amount,adjustflag'
        dimension = daily_query
        frequency = 'd'
        now = datetime.datetime.now().strftime('%H:%M:%S')
        print(f'尝试获取 {code} 数据 {now}')
        # 根据查询数据的频率，修正查询数据的维度与频率
        if data_frequency == 'd':
            dimension = daily_query
            frequency = 'd'
        elif data_frequency == '5':
            dimension = min_query
            frequency = '5'

        data_list = []

        # 如果需要获取日交易数据，直接发送一个请求
        if data_frequency == 'd':
            rs = bs.query_history_k_data_plus(code, dimension, start_date=start_date, end_date=end_date,
                                              frequency=frequency, adjustflag='3')
            if rs.error_code == '0':
                # 打印结果集
                self.bao_count += 1
                while (rs.error_code == '0') & rs.next():
                    # 获取一条记录，将记录合并在一起
                    data_list.append(rs.get_row_data())
                # TODO 进度条
                _output.write(f'\r成功获取 {code} 从 {start_date} 至 {end_date} 的数据')
            else:
                print('query_history_k_data_plus respond error_code:' + rs.error_code)
                print('query_history_k_data_plus respond  error_msg:' + rs.error_msg)
            result = pd.DataFrame(data_list, columns=rs.fields)
            print(f'\n已经获取BaoStock数据 {self.bao_count} 次')
            return result

        # 如果需要获取的是5min交易数据，分段获取
        start = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
        total_days = (end - start).days
        offset = 365 * 2

        for i in range(int(total_days / offset) + 1):
            start_temp = (start + datetime.timedelta(days=offset * i)).strftime("%Y-%m-%d")
            if i == int(total_days / offset):
                end_temp = end_date
            else:
                end_temp = (start + datetime.timedelta(days=offset * (i + 1))).strftime("%Y-%m-%d")
            now = datetime.datetime.now().strftime('%H:%M:%S')
            _output.write(f'\r尝试获取 {code} 从 {start_temp} 至 {end_temp} 的数据 {now}')
            rs = bs.query_history_k_data_plus(code, dimension, start_date=start_temp, end_date=end_temp,
                                              frequency=frequency, adjustflag='3')
            if rs.error_code == '0':
                # 打印结果集
                self.bao_count += 1
                while (rs.error_code == '0') & rs.next():
                    # 获取一条记录，将记录合并在一起
                    data_list.append(rs.get_row_data())
                # TODO 进度条
                _output.write(f'\r成功获取 {code} 从 {start_temp} 至 {end_temp} 的数据')
            else:
                print('query_history_k_data_plus respond error_code:' + rs.error_code)
                print('query_history_k_data_plus respond  error_msg:' + rs.error_msg)
        result = pd.DataFrame(data_list, columns=rs.fields)
        print(f'已经获取 {self.bao_count} 次')
        return result

    # 获取一系列DataFrame的长度
    def count_data(self, data):
        count = data.count().date
        return count

    # 获取DataFrame或者某只股票的最近更新
    def get_last_date(self, data_or_code, data_frequency='d'):
        if data_frequency == 'd':
            path = 'day/'
        elif data_frequency == '5':
            path = 'min/'
        else:
            print('Frequency shoulb be d or 5.')
            return
        if type(data_or_code) == pd.core.frame.DataFrame:
            last_date = data_or_code.iloc[-1].date
        elif type(data_or_code) == str:
            date_data = pd.read_csv(STOCK_URL + path + data_or_code + '.csv', usecols=['date'])
            if date_data.count().date == 0:
                print(f'{data_or_code}.csv 无数据')
                return 0
            else:
                last_date = date_data.iloc[-1].date
        return last_date

    # 通过获取sh.000001的日交易数据来获取数据最新,目前往前推10天
    def get_baostock_last_date(self):
        daily_query = 'date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,isST'
        start_date = (datetime.datetime.now().date() + datetime.timedelta(days=-10)).strftime("%Y-%m-%d")
        end_date = datetime.datetime.now().strftime('%Y-%m-%d')
        self.login()
        rs = bs.query_history_k_data_plus('sh.000001', daily_query, start_date=start_date, end_date=end_date,
                                          frequency='d', adjustflag='3')
        result = None
        if rs.error_code == '0':
            # 打印结果集
            data_list = []
            while (rs.error_code == '0') & rs.next():
                # 获取一条记录，将记录合并在一起
                data_list.append(rs.get_row_data())
            result = pd.DataFrame(data_list, columns=rs.fields)
        last_date = result.iloc[-1].date
        self.logout()
        return last_date

    # 根据数据频率设定文件目录
    def set_path(self, data_frequency):
        if data_frequency == 'd':
            path = STOCK_URL + 'day/'
        elif data_frequency == '5':
            path = STOCK_URL + 'min/'
        else:
            print('Frequency shoulb be d or 5.')
        return path

    # 生成CSV文件
    def generate_csv(self, code='sh.600000', data_frequency='d', *, data_frame):
        path = self.set_path(data_frequency)
        if data_frame.count().date == 0:
            print('数据不能为空')
            min_ignore = self.read_min_ignore()
            if not self.is_code_in_min_ignore(code=code, min_ignore=min_ignore):
                self.add_to_min_ignore(code=code)
            return
        else:
            result = data_frame
            count = result.count().date
            if count < 10000:
                result.to_csv(path + code + '.csv', mode='w', index=False)
                last_date = self.get_last_date(data_or_code=code, data_frequency=data_frequency)
                print(f'{code}.csv 已经生成，最新日期为 {last_date}')
                self.sleep(1)
            else:
                result[:10000].to_csv(path + code + '.csv', mode='w', index=False)
                self.add_to_csv(code=code, data_frequency=data_frequency, data_frame=result[10000:])

    # 向CSV中注入数据
    def add_to_csv(self, code='sh.600000', data_frequency='d', *, data_frame):
        path = self.set_path(data_frequency)
        count = data_frame.count().date
        if count == 0:
            print('数据不能为空')
            return
        elif count <= self.data_split:
            data_frame.to_csv(path + code + '.csv', mode='a', header=False, index=False)
            last = self.get_last_date(data_or_code=code, data_frequency=data_frequency)
            _output.write(f'\r{code} 已经更新至 {last}')
        else:
            for i in range(int(count / self.data_split) + 1):
                t = data_frame[self.data_split * i:(i + 1) * self.data_split]
                t.to_csv(path + code + '.csv', mode='a', header=False, index=False)
                last = self.get_last_date(data_or_code=code, data_frequency=data_frequency)
                _output.write(f'\r{code} 已经更新至 {last}')
            self.sleep(2)
        print(f'{code}.csv 已经更新至 {last}')

    # 生成分钟数据黑名单，把没有分钟数据的指数存入
    def generate_min_ignore(self):
        t = {'code': []}
        df = pd.DataFrame(data=t, index=None)
        df.to_csv(STOCK_URL + 'min_ignore.csv', mode='w', index=False, encoding="GBK")
        print(f'成功创建 min_ignore.csv')

    # 判断股票代码是否在分钟时间黑名单中
    def is_code_in_min_ignore(self, code, min_ignore):
        if min_ignore is None:
            return False
        ignore_list = min_ignore['code'].values.tolist()
        if code in ignore_list:
            return True
        else:
            return False

    # 将股票代码添加至分钟数据黑名单
    def add_to_min_ignore(self, code):
        try:
            t = {'code': [code]}
            df = pd.DataFrame(data=t, index=None)
            df.to_csv(STOCK_URL + 'min_ignore.csv', mode='a', header=False, index=False, encoding="GBK")
            print(f'已经添加 {code} 至 min_ignore.csv.')
        except Exception as e:
            print(e)
            self.generate_min_ignore()
            self.add_to_min_ignore(code=code)

    # 读取分钟数据黑名单
    def read_min_ignore(self):
        try:
            ignore_df = pd.read_csv(STOCK_URL + 'min_ignore.csv', usecols=['code'])
            return ignore_df
        except Exception as e:
            print(e)
            self.generate_min_ignore()
            self.read_min_ignore()

    # 更新一只股票数据
    def up_to_date(self, code='sh.600000', data_frequency='d', end=''):
        try:
            last_date = self.get_last_date(data_or_code=code, data_frequency=data_frequency)
            if end == '':
                end = self.get_baostock_last_date()
            if last_date == end:
                print(f'{code} 无需更新，最新日期 {end}')
                return
            start = (datetime.datetime.strptime(last_date, '%Y-%m-%d').date() + datetime.timedelta(days=1)).strftime(
                '%Y-%m-%d')
            add_data = self.get_data(code=code, data_frequency=data_frequency, start_date=start, end_date=end)
            self.add_to_csv(code=code, data_frequency=data_frequency, data_frame=add_data)
        except Exception as e:
            print(e)
            print(f'没有找到 {code}.csv')
            start = self.init_date
            end = datetime.datetime.now().strftime('%Y-%m-%d')
            add_data = self.get_data(code=code, data_frequency=data_frequency, start_date=start, end_date=end)
            self.generate_csv(code=code, data_frequency=data_frequency, data_frame=add_data)

    # 获取所有股票代码
    def get_all_stock_code(self):
        date = datetime.datetime.now().strftime('%Y-%m-%d')
        # 获取证券信息
        self.login()
        rs = bs.query_all_stock(day='2020-06-24')
        # _output.write('query_all_stock respond error_code:' + rs.error_code)
        # _output.write('query_all_stock respond  error_msg:' + rs.error_msg)

        # 打印结果集
        data_list = []
        while (rs.error_code == '0') & rs.next():
            # 获取一条记录，将记录合并在一起
            data_list.append(rs.get_row_data())
        result = pd.DataFrame(data_list, columns=rs.fields)
        self.logout()
        # 结果集输出到csv文件
        result.to_csv(STOCK_URL + 'all_stock.csv', mode='w', index=False, encoding="GBK")
        print(f'所有指数代码已经更新至 {date}')

    # 更新所有股票
    def update_all_stock(self):
        try:
            min_ignore = self.read_min_ignore()
            self.login()
            code = pd.read_csv(STOCK_URL + 'all_stock.csv', usecols=['code'])
            count = code.count().code
            end = self.get_baostock_last_date()
            if count == 0:
                print('指数代码为空，请检查代码')
                return
            else:
                _output.write('\r开始更新日交易数据。。。')
                for row in code.iterrows():
                    self.up_to_date(code=row[1].code, data_frequency='d', end=end)
                print('日交易数据更新完毕')
                _output.write('\r开始更新日5分钟交易数据。。。')

                for row in code.iterrows():
                    if self.is_code_in_min_ignore(code=row[1].code, min_ignore=min_ignore):
                        print(f'{row[1].code} 已被忽略')
                        continue
                    self.up_to_date(code=row[1].code, data_frequency='5', end=end)
                print('5min交易数据更新完毕')
            self.logout()
            print('更新完毕')
        except Exception as e:
            raise e


baostock = BaoStock()


# TODO 多线程管理
# TODO 允许查询更新进度
# TODO 僵尸请求自动重新请求

def update_all_stock():
    baostock.update_all_stock()


def start_update_all_stock():
    t = Process(target=update_all_stock, name='BaoStock_update_all_stock')
    DataManager.process_register(t)
    _output.write("\rBaoStock_update_all_stock is running!!")
