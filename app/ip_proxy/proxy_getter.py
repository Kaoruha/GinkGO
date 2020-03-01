"""
"""
import os

from scrapy import cmdline
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from app import spider
from app.spider.spider.spiders.ip_proxy import WuYouProxySpider
from app.ip_proxy.proxy_helper import start_crawl


def wuyou_proxy_get():
    # 获取spiders文件所在的目录,并将工作目录切换到spider所在目录下
    os.chdir(os.path.dirname(spider.__file__))
    print(os.path.dirname(spider.__file__))
    cmdline.execute("scrapy crawl wuyou_proxy".split())
    return 'Success'
