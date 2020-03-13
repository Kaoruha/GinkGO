from multiprocessing import Process
from scrapy.crawler import CrawlerProcess
from app.ip_proxy.setting import DATA_URL
from app.beu_spider.beu_spider.spiders.httpbin import HTTPBinIPSpider, HTTPBinUserAgentSpider
from app.beu_spider.beu_spider.spiders.ip_proxy import WuYouProxySpider

download_middlewares = {
    'app.beu_spider.beu_spider.middlewares.BeuSpiderDownloaderMiddleware': 543,
    'app.beu_spider.beu_spider.middlewares.RandomUserAgentMiddleware': 543,
    # 'beu_spider.middlewares.RandomIPProxyMiddleware': 543,
}


def wuyou(file_name='spiderdata'):
    file_ulr = DATA_URL + file_name + '.json'
    settings = dict(
        FEED_URI=file_ulr,
        DOWNLOADER_MIDDLEWARES=download_middlewares
    )
    process = CrawlerProcess(settings)
    process.crawl(HTTPBinUserAgentSpider)
    process.start()  # the script will block here until the crawling is finished


def start_thread():
    t = Process(target=wuyou, kwargs={"file_name": 'fuckme'})
    # t = Process(target=test)
    t.start()
    print("主线程")
