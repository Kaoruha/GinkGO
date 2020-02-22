import scrapy
import datetime
import time


class StockDetailsCnSpider(scrapy.Spider):
    name = 'stock_cn'
    allowed_domains = ['http://market.finance.sina.com.cn/']
    source_url = 'http://market.finance.sina.com.cn/transHis.php?symbol='
    stock_sn = 'sz000001'
    date = '2020-02-05'
    page = 70
    start_urls = [source_url + stock_sn + '&date=' + date + '&page=' + str(page)]
    target_url = source_url + stock_sn + '&date=' + date + '&page=' + str(page)
    wait_for_seconds = 1
    target_date = '2020-02-01'

    def __init__(self, name='stock_cn', stock_sn='sz000001', date='2020-02-04'):
        self.name = name
        self.stock_sn = stock_sn
        self.date = date

    @classmethod
    def parse(cls, response):
        try:
            # 1. 股市休市时，页面返回的是"输入的代码有误或没有交易数据"，用error_msg接收
            error_msg = response.xpath('/html/body//div[@class="dataOuter"]/div/text()').get().strip()
            is_today_off = True if error_msg == '输入的代码有误或没有交易数据' else False
            # 2. 如果今天休市，则爬取下一天的数据，直到目标日期
            if is_today_off:
                print(cls.date + '休市')
                cls.__change_date(date_delta=-1)
                # 2.1. 如果超过期限，则返回
                if cls.__is_overdue(current_date=cls.date):
                    print('今天休市，也超过期限')
                    return
                # 2.2. 如果没超过期限，则爬取
                else:
                    print('今天休市，准备爬取下一天')
                    time.sleep(cls.wait_for_seconds)
                    yield scrapy.Request(cls.target_url, callback=cls.parse, dont_filter=True)
            # 3. 如果今天开市，则执行爬虫操作
            else:
                selectors = response.xpath('//tbody/tr')
                count = len(selectors)
                # 3.1. 如果response的list为空，说明当天数据爬完了，开始下一天的数据爬取
                if count == 0:
                    cls.__change_date(date_delta=-1)
                    # 2.1. 如果超过期限，则返回
                    if cls.__is_overdue(current_date=cls.date):
                        print('今儿个开市，但是超过期限')
                        return
                    # 2.2. 如果没超过期限，则爬取
                    else:
                        print('今儿个开市，数据爬完准备开始爬取下一天')
                        time.sleep(cls.wait_for_seconds)
                        yield scrapy.Request(cls.target_url, callback=cls.parse, dont_filter=True)
                # 3.2. 如果response的list不为空，则开始解析
                else:
                    for selector in selectors:
                        timestamp = selector.xpath('./th[1]/text()').get()
                        mkt_value = selector.xpath('./td[1]/text()').get()
                        value_change = selector.xpath('./td[2]/text()').get()
                        transaction_volume = selector.xpath('./td[3]/text()').get()
                        transaction_amount = selector.xpath('./td[4]/text()').get()
                        buy_or_sale = selector.xpath('./th[2]/h5/text()|./th[2]/h6/text()').get()
                        # TODO 处理所有数据
                        print(timestamp, mkt_value)
                    # 3.3. 本页数据处理完毕后，休息片刻进行下一页数据的爬取
                    print(cls.date, '爬完第', cls.page, '页，准备爬下一页')
                    cls.__next_page()
                    time.sleep(cls.wait_for_seconds)
                    yield scrapy.Request(cls.target_url, callback=cls.parse, dont_filter=True)
                    # TODO 需要反反爬虫来提升效率
        except Exception as e:
            raise e

    @classmethod
    def __next_page(cls):
        cls.page += 1
        cls.__url_update()

    @classmethod
    def __change_date(cls, date_delta=-1):
        current_date = datetime.datetime.strptime(cls.date, '%Y-%m-%d')
        target_date = current_date + datetime.timedelta(days=date_delta)  # days参数1是明天，-1即是昨天。
        cls.date = target_date.date().strftime('%Y-%m-%d')
        cls.page = 1
        cls.__url_update()


    @classmethod
    def __url_update(cls):
        cls.target_url = cls.source_url + cls.stock_sn + '&date=' + cls.date + '&page=' + str(cls.page)

    @classmethod
    def __is_overdue(cls, current_date):
        try:
            now = datetime.datetime.strptime(current_date, "%Y-%m-%d")
        except Exception as e:
            raise e
        deadline = datetime.datetime.strptime(cls.target_date, "%Y-%m-%d")
        # 如果过期，返回Ture
        if now < deadline:
            return True
        else:
            # 如果没过期，返回False
            return False
