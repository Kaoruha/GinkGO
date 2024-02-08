from ginkgo.data.ginkgo_data import GDATA
import multiprocessing


if __name__ == "__main__":
    GDATA.run_redis_worker(2)
