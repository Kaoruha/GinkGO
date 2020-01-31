import scrapy


class StockDetailsCnSpider(scrapy.Spider):
    name = 'stock_details_cn'
    allowed_domains = ['http://market.finance.sina.com.cn/']
    source_url = 'http://market.finance.sina.com.cn/transHis.php?symbol='
    stock_sn = 'sz000001'
    date = '2018-04-27'
    page = 1
    start_urls = [source_url + stock_sn + '&date=' + date + '&page=' + str(page)]

    def parse(self, response):
        try:
            selectors = response.xpath('//tbody/tr')
            for selector in selectors:
                timestamp = selector.xpath('./th[1]/text()').get()
                mkt_value = selector.xpath('./td[1]/text()').get()
                value_change = selector.xpath('./td[2]/text()').get()
                volume = selector.xpath('./td[3]/text()').get()
                total_volume = selector.xpath('./td[4]/text()').get()
                buy_or_sale = selector.xpath('./th[2]/h5/text()|./th[2]/h6/text()').get()
        except Exception as e:

            return
