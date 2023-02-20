"""
@Author:sunny
@Create:2020-06-29  23-34-36
@Description:新浪股票分钟交易数据获取
"""
from multiprocessing import Process
from scrapy.crawler import CrawlerProcess

from app.data.manager import DataManager
from app.data.setting import DATA_URL, DOWN_MIDDLEWARES
from app.beu_spider.beu_spider.spiders.stock_details_cn import StockDetailsCnSpider


def stock(file_name='spiderdata'):
    file_ulr = DATA_URL + file_name + '.json'
    settings = dict(
        FEED_URI=file_ulr,
        DOWNLOADER_MIDDLEWARES=DOWN_MIDDLEWARES
    )
    process = CrawlerProcess(settings)
    StockDetailsCnSpider.initialize(
        stock_sn='sz000002',
        start_date='2020-02-28',
        end_date='2020-03-01'
    )
    process.crawl(StockDetailsCnSpider)
    process.start()  # the script will block here until the crawling is finished


def start_thread():
    t = Process(target=stock, kwargs={"file_name": 'sz000001'}, name='scrapy')
    DataManager.process_register(t)
    print("主线程")