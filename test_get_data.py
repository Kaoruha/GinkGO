import pandas as pd
from ginkgo_server.data.ginkgo_mongo import ginkgo_mongo as gm


if __name__ == "__main__":
    gm.update_all_coin()
