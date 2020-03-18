from multiprocessing import Process
from scrapy.crawler import CrawlerProcess
from app.ip_proxy.setting import DATA_URL, DOWN_MIDDLEWARES
from app.beu_spider.beu_spider.spiders.httpbin import HTTPBinIPSpider, HTTPBinUserAgentSpider
from app.beu_spider.beu_spider.spiders.ip_proxy import WuYouProxySpider
from app.ip_proxy.ip_proxy import IPProxyManager


def wuyou(file_name='spiderdata'):
    file_ulr = DATA_URL + file_name + '.json'
    settings = dict(
        FEED_URI=file_ulr,
        DOWNLOADER_MIDDLEWARES=DOWN_MIDDLEWARES
    )
    process = CrawlerProcess(settings)
    process.crawl(HTTPBinUserAgentSpider)
    process.start()  # the script will block here until the crawling is finished


def start_thread():
    t = Process(target=wuyou, kwargs={"file_name": 'hh'}, name='wuyou_spider')
    IPProxyManager.process_register(t)
    print("主线程")
