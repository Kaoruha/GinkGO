import datetime
from ginkgo.data.ginkgo_mongo import ginkgo_mongo as gm


def get_next_trade_date(self, code, current_date):
    """
    根据标的代码以及当前日期，返回最近的一个可交易日期

    此处利用到了未来的数据，需要当心
    """
    start = datetime.datetime.strptime(current_date, "%Y-%m-%d").date()
    end = (start + datetime.timedelta(days=30)).strftime("%Y-%m-%d")

    try:
        df = gm.query_stock(
            code=code,
            start_date=current_date,
            end_date=end,
            frequency="d",
            adjust_flag=3,
        )["date"].head(2)
        return df.iloc[1]
    except Exception as e:
        return None
