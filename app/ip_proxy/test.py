from multiprocessing import Process
from scrapy.crawler import CrawlerProcess
from app.beu_spider.beu_spider.spiders.stock_details_cn import StockDetailsCnSpider
from app.beu_spider.beu_spider.spiders.httpbin import HTTPBinIPSpider, HTTPBinUserAgentSpider
from app.beu_spider.beu_spider.spiders.ip_proxy import WuYouProxySpider
from scrapy.utils.project import get_project_settings


# process.start()  # the script will block here until the crawling is finished

def stock():
    process = CrawlerProcess({
        'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)'
    })
    StockDetailsCnSpider.set_date('2020-01-02')
    process.crawl(StockDetailsCnSpider)
    process.start()  # the script will block here until the crawling is finished


def ip():
    process = CrawlerProcess({
        'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)'
    })
    StockDetailsCnSpider.set_date('2020-01-02')
    process.crawl(HTTPBinIPSpider)
    process.start()  # the script will block here until the crawling is finished


def wuyou(file_name='spiderdata'):
    file_ulr = 'static/spider/' + file_name + '.json'
    settings = dict(
        USER_AGENT='Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)',
        FEED_URI=file_ulr,
        meta={'proxy': "http://163.204.245.146:9999"}
    )
    process = CrawlerProcess(settings)
    process.crawl(WuYouProxySpider)
    process.start()  # the script will block here until the crawling is finished
    # TODO 中间件

def test():
    process = CrawlerProcess(get_project_settings())
    process.crawl(WuYouProxySpider)  # scrapy项目中spider的name值
    process.start()


def start_thread():
    t = Process(target=wuyou, kwargs={"file_name": 'fuckme'})
    # t = Process(target=test)
    t.start()
    print("主线程")
