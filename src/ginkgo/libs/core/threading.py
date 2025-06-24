from typing import List, Dict

import os
import sys
import json
import time
import datetime
import multiprocessing
import subprocess
import signal
import tempfile
import psutil
import threading
from rich.live import Live

from rich.console import Console

from multiprocessing import Process


from ginkgo.libs.core.config import GCONF
from ginkgo.libs.utils.common import retry
from ginkgo.libs.core.logger import GinkgoLogger
from ginkgo.notifier.notifier_beep import beep


console = Console()
control_logger = GinkgoLogger("main_control", file_names=["main_control.log"], console_log=True)
worker_logger = GinkgoLogger("dataworker", file_names=["data_worker.log"], console_log=True)


class GinkgoThreadManager:
    """
    Args:
        None
    Return:
        None
    """

    def __init__(self, *args, **kwargs):
        super(GinkgoThreadManager, self).__init__()
        self.thread_pool_name = "ginkgo_thread_pool"
        self.dataworker_pool_name = "ginkgo_dataworker"
        self.lock = threading.Lock()  # TODO
        self.watchdog_name = "watch_dog"  # Watchdog ensures the operation of the main control.
        self.maincontrol_name = "main_control"
        from ginkgo.data.drivers import create_redis_connection

        self.redis_conn = create_redis_connection()

    def get_redis_key_about_worker_status(self, pid: str, *args, **kwargs) -> str:
        return f"{str(pid)}_status"

    def process_task(self, type: str, code: str, fast: bool = None,max_update:int=0, *args, **kwargs):
        pid = os.getpid()
        if type == "stockinfo":
            worker_logger.INFO("Dealing with update stock_info command.")
            try:
                self.upsert_worker_status(pid=pid, task_name="update_stock_info", status="RUNNING")
                from ginkgo.data import fetch_and_update_stockinfo

                fetch_and_update_stockinfo()
                self.upsert_worker_status(pid=pid, task_name="update_stock_info", status="IDLE")
            except Exception as e:
                worker_logger.ERROR(f"Error occured when dealing with update stock_info command. {e}")
                self.upsert_worker_status(pid=pid, task_name="update_stock_info", status="ERROR")
            finally:
                pass
        elif type == "calender":
            worker_logger.INFO("Dealing with update calandar command.")
            try:
                self.upsert_worker_status(pid=pid, task_name="update_calender", status="RUNNING")
                from ginkgo.data import fetch_and_update_tradeday

                fetch_and_update_tradeday()
                self.upsert_worker_status(pid=pid, task_name="update_calender", status="IDLE")
            except Exception as e:
                data_logger.ERROR(e)
                self.upsert_worker_status(pid=pid, task_name="update_calender", status="ERROR")
            finally:
                pass
        elif type == "adjust":
            worker_logger.INFO(
                f"Dealing with the command updating adjustfactor about {code}. {'in fast mode' if value['fast'] else 'in complete mode'}."
            )
            try:
                self.upsert_worker_status(pid=pid, task_name=f"update_calender_{code}", status="RUNNING")
                from ginkgo.data import fetch_and_update_adjustfactor

                fetch_and_update_adjustfactor(code, value["fast"])
                self.upsert_worker_status(pid=pid, task_name=f"update_calender_{code}", status="IDLE")
            except Exception as e:
                data_logger.ERROR(e)
                self.upsert_worker_status(pid=pid, task_name=f"update_calender_{code}", status="ERROR")
            finally:
                pass
        elif type == "bar":
            worker_logger.INFO(
                f"Dealing with the command updating daybar about {code} {'in fast mode' if fast else 'in complete mode'}."
            )
            try:
                self.upsert_worker_status(
                    pid=pid,
                    task_name=f"update_daybar_{code}_{'fast_mode' if fast else 'normal_model'}",
                    status="RUNNING",
                )
                from ginkgo.data import fetch_and_update_cn_daybar

                fetch_and_update_cn_daybar(code=code, fast_mode=fast)
                self.upsert_worker_status(
                    pid=pid,
                    task_name=f"update_daybar_{code}_{'fast_mode' if fast else 'normal_model'}",
                    status="DONE",
                )
            except Exception as e:
                data_logger.ERROR(e)
                self.upsert_worker_status(
                    pid=pid,
                    task_name=f"update_daybar_{code}_{'fast_mode' if fast else 'normal_model'}",
                    status="ERROR",
                )
            finally:
                pass
        elif type == "tick":
            worker_logger.INFO(
                f"Dealing with the command updating tick about {code} {'in fast mode' if fast else 'in complete mode'}."
            )
            try:
                self.upsert_worker_status(
                    pid=pid,
                    task_name=f"update_tick_{code}_{'fast_mode' if fast else 'normal_model'}",
                    status="RUNNING",
                )
                from ginkgo.data import fetch_and_update_tick

                fetch_and_update_tick(code=code, fast_mode=fast, max_backtrack_day=max_update)
                self.upsert_worker_status(
                    pid=pid,
                    task_name=f"update_tick_{code}_{'fast_mode' if fast else 'normal_model'}",
                    status="IDEL",
                )
            except Exception as e:
                data_logger.ERROR(e)
                self.upsert_worker_status(
                    pid=pid,
                    task_name=f"update_tick_{code}_{'fast_mode' if fast else 'normal_model'}",
                    status="ERROR",
                )
        elif type == "other":
            worker_logger.WARN(f"Got the command no in list. {value}")
            self.upsert_worker_status(
                pid=pid,
                task_name="got a unrecognized task",
                status="IDLE",
            )
            print("看看传的啥")
            print(value)

    def run_data_worker(self, *args, **kwargs):
        from ginkgo.data.drivers import GinkgoConsumer

        pid = os.getpid()
        self.register_worker_pid(pid)
        print(f"Current Worker: {self.get_worker_count()}")
        self.upsert_worker_status(pid=pid, task_name="No Task", status="IDLE")
        con = GinkgoConsumer("ginkgo_data_update", "ginkgo_data")
        worker_logger.INFO(f"Start Listen Kafka Topic: ginkgo_data_update Group: ginkgo_data  PID:{pid}")
        try:
            for msg in con.consumer:
                beep(freq=900.7, repeat=2, delay=10, length=100)
                con.commit()
                value = msg.value
                type = value["type"]
                code = value["code"]
                fast = None
                if "fast" in value.keys():
                    fast = value["fast"]
                if "max_update" in value.keys():
                    max_update = value['max_update']
                worker_logger.INFO(f"Got siganl. {type} {code}")
                if type == "kill":
                    # Try a new way to jump out of loop
                    raise StopIteration  # Jump out of for loop.
                try:
                    self.process_task(type=type, code=code, fast=fast, max_update=max_update)
                except Exception as e2:
                    time.sleep(2)
                finally:
                    pass
        except StopIteration:
            worker_logger.INFO(f"Woker PID:{pid} terminated.")
            self.upsert_worker_status(pid=pid, task_name="", status="killed")
        except Exception as e:
            worker_logger.ERROR(e)
        finally:
            self.unregister_worker_pid(pid)

    def run_data_worker_daemon(self, *args, **kwargs):
        content = """
from ginkgo.libs.ginkgo_thread import GinkgoThreadManager

if __name__ == "__main__":
    gtm = GinkgoThreadManager()
    gtm.run_data_worker()
"""
        with tempfile.NamedTemporaryFile("w", delete=False, prefix="ginkgo_dataworker_", suffix=".py") as file:
            file.write(content)
            file_name = file.name
        try:
            log_dir = GCONF.LOGGING_PATH
            worker_logger.INFO(f"Write temp file.")
            pid = os.getpid()
            pid = str(pid)
            with open(file_name, "w") as file:
                file.write(content)
            worker_logger.INFO(f"Run daemon.")
            command = ["nohup", f"{GCONF.PYTHONPATH}", "-u", f"{file_name}"]
            with open("/dev/null", "w") as devnull:
                subprocess.Popen(command, stdout=devnull, stderr=devnull)

            console.print(f":sun_with_face: Data Worker is [steel_blue1]RUNNING[/steel_blue1] now.")
            time.sleep(0.5)
        except Exception as e:
            worker_logger.ERROR(f"DataWorker can not start. {e}")
        finally:
            if os.path.exists(file_name):
                os.remove(file_name)

    def start_multi_worker(self, count: int = 4, *args, **kwargs) -> None:
        for i in range(count):
            self.run_data_worker_daemon()

    def reset_all_workers(self, *args, **kwargs):
        while self.get_worker_count() > 0:
            for pid in self.get_worker_pids():
                print(f"get worker : {pid}")
                if isinstance(pid, bytes):
                    pid = pid.decode("utf-8")
                try:
                    proc = psutil.Process(int(pid))
                    if proc.is_running():
                        os.kill(int(pid), signal.SIGKILL)
                    self.unregister_worker_pid(pid)
                    console.print(f":leaf_fluttering_in_wind: Kill PID: {pid}")
                    time.sleep(0.4)
                except psutil.NoSuchProcess:
                    self.unregister_worker_pid(pid)
                except Exception as e:
                    pass
        console.print(":world_map:  Reset all data worker cache in REDIS.")

    def reset_pool(self, *args, **kwargs):
        from ginkgo.data import get_thread_count

        while get_thread_count() > 0:
            key = self._redis.lpop(self.thread_pool_name).decode("utf-8")
            key = key.split(self.get_thread_cache_name(""))[1]
            self.kill_thread(key)
        console.print("Reset all thread cache in REDIS.")

    def get_thread_cache_name(self, name: str, *args, **kwargs) -> str:
        return f"ginkgo_thread_{name}"

    def get_thread_pool_detail(self) -> Dict:
        # TODO
        pool = self.get_thread_pool_list()
        r = {}
        for key in pool:
            key = key.decode("utf-8")
            value = self._redis.get(key).decode("utf-8")
            key = key.split(self.get_thread_cache_name(""))[1]
            is_alive = self.get_thread_status(key)
            if is_alive:
                r[key] = {"pid": value, "alive": is_alive}
        return r

    def add_thread(self, name: str, target: threading.Thread) -> None:
        # TODO
        # TODO
        key = self.get_thread_cache_name(name)
        if key.encode() in self.get_thread_pool_list():
            console.print(f"{name} exists. Please change the name and try it again.")
            return
        pid = os.getpid()
        t = threading.Thread(target=target, name=name)
        self._redis.set(key, str(pid))
        self._redis.lpush(self.thread_pool_name, key)
        t.start()

    def get_thread_status(self, name: str) -> bool:
        # TODO
        from ginkgo.data import remove_from_redis

        key = self.get_thread_cache_name(name)
        value = self._redis.get(key).decode("utf-8")
        pid = int(value)
        try:
            proc = psutil.Process(int(value))
            return proc.is_running()
        except psutil.NoSuchProcess:
            remove_from_redis(key)
            console.print(f"No suck process, remove {key} from REDIS.")

    def kill_thread(self, name: str) -> None:
        # TODO
        key = self.get_thread_cache_name(name)
        if self._redis.exists(key):
            value = self._redis.get(key).decode("utf-8")
            pid = int(value)
            try:
                proc = psutil.Process(pid)
                if proc.is_running():
                    os.kill(pid, signal.SIGKILL)
                GDATA.remove_from_redis(key)
                self._redis.lrem(self.thread_pool_name, 0, key)
                console.print(f"Kill thread:{key} pid: {pid}")
            except Exception as e:
                GDATA.remove_from_redis(key)
                self._redis.lrem(self.thread_pool_name, 0, key)
                console.print(f"Remove {name} from REDIS.")

    def restart_thread(self, name: str, target) -> None:
        self.kill_thread(name)
        self.add_thread(name, target)

    def get_proc_status(self, pid: int) -> str:
        try:
            proc = psutil.Process(int(pid))
            return proc.status().upper()
        except Exception as e:
            return "NOT EXIST"
        finally:
            pass

    @property
    def main_status(self) -> str:
        pid = self.redis_conn.get(self.maincontrol_name)
        if pid is not None:
            status = self.get_proc_status(pid)
            if status == "NOT EXIST":
                self.redis_conn.delete(self.maincontrol_name)
            return self.get_proc_status(pid)
        return "NOT EXIST"

    @property
    def watch_dog_status(self) -> str:
        cache = self.redis_conn.get(self.watchdog_name)
        if cache:
            return self.get_proc_status(cache)
            if status == "NOT EXIST":
                self.redis_conn.delete(self.watchdog_name)
        return "NOT EXIST"

    def process_main_control_command(self, value: str) -> None:
        # TODO
        control_logger.INFO(f"Deal with main control. {value}")
        if value["type"] == "run_live":
            # Get status
            id = value["id"]
            pid = GDATA.get_pid_of_liveengine(id)
            control_logger.INFO(f"LiveEngine is running on PROCESS: {pid}")
            if pid is None:
                control_logger.INFO(f"{pid} not exist in redis, try run new live engine.")
                self.run_live_daemon(id)
                return
            try:
                proc = psutil.Process(pid)
                if proc.is_running():
                    control_logger.INFO(f"PID:{pid} is running, pass running new live engine.")
                    return
            except Exception as e:
                control_logger.INFO(f"{pid} in redis, but proc {pid} not exist, try run new live engine..")
                print(e)
            self.run_live(id)
        elif value["type"] == "stop_live":
            console.print("Stop live.")
            id = value["id"]
            GDATA.remove_liveengine(id)
        else:
            control_logger.WARN(f"Can not process {type}.")

    def run_live(self, id: str, *args, **kwargs):
        # TODO
        console.print(f"Try run live engine {id}")
        from ginkgo.backtest.engines.live_engine import LiveEngine

        e = LiveEngine(id)
        e.start()

    def run_live_daemon(self, id: str, *args, **kwargs):
        # TODO
        GDATA.clean_live_status()
        content = f"""
from ginkgo.backtest.engines.live_engine import LiveEngine


if __name__ == "__main__":
    e = LiveEngine("{id}")
    e.start()
"""
        with tempfile.NamedTemporaryFile("w", delete=False, prefix="ginkgo_live_", suffix=".py") as file:
            file.write(content)
            file_name = file.name
        try:
            work_dir = GCONF.WORKING_PATH
            log_dir = GCONF.LOGGING_PATH
            with open(file_name, "w") as file:
                file.write(content)
            command = ["nohup", f"{GCONF.PYTHONPATH}", "-u", f"{file_name}", ">/dev/null", "2>&1", "&"]
            subprocess.run(command)
            console.print(f":sun_with_face: Live {id} is [steel_blue1]RUNNING[/steel_blue1] now.")
            time.sleep(1)
        except Exception as e:
            print(e)
        finally:
            if os.path.exists(file_name):
                os.remove(file_name)

    def handle_sigint(self, signum, frame):
        # 自定义 Ctrl+C 行为
        print("\r[INFO] Gracefully stopping...")
        raise KeyboardInterrupt

    def consume_main_control_message(self, *args, **kwargs) -> None:
        signal.signal(signal.SIGINT, self.handle_sigint)
        from ginkgo.data.drivers import GinkgoConsumer

        topic_name = "ginkgo_main_control"
        console.print(f"[bold blue]Initializing consumer for topic: {topic_name}[/bold blue]")
        con = GinkgoConsumer(topic=topic_name, offset="latest")
        console.print(f"[bold green]Consumer initialized successfully![/bold green]")
        max_try = 10

        error_time = 0
        exit_count = 0

        while True:
            try:
                for msg in con.consumer:
                    value = msg.value
                    self.process_main_control_command(value)
                    error_time = 0  # 成功处理消息后重置错误计数
                    exit_count = 0  # 成功处理消息后重置退出计数
            except KeyboardInterrupt:
                exit_count += 1
                console.print(f"Try Harder, {exit_count}/3.")
                if exit_count >= 3:
                    console.print("[bold red]Main control service terminated by user.[/bold red]")
                    break
            except Exception as e:
                error_time += 1
                console.print(f"[bold red]Error in message consumption: {e}[/bold red]")
                if error_time >= max_try:
                    console.print(f"[bold red]Max retry attempts reached: {max_try}[/bold red]")
                    raise StopIteration
                time.sleep(1)  # 短暂休眠后重试

    def run_main_control(self, *args, **kwargs) -> None:

        self.kill_maincontrol()
        pid = os.getpid()
        self.redis_conn.set(self.maincontrol_name, str(pid))
        v = self.redis_conn.get(self.maincontrol_name)
        console.print(v)
        try:
            self.consume_main_control_message()
        except StopIteration:
            console.print("[bold red]Main control service stopped due to critical error.[/bold red]")
        except Exception as e:
            console.print(f"[bold red]Unexpected error: {e}[/bold red]")
        finally:
            # 确保 Redis 键被清理
            self.redis_conn.delete(self.maincontrol_name)
            console.print("[bold yellow]Main control service cleaned up.[/bold yellow]")

    def kill_maincontrol(self) -> None:
        pid = self.redis_conn.get(self.maincontrol_name)
        if pid is None:
            control_logger.INFO(f"Ginkgo MainControl not exist.")
            return
        control_logger.INFO(f"Ginkgo Maincontrol exist. PID:{int(pid)}")
        self.kill_proc(int(pid))
        control_logger.INFO(f"Remove Maincontrol pid from redis.")
        self.redis_conn.delete(self.maincontrol_name)

    def check_main_control_alive(self) -> None:
        exit_count = 0
        dead_count = 0
        check_interval = 5
        signal.signal(signal.SIGINT, self.handle_sigint)
        alive_count = 0
        while True:
            try:
                if self.main_status != "NOT EXIST":
                    console.print(f"Main Control is alive. Wait for next check. {datetime.datetime.now()}")
                    dead_count = 0
                    alive_count += 1
                    if alive_count >= 4:
                        exit_count = 0
                        alive_count = 0
                else:
                    dead_count += 1
                    if dead_count >= 2:
                        console.print("Will pull the main control up.")
                        self.run_main_control_daemon()
                time.sleep(check_interval)
            except KeyboardInterrupt:
                exit_count += 1
                console.print(f"Try Harder, {exit_count}/3.")
                if exit_count >= 3:
                    console.print("[bold red]Main control service terminated by user.[/bold red]")
                    break
            except Exception as e:
                error_time += 1
                console.print(f"[bold red]Error in function check main control alive: {e}[/bold red]")
                if error_time >= max_try:
                    console.print(f"[bold red]Max retry attempts reached: {max_try}[/bold red]")
                    raise StopIteration
                time.sleep(5)  # 短暂休眠后重试

    def run_watch_dog(self) -> None:
        self.kill_watch_dog()
        pid = os.getpid()
        console.print(f"Watch dog PID: {pid}")

        key = self.watchdog_name
        self.redis_conn.set(key, str(pid))
        try:
            self.check_main_control_alive()
        except KeyboardInterrupt:
            console.print("[bold red]Watch dog stopped due to critical error.[/bold red]")
        except Exception as e:
            console.print(f"[bold red]Watchdog encountered an error: {e}[/bold red]")
        finally:
            # 清理 Redis 键
            self.redis_conn.delete(self.watchdog_name)
            console.print("[bold yellow]Watchdog process cleaned up.[/bold yellow]")

    def kill_watch_dog(self) -> None:
        pid = self.redis_conn.get(self.watchdog_name)
        if pid is None:
            control_logger.INFO(f"Watch dog not exist.")
            return
        control_logger.INFO(f"Watch dog exist. PID:{int(pid)}")
        self.kill_proc(int(pid))
        control_logger.INFO(f"Remove watchdog pid from redis.")
        self.redis_conn.delete(self.watchdog_name)

    def run_watch_dog_daemon(self) -> None:
        content = """
from ginkgo.libs import GinkgoThreadManager

if __name__ == "__main__":
    gtm = GinkgoThreadManager()
    gtm.run_watch_dog()
    """
        with tempfile.NamedTemporaryFile("w", delete=False, prefix="ginkgo_watch_dog_", suffix=".py") as file:
            file.write(content)
            file_name = file.name
        try:
            work_dir = GCONF.WORKING_PATH
            log_dir = GCONF.LOGGING_PATH
            command = [
                "nohup",
                f"{work_dir}/venv/bin/python",
                "-u",
                f"{file_name}",
            ]
            # 打开一个空设备文件来完全忽略输出
            with open("/dev/null", "w") as devnull:
                subprocess.Popen(command, stdout=devnull, stderr=devnull)
            console.print(f":sun_with_face: Ginkgo WatchDog is [steel_blue1]RUNNING[/steel_blue1] now.")
            time.sleep(2)
        except Exception as e:
            print(e)
        finally:
            if os.path.exists(file_name):
                os.remove(file_name)

    def run_main_control_daemon(self) -> None:
        content = """
from ginkgo.libs import GinkgoThreadManager

if __name__ == "__main__":
    gtm = GinkgoThreadManager()
    gtm.run_main_control()
"""
        with tempfile.NamedTemporaryFile("w", delete=False, prefix="ginkgo_main_control_", suffix=".py") as file:
            file.write(content)
            file_name = file.name
        try:
            work_dir = GCONF.WORKING_PATH
            log_dir = GCONF.LOGGING_PATH
            with open(file_name, "w") as file:
                file.write(content)
            command = ["nohup", f"{work_dir}/venv/bin/python", "-u", f"{file_name}"]
            with open("/dev/null", "w") as devnull:
                subprocess.Popen(command, stdout=devnull, stderr=devnull)
            console.print(f":sun_with_face: Ginkgo Main Contrl is [steel_blue1]RUNNING[/steel_blue1] now.")
            time.sleep(2)
        except Exception as e:
            print(e)
        finally:
            if os.path.exists(file_name):
                os.remove(file_name)

    def kill_proc(self, pid: int) -> None:
        try:
            proc = psutil.Process(int(pid))
            if proc.is_running():
                control_logger.DEBUG(f"Kill PID: {pid}")
                os.kill(int(pid), signal.SIGKILL)
            console.print(f":leaf_fluttering_in_wind: Kill PID: {pid}")
            time.sleep(0.4)
        except Exception as e:
            console.print(f":leaf_fluttering_in_wind: Kill PID Failed: {e}")
        finally:
            pass

    def clean_thread_pool(self, *args, **kwargs) -> None:
        cursor = "0"
        while cursor != 0:
            cursor, elements = self.redis_conn.sscan(self.thread_pool_name, cursor=cursor, count=100)
            for item in elements:
                pid = item.decode("utf-8")
                try:
                    pid = int(pid)
                    proc = psutil.Process(pid)
                    if not proc.is_running():
                        self.unregister_worker_pid(pid)
                except psutil.NoSuchProcess as e:
                    self.unregister_worker_pid(pid)
                except Exception as e:
                    pass
                finally:
                    pass

    def clean_worker_pool(self, *args, **kwargs) -> None:
        cursor = "0"
        while cursor != 0:
            cursor, elements = self.redis_conn.sscan(self.dataworker_pool_name, cursor=cursor, count=100)
            for item in elements:
                pid = item.decode("utf-8")
                try:
                    pid = int(pid)
                    proc = psutil.Process(pid)
                    if not proc.is_running():
                        self.unregister_worker_pid(pid)
                except psutil.NoSuchProcess as e:
                    self.unregister_worker_pid(pid)
                except Exception as e:
                    pass
                finally:
                    pass

    def get_thread_pids(self) -> List:
        res = []
        cursor = "0"
        while cursor != 0:
            cursor, elements = self.redis_conn.sscan(self.thread_pool_name, cursor=cursor, count=100)
            for item in elements:
                res.append(item.decode("utf-8"))
        return res

    def get_worker_pids(self) -> List:
        res = []
        cursor = "0"
        while cursor != 0:
            cursor, elements = self.redis_conn.sscan(self.dataworker_pool_name, cursor=cursor, count=100)
            for item in elements:
                res.append(item.decode("utf-8"))
        return res

    def register_thread_pid(self, pid: str, *args, **kwargs) -> None:
        self.redis_conn.sadd(self.thread_pool_name, str(pid))

    def unregister_thread_pid(self, pid: str, *args, **kwargs) -> None:
        self.redis_conn.srem(self.thread_pool_name, 0, str(pid))

    def register_worker_pid(self, pid: str, *args, **kwargs) -> None:
        # register work should register to thread pool at the same time
        self.redis_conn.sadd(self.thread_pool_name, str(pid))
        self.redis_conn.sadd(self.dataworker_pool_name, str(pid))

    def unregister_worker_pid(self, pid: str, *args, **kwargs) -> None:
        # unregister work should register to thread pool at the same time
        self.redis_conn.srem(self.thread_pool_name, 0, str(pid))
        self.redis_conn.srem(self.dataworker_pool_name, 0, str(pid))

    def get_thread_count(self, *args, **kwargs) -> int:
        return self.redis_conn.scard(self.thread_pool_name)

    def get_worker_count(self, *args, **kwargs) -> int:
        return self.redis_conn.scard(self.dataworker_pool_name)

    def get_worker_status(self, pid: str, *args, **kwargs) -> Dict:
        pid = str(pid)
        key = self.get_redis_key_about_worker_status(pid)
        type = self.redis_conn.type(key)
        res = self.redis_conn.get(key)
        return json.loads(res) if res else None

    def get_workers_status(self) -> Dict:
        res = {}
        for pid in self.get_worker_pids():
            data = self.get_worker_status(pid)
            if data is None:
                continue
            res[pid] = data
        return res

    def upsert_worker_status(self, pid: str, task_name: str, status: str, *args, **kwargs):
        pid = str(pid)
        worker_pids = self.get_worker_pids()
        if pid not in worker_pids:
            register_worker_pid(pid)
            control_logger.WARN(f"Process: {pid} should have registered. Please Check the code.")
        key = self.get_redis_key_about_worker_status(pid)
        status_data = {
            "task_name": task_name,
            "status": status,
            "time_stamp": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
        }
        status_data = json.dumps(status_data)
        # Redis set with xx and nx is more efficient than do exists then set or update
        result = self.redis_conn.set(key, status_data, xx=True)
        # if update failed, do insert.
        if result is None:
            self.redis_conn.set(key, status_data, nx=True)

    def clean_worker_status(self, *args, **kwargs) -> None:
        for pid in self.get_worker_pids():
            try:
                pid = str(pid)
                status = self.get_worker_status(pid)
                key = self.get_redis_key_about_worker_status(pid)
                if status is None:
                    self.redis_conn.delete(key)
                if status["status"] == "killed":
                    self.redis_conn.delete(key)
            except psutil.NoSuchProcess as e:
                self.redis_conn.delete(key)
            except Exception as e:
                pass
            finally:
                pass
