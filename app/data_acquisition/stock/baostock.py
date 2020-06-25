import threading
import baostock as bs
import sys
import pandas as pd
from app.config.setting import STOCK_URL
import datetime, time
from multiprocessing import Process
from app.data_acquisition.manager import DataManager

_output = sys.stdout


class BaoStock(object):
    _instance_lock = threading.Lock()
    init_date = '1999-07-26'
    data_split = 10000

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
        for i in range(sleep_second):
            t = sleep_second - i
            _output.write(f'\r还需等待 {t} 秒' + '=' * t)
            time.sleep(1)

    def get_data(self, code='sh.600000', data_frequency='d', start_date='init_date', end_date='2006-02-01'):
        daily_query = 'date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,isST'
        min_query = 'date,time,code,open,high,low,close,volume,amount,adjustflag'
        dimension = daily_query
        frequency = 'd'
        # 根据查询数据的频率，修正查询数据的维度与频率
        if data_frequency == 'd':
            dimension = daily_query
            frequency = 'd'
        elif data_frequency == '5':
            dimension = min_query
            frequency = '5'
        self.login()
        print(f'尝试获取 {code} 数据。。。')
        rs = bs.query_history_k_data_plus(code, dimension, start_date=start_date, end_date=end_date,
                                          frequency=frequency, adjustflag='3')
        result = None
        if rs.error_code == '0':
            # 打印结果集
            data_list = []
            while (rs.error_code == '0') & rs.next():
                # 获取一条记录，将记录合并在一起
                data_list.append(rs.get_row_data())
            result = pd.DataFrame(data_list, columns=rs.fields)
            # TODO 进度条
            print(f'已经获取 {code} 数据')
        else:
            print('query_history_k_data_plus respond error_code:' + rs.error_code)
            print('query_history_k_data_plus respond  error_msg:' + rs.error_msg)
        self.logout()
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
        rs = bs.query_history_k_data_plus('sh.000001',daily_query,start_date=start_date, end_date=end_date,frequency='d', adjustflag='3')
        result = None
        if rs.error_code == '0':
            # 打印结果集
            data_list = []
            while (rs.error_code == '0') & rs.next():
                # 获取一条记录，将记录合并在一起
                data_list.append(rs.get_row_data())
            result = pd.DataFrame(data_list, columns=rs.fields)
        last_date = result.iloc[-1].date
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
            return
        else:
            result = data_frame
            count = result.count().date
            if count < 10000:
                result.to_csv(path + code + '.csv', mode='w', index=False)
                print(f'{code}.csv 已经生成')
            else:
                result[:10000].to_csv(path + code + '.csv', mode='w', index=False)
                self.add_to_csv(code=code, data_frequency=data_frequency, data_frame=result[10000:])

    # 向CSV中注入数据
    def add_to_csv(self, code='sh.600000', data_frequency='d', *, data_frame):
        path = self.set_path(data_frequency)
        count = data_frame.count().date
        print(count)
        if count == 0:
            print('数据不能为空')
            return
        elif count <= self.data_split:
            data_frame.to_csv(path + code + '.csv', mode='a', header=False, index=False)
            last = self.get_last_date(data_or_code=code, data_frequency=data_frequency)
            print(f'{code}已经更新至{last}')
        else:
            pass
            for i in range(int(count / self.data_split) + 1):
                t = data_frame[self.data_split * (i):(i + 1) * self.data_split]
                t.to_csv(path + code + '.csv', mode='a', header=False, index=False)
                last = self.get_last_date(data_or_code=code, data_frequency=data_frequency)
                print(f'{code}已经更新至{last}')
            self.sleep(10)
        print(f'{code}.csv 已经更新至最新')

    # 更新一只股票数据
    def up_to_date(self, code='sh.600000', data_frequency='d'):
        try:
            last_date = self.get_last_date(data_or_code=code, data_frequency=data_frequency)
            h = datetime.datetime.now().hour
            # 目前设定P.M.06:00后更新当天数据，6点之前更新至昨日即可
            end = self.get_baostock_last_date()
            if last_date == end:
                print(f'{code} 已经更新至最新 {end}')
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
            count = add_data.count().date
            if count == 0:
                print(f'{code} 没有数据')
            else:
                print(f'尝试创建 {code}.csv。。。')
                self.generate_csv(code=code, data_frequency=data_frequency, data_frame=add_data)

    # 获取所有股票代码
    def get_all_stock_code(self):
        date = datetime.datetime.now().strftime('%Y-%m-%d')
        # 获取证券信息
        rs = bs.query_all_stock(day='2020-06-24')
        # _output.write('query_all_stock respond error_code:' + rs.error_code)
        # _output.write('query_all_stock respond  error_msg:' + rs.error_msg)

        # 打印结果集
        data_list = []
        while (rs.error_code == '0') & rs.next():
            # 获取一条记录，将记录合并在一起
            data_list.append(rs.get_row_data())
        result = pd.DataFrame(data_list, columns=rs.fields)
        # 结果集输出到csv文件
        result.to_csv(STOCK_URL + 'all_stock.csv', mode='w', index=False, encoding="GBK")
        print(f'所有指数代码已经更新至 {date}')

    # 更新所有股票
    def update_all_stock(self):
        try:
            code = pd.read_csv(STOCK_URL + 'all_stock.csv', usecols=['code'])
            count = code.count().code
            if count == 0:
                print('指数代码为空，请检查')
                return
            else:
                _output.write('\r开始更新日交易数据。。。')
                for row in code.iterrows():
                    self.up_to_date(code=row[1].code, data_frequency='d')

                _output.write('\r开始更新日5分钟交易数据。。。')

                for row in code.iterrows():
                    self.up_to_date(code=row[1].code, data_frequency='5')
        except Exception as e:
            raise e


baostock = BaoStock()


def start_update_all_stock():
    t = Process(target=baostock.update_all_stock, name='BaoStock_update_all_stock')
    DataManager.process_register(t)
    _output.write("\rBaoStock_update_all_stock is running!!")
