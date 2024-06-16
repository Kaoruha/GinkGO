import os
import sys
import time
import datetime
import signal
import psutil
import threading
from rich.live import Live
from rich.console import Console

from ginkgo.data.ginkgo_data import GDATA
from ginkgo.data.drivers import GinkgoConsumer
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.notifier.notifier_beep import beep
from ginkgo.libs.ginkgo_logger import GLOG


console = Console()


class GinkgoThreadManager:
    def __init__(self):
        super(GinkgoThreadManager, self).__init__()
        self.thread_pool_name = "ginkgo_thread_pool"
        self.dataworker_pool_name = "ginkgo_dataworker"
        self.lock = threading.Lock()  # TODO
        self._redis = None
        self.max_try = 5
        self.watchdog_name = "watch_dog"
        self.maincontrol_name = "main_control"

    def run_dataworker(self):
        pid = os.getpid()
        GDATA.get_redis().lpush(self.dataworker_pool_name, str(pid))
        error_time = 0
        GLOG.reset_logfile("dataworker.log")
        while True:
            try:
                con = GinkgoConsumer("ginkgo_data_update", "ginkgo_data")
                print(
                    f"Start Listen Kafka Topic: ginkgo_data_update Group: ginkgo_data  PID:{pid}"
                )
                for msg in con.consumer:
                    beep(freq=90.7, repeat=1, delay=200, length=100)
                    error_time = 0
                    value = msg.value
                    type = value["type"]
                    code = value["code"]
                    GLOG.DEBUG(f"Got siganl. {type} {code}")

                    if type == "kill":
                        con.commit()
                        GDATA.get_redis().lrem(self.dataworker_pool_name, 0, str(pid))
                        sys.exit(0)
                    elif type == "stockinfo":
                        GDATA.update_stock_info()
                    elif type == "calender":
                        GDATA.update_cn_trade_calendar()
                    elif type == "adjust":
                        GDATA.update_cn_adjustfactor(code)
                    elif type == "bar":
                        GDATA.update_cn_daybar(code, value["fast"])
                    elif type == "tick":
                        GDATA.update_tick(code, value["fast"])
                    elif type == "other":
                        print(value)
                    con.commit()
            except Exception as e2:
                con.commit()
                error_time += 1
                if error_time > self.max_try:
                    break
                else:
                    time.sleep(min(5 * (2**error_time), 300))
        GDATA.get_redis().lrem(self.dataworker_pool_name, 0, str(pid))

    def run_dataworker_daemon(self):
        file_name = "dataworker_run.py"
        content = """ 
from ginkgo.libs.ginkgo_thread import GinkgoThreadManager

if __name__ == "__main__": 
    gtm = GinkgoThreadManager() 
    gtm.run_dataworker()
"""

        work_dir = GCONF.WORKING_PATH
        log_dir = GCONF.LOGGING_PATH
        with open(file_name, "w") as file:
            file.write(content)
        cmd = f"nohup {work_dir}/venv/bin/python -u {work_dir}/{file_name} >>{GCONF.LOGGING_PATH}/data_worker.log 2>&1 &"
        # print(cmd)
        os.system(cmd)
        # print(f"Current Worker: {self.dataworker_count}")
        count = datetime.timedelta(seconds=0)
        t0 = datetime.datetime.now()
        console.print(
            f":sun_with_face: Data Worker is [steel_blue1]RUNNING[/steel_blue1] now."
        )
        time.sleep(2)
        os.remove(f"{work_dir}/{file_name}")

    def start_multi_worker(self, count: int = 4) -> None:
        for i in range(count):
            self.run_dataworker_daemon()

    @property
    def dataworker_count(self):
        self.clean_dataworker_pool()
        return GDATA.get_redis().llen(self.dataworker_pool_name)

    def clean_dataworker_pool(self):
        exsit_list = []
        for i in range(GDATA.get_redis().llen(self.dataworker_pool_name)):
            pid = GDATA.get_redis().lpop(self.dataworker_pool_name).decode("utf-8")
            pid = int(pid)
            try:
                proc = psutil.Process(pid)
                if proc.is_running():
                    exsit_list.append(pid)
            except Exception as e:
                pass
        for i in exsit_list:
            GDATA.get_redis().lpush(self.dataworker_pool_name, str(i))

    def reset_worker_pool(self):
        while GDATA.get_redis().llen(self.dataworker_pool_name) > 0:
            pid = GDATA.get_redis().lpop(self.dataworker_pool_name).decode("utf-8")
            try:
                proc = psutil.Process(int(pid))
                if proc.is_running():
                    os.kill(int(pid), signal.SIGKILL)
                GDATA.get_redis().lrem(self.dataworker_pool_name, 0, pid)
                console.print(f":leaf_fluttering_in_wind: Kill PID: {pid}")
                time.sleep(0.4)
            except Exception as e:
                pass
        console.print(":world_map:  Reset all data worker cache in REDIS.")

    def reset_pool(self):
        while GDATA.get_redis().llen(self.thread_pool_name) > 0:
            key = GDATA.get_redis().lpop(self.thread_pool_name).decode("utf-8")
            key = key.split(self.get_thread_cache_name(""))[1]
            self.kill_thread(key)
        print("Reset all thread cache in REDIS.")

    def get_thread_cache_name(self, name: str) -> str:
        return f"ginkgo_thread_{name}"

    def get_thread_pool_list(self) -> list:
        data = GDATA.get_redis().lrange(self.thread_pool_name, 0, -1)
        return data

    def get_thread_pool_detail(self) -> dict:
        pool = self.get_thread_pool_list()
        r = {}
        for key in pool:
            key = key.decode("utf-8")
            value = GDATA.get_redis().get(key).decode("utf-8")
            key = key.split(self.get_thread_cache_name(""))[1]
            is_alive = self.get_thread_status(key)
            if is_alive:
                r[key] = {"pid": value, "alive": is_alive}
        return r

    def get_count_of_thread(self) -> int:
        cache_name = self.thread_pool_name
        if GDATA.get_redis().exists(cache_name):
            return GDATA.get_redis().llen(cache_name)
        else:
            return 0

    def add_thread(self, name: str, target: threading.Thread) -> None:
        key = self.get_thread_cache_name(name)
        if key.encode() in self.get_thread_pool_list():
            print(f"{name} exists. Please change the name and try it again.")
            return
        pid = os.getpid()
        t = threading.Thread(target=target, name=name)
        GDATA.get_redis().set(key, str(pid))
        GDATA.get_redis().lpush(self.thread_pool_name, key)
        t.start()

    def get_thread_status(self, name: str) -> bool:
        key = self.get_thread_cache_name(name)
        value = GDATA.get_redis().get(key).decode("utf-8")
        pid = int(value)
        try:
            proc = psutil.Process(int(value))
            return proc.is_running()
        except psutil.NoSuchProcess:
            GDATA.remove_from_redis(key)
            GDATA.get_redis().lrem(self.thread_pool_name, 0, key)
            print(f"No suck process, remove {key} from REDIS.")

    def kill_thread(self, name: str) -> None:
        key = self.get_thread_cache_name(name)
        if GDATA.get_redis().exists(key):
            value = GDATA.get_redis().get(key).decode("utf-8")
            pid = int(value)
            try:
                proc = psutil.Process(pid)
                if proc.is_running():
                    os.kill(pid, signal.SIGKILL)
                GDATA.remove_from_redis(key)
                GDATA.get_redis().lrem(self.thread_pool_name, 0, key)
                print(f"Kill thread:{key} pid: {pid}")
            except Exception as e:
                GDATA.remove_from_redis(key)
                GDATA.get_redis().lrem(self.thread_pool_name, 0, key)
                print(f"Remove {name} from REDIS.")

    def restart_thread(self, name: str, target) -> None:
        self.kill_thread(name)
        self.add_thread(name, target)

    def get_proc_status(self, pid: int) -> str:
        # TODO
        try:
            proc = psutil.Process(int(pid))
            if proc.is_running():
                return "RUNNING"
            elif proc.is_sleeping():
                return "SLEEPING"
            else:
                return "DEAD"
        except Exception as e:
            return "NOT EXIST"

    def main_status(self) -> str:
        temp_redis = GDATA.get_redis()
        name = self.maincontrol_name
        # TODO
        if temp_redis.exists(self.maincontrol_name):
            cache = temp_redis.get(self.maincontrol_name).decode("utf-8")
            print("get pid of main_control")
            print(cache)
            try:
                proc = psutil.Process(int(cache))
                if proc.is_running():
                    return "RUNNING"
                elif proc.is_sleeping():
                    return "SLEEPING"
                else:
                    return "DEAD"
            except Exception as e:
                return "DEAD"
        return "NOT EXIST"

    def watch_dog_status(self) -> str:
        temp_redis = GDATA.get_redis()
        name = self.get_thread_cache_name(self.watchdog_name)
        # TODO
        if temp_redis.exists(name):
            cache = temp_redis.get(name).decode("utf-8")
            try:
                proc = psutil.Process(int(cache))
                if proc.is_running():
                    return "RUNNING"
                elif proc.is_sleeping():
                    return "SLEEPING"
                else:
                    return "DEAD"
            except Exception as e:
                return "DEAD"
        return "NOT EXIST"

    def watch_dog(self) -> None:
        pid = os.getpid()
        GDATA.get_redis().set(self.watchdog_name, str(pid))
        while True:
            status = self.main_status()
            if stats is not "RUNNING":
                # TODO Restart main_control
                pass
            print(f"{datetime.datetime.now()}  watch dog, {status}")
            time.sleep(10)

    def main_control(self) -> None:
        pid = os.getpid()
        GDATA.get_redis().set(self.maincontrol_name, str(pid))
        v = GDATA.get_redis().get(self.maincontrol_name)
        print(v)
        GLOG.reset_logfile("for_test.log")
        count = 0
        while True:
            count += 1
            print(f"Main loop, {datetime.datetime.now()}")
            if count % 2 == 0:
                GLOG.INFO("Alive.")
            else:
                GLOG.ERROR("Alive.")
            time.sleep(4)


GTM = GinkgoThreadManager()
