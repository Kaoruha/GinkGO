from ginkgo.backtest.engines.live_engine import LiveEngine
from ginkgo.data.ginkgo_data import GDATA

# e = LiveEngine("4d79d46058184381a478620666830318")
# e.start()

GDATA.send_signal_to_liveengine("4d79d46058184381a478620666830318", "restart")

# res = GDATA.clean_live_status()
# print(res)
