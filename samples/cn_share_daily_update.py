import logging
from ginkgo.data.ginkgo_data import GDATA
from ginkgo import GLOG


if __name__ == "__main__":
    GLOG.logger.setLevel(logging.INFO)
    GDATA.create_all()
    GDATA.update_stock_info()
    GDATA.update_trade_calendar()
    GDATA.update_all_cn_daybar_aysnc()
    GDATA.update_all_cn_adjustfactor_aysnc()
