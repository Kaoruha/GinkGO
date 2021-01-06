DATA_URL = 'static/spider/'  # 爬取数据本地缓存地址

DATA_DRIVER = 'MONGODB'  # 数据库驱动，mongodb、mysql

DOWN_MIDDLEWARES = {
    'app.beu_spider.beu_spider.middlewares.BeuSpiderDownloaderMiddleware': 543,
    'app.beu_spider.beu_spider.middlewares.RandomUserAgentMiddleware': 543,
    # 'beu_spider.middlewares.RandomIPProxyMiddleware': 543,
}
