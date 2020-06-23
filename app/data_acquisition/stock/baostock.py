import baostock as bs
import pandas as pd
from app.config.setting import STOCK_URL
import datetime, time
from multiprocessing import Process
from app.data_acquisition.manager import DataManager


class BaoStock(object):

    @property
    def code(self):
        return self.code

    @code.setter
    def code(self, code):
        self.code = code

    @property
    def start_date(self):
        return self.start_date

    @start_date.setter
    def start_date(self, start_date):
        self.start_date = start_date

    @property
    def end_date(self):
        return self.end_date

    @end_date.setter
    def end_date(self, end_date):
        self.end_date = end_date

    def __init__(cls, code='sh.600000', start_date='2006-01-01', end_date=''):
        cls.code = code
        cls.start_date = start_date
        if end_date == '':
            cls.end_date = datetime.datetime.now().strftime('%Y-%m-%d')
        else:
            cls.end_date = end_date

    @classmethod
    def __login(cls):
        # 登陆系统
        lg = bs.login()
        # 显示登陆返回信息
        if lg.error_code == 0:
            return
        else:
            # print('login respond error_code:' + lg.error_code)
            # print('login respond  error_msg:' + lg.error_msg)
            return

    @staticmethod
    def today_str():
        """
        获取今天日期的字符串

        :return: 今天日期YYYY-MM-DD的字符串
        """
        return datetime.datetime.now().strftime('%Y-%m-%d')

    @staticmethod
    def today_date():
        """
        获取今天日期的date格式

        :return: 今天日期YYYY-MM-DD的date格式
        """
        return datetime.datetime.strptime(datetime.datetime.today().strftime("%Y-%m-%d"), '%Y-%m-%d').date()

    @classmethod
    def __get_last_date(cls, freq='day/'):
        date_data = pd.read_csv(STOCK_URL + freq + cls.code + '.csv', usecols=['date'])
        print('读取文件{}'.format(cls.code + '.csv'))
        if date_data.count().date == 0:
            return False
        else:
            last_date = date_data.iloc[-1, 0]
            return datetime.datetime.strptime(last_date, "%Y-%m-%d")

    @classmethod
    def __result_show(cls, freq='day/'):
        print('{} 存储完成，已更新至{}'.format((cls.code + '.csv'), cls.__get_last_date(freq=freq).strftime('%Y-%m-%d')))
        # TODO Log记录

    @classmethod
    def __get_date_day(cls):
        # 登陆系统
        cls.__login()

        # 获取沪深A股历史K线数据
        # 详细指标参数，参见“历史行情指标参数”章节；“分钟线”参数与“日线”参数不同。
        # 分钟线指标：date,time,code,open,high,low,close,volume,amount,adjustflag
        rs = bs.query_history_k_data_plus(cls.code,
                                          'date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,'
                                          'tradestatus,pctChg,isST',
                                          start_date=cls.start_date, end_date=cls.end_date,
                                          frequency='d', adjustflag='3')
        # if rs.error_code == 0:
        #     return
        # else:
        #     print('query_history_k_data_plus respond error_code:' + rs.error_code)
        #     print('query_history_k_data_plus respond  error_msg:' + rs.error_msg)

        # 打印结果集
        data_list = []
        while (rs.error_code == '0') & rs.next():
            # 获取一条记录，将记录合并在一起
            data_list.append(rs.get_row_data())
        result = pd.DataFrame(data_list, columns=rs.fields)
        # 登出系统
        bs.logout()
        return result

    @classmethod
    def __get_date_minute(cls, frequency='5'):
        cls.__login()

        # 获取沪深A股历史K线数据
        # 详细指标参数，参见“历史行情指标参数”章节；“分钟线”参数与“日线”参数不同。
        # 分钟线指标：date,time,code,open,high,low,close,volume,amount,adjustflag
        rs = bs.query_history_k_data_plus(cls.code,
                                          'date,time,code,open,high,low,close,volume,amount,adjustflag',
                                          start_date=cls.start_date, end_date=cls.end_date,
                                          frequency=frequency, adjustflag='3')
        # if rs.error_code == 0:
        #     return
        # else:
        #     print('query_history_k_data_plus respond error_code:' + rs.error_code)
        #     print('query_history_k_data_plus respond  error_msg:' + rs.error_msg)

        # 打印结果集
        data_list = []
        while (rs.error_code == '0') & rs.next():
            # 获取一条记录，将记录合并在一起
            data_list.append(rs.get_row_data())
        result = pd.DataFrame(data_list, columns=rs.fields)
        # 登出系统
        # TODO 进度条
        bs.logout()
        return result

    @classmethod
    def init_stock_day(cls):
        result = cls.__get_date_day()
        # 本地化存储CSV
        if result.count().date == 0:
            print('{} has no daily date.'.format(cls.code))
        else:
            result.to_csv(STOCK_URL + 'day/' + cls.code + '.csv', mode='w', index=False)
            cls.__result_show(freq='day/')
            cls.wait_for_seconds()

    @classmethod
    def init_stock_minute(cls):
        print('Trying init {} 5min date.'.format(cls.code))
        result = cls.__get_date_minute()
        # 本地化存储CSV
        if result.count().date == 0:
            print('{} has no 5min date.'.format(cls.code))
        else:
            result.to_csv(STOCK_URL + 'min/' + cls.code + '.csv', mode='w', index=False)
            cls.wait_for_seconds()
            cls.__result_show(freq='min/')

    @classmethod
    def up_to_date_day(cls):
        url = 'day/'
        try:
            last_date = cls.__get_last_date(freq=url)
            check_day = cls.today_str()
            print('正在读取文件{}'.format(cls.code + '.csv'))
            # TODO 时间比较BUG
            h = datetime.datetime.now().hour
            if h <= 16:
                check_day = (cls.today_date() + datetime.timedelta(days=-1)).strftime("%Y-%m-%d")
            if last_date.strftime("%Y-%m-%d") == check_day:
                print('{}当前数据已经最新'.format(cls.code))
            else:
                cls.start_date = (last_date + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                cls.end_date = datetime.datetime.now().strftime('%Y-%m-%d')
                result = cls.__get_date_day()
                # 向CSV末尾追加数据
                if result.count().date > 0:
                    result.to_csv(STOCK_URL + url + cls.code + '.csv', mode='a', header=False, index=False)
                    cls.__result_show(freq=url)
                    cls.wait_for_seconds()
                else:
                    print('{} has no 5min date.'.format(cls.code))
        except Exception as e:
            print('未找到{}.CSV文件'.format(cls.code))
            cls.start_date = '2006-01-01'
            cls.end_date = datetime.datetime.now().strftime('%Y-%m-%d')
            cls.init_stock_day()

    @classmethod
    def up_to_date_minute(cls):
        url = 'min/'
        try:
            last_date = cls.__get_last_date(freq=url)
            if not last_date:
                print('{} has no 5min date.')
                return
            print('正在读取文件{}'.format(cls.code + '.csv'))
            # TODO 时间比较BUG
            h = datetime.datetime.now().hour

            if h <= 16:
                # 16:00 前根据前一天来确定更新校验日期
                check_day = (cls.today_date() + datetime.timedelta(days=-1)).strftime("%Y-%m-%d")
            if last_date.strftime("%Y-%m-%d") == check_day:
                print('{}当前数据已经最新'.format(cls.code))
            else:
                # 数据并非最新，进行更新
                cls.start_date = (last_date + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                cls.end_date = datetime.datetime.now().strftime('%Y-%m-%d')
                result = cls.__get_date_minute()
                # 向CSV末尾追加数据
                if result.count().date > 0:
                    result.to_csv(STOCK_URL + url + cls.code + '.csv', mode='a', header=False, index=False)
                    cls.__result_show(freq=url)
                    cls.wait_for_seconds()
                else:
                    print('{} has no 5min date.'.format(cls.code))

        except Exception as e:
            print('未找到{}.CSV文件'.format(cls.code))
            cls.start_date = '2006-01-01'
            cls.end_date = datetime.datetime.now().strftime('%Y-%m-%d')
            cls.init_stock_minute()

    @classmethod
    def get_all_stock_code(cls):
        date = cls.today_str()
        cls.__login()

        # 获取证券信息
        rs = bs.query_all_stock(day=date)
        # print('query_all_stock respond error_code:' + rs.error_code)
        # print('query_all_stock respond  error_msg:' + rs.error_msg)

        # 打印结果集
        data_list = []
        while (rs.error_code == '0') & rs.next():
            # 获取一条记录，将记录合并在一起
            data_list.append(rs.get_row_data())
        result = pd.DataFrame(data_list, columns=rs.fields)
        # 结果集输出到csv文件
        result.to_csv(STOCK_URL + 'all_stock.csv', mode='w', index=False, encoding="GBK")
        cls.wait_for_seconds()

        # 登出系统
        bs.logout()

    @classmethod
    def update_all(cls):
        try:
            code_data = pd.read_csv(STOCK_URL + 'all_stock.csv', usecols=['code'])
        except Exception as e:
            cls.get_all_stock_code()
            cls.update_all()

        start = time.clock()
        for row in code_data.iterrows():
            s = row[1].code
            cls.code = s
            cls.up_to_date_day()
            print('{} is done! It cost {} seconds'.format(s, (format(time.clock() - start, '.2f'))))

        print("All Day Data Done!")
        for row in code_data.iterrows():
            s = row[1].code
            cls.code = s
            cls.up_to_date_minute()
            print('{} is done! It cost {} seconds'.format(s, (format(time.clock() - start, '.2f'))))

    @staticmethod
    def start_update_all_stock():
        t = Process(target=update_all_stock, name='BaoStock_update_all_stock')
        DataManager.process_register(t)
        print("BaoStock_update_all_stock is running!!")

    @staticmethod
    def wait_for_seconds():
        time.sleep(2)


def update_all_stock():
    BaoStock.update_all()
