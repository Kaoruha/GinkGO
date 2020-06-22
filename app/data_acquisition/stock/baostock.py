import baostock as bs
import pandas as pd
from app.config.setting import STOCK_URL
import datetime


class BaoStock(object):
    def __init__(self, code='sh.600000', start_date='2006-01-01', end_date=''):
        self.code = code
        self.start_date = start_date
        if end_date == '':
            self.end_date = datetime.datetime.now().strftime('%Y-%m-%d')
        else:
            self.end_date = end_date

    @staticmethod
    def today_str():
        return datetime.datetime.now().strftime('%Y-%m-%d')

    @staticmethod
    def today_date():
        return datetime.datetime.strptime(datetime.datetime.today().strftime("%Y-%m-%d"), '%Y-%m-%d').date()

    def __get_last_date(self, freq='day/'):
        date_data = pd.read_csv(STOCK_URL + freq + self.code + '.csv', usecols=['date'])
        print('读取文件{}'.format(self.code + '.csv'))
        last_date = date_data.iloc[-1, 0]
        return datetime.datetime.strptime(last_date, "%Y-%m-%d")

    def __result_show(self, freq='day/'):
        print('{} 存储完成，已更新至{}'.format((self.code + '.csv'), self.__get_last_date(freq=freq)))
        # TODO Log记录

    def __get_date_day(self):
        # 登陆系统
        lg = bs.login()
        # 显示登陆返回信息
        print('login respond error_code:' + lg.error_code)
        print('login respond  error_msg:' + lg.error_msg)

        # 获取沪深A股历史K线数据
        # 详细指标参数，参见“历史行情指标参数”章节；“分钟线”参数与“日线”参数不同。
        # 分钟线指标：date,time,code,open,high,low,close,volume,amount,adjustflag
        rs = bs.query_history_k_data_plus(self.code,
                                          'date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,'
                                          'tradestatus,pctChg,isST',
                                          start_date=self.start_date, end_date=self.end_date,
                                          frequency='d', adjustflag='3')
        print('query_history_k_data_plus respond error_code:' + rs.error_code)
        print('query_history_k_data_plus respond  error_msg:' + rs.error_msg)

        # 打印结果集
        data_list = []
        while (rs.error_code == '0') & rs.next():
            # 获取一条记录，将记录合并在一起
            data_list.append(rs.get_row_data())
        result = pd.DataFrame(data_list, columns=rs.fields)
        # 登出系统
        bs.logout()
        return result

    def __get_date_minute(self, frequency='5'):
        # 登陆系统
        lg = bs.login()
        # 显示登陆返回信息
        if lg.error_code == 0:
            return
        else:
            print('login respond error_code:' + lg.error_code)
            print('login respond  error_msg:' + lg.error_msg)

        # 获取沪深A股历史K线数据
        # 详细指标参数，参见“历史行情指标参数”章节；“分钟线”参数与“日线”参数不同。
        # 分钟线指标：date,time,code,open,high,low,close,volume,amount,adjustflag
        rs = bs.query_history_k_data_plus(self.code,
                                          'date,time,code,open,high,low,close,volume,amount,adjustflag',
                                          start_date=self.start_date, end_date=self.end_date,
                                          frequency=frequency, adjustflag='3')
        if rs.error_code == 0:
            return
        else:
            print('query_history_k_data_plus respond error_code:' + rs.error_code)
            print('query_history_k_data_plus respond  error_msg:' + rs.error_msg)

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

    def init_stock_day(self):
        result = self.__get_date_day()
        # 本地化存储CSV
        result.to_csv(STOCK_URL + 'day/' + self.code + '.csv', mode='w', index=False)
        self.__result_show(freq='day/')

    def init_stock_minute(self):
        result = self.__get_date_minute()
        # 本地化存储CSV

        result.to_csv(STOCK_URL + 'min/' + self.code + '.csv', mode='w', index=False)
        self.__result_show(freq='min/')

    def up_to_date_day(self):
        url = 'day/'
        try:
            last_date = self.__get_last_date(freq=url)
            print('正在读取文件{}'.format(self.code + '.csv'))
            # TODO 时间比较BUG
            h = datetime.datetime.now().hour
            if h <= 16:
                check_day = (self.today_date() + datetime.timedelta(days=-1)).strftime("%Y-%m-%d")
            if last_date.strftime("%Y-%m-%d") == check_day:
                print('{}当前数据已经最新'.format(self.code))
            else:
                self.start_date = (last_date + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                self.end_date = datetime.datetime.now().strftime('%Y-%m-%d')
                result = self.__get_date_day()
                # 向CSV末尾追加数据
                result.to_csv(STOCK_URL + url + self.code + '.csv', mode='a', header=False, index=False)
                self.__result_show(freq=url)
        except Exception as e:
            print('未找到对应CSV文件')
            self.start_date = '2006-01-01'
            self.end_date = datetime.datetime.now().strftime('%Y-%m-%d')
            self.init_stock_day()

    def up_to_date_minute(self):
        url = 'min/'
        try:
            last_date = self.__get_last_date(freq=url)
            print('正在读取文件{}'.format(self.code + '.csv'))
            # TODO 时间比较BUG
            h = datetime.datetime.now().hour
            if h <= 16:
                check_day = (self.today_date() + datetime.timedelta(days=-1)).strftime("%Y-%m-%d")
            if last_date.strftime("%Y-%m-%d") == check_day:
                print('{}当前数据已经最新'.format(self.code))
            else:
                self.start_date = (last_date + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                self.end_date = datetime.datetime.now().strftime('%Y-%m-%d')
                result = self.__get_date_minute()
                # 向CSV末尾追加数据
                result.to_csv(STOCK_URL + url + self.code + '.csv', mode='a', header=False, index=False)
                self.__result_show(freq=url)
        except Exception as e:
            print('未找到对应CSV文件')
            self.start_date = '2006-01-01'
            self.end_date = datetime.datetime.now().strftime('%Y-%m-%d')
            self.init_stock_minute()

    @classmethod
    def get_all_stock(cls, date='2020-06-01'):
        # 登陆系统
        lg = bs.login()
        # 显示登陆返回信息
        print('login respond error_code:' + lg.error_code)
        print('login respond  error_msg:' + lg.error_msg)

        # 获取证券信息
        t = cls.today_str()
        print(t)
        print(type(t))
        rs = bs.query_all_stock(day=date)
        print('query_all_stock respond error_code:' + rs.error_code)
        print('query_all_stock respond  error_msg:' + rs.error_msg)

        # 打印结果集
        data_list = []
        while (rs.error_code == '0') & rs.next():
            # 获取一条记录，将记录合并在一起
            data_list.append(rs.get_row_data())
        result = pd.DataFrame(data_list, columns=rs.fields)
        # 结果集输出到csv文件
        result.to_csv(STOCK_URL + 'all_stock.csv', mode='w', index=False, encoding="GBK")

        # 登出系统
        bs.logout()

    @classmethod
    def update_all(cls):
        code_data = pd.read_csv(STOCK_URL + 'all_stock.csv', usecols=['code'])
        for row in code_data.iterrows():
            s = row[1].code
            temp = BaoStock(code=s)
            temp.up_to_date_day()
            print('{} is done!'.format(s))
            # time.sleep(1)

        print("All Day Data Done!")
        # for row in code_data.iterrows():
        #     s = row[1].code
        #     temp = BaoStock(code=s)
        #     temp.up_to_date_minute()
        #     print('{} is done!'.format(s))
        #     time.sleep(5)
