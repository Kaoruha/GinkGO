import os
import sys
import time
import datetime
import signal
import tempfile
import psutil
import threading
from rich.live import Live
from rich.console import Console
from multiprocessing import Process
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.data.drivers import GinkgoConsumer
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.notifier.notifier_beep import beep
from ginkgo.libs.ginkgo_logger import GinkgoLogger


console = Console()
control_logger = GinkgoLogger("main_control", "main_control.log")
worker_logger = GinkgoLogger("dataworker", "data_worker.log")


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
        con = GinkgoConsumer("ginkgo_data_update", "ginkgo_data")
        while True:
            try:
                worker_logger.INFO(
                    f"Start Listen Kafka Topic: ginkgo_data_update Group: ginkgo_data  PID:{pid}"
                )
                for msg in con.consumer:
                    beep(freq=900.7, repeat=2, delay=10, length=100)
                    con.commit()
                    error_time = 0
                    value = msg.value
                    type = value["type"]
                    code = value["code"]
                    worker_logger.INFO(f"Got siganl. {type} {code}")

                    if type == "kill":
                        worker_logger.INFO("Dealing with kill command.")
                        GDATA.get_redis().lrem(self.dataworker_pool_name, 0, str(pid))
                        sys.exit(0)
                    elif type == "stockinfo":
                        worker_logger.INFO("Dealing with update stock_info command.")
                        try:
                            GDATA.update_stock_info()
                        except Exception as e:
                            pass
                    elif type == "calender":
                        worker_logger.INFO("Dealing with update calandar command.")
                        try:
                            GDATA.update_cn_trade_calendar()
                        except Exception as e:
                            pass
                    elif type == "adjust":
                        worker_logger.INFO(
                            f"Dealing with the command updating adjustfactor about {code}. {'in fast mode' if value['fast'] else 'in complete mode'}."
                        )
                        try:
                            GDATA.update_cn_adjustfactor(code, value["fast"])
                        except Exception as e:
                            pass
                    elif type == "bar":
                        worker_logger.INFO(
                            f"Dealing with the command updating daybar about {code} {'in fast mode' if value['fast'] else 'in complete mode'}."
                        )
                        try:
                            GDATA.update_cn_daybar(code, value["fast"])
                        except Exception as e:
                            pass
                    elif type == "tick":
                        worker_logger.INFO(
                            f"Dealing with the command updating tick about {code} {'in fast mode' if value['fast'] else 'in complete mode'}."
                        )
                        try:
                            GDATA.update_tick(code, value["fast"])
                        except Exception as e:
                            pass
                    elif type == "other":
                        worker_logger.WARN(f"Got the command no in list. {value}")
                        print(value)
            except Exception as e2:
                con.commit()
                error_time += 1
                if error_time > self.max_try:
                    worker_logger.INFO(f"Error {error_time} times. Restart the worker.")
                    con = GinkgoConsumer("ginkgo_data_update", "ginkgo_data")
                    break
                else:
                    worker_logger.INFO(
                        f"Error {error_time} / {self.max_try} times. {e2}"
                    )
                    time.sleep(min(5 * (2**error_time), 300))
        GDATA.get_redis().lrem(self.dataworker_pool_name, 0, str(pid))

    def run_dataworker_daemon(self):
        content = """
from ginkgo.libs.ginkgo_thread import GinkgoThreadManager

if __name__ == "__main__":
    gtm = GinkgoThreadManager()
    gtm.run_dataworker()
"""
        with tempfile.NamedTemporaryFile(
            "w", delete=False, prefix="ginkgo_dataworker_", suffix=".py"
        ) as file:
            file.write(content)
            file_name = file.name
        try:
            work_dir = GCONF.WORKING_PATH
            log_dir = GCONF.LOGGING_PATH
            worker_logger.INFO(f"Write temp file.")
            with open(file_name, "w") as file:
                file.write(content)
            cmd = f"nohup {work_dir}/venv/bin/python -u {file_name} >>{GCONF.LOGGING_PATH}/data_worker_daemon.log 2>&1 &"
            # TODO Dynamic log file.
            worker_logger.INFO(f"Run daemon.")
            os.system(cmd)
            count = datetime.timedelta(seconds=0)
            t0 = datetime.datetime.now()
            console.print(
                f":sun_with_face: Data Worker is [steel_blue1]RUNNING[/steel_blue1] now."
            )
            time.sleep(1)
        except Exception as e:
            worker_logger.ERROR(f"DataWorker can not start. {e}")
        finally:
            if os.path.exists(file_name):
                os.remove(file_name)

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

    @property
    def main_status(self) -> str:
        temp_redis = GDATA.get_redis()
        if temp_redis.exists(self.maincontrol_name):
            cache = temp_redis.get(self.maincontrol_name).decode("utf-8")
            return self.get_proc_status(cache)
        return "NOT EXIST"

    @property
    def watch_dog_status(self) -> str:
        temp_redis = GDATA.get_redis()
        if temp_redis.exists(self.watchdog_name):
            cache = temp_redis.get(self.watchdog_name).decode("utf-8")
            return self.get_proc_status(cache)
        return "NOT EXIST"

    def watch_dog(self) -> None:
        self.kill_watch_dog()
        pid = os.getpid()
        GDATA.get_redis().set(self.watchdog_name, str(pid))
        dead_count = 0
        while True:
            if self.main_status == "RUNNING":
                dead_count = 0
            else:
                dead_count += 1
                if dead_count >= 2:
                    print("Will pull the main control up.")
                    self.run_main_control_daemon()
            print(f"{datetime.datetime.now()}  watch dog, {self.watch_dog_status}")
            time.sleep(2)

    def process_main_control_command(self, value: str) -> None:
        control_logger.INFO(f"Deal with main control. {value}")
        if value["type"] == "run_live":
            # Get status
            id = value["id"]
            pid = GDATA.get_pid_of_liveengine(id)
            control_logger.INFO(f"LiveEngine is running on PROCESS: {pid}")
            if pid is None:
                control_logger.INFO(
                    f"{pid} not exist in redis, try run new live engine."
                )
                self.run_live_daemon(id)
                return
            try:
                proc = psutil.Process(pid)
                if proc.is_running():
                    control_logger.INFO(
                        f"PID:{pid} is running, pass running new live engine."
                    )
                    return
            except Exception as e:
                control_logger.INFO(
                    f"{pid} in redis, but proc {pid} not exist, try run new live engine.."
                )
                print(e)
            self.run_live(id)
        elif value["type"] == "stop_live":
            print("Stop live.")
            id = value["id"]
            GDATA.remove_liveengine(id)
        else:
            control_logger.WARN(f"Can not process {type}.")

    def run_live(self, id: str):
        print(f"Try run live engine {id}")
        from ginkgo.backtest.engines.live_engine import LiveEngine

        e = LiveEngine(id)
        e.start()

    def run_live_daemon(self, id: str):
        GDATA.clean_live_status()
        content = f"""
from ginkgo.backtest.engines.live_engine import LiveEngine


if __name__ == "__main__":
    e = LiveEngine("{id}")
    e.start()
"""
        with tempfile.NamedTemporaryFile(
            "w", delete=False, prefix="ginkgo_live_", suffix=".py"
        ) as file:
            file.write(content)
            file_name = file.name
        try:
            work_dir = GCONF.WORKING_PATH
            log_dir = GCONF.LOGGING_PATH
            with open(file_name, "w") as file:
                file.write(content)
            cmd = f"nohup {work_dir}/venv/bin/python -u {file_name} > /dev/null 2>&1 &"
            # print(cmd)
            os.system(cmd)
            # print(f"Current Worker: {self.dataworker_count}")
            count = datetime.timedelta(seconds=0)
            t0 = datetime.datetime.now()
            console.print(
                f":sun_with_face: Live {id} is [steel_blue1]RUNNING[/steel_blue1] now."
            )
            time.sleep(2)
        except Exception as e:
            print(e)
        finally:
            if os.path.exists(file_name):
                os.remove(file_name)

    def main_control(self) -> None:
        GDATA.clean_liveengine()
        GDATA.clean_live_status()
        self.kill_maincontrol()
        pid = os.getpid()
        GDATA.get_redis().set(self.maincontrol_name, str(pid))
        v = GDATA.get_redis().get(self.maincontrol_name)
        print(v)
        GLOG = GinkgoLogger("main_control", "main_control.log")
        while True:
            try:
                topic_name = f"ginkgo_main_control"
                con = GinkgoConsumer(
                    topic=topic_name,
                    # group_id=f"ginkgo_live_engine_{self.engine_id}",
                    offset="latest",
                )
                GLOG.INFO(f"Start Listen {topic_name}  PID:{pid}")
                for msg in con.consumer:
                    error_time = 0
                    value = msg.value
                    self.process_main_control_command(value)
            except Exception as e2:
                print(e2)
                error_time += 1
                if error_time > max_try:
                    sys.exit(0)
                else:
                    pass

    def kill_watch_dog(self) -> None:
        pid = GDATA.get_redis().get(self.watchdog_name)
        self.kill_proc(int(pid))

    def kill_maincontrol(self) -> None:
        pid = GDATA.get_redis().get(self.maincontrol_name)
        self.kill_proc(int(pid))

    def run_watch_dog_daemon(self) -> None:
        content = """
from ginkgo.libs.ginkgo_thread import GinkgoThreadManager

if __name__ == "__main__":
    gtm = GinkgoThreadManager()
    gtm.watch_dog()
"""

        with tempfile.NamedTemporaryFile(
            "w", delete=False, prefix="ginkgo_watch_dog_", suffix=".py"
        ) as file:
            file.write(content)
            file_name = file.name

        try:
            work_dir = GCONF.WORKING_PATH
            log_dir = GCONF.LOGGING_PATH
            cmd = f"nohup {work_dir}/venv/bin/python -u {file_name} > /dev/null 2>&1 &"
            os.system(cmd)
            # print(f"Current Worker: {self.dataworker_count}")
            count = datetime.timedelta(seconds=0)
            t0 = datetime.datetime.now()
            console.print(
                f":sun_with_face: Ginkgo WatchDog(Main) is [steel_blue1]RUNNING[/steel_blue1] now."
            )
            time.sleep(2)
        except Exception as e:
            print(e)
        finally:
            if os.path.exists(file_name):
                os.remove(file_name)

    def run_main_control_daemon(self) -> None:
        content = """
from ginkgo.libs.ginkgo_thread import GinkgoThreadManager

if __name__ == "__main__":
    gtm = GinkgoThreadManager()
    gtm.main_control()
"""
        with tempfile.NamedTemporaryFile(
            "w", delete=False, prefix="ginkgo_main_control_", suffix=".py"
        ) as file:
            file.write(content)
            file_name = file.name

        try:
            work_dir = GCONF.WORKING_PATH
            log_dir = GCONF.LOGGING_PATH
            with open(file_name, "w") as file:
                file.write(content)
            cmd = f"nohup {work_dir}/venv/bin/python -u {file_name} > /dev/null 2>&1 &"
            # print(cmd)
            os.system(cmd)
            # print(f"Current Worker: {self.dataworker_count}")
            count = datetime.timedelta(seconds=0)
            t0 = datetime.datetime.now()
            console.print(
                f":sun_with_face: Ginkgo Main COntrl is [steel_blue1]RUNNING[/steel_blue1] now."
            )
            time.sleep(2)
        except Exception as e:
            print(e)
        finally:
            if os.path.exists(file_name):
                os.remove(file_name)

    def kill_proc(self, pid: int):
        try:
            proc = psutil.Process(int(pid))
            if proc.is_running():
                os.kill(int(pid), signal.SIGKILL)
            console.print(f":leaf_fluttering_in_wind: Kill PID: {pid}")
            time.sleep(0.4)
        except Exception as e:
            print(e)
            pass


GTM = GinkgoThreadManager()
