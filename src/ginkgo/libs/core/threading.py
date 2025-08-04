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


from .config import GCONF
from ..utils.common import retry
from .logger import GinkgoLogger
from ...notifier.notifier_beep import beep


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
        
        # 使用RedisService统一管理Redis操作
        self._redis_service = None
        # KafkaService延迟初始化，避免循环导入
        self._kafka_service = None
    
    @property
    def redis_service(self):
        """延迟加载RedisService实例"""
        if self._redis_service is None:
            from ginkgo.data.containers import container
            self._redis_service = container.redis_service()
        return self._redis_service
    
    @property
    def kafka_service(self):
        """延迟加载KafkaService实例"""
        if self._kafka_service is None:
            from ginkgo.data.containers import container
            self._kafka_service = container.kafka_service()
        return self._kafka_service

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
                self.upsert_worker_status(pid=pid, task_name="update_stock_info", status="COMPLETE")
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
                self.upsert_worker_status(pid=pid, task_name="update_calender", status="COMPLETE")
            except Exception as e:
                data_logger.ERROR(e)
                self.upsert_worker_status(pid=pid, task_name="update_calender", status="ERROR")
            finally:
                pass
        elif type == "adjust":
            worker_logger.INFO(
                f"Dealing with the command updating adjustfactor about {code}. {'in fast mode' if fast else 'in complete mode'}."
            )
            try:
                self.upsert_worker_status(pid=pid, task_name=f"update_adjustfactor_{code}", status="RUNNING")
                from ginkgo.data import fetch_and_update_adjustfactor

                fetch_and_update_adjustfactor(code, fast)
                self.upsert_worker_status(pid=pid, task_name=f"update_adjustfactor_{code}", status="COMPLETE")
            except Exception as e:
                worker_logger.ERROR(e)
                self.upsert_worker_status(pid=pid, task_name=f"update_adjustfactor_{code}", status="ERROR")
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
                    status="COMPLETE",
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
                    status="COMPLETE",
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
        pid = os.getpid()
        self.register_worker_pid(pid)
        print(f"Current Worker: {self.get_worker_count()}")
        self.upsert_worker_status(pid=pid, task_name="No Task", status="IDLE")
        
        worker_logger.INFO(f":arrows_counterclockwise: Worker PID:{pid} initializing...")
        worker_logger.INFO(f":satellite_antenna: Start Listen Kafka Topic: ginkgo_data_update Group: ginkgo_data  PID:{pid}")
        
        # 测试Kafka连接状态
        try:
            kafka_health = self.kafka_service.health_check()
            worker_logger.INFO(f":green_heart: Kafka health check: {kafka_health.get('status', 'unknown')}")
        except Exception as e:
            worker_logger.WARN(f":warning: Kafka health check failed: {e}")
        
        # 定义消息处理回调函数
        def data_worker_message_handler(message_data):
            try:
                # 增加详细的调试日志
                worker_logger.INFO(f":dart: [PID:{pid}] Received Kafka message")
                worker_logger.INFO(f":page_facing_up: Raw message data: {message_data}")
                
                beep(freq=900.7, repeat=2, delay=10, length=100)
                
                # 从KafkaService消息格式中提取原始数据（逻辑保持不变）
                if "value" in message_data:
                    value = message_data["value"]
                    worker_logger.INFO(f":package: Extracted value from message: {value}")
                else:
                    # 如果是直接的消息内容
                    value = message_data.get("content", message_data)
                    worker_logger.INFO(f":package: Using direct content: {value}")
                
                type = value["type"]
                code = value["code"]
                fast = None
                max_update = 0
                if "fast" in value.keys():
                    fast = value["fast"]
                if "max_update" in value.keys():
                    max_update = value['max_update']
                    
                worker_logger.INFO(f":clipboard: Parsed task: type={type}, code={code}, fast={fast}, max_update={max_update}")
                
                if type == "kill":
                    # 通过返回False来停止消费
                    worker_logger.INFO(f"💀 Worker PID:{pid} received kill signal.")
                    self.upsert_worker_status(pid=pid, task_name="", status="killed")
                    return False
                
                try:
                    worker_logger.INFO(f":rocket: Starting task execution: {type}")
                    self.process_task(type=type, code=code, fast=fast, max_update=max_update)
                    worker_logger.INFO(f":white_check_mark: Task execution completed successfully")
                    return True  # 消息处理成功
                except Exception as e2:
                    worker_logger.ERROR(f":x: Error processing task {type} {code}: {e2}")
                    import traceback
                    worker_logger.ERROR(f":magnifying_glass_tilted_left: Traceback: {traceback.format_exc()}")
                    time.sleep(2)
                    return False  # 消息处理失败
                    
            except Exception as e:
                worker_logger.ERROR(f"💥 Error in message handler: {e}")
                import traceback
                worker_logger.ERROR(f":magnifying_glass_tilted_left: Handler traceback: {traceback.format_exc()}")
                return False
        
        try:
            # 使用KafkaService订阅消息
            worker_logger.INFO(f"📨 Attempting to subscribe to ginkgo_data_update...")
            success = self.kafka_service.subscribe_topic(
                topic="ginkgo_data_update",
                handler=data_worker_message_handler,
                group_id="ginkgo_data",
                auto_start=True
            )
            
            if not success:
                worker_logger.ERROR(":x: Failed to subscribe to ginkgo_data_update topic")
                return
            else:
                worker_logger.INFO(":white_check_mark: Successfully subscribed to Kafka topic")
            
            worker_logger.INFO(f":hourglass_not_done: Worker PID:{pid} is now waiting for messages...")
            
            # 保持进程运行，直到接收到kill信号
            while True:
                worker_status = self.get_worker_status(str(pid))
                if worker_status and worker_status.get("status") == "killed":
                    worker_logger.INFO(f"🛑 Worker PID:{pid} received kill status, shutting down...")
                    break
                time.sleep(1)
                
        except KeyboardInterrupt:
            worker_logger.INFO(f"Worker PID:{pid} interrupted by user.")
            self.upsert_worker_status(pid=pid, task_name="", status="killed")
        except Exception as e:
            worker_logger.ERROR(f"Worker error: {e}")
            self.upsert_worker_status(pid=pid, task_name="", status="ERROR")
        finally:
            # 取消订阅和清理
            try:
                self.kafka_service.unsubscribe_topic("ginkgo_data_update")
            except:
                pass
            self.unregister_worker_pid(pid)
            worker_logger.INFO(f"Worker PID:{pid} cleanup completed.")

    def run_data_worker_daemon(self, *args, **kwargs):
        content = """
from ginkgo.libs.core.threading import GinkgoThreadManager

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
            key = self.redis_service.pop_from_thread_list(self.thread_pool_name)
            if key:
                key = key.split(self.get_thread_cache_name(""))[1]
                self.kill_thread(key)
            else:
                break
        console.print("Reset all thread cache in REDIS.")

    def get_thread_cache_name(self, name: str, *args, **kwargs) -> str:
        return f"ginkgo_thread_{name}"

    def get_thread_pool_detail(self) -> Dict:
        # TODO
        thread_pids = self.get_thread_pids()
        r = {}
        for thread_pid in thread_pids:
            # 假设这是线程缓存key格式
            if thread_pid.startswith(self.get_thread_cache_name("")):
                thread_name = thread_pid.split(self.get_thread_cache_name(""))[1]
                value = self.redis_service.get_thread_from_cache(thread_pid)
                if value:
                    is_alive = self.get_thread_status(thread_name)
                    if is_alive:
                        r[thread_name] = {"pid": value, "alive": is_alive}
        return r

    def add_thread(self, name: str, target: threading.Thread) -> None:
        # TODO
        # TODO
        key = self.get_thread_cache_name(name)
        # 检查线程是否已存在
        if self.redis_service.exists(key):
            console.print(f"{name} exists. Please change the name and try it again.")
            return
        pid = os.getpid()
        t = threading.Thread(target=target, name=name)
        self.redis_service.set_thread_cache(key, str(pid))
        self.redis_service.add_to_thread_list(self.thread_pool_name, key)
        t.start()

    def get_thread_status(self, name: str) -> bool:
        # TODO
        key = self.get_thread_cache_name(name)
        value = self.redis_service.get_thread_from_cache(key)
        if not value:
            return False
        try:
            pid = int(value)
            proc = psutil.Process(pid)
            return proc.is_running()
        except psutil.NoSuchProcess:
            self.redis_service.delete_cache(key)
            console.print(f"No such process, remove {key} from REDIS.")
            return False
        except (ValueError, TypeError):
            return False

    def kill_thread(self, name: str) -> None:
        # TODO
        key = self.get_thread_cache_name(name)
        if self.redis_service.exists(key):
            value = self.redis_service.get_thread_from_cache(key)
            if value:
                try:
                    pid = int(value)
                    proc = psutil.Process(pid)
                    if proc.is_running():
                        os.kill(pid, signal.SIGKILL)
                    self.redis_service.delete_cache(key)
                    self.redis_service.remove_from_thread_list(self.thread_pool_name, key)
                    console.print(f"Kill thread:{key} pid: {pid}")
                except Exception as e:
                    self.redis_service.delete_cache(key)
                    self.redis_service.remove_from_thread_list(self.thread_pool_name, key)
                    console.print(f"Remove {name} from REDIS.")

    def restart_thread(self, name: str, target) -> None:
        self.kill_thread(name)
        self.add_thread(name, target)

    def get_proc_status(self, pid) -> str:
        try:
            # Handle cases where pid might be None, "None", or non-numeric
            if pid is None or pid == "None" or not str(pid).isdigit():
                return "NOT EXIST"
            proc = psutil.Process(int(pid))
            return proc.status().upper()
        except Exception as e:
            return "NOT EXIST"
        finally:
            pass

    @property
    def main_status(self) -> str:
        pid = self.redis_service.get_main_process_pid()
        if pid is not None:
            status = self.get_proc_status(pid)
            if status == "NOT EXIST":
                self.redis_service.unregister_main_process()
            return self.get_proc_status(pid)
        return "NOT EXIST"

    @property
    def watch_dog_status(self) -> str:
        pid = self.redis_service.get_watchdog_pid()
        if pid is not None:
            status = self.get_proc_status(pid)
            if status == "NOT EXIST":
                self.redis_service.unregister_watchdog()
            return status
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
        from ginkgo.backtest.execution.engines.live_engine import LiveEngine

        e = LiveEngine(id)
        e.start()

    def run_live_daemon(self, id: str, *args, **kwargs):
        # TODO
        GDATA.clean_live_status()
        content = f"""
