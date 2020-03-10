import scrapy
import datetime
from ..items import IpItem


# 无忧代理 http://www.data5u.com/
# 代理66 http://www.66ip.cn/
# 西刺代理 http://www.xicidaili.com
# guobanjia http://www.goubanjia.com/
# 快代理 https://www.kuaidaili.com
# 码农代理 https://proxy.coderbusy.com/
# 云代理 http://www.ip3366.net/free/
# 免费代理库 http://ip.jiangxianli.com/?page=1
# 齐云代理 http://www.qydaili.com/free/?action=china&page=1
# 89免费代理 http://www.89ip.cn/index.html


class WuYouProxySpider(scrapy.Spider):
    name = 'wuyou_proxy'
    allowed_domains = ['http://www.data5u.com/']
    start_urls = ['http://www.data5u.com/']
    proxy_list = []

    @classmethod
    def parse(cls, response):
        try:
            base = response.xpath('//ul/li/ul')
            for proxy in base:
                ip = proxy.xpath('./span[1]/li/text()').get()  # IP地址
                port = proxy.xpath('./span[2]/li/text()').get()  # 端口号
                schema = proxy.xpath('./span[4]/li/text()').get()  # 代理类型
                temp = IpItem(
                    ip=ip,
                    port=port,
                    schema=schema,
                    update_time=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    original='无忧代理'
                )
                if ip != 'IP':
                    yield temp
            # IPProxy.add_all(items=cls.proxy_list)
        except Exception as e:
            raise e
