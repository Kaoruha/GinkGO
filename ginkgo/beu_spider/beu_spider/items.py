# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


# class BeuSpiderItem(scrapy.Item):
#     # define the fields for your item here like:
#     # name = scrapy.Field()
#     pass


class IpItem(scrapy.Item):
    schema = scrapy.Field()  # 代理的类型 http/https
    ip = scrapy.Field()  # 代理的IP地址
    port = scrapy.Field()  # 代理的端口号
    original = scrapy.Field()  # 代理来源
    update_time = scrapy.Field()  # 代理状态更新时间

class StockItem(scrapy.Item):
    timestamp = scrapy.Field()  # 时间戳
    mkt_value = scrapy.Field()  # 市场价
    value_change = scrapy.Field()  # 涨跌幅
    volume = scrapy.Field()  # 成交量
    amount = scrapy.Field()  # 成交额
    buy_or_sale = scrapy.Field()  # 买入还是卖出