from ginkgo.backtest.execution.engines.live_engine import LiveEngine


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

        topic_name = "ginkgo_main_control"
        console.print(f"[bold blue]Initializing consumer for topic: {topic_name}[/bold blue]")
        
        max_try = 10
        error_time = 0
        exit_count = 0
        keep_running = True
        
        # 定义主控制消息处理回调函数
        def main_control_message_handler(message_data):
            nonlocal error_time, exit_count, keep_running
            try:
                # 从KafkaService消息格式中提取原始数据
                if "value" in message_data:
                    value = message_data["value"]
                else:
                    # 如果是直接的消息内容
                    value = message_data.get("content", message_data)
                
                self.process_main_control_command(value)
                error_time = 0  # 成功处理消息后重置错误计数
                exit_count = 0  # 成功处理消息后重置退出计数
                return True
                
            except Exception as e:
                control_logger.ERROR(f"Error processing main control command: {e}")
                return False
        
        try:
            # 使用KafkaService订阅主控制消息
            success = self.kafka_service.subscribe_topic(
                topic=topic_name,
                handler=main_control_message_handler,
                group_id="main_control_group",
                auto_start=True
            )
            
            if not success:
                console.print("[bold red]Failed to subscribe to main control topic[/bold red]")
                return
                
            console.print(f"[bold green]Consumer initialized successfully![/bold green]")
            
            # 保持服务运行
            while keep_running:
                try:
                    time.sleep(1)  # 主循环休眠
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
                    
        finally:
            # 清理订阅
            try:
                self.kafka_service.unsubscribe_topic(topic_name)
                console.print("[bold yellow]Main control topic unsubscribed.[/bold yellow]")
            except:
                pass

    def run_main_control(self, *args, **kwargs) -> None:

        self.kill_maincontrol()
        pid = os.getpid()
        self.redis_service.register_main_process(pid)
        console.print(f"Main control registered with PID: {pid}")
        try:
            self.consume_main_control_message()
        except StopIteration:
            console.print("[bold red]Main control service stopped due to critical error.[/bold red]")
        except Exception as e:
            console.print(f"[bold red]Unexpected error: {e}[/bold red]")
        finally:
            # 确保 Redis 键被清理
            self.redis_service.unregister_main_process()
            console.print("[bold yellow]Main control service cleaned up.[/bold yellow]")

    def kill_maincontrol(self) -> None:
        pid = self.redis_service.get_main_process_pid()
        if pid is None:
            control_logger.INFO(f"Ginkgo MainControl not exist.")
            return
        control_logger.INFO(f"Ginkgo Maincontrol exist. PID:{int(pid)}")
        self.kill_proc(int(pid))
        control_logger.INFO(f"Remove Maincontrol pid from redis.")
        self.redis_service.unregister_main_process()

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

        self.redis_service.register_watchdog(pid)
        try:
            self.check_main_control_alive()
        except KeyboardInterrupt:
            console.print("[bold red]Watch dog stopped due to critical error.[/bold red]")
        except Exception as e:
            console.print(f"[bold red]Watchdog encountered an error: {e}[/bold red]")
        finally:
            # 清理 Redis 键
            self.redis_service.unregister_watchdog()
            console.print("[bold yellow]Watchdog process cleaned up.[/bold yellow]")

    def kill_watch_dog(self) -> None:
        pid = self.redis_service.get_watchdog_pid()
        if pid is None:
            control_logger.INFO(f"Watch dog not exist.")
            return
        control_logger.INFO(f"Watch dog exist. PID:{int(pid)}")
        self.kill_proc(int(pid))
        control_logger.INFO(f"Remove watchdog pid from redis.")
        self.redis_service.unregister_watchdog()

    def run_watch_dog_daemon(self) -> None:
        content = """
from ginkgo.libs.core.threading import GinkgoThreadManager

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
from ginkgo.libs.core.threading import GinkgoThreadManager

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
        cursor = 0
        while cursor != 0:
            cursor, elements = self.redis_service.scan_thread_pool(self.thread_pool_name, cursor=cursor, count=100)
            for pid_str in elements:
                try:
                    # Check if pid is valid before converting to int
                    if not pid_str or pid_str == "None" or not pid_str.isdigit():
                        self.redis_service.remove_from_thread_pool_set(self.thread_pool_name, pid_str)
                        continue
                    pid = int(pid_str)
                    proc = psutil.Process(pid)
                    if not proc.is_running():
                        self.redis_service.remove_from_thread_pool_set(self.thread_pool_name, pid_str)
                except psutil.NoSuchProcess as e:
                    self.redis_service.remove_from_thread_pool_set(self.thread_pool_name, pid_str)
                except (ValueError, TypeError) as e:
                    # Handle cases where pid cannot be converted to int
                    self.redis_service.remove_from_thread_pool_set(self.thread_pool_name, pid_str)
                except Exception as e:
                    pass
                finally:
                    pass

    def clean_worker_pool(self, *args, **kwargs) -> None:
        cursor = 0
        while cursor != 0:
            cursor, elements = self.redis_service.scan_worker_pool(self.dataworker_pool_name, cursor=cursor, count=100)
            for pid_str in elements:
                try:
                    # Check if pid is valid before converting to int
                    if not pid_str or pid_str == "None" or not pid_str.isdigit():
                        self.unregister_worker_pid(pid_str)
                        continue
                    pid = int(pid_str)
                    proc = psutil.Process(pid)
                    if not proc.is_running():
                        self.unregister_worker_pid(pid_str)
                except psutil.NoSuchProcess as e:
                    self.unregister_worker_pid(pid_str)
                except (ValueError, TypeError) as e:
                    # Handle cases where pid cannot be converted to int
                    self.unregister_worker_pid(pid_str)
                except Exception as e:
                    pass
                finally:
                    pass

    def get_thread_pids(self) -> List:
        res = []
        cursor = 0
        while cursor != 0:
            cursor, elements = self.redis_service.scan_thread_pool(self.thread_pool_name, cursor=cursor, count=100)
            for item in elements:
                res.append(item)
        return res

    def get_worker_pids(self) -> List:
        worker_pids = self.redis_service.get_all_workers("data_worker")
        return [str(pid) for pid in worker_pids]

    def register_thread_pid(self, pid: str, *args, **kwargs) -> None:
        self.redis_service.add_to_thread_pool_set(self.thread_pool_name, str(pid))

    def unregister_thread_pid(self, pid: str, *args, **kwargs) -> None:
        self.redis_service.remove_from_thread_pool_set(self.thread_pool_name, str(pid))

    def register_worker_pid(self, pid: str, *args, **kwargs) -> None:
        # register work should register to thread pool at the same time
        self.redis_service.add_worker_to_pool(int(pid), "data_worker")

    def unregister_worker_pid(self, pid: str, *args, **kwargs) -> None:
        # unregister work should register to thread pool at the same time
        self.redis_service.remove_worker_from_pool(int(pid), "data_worker")

    def get_thread_count(self, *args, **kwargs) -> int:
        return self.redis_service.get_worker_pool_size("general")

    def get_worker_count(self, *args, **kwargs) -> int:
        return self.redis_service.get_worker_pool_size("data_worker")

    def get_worker_status(self, pid: str, *args, **kwargs) -> Dict:
        pid = str(pid)
        task_key = f"ginkgo_worker_status_{pid}"
        status_data = self.redis_service.get_task_status_by_key(task_key)
        return status_data

    def get_workers_status(self) -> Dict:
        res = {}
        for pid in self.get_worker_pids():
            data = self.get_worker_status(pid)
            if data is None:
                continue
            
            # Calculate task running time from timestamp
            try:
                if "time_stamp" in data:
                    task_start_time = datetime.datetime.strptime(data["time_stamp"], "%Y%m%d%H%M%S")
                    current_time = datetime.datetime.now()
                    running_duration = current_time - task_start_time
                    
                    # Format running time as human readable
                    total_seconds = int(running_duration.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    
                    if hours > 0:
                        data["running_time"] = f"{hours}h {minutes}m"
                    elif minutes > 0:
                        data["running_time"] = f"{minutes}m {seconds}s"
                    else:
                        data["running_time"] = f"{seconds}s"
                else:
                    data["running_time"] = "N/A"
            except (ValueError, TypeError) as e:
                data["running_time"] = "N/A"
            
            # Get memory usage for the process
            try:
                proc = psutil.Process(int(pid))
                if proc.is_running():
                    memory_info = proc.memory_info()
                    memory_mb = round(memory_info.rss / 1024 / 1024, 1)  # Convert bytes to MB
                    data["memory_mb"] = f"{memory_mb} MB"
                else:
                    data["memory_mb"] = "N/A"
            except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError) as e:
                data["memory_mb"] = "N/A"
            except Exception as e:
                data["memory_mb"] = "N/A"
            
            res[pid] = data
        return res

    def upsert_worker_status(self, pid: str, task_name: str, status: str, *args, **kwargs):
        pid = str(pid)
        worker_pids = self.get_worker_pids()
        if pid not in worker_pids:
            self.register_worker_pid(pid)
            control_logger.WARN(f"Process: {pid} should have registered. Please Check the code.")
        
        task_key = f"ginkgo_worker_status_{pid}"
        status_data = {
            "task_name": task_name,
            "status": status,
            "time_stamp": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
        }
        
        # 使用RedisService设置任务状态，TTL设为1小时
        self.redis_service.set_task_status(task_key, status_data, ttl=3600)

    def clean_worker_status(self, *args, **kwargs) -> None:
        for pid in self.get_worker_pids():
            try:
                pid = str(pid)
                status = self.get_worker_status(pid)
                key = self.get_redis_key_about_worker_status(pid)
                if status is None:
                    self.redis_service.delete_cache(key)
                    continue
                if status.get("status") == "killed":
                    self.redis_service.delete_cache(key)
            except psutil.NoSuchProcess as e:
                key = self.get_redis_key_about_worker_status(pid)
                self.redis_service.delete_cache(key)
            except Exception as e:
                pass
            finally:
                pass
