from ginkgo.data.ginkgo_data import GDATA
from ginkgo.libs.ginkgo_logger import GLOG
import logging


if __name__ == "__main__":
    GLOG.set_level(logging.INFO)
    GDATA.create_all()
    GDATA.update_stock_info()
    GDATA.update_trade_calendar()
    GDATA.update_all_cn_adjustfactor_aysnc()
    GDATA.update_all_cn_daybar_aysnc()
    GDATA.update_all_cn_tick_aysnc(fast_mode=False)
    # GDATA.update_all_cn_tick_aysnc(fast_mode=True)
