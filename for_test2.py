from src.ginkgo.data.ginkgo_data import GDATA
from src.ginkgo.data.drivers.ginkgo_kafka import *


# GDATA.send_signal_stop_dataworker()
# GDATA.send_signal_update_calender()

GDATA.send_signal_to_liveengine("test002", "stop")
# msg_count = get_unconsumed_message("live_control")
# print(msg_count)
