from ginkgo.data.ginkgo_data import GinkgoData
from ginkgo.enums import FREQUENCY_TYPES


gd = GinkgoData()


t = gd.get_bar_lastdate("sh.000002", FREQUENCY_TYPES.DAY)
print(t)
