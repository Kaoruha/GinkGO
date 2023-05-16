from ginkgo.data.ginkgo_data import GinkgoData


gd = GinkgoData()


gd.create_all()
gd.update_cn_codelist_to_latest_entire_async()

gd.update_bar_to_latest_entire_async()
