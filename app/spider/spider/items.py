# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class SpiderItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass


class IpItem(scrapy.Item):
    schema = scrapy.Field()  # 代理的类型 http/https
    ip = scrapy.Field()  # 代理的IP地址
    port = scrapy.Field()  # 代理的端口号
    original = scrapy.Field()  # 代理来源
    update_time = scrapy.Field()  # 代理状态更新时间
