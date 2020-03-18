# -*- coding: utf-8 -*-
import scrapy
import time


class HTTPBinUserAgentSpider(scrapy.Spider):
    """
    爬取User-Agent列表，并存储
    保持更新
    """
    name = 'user_agent_test'
    allowed_domains = ['httpbin.org']
    start_urls = ['http://httpbin.org/user-agent']

    def parse(self, response):
        try:
            print(response.text)
            time.sleep(2)
            yield scrapy.Request(self.start_urls[0], callback=self.parse, dont_filter=True)
        except Exception as e:
            raise e


class HTTPBinIPSpider(scrapy.Spider):
    """
    爬取IP列表，并存储
    保持更新
    """
    name = 'ip_test'
    allowed_domains = ['httpbin.org']
    start_urls = ['http://httpbin.org/ip']

    def parse(self, response):
        try:
            print(response.text)
            time.sleep(12)
            yield scrapy.Request(self.start_urls[0], callback=self.parse, dont_filter=True)
        except Exception as e:
            raise e
