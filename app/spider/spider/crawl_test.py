from scrapy import cmdline
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from app.spider.spider.spiders.ip_proxy import WuYouProxySpider

if __name__ == '__main__':
    # cmdline.execute("scrapy crawl wuyou_proxy".split())
    print('Start!')
    process = CrawlerProcess(get_project_settings())
    process.crawl(WuYouProxySpider)
    process.start()
    print('Done!')

