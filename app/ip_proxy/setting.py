DATA_URL = 'static/spider/'  # 爬取数据临时存储地址

DOWN_MIDDLEWARES = {
    'app.beu_spider.beu_spider.middlewares.BeuSpiderDownloaderMiddleware': 543,
    'app.beu_spider.beu_spider.middlewares.RandomUserAgentMiddleware': 543,
    # 'beu_spider.middlewares.RandomIPProxyMiddleware': 543,
}
