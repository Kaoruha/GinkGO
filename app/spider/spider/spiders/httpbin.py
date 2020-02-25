import scrapy
import datetime
import time


class HTTPBinSpider(scrapy.Spider):
    """
    爬取User-Agent列表，并存储
    保持更新
    """
    name = 'httpbin'
    allowed_domains = ['httpbin.org']
    start_urls = ['http://httpbin.org/user-agent']

    def parse(self, response):
        try:
            print(response.text)
            yield scrapy.Request(self.start_urls[0], callback=self.parse, dont_filter=True)
        except Exception as e:
            raise e
