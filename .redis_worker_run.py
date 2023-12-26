from ginkgo.data.ginkgo_data import GDATA
import multiprocessing


if __name__ == "__main__":
    cpu_count = multiprocessing.cpu_count()
    print(f"Current CPU: {cpu_count}")
    cpu_count = 0.8 * cpu_count
    cpu_count = int(cpu_count)
    print(f"After time 0.8, final count is {cpu_count}")
    GDATA.run_redis_worker(cpu_count)
