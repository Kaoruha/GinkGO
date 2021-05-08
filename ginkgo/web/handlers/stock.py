from ginkgo.data.ginkgo_mongo import ginkgo_mongo as gm
from ginkgo.web.handlers.base_handler import BaseHandler
import time

URL = "/api/stock"


class GetStockInfoHandler(BaseHandler):
    url_prefix = URL + "/get_stock_info"

    def get(self, *args, **kwargs):
        start = time.time()
        stock_info = gm.get_all_stockcode_by_mongo().fillna(1)
        end1 = time.time()
        res = []

        for index, row in stock_info.iterrows():
            item = {
                "code": row.code,
                "name": row.code_name,
                "trade_status": row.trade_status,
                # 'has_min5': row.has_min5
            }
            res.append(item)
        end2 = time.time()

        print(
            f"查询StockInfoLists耗时: {round(end2-start, 3)}s   数据库查询耗时: {round(end1-start, 3)}s  Json拼接耗时: {round(end2-start, 3)}s"
        )
        self.finish({"data": res})


class GetStockDetail(BaseHandler):
    url_prefix = URL + "/get_stock_detail"

    def get(self, *args, **kwargs):
        res = {"name": 12, "age": 10}
        self.finish(res)
