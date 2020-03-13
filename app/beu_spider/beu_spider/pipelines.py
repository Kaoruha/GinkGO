# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
import codecs
import json


class BeuSpiderPipeline(object):
    def process_item(self, item, spider):
        return item


class JsonPipeline(object):
    """
    将数据保存到json文件，由于文件编码问题太多，这里用codecs打开，可以避免很多编码异常问题
        在类加载时候自动打开文件，制定名称、打开类型(只读)，编码
        重载process_item，将item写入json文件，由于json.dumps处理的是dict，所以这里要把item转为dict
        为了避免编码问题，这里还要把ensure_ascii设置为false，最后将item返回回去，因为其他类可能要用到
        调用spider_closed信号量，当爬虫关闭时候，关闭文件
    """

    def __init__(self, filename='spider_data'):
        self.file = codecs.open(filename + '.json', 'w', encoding="utf-8")

    def process_item(self, item, spider):
        lines = json.dumps(dict(item), ensure_ascii=False) + "\n"
        self.file.write(lines)
        return item

    def spider_closed(self, spider):
        self.file.close()
