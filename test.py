from ginkgo.libs.ginkgo_thread import GinkgoThreadManager
from ginkgo.data import *

if __name__ == "__main__":
    # send_signal_kill_a_worker()
    gtm = GinkgoThreadManager()
    # a = create_redis_connection().get(gtm.watchdog_name)
    # print(a)
    gtm.run_data_worker()
