from ginkgo.data.ginkgo_data import GinkgoData
from ginkgo.data.models import *

if __name__ == "__main__":
    gd = GinkgoData()
    gd.create_all()
    gd.update_cn_codelist_to_latest_entire_async()
    gd.update_bar_to_latest_entire_async()
