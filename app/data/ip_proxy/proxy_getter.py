"""
IP代理获取
"""
from multiprocessing import Process
from scrapy.crawler import CrawlerProcess
from app.data.setting import DATA_URL, DOWN_MIDDLEWARES
from app.beu_spider.beu_spider.spiders.httpbin import HTTPBinUserAgentSpider,HTTPBinIPSpider
from app.beu_spider.beu_spider.spiders.ip_proxy import WuYouProxySpider
from app.data.manager import DataManager


def wuyou(file_name='spiderdata'):
    file_ulr = DATA_URL + file_name + '.json'
    settings = dict(
        FEED_URI=file_ulr,
        DOWNLOADER_MIDDLEWARES=DOWN_MIDDLEWARES
    )
    process = CrawlerProcess(settings)
    process.crawl(WuYouProxySpider)
    process.start()  # the script will block here until the crawling is finished


def start_thread():
    t = Process(target=wuyou, kwargs={"file_name": 'ipproxy'}, name='wuyou_spider')
    DataManager.process_register(t)
    print("主线程")
