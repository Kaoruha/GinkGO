# Upstream: 全局所有模块 (通过GTM单例管理线程/Worker)、CLI命令(ginkgo worker)
# Downstream: GCONF(配置), GLOG(日志), GinkgoLogger, retry(装饰器), psutil, rich, redis_service/kafka_service(延迟加载)
# Role: GinkgoThreadManager线程/进程管理器，支持Kafka数据Worker管理






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
from ginkgo.libs import GLOG


console = Console()
control_logger = GinkgoLogger("main_control", file_names=["main_control.log"], console_log=True)
worker_logger = GinkgoLogger("dataworker", file_names=["data_worker.log"], console_log=True)


class GinkgoThreadManager:
    """
    线程/进程管理器，支持任务分发、Worker管理、实时引擎启停。

    Args:
        redis_service: 可选的Redis服务实例，不传则延迟从 data.containers 获取
        kafka_service: 可选的Kafka服务实例，不传则延迟从 data.containers 获取
        on_task_complete: 可选回调 callable(task_name, detail)，任务成功时触发
        on_task_error: 可选回调 callable(task_name, error)，任务失败时触发
    """

    def __init__(self, *args, redis_service=None, kafka_service=None,
                 on_task_complete=None, on_task_error=None, **kwargs):
        super().__init__()
        self.thread_pool_name = "ginkgo_thread_pool"
        self.dataworker_pool_name = "ginkgo_dataworker"
        self.lock = threading.Lock()  # TODO

        # 依赖注入的服务实例
        self._redis_service = redis_service
        self._kafka_service = kafka_service

        # 通知回调（由业务层注入，如 beep 提示音）
        self._on_task_complete = on_task_complete
        self._on_task_error = on_task_error

        # #5516: in-memory 线程句柄注册表。Redis 缓存存线程 ident（非宿主 pid），
        # 但 ident 跨进程无法查存活，故本地保留 Thread 句柄供 get_thread_status/kill_thread 使用。
        self._threads: Dict[str, threading.Thread] = {}
    
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

    def _notify_complete(self, task_name: str, detail: str = ""):
        """任务完成通知（由业务层注入回调，如 beep 提示音）"""
        if self._on_task_complete:
            try:
                self._on_task_complete(task_name, detail)
            except Exception as e:
                GLOG.WARNING(f"{e}")
                pass

    def _notify_error(self, task_name: str, error: str = ""):
        """任务失败通知"""
        if self._on_task_error:
            try:
                self._on_task_error(task_name, error)
            except Exception as e:
                GLOG.WARNING(f"{e}")
                pass

    def get_redis_key_about_worker_status(self, pid: str, *args, **kwargs) -> str:
        return f"{str(pid)}_status"

    def process_task(self, type: str, code: str, full: bool = False, force: bool = False, *args, **kwargs):
        pid = os.getpid()

        # 打印Kafka消息解析详情
        GLOG.DEBUG("=" * 80)
        GLOG.DEBUG(f"Kafka Message解析 - PID: {pid}")
        GLOG.DEBUG(f"   type: {type}")
        GLOG.DEBUG(f"   code: {code}")
        GLOG.DEBUG(f"   full: {full}")
        GLOG.DEBUG(f"   force: {force}")

        # 根据消息类型打印处理逻辑映射
        if type == "stockinfo":
            GLOG.DEBUG("   处理逻辑: stockinfo 同步")
        elif type == "calender":
            GLOG.DEBUG("   处理逻辑: 交易日历同步")
        elif type == "bar":
            strategy = f"日K线同步({{'强制覆盖' if force else '跳过已有'}})"
            GLOG.DEBUG(f"   处理逻辑: {strategy}")
            GLOG.DEBUG(f"   实际调用: fetch_and_update_cn_daybar(code={code})")
        elif type == "tick":
            if full:
                sync_mode = f"全量同步({{'强制覆盖' if force else '跳过已有'}})"
                GLOG.DEBUG(f"   处理逻辑: Tick {sync_mode}")
                GLOG.DEBUG(f"   实际调用: TickService.sync_backfill_by_date(code={code}, force_overwrite={force})")
            else:
                sync_mode = f"增量同步({{'强制覆盖' if force else '跳过已有'}})"
                GLOG.DEBUG(f"   处理逻辑: Tick {sync_mode}")
                GLOG.DEBUG(f"   实际调用: fetch_and_update_tick(code={code})")
        elif type == "adjust":
            strategy = f"复权因子同步({{'强制覆盖' if force else '跳过已有'}}) + 计算"
            GLOG.DEBUG(f"   处理逻辑: {strategy}")
            GLOG.DEBUG(f"   实际调用: fetch_and_update_adjustfactor(code={code}) + calculate({code})")
        else:
            GLOG.DEBUG("   处理逻辑: 未知类型")

        GLOG.DEBUG("=" * 80)

        # 实际任务处理逻辑
        if type == "stockinfo":
            # 使用container service方法
            worker_logger.INFO("🔄 Syncing stock information for all stocks")
            try:
                self.upsert_worker_status(pid=pid, task_name="update_stock_info", status="RUNNING")

                from ginkgo.data.containers import container
                stockinfo_service = container.stockinfo_service()

                # 同步所有股票信息
                result = stockinfo_service.sync_all()

                if result.success:
                    worker_logger.INFO("✅ Stock information sync completed")
                    if result.data and 'records_processed' in result.data:
                        worker_logger.INFO(f"📊 Processed {result.data['records_processed']} stock records")
                else:
                    worker_logger.ERROR(f"❌ Stock information sync failed: {result.error}")

                self.upsert_worker_status(pid=pid, task_name="update_stock_info", status="COMPLETE" if result.success else "ERROR")
                if result.success:
                    self._notify_complete("update_stock_info")
                else:
                    self._notify_error("update_stock_info", result.error)
            except Exception as e:
                worker_logger.ERROR(f"💥 Stock information sync error: {str(e)}")
                self.upsert_worker_status(pid=pid, task_name="update_stock_info", status="ERROR")
                self._notify_error("update_stock_info", str(e))
        elif type == "calender":
            # 使用container CRUD方法（TradeDay目前没有专门的Service）
            worker_logger.INFO("🔄 Updating trading calendar (placeholder)")
            try:
                self.upsert_worker_status(pid=pid, task_name="update_calender", status="RUNNING")

                # TradeDay同步目前是占位符实现，没有实际的同步服务
                # TODO: 需要实现TradeDayService或找到合适的数据源
                from ginkgo.data import fetch_and_update_tradeday
                fetch_and_update_tradeday()

                # 或者使用container中的TradeDayCRUD进行基础操作
                # from ginkgo.data.containers import container
                # trade_day_crud = container.cruds.trade_day()

                worker_logger.INFO("✅ Trading calendar update completed (placeholder)")
                self.upsert_worker_status(pid=pid, task_name="update_calender", status="COMPLETE")
                self._notify_complete("update_calender")
            except Exception as e:
                worker_logger.ERROR(f"💥 Trading calendar update error: {str(e)}")
                self.upsert_worker_status(pid=pid, task_name="update_calender", status="ERROR")
                self._notify_error("update_calender", str(e))
        elif type == "adjust":
            # 使用container service方法
            worker_logger.INFO(
                f"🔄 Syncing adjustfactor data for {code}. full={full}, force={force}"
            )
            try:
                self.upsert_worker_status(
                    pid=pid,
                    task_name=f"update_adjustfactor_{code}_full_{force}",
                    status="RUNNING",
                )

                from ginkgo.data.containers import container
                adjustfactor_service = container.adjustfactor_service()

                # 同步adjustfactor数据
                result = adjustfactor_service.sync(code, fast_mode=not full)

                if result.success:
                    worker_logger.INFO(f"✅ Adjustfactor sync completed for {code}")
                    if result.data and 'records_processed' in result.data:
                        worker_logger.INFO(f"📊 Processed {result.data['records_processed']} records for {code}")

                    # 同步完成后立即计算复权因子
                    try:
                        calc_result = adjustfactor_service.calculate(code)
                        if calc_result.success:
                            worker_logger.INFO(f"✅ Adjustment factor calculation completed for {code}")
                            if calc_result.data and 'records_processed' in calc_result.data:
                                worker_logger.INFO(f"📊 Calculated {calc_result.data['records_processed']} adjustment factors for {code}")
                        else:
                            worker_logger.ERROR(f"❌ Adjustment factor calculation failed for {code}: {calc_result.error}")
                    except Exception as e:
                        worker_logger.ERROR(f"💥 Error calculating adjustment factors for {code}: {str(e)}")
                else:
                    worker_logger.ERROR(f"❌ Adjustfactor sync failed for {code}: {result.error}")

                self.upsert_worker_status(
                    pid=pid,
                    task_name=f"update_adjustfactor_{code}_full_{force}",
                    status="COMPLETE" if result.success else "ERROR",
                )
                if result.success:
                    self._notify_complete(f"update_adjustfactor_{code}")
                else:
                    self._notify_error(f"update_adjustfactor_{code}", result.error)
            except Exception as e:
                worker_logger.ERROR(f"💥 Adjustfactor sync error for {code}: {str(e)}")
                self.upsert_worker_status(
                    pid=pid,
                    task_name=f"update_adjustfactor_{code}_full_{force}",
                    status="ERROR",
                )
                self._notify_error(f"update_adjustfactor_{code}", str(e))
        elif type == "bar":
            # 使用container service方法
            worker_logger.INFO(
                f"🔄 Syncing bar data for {code}. full={full}, force={force}"
            )
            try:
                self.upsert_worker_status(
                    pid=pid,
                    task_name=f"update_daybar_{code}_full_{force}",
                    status="RUNNING",
                )

                from ginkgo.data.containers import container
                bar_service = container.bar_service()

                if full:
                    # 全量同步：使用sync_range从上市日期开始
                    result = bar_service.sync_range(code=code, start_date=None, end_date=None)
                else:
                    # 增量同步
                    result = bar_service.sync_smart(code=code, fast_mode=not force)

                if result.success:
                    worker_logger.INFO(f"✅ Bar sync completed for {code}")
                    if result.data:
                        # 如果data是DataSyncResult对象，直接访问其属性
                        if hasattr(result.data, 'records_processed'):
                            worker_logger.INFO(f"📊 Processed {result.data.records_processed} records for {code}")
                        # 如果data是字典，检查键
                        elif isinstance(result.data, dict) and 'records_processed' in result.data:
                            worker_logger.INFO(f"📊 Processed {result.data['records_processed']} records for {code}")
                else:
                    worker_logger.ERROR(f"❌ Bar sync failed for {code}: {result.error}")

                self.upsert_worker_status(
                    pid=pid,
                    task_name=f"update_daybar_{code}_full_{force}",
                    status="COMPLETE" if result.success else "ERROR",
                )
                if result.success:
                    self._notify_complete(f"update_daybar_{code}")
                else:
                    self._notify_error(f"update_daybar_{code}", result.error)
            except Exception as e:
                worker_logger.ERROR(f"💥 Bar sync error for {code}: {str(e)}")
                self.upsert_worker_status(
                    pid=pid,
                    task_name=f"update_daybar_{code}_full_{force}",
                    status="ERROR",
                )
                self._notify_error(f"update_daybar_{code}", str(e))
        elif type == "tick":
            # 根据full/force参数映射到实际的同步策略
            if full:
                # 全量同步模式：使用sync_backfill_by_date方法
                sync_mode = f"backfill_{'force' if force else 'skip'}"
                worker_logger.INFO(
                    f"Dealing with tick backfill sync for {code} ({sync_mode} mode)."
                )
                task_name = f"tick_backfill_{code}_{sync_mode}"

                try:
                    self.upsert_worker_status(
                        pid=pid,
                        task_name=task_name,
                        status="RUNNING",
                    )
                    from ginkgo.data.containers import container

                    # 调用TickService的逐日回溯方法
                    tick_service = container.tick_service()
                    result = tick_service.sync_backfill_by_date(code=code, force_overwrite=force)

                    if result.success:
                        worker_logger.INFO(f"✅ Tick backfill sync completed for {code}")
                    else:
                        worker_logger.ERROR(f"❌ Tick backfill sync failed for {code}: {result.message}")

                    self.upsert_worker_status(
                        pid=pid,
                        task_name=task_name,
                        status="COMPLETE" if result.success else "ERROR",
                    )
                    if result.success:
                        self._notify_complete(task_name)
                    else:
                        self._notify_error(task_name, result.message)
                except Exception as e:
                    worker_logger.ERROR(f"💥 Tick backfill sync error for {code}: {str(e)}")
                    self.upsert_worker_status(
                        pid=pid,
                        task_name=task_name,
                        status="ERROR",
                    )
                    self._notify_error(task_name, str(e))
            else:
                # 增量同步模式：使用container service方法
                sync_mode = f"incremental_{'force' if force else 'skip'}"
                worker_logger.INFO(
                    f"🔄 Tick incremental sync for {code} ({sync_mode} mode)."
                )
                task_name = f"tick_incremental_{code}_{sync_mode}"

                try:
                    self.upsert_worker_status(
                        pid=pid,
                        task_name=task_name,
                        status="RUNNING",
                    )
                    from ginkgo.data.containers import container
                    tick_service = container.tick_service()

                    # 增量同步：从最新日期开始同步到当前，根据force参数决定是否强制覆盖
                    result = tick_service.sync_smart(code=code, fast_mode=not force)

                    if result.success:
                        worker_logger.INFO(f"✅ Tick incremental sync completed for {code}")
                        if result.data:
                            # 如果data是DataSyncResult对象，直接访问其属性
                            if hasattr(result.data, 'records_processed'):
                                worker_logger.INFO(f"📊 Processed {result.data.records_processed} records for {code}")
                            # 如果data是字典，检查键
                            elif isinstance(result.data, dict) and 'records_processed' in result.data:
                                worker_logger.INFO(f"📊 Processed {result.data['records_processed']} records for {code}")
                    else:
                        worker_logger.ERROR(f"❌ Tick incremental sync failed for {code}: {result.error}")

                    self.upsert_worker_status(
                        pid=pid,
                        task_name=task_name,
                        status="COMPLETE" if result.success else "ERROR",
                    )
                    if result.success:
                        self._notify_complete(task_name)
                    else:
                        self._notify_error(task_name, result.error)
                except Exception as e:
                    worker_logger.ERROR(f"💥 Tick incremental sync error for {code}: {str(e)}")
                    self.upsert_worker_status(
                        pid=pid,
                        task_name=task_name,
                        status="ERROR",
                    )
                    self._notify_error(task_name, str(e))
        elif type == "other":
            worker_logger.WARN(f"Got the command no in list. {value}")
            self.upsert_worker_status(
                pid=pid,
                task_name="got a unrecognized task",
                status="IDLE",
            )
            GLOG.DEBUG("看看传的啥")
            GLOG.DEBUG(value)

    def run_data_worker(self, *args, **kwargs):
        """Run data worker in containerized mode using DataWorker class."""
        import os
        import socket
        try:
            from ginkgo.data.worker.worker import DataWorker
            from ginkgo import service_hub

            # Get node_id from kwargs or environment
            node_id = kwargs.get('node_id') or os.getenv("GINKGO_NODE_ID")
            if node_id is None:
                node_id = f"data_worker_{socket.gethostname()}"

            # Get services from service_hub
            bar_crud = service_hub.data.cruds.bar()

            # Create DataWorker instance
            worker = DataWorker(
                bar_crud=bar_crud,
                group_id="data_worker_group",
                auto_offset_reset="earliest",
                node_id=node_id
            )

            # Start worker
            worker_logger.INFO(":rocket: Starting DataWorker...")
            if worker.start():
                worker_logger.INFO(":white_check_mark: DataWorker started successfully")
                # Keep worker running
                worker.wait_for_completion()
            else:
                worker_logger.ERROR(":x: Failed to start DataWorker")

        except ImportError as e:
            worker_logger.ERROR(f":x: Failed to import DataWorker: {e}")
            worker_logger.ERROR(":information: Make sure the data.worker module is properly installed")
        except Exception as e:
            worker_logger.ERROR(f":x: Error running DataWorker: {e}")

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
            worker_logger.ERROR(f"DataWorker can not start. {str(e)}")
        finally:
            if os.path.exists(file_name):
                os.remove(file_name)

    def start_multi_worker(self, count: int = 4, *args, **kwargs) -> None:
        for i in range(count):
            self.run_data_worker_daemon()

    def reset_all_workers(self, *args, **kwargs):
        while self.get_worker_count() > 0:
            for pid in self.get_worker_pids():
                GLOG.DEBUG(f"get worker : {pid}")
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
                    GLOG.WARNING(f"{e}")
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
        key = self.get_thread_cache_name(name)
        # 检查线程是否已存在
        if self.redis_service.exists(key):
            console.print(f"{name} exists. Please change the name and try it again.")
            return
        t = threading.Thread(target=target, name=name)
        t.start()
        # #5516: 缓存线程 ident（非宿主 pid）并保留 in-memory 句柄。
        # 此前存 os.getpid() 会让 kill_thread SIGKILL 宿主进程（自杀），
        # 且同进程多线程 pid 相同无法区分。
        self._threads[name] = t
        self.redis_service.set_thread_cache(key, str(t.ident))
        self.redis_service.add_to_thread_list(self.thread_pool_name, key)

    def get_thread_status(self, name: str) -> bool:
        # #5516: 优先用 in-memory Thread 句柄判断真实存活（is_alive），
        # 而非用 psutil 查宿主进程（对 in-process 线程恒为 True，无法反映线程实际状态）。
        key = self.get_thread_cache_name(name)
        t = self._threads.get(name)
        if t is not None:
            return t.is_alive()
        # 无句柄（跨进程 GTM 实例 / 历史残留）：清理缓存并视为不存活
        if self.redis_service.exists(key):
            self.redis_service.delete_cache(key)
            self.redis_service.remove_from_thread_list(self.thread_pool_name, key)
        return False

    def kill_thread(self, name: str) -> None:
        # #5516: Python 无法从外部安全强杀 threading.Thread（无 thread.kill()）。
        # 此前缓存 os.getpid() 后 os.kill(host_pid, SIGKILL) 会杀掉整个宿主进程
        # （自杀脚枪）。现仅清理注册（缓存 + 线程列表 + in-memory 句柄），
        # 目标线程需自行协作式停止。
        key = self.get_thread_cache_name(name)
        self._threads.pop(name, None)
        self.redis_service.delete_cache(key)
        self.redis_service.remove_from_thread_list(self.thread_pool_name, key)
        console.print(f"Unregistered thread:{key} (in-process threads cannot be hard-killed; cooperative stop required).")

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
        while True:
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
                    GLOG.WARNING(f"{e}")
                    pass
                finally:
                    pass
            if cursor == 0:
                break

    def clean_worker_pool(self, *args, **kwargs) -> None:
        cursor = 0
        while True:
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
                    GLOG.WARNING(f"{e}")
                    pass
                finally:
                    pass
            if cursor == 0:
                break

    def get_thread_pids(self) -> List:
        res = []
        cursor = 0
        while True:
            cursor, elements = self.redis_service.scan_thread_pool(self.thread_pool_name, cursor=cursor, count=100)
            for item in elements:
                res.append(item)
            if cursor == 0:
                break
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
                GLOG.WARNING(f"{e}")
                pass
            finally:
                pass

