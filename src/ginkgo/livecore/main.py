# Upstream: 无（顶层入口，独立进程启动）
# Downstream: DataManager（市场数据发布）、TradeGatewayAdapter（订单执行）、Scheduler（调度，Phase 5）
# Role: LiveCore业务逻辑层容器，启动和管理所有LiveCore组件线程，提供统一生命周期管理


"""
LiveCore控制节点（Control Plane）

LiveCore是实盘交易的控制节点，负责管理以下控制平面组件：
- Scheduler: 调度器，负责Portfolio在ExecutionNode间的分配（Phase 5实现）
- DataFeeder: 数据源管理器，发布市场数据到Kafka（Phase 4实现）
- TradeGatewayAdapter: 交易网关适配器，订阅Kafka订单并执行（Phase 3已实现）

注意：
- ExecutionNode是独立工作节点，不归LiveCore管理
- ExecutionNode自行启动，通过Redis心跳被Scheduler发现
- LiveCore通过Redis/Kafka与ExecutionNode通信

设计要点：
- 多线程容器：每个组件在独立线程中运行
- 优雅关闭：支持SIGINT/SIGTERM信号处理
- 线程管理：等待所有线程结束
- 配置管理：从配置文件或环境变量加载组件配置

MVP阶段（Phase 3）：
- ✅ 基础容器框架（LiveCore类、启动/停止/等待方法）
- ✅ 信号处理（SIGINT/SIGTERM）
- ✅ TradeGatewayAdapter线程占位符（T028已完成，等待broker配置）
- ✅ Scheduler调度器（Phase 5实现）
- ⏳ DataManager线程占位符（Phase 4实现）

Phase 4扩展：
- DataManager完整实现（数据源订阅、Kafka发布）

Phase 5扩展：
- Scheduler调度逻辑（无状态设计，Redis存储）
- 优雅重启机制
- 故障恢复机制

使用方式：
```python
# 方式1：直接运行
python -m ginkgo.livecore.main

# 方式2：代码启动
from ginkgo.livecore.main import LiveCore
livecore = LiveCore()
livecore.start()
livecore.wait()
```
"""

from threading import Thread, Event
import signal
import sys
from typing import Optional, List, Dict

class LiveCore:
    """
    LiveCore控制节点（多线程）

    职责：
    - 启动和管理控制平面组件线程
    - 提供统一的生命周期管理（start/stop/wait）
    - 处理系统信号（SIGINT/SIGTERM）实现优雅关闭
    - 集成DataFeeder、TradeGatewayAdapter、Scheduler等控制平面组件
    """

    def __init__(self, config: Optional[dict] = None):
        """
        初始化LiveCore控制节点

        Args:
            config: 配置字典（可选），包含broker配置、Kafka配置等
        """
        self.threads = []
        self.is_running = False
        self.config = config or {}

        # 停止事件（用于信号处理）
        self._stop_event = Event()

        # 组件实例（持有引用以便停止）
        self.data_manager = None
        self.trade_gateway_adapter = None
        self.scheduler = None

    def start(self):
        """
        启动控制平面组件线程

        启动顺序：
        1. DataFeeder（发布市场数据到Kafka）
        2. TradeGatewayAdapter（订阅Kafka订单并执行）
        3. Scheduler（调度器，发现ExecutionNode并分配Portfolio）

        注意：
        - ExecutionNode是独立工作节点，需要单独启动
        - Scheduler通过Redis心跳自动发现ExecutionNode
        """
        if self.is_running:
            print("[WARNING] LiveCore is already running")
            return

        self.is_running = True
        print("Starting LiveCore Control Plane...")

        # 启动DataFeeder线程（Phase 4实现）
        self._start_data_manager()

        # 启动TradeGatewayAdapter线程（Phase 3已实现，需要broker配置）
        self._start_trade_gateway_adapter()

        # 启动Scheduler线程（Phase 5实现）
        self._start_scheduler()

        # 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        print("LiveCore Control Plane started successfully")
        print(f"Active components: {len(self.threads)}")
        for i, thread in enumerate(self.threads, 1):
            thread_name = getattr(thread, 'name', thread.__class__.__name__)
            is_alive = thread.is_alive()
            status = "✅ Running" if is_alive else "❌ Stopped"
            print(f"  [{i}] {thread_name}: {status}")

    def stop(self):
        """
        停止所有控制平面组件 - 优雅关闭流程

        核心策略：
        1. 设置停止标志（通知所有组件停止）
        2. 按逆序停止组件（TradeGatewayAdapter → DataFeeder → Scheduler）
        3. 等待所有线程完成清理
        4. 清理资源（Kafka、Redis、内存）
        """
        if not self.is_running:
            print("[WARNING] LiveCore is not running")
            return

        print("")
        print("═══════════════════════════════════════════════════════")
        print("🛑 Stopping LiveCore Control Plane")
        print("═══════════════════════════════════════════════════════")

        # 0. 设置停止标志
        print("[Step 1] Setting stop flag...")
        self.is_running = False
        self._stop_event.set()
        print("  ✅ Stop flag set")

        # 1. 停止 TradeGatewayAdapter（优先级最高：处理订单）
        print("[Step 2] Stopping TradeGatewayAdapter...")
        if self.trade_gateway_adapter and hasattr(self.trade_gateway_adapter, 'stop'):
            self.trade_gateway_adapter.stop()
            print("  ✅ TradeGatewayAdapter stopped")
        else:
            print("  ℹ️  TradeGatewayAdapter not running")

        # 2. 停止 DataFeeder（停止发布市场数据）
        print("[Step 3] Stopping DataFeeder...")
        if self.data_manager and hasattr(self.data_manager, 'stop'):
            self.data_manager.stop()
            print("  ✅ DataFeeder stopped")
        else:
            print("  ℹ️  DataFeeder not running")

        # 3. 停止 Scheduler（停止调度）
        print("[Step 4] Stopping Scheduler...")
        if self.scheduler and hasattr(self.scheduler, 'stop'):
            self.scheduler.stop()
            print("  ✅ Scheduler stopped")
        else:
            print("  ℹ️  Scheduler not running")

        # 4. 等待所有线程完成清理
        print(f"[Step 5] Waiting for {len(self.threads)} threads to finish...")
        finished_count = 0
        timeout_count = 0
        for i, thread in enumerate(self.threads):
            if thread.is_alive():
                print(f"  ⏳ Waiting for thread {i+1}/{len(self.threads)}...")
                thread.join(timeout=5)
                if thread.is_alive():
                    print(f"  ⚠️  Thread {i+1} did not finish gracefully (timeout)")
                    timeout_count += 1
                else:
                    print(f"  ✅ Thread {i+1} finished")
                    finished_count += 1
            else:
                print(f"  ✅ Thread {i+1} already stopped")
                finished_count += 1

        print(f"  ✅ Threads finished: {finished_count}/{len(self.threads)}")
        if timeout_count > 0:
            print(f"  ⚠️  Threads timeout: {timeout_count}/{len(self.threads)}")

        # 5. 清空线程列表
        self.threads.clear()

        print("")
        print("═══════════════════════════════════════════════════════")
        print("✅ LiveCore Control Plane stopped gracefully")
        print("═══════════════════════════════════════════════════════")
        print("")

    def wait(self):
        """
        等待所有线程结束

        阻塞主线程，直到：
        - 收到KeyboardInterrupt（Ctrl+C）
        - 收到系统信号（SIGINT/SIGTERM）
        - 所有线程自然结束

        改进：使用 Event 机制，可以响应信号处理器的停止请求
        """
        try:
            # 等待停止事件或所有线程结束
            while not self._stop_event.is_set():
                # 检查所有线程是否都已结束
                alive_threads = [t for t in self.threads if t.is_alive()]
                if not alive_threads:
                    break

                # 等待一小段时间（可以响应信号）
                self._stop_event.wait(timeout=0.5)

        except KeyboardInterrupt:
            print("\n[INFO] Received keyboard interrupt, shutting down...")
        finally:
            # 确保停止组件（无论是正常退出还是异常）
            if self.is_running:
                self.stop()

    def _signal_handler(self, signum, frame):
        """
        处理停止信号（SIGINT/SIGTERM）

        Args:
            signum: 信号编号
            frame: 当前堆栈帧

        工作原理：
        1. 设置停止事件，让 wait() 退出循环
        2. wait() 会调用 stop() 进行清理
        3. 避免在信号处理器中直接 join 线程
        """
        print(f"\n[INFO] Received signal {signum}, initiating graceful shutdown...")
        self._stop_event.set()  # 设置事件，让 wait() 退出

    def _start_data_manager(self):
        """
        启动DataManager线程

        Phase 3状态：
        - 使用占位符验证LiveCore容器框架
        - 完整DataManager实现在Phase 4

        Phase 4集成方式：
        ```python
        from ginkgo.livecore.data_manager import DataManager

        self.data_manager = DataManager()
        self.data_manager.start()
        self.threads.append(self.data_manager)
        ```
        """
        print("DataManager thread starting... (placeholder, implementation in Phase 4)")

        # 创建占位符线程
        data_thread = Thread(target=self._data_manager_placeholder, daemon=True)
        data_thread.start()
        self.threads.append(data_thread)

        """
        # Phase 4集成代码（取消注释）：
        from ginkgo.livecore.data_manager import DataManager
        self.data_manager = DataManager()
        self.data_manager.start()
        self.threads.append(self.data_manager)
        print("DataManager started successfully")
        """

    def _data_manager_placeholder(self):
        """
        DataManager占位函数（MVP阶段）

        Phase 3：使用占位符验证LiveCore容器框架
        Phase 4：替换为实际DataManager实例
        """
        print("DataManager thread running (placeholder)")
        import time
        while self.is_running:
            time.sleep(1)

    def _start_trade_gateway_adapter(self):
        """
        启动TradeGatewayAdapter线程

        Phase 3状态：
        - TradeGatewayAdapter类已实现（T028完成）
        - 需要配置broker实例（IBroker接口）
        - 当前使用占位符，等待broker配置

        集成方式（Phase 4完成broker配置后启用）：
        ```python
        from ginkgo.livecore.trade_gateway_adapter import TradeGatewayAdapter
        from ginkgo.trading.interfaces import IBroker

        # 1. 从config或环境变量加载broker配置
        brokers = self._load_brokers()

        # 2. 创建TradeGatewayAdapter实例
        self.trade_gateway_adapter = TradeGatewayAdapter(brokers=brokers)

        # 3. 启动线程（TradeGatewayAdapter继承Thread）
        self.trade_gateway_adapter.start()
        self.threads.append(self.trade_gateway_adapter)
        ```
        """
        print("TradeGatewayAdapter thread starting... (T028 completed, waiting for broker config)")

        # TODO: Phase 4 - 实际集成TradeGatewayAdapter（需要broker配置）
        # 当前使用占位符进行MVP测试
        gateway_thread = Thread(target=self._trade_gateway_placeholder, daemon=True)
        gateway_thread.start()
        self.threads.append(gateway_thread)

        """
        # Phase 4集成代码（取消注释并配置brokers）：
        brokers = self._load_brokers()
        if brokers:
            self.trade_gateway_adapter = TradeGatewayAdapter(brokers=brokers)
            self.trade_gateway_adapter.start()
            self.threads.append(self.trade_gateway_adapter)
            print("TradeGatewayAdapter started successfully")
        else:
            print("[WARNING] No brokers configured, TradeGatewayAdapter not started")
        """

    def _trade_gateway_placeholder(self):
        """
        TradeGatewayAdapter占位函数（MVP阶段）

        Phase 3：使用占位符验证LiveCore容器框架
        Phase 4：替换为实际TradeGatewayAdapter实例
        """
        print("TradeGatewayAdapter thread running (placeholder)")
        import time
        while self.is_running:
            time.sleep(1)

    def _start_scheduler(self):
        """
        启动Scheduler调度器（Phase 5实现）

        Scheduler是LiveCore的调度组件，负责：
        - 定期执行调度算法（每30秒）
        - ExecutionNode心跳检测（TTL=30秒）
        - Portfolio动态分配到ExecutionNode
        - ExecutionNode故障时自动迁移Portfolio

        设计要点：
        - 无状态设计：所有调度数据存储在Redis
        - 水平扩展：支持多个Scheduler实例
        - 故障恢复：自动检测离线Node并迁移Portfolio

        Raises:
            ImportError: 如果无法导入 Scheduler 模块
            Exception: 如果 Scheduler 启动失败（会阻止 LiveCore 启动）
        """
        try:
            from ginkgo.livecore.scheduler import Scheduler
            from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer

            # 创建Kafka生产者
            kafka_producer = GinkgoProducer()

            # 创建Scheduler实例（Redis client 由 Scheduler 内部创建）
            scheduler_interval = self.config.get('scheduler_interval', 30)  # 默认30秒
            self.scheduler = Scheduler(
                kafka_producer=kafka_producer,
                schedule_interval=scheduler_interval,
                node_id="livecore_scheduler"
            )

            # 启动Scheduler线程（Scheduler继承Thread）
            self.scheduler.start()
            self.threads.append(self.scheduler)

            print(f"Scheduler started successfully (interval={scheduler_interval}s)")

        except ImportError as e:
            print(f"[ERROR] Failed to import Scheduler: {e}")
            print("[ERROR] Scheduler is a critical component for Phase 5, cannot continue")
            raise  # 重新抛出异常，阻止 LiveCore 启动
        except Exception as e:
            print(f"[ERROR] Failed to start Scheduler: {e}")
            print("[ERROR] Scheduler is a critical component for Phase 5, cannot continue")
            raise  # 重新抛出异常，阻止 LiveCore 启动

    def _load_brokers(self) -> List:
        """
        加载broker配置

        Returns:
            List[IBroker]: broker实例列表

        配置来源（按优先级）：
        1. self.config['brokers'] - 构造函数传入
        2. 环境变量 GINKGO_BROKERS
        3. 配置文件 ~/.ginkgo/brokers.yml
        """
        # TODO: Phase 4实现broker加载逻辑
        # 1. 检查config
        if 'brokers' in self.config:
            return self.config['brokers']

        # 2. 检查环境变量
        # import os
        # brokers_config = os.getenv('GINKGO_BROKERS')
        # if brokers_config:
        #     return parse_brokers_config(brokers_config)

        # 3. 检查配置文件
        # config_path = os.path.expanduser('~/.ginkgo/brokers.yml')
        # if os.path.exists(config_path):
        #     return load_brokers_from_yaml(config_path)

        print("[DEBUG] No brokers configured")
        return []


if __name__ == "__main__":
    """
    LiveCore主入口

    启动方式：
    1. 直接运行：python -m ginkgo.livecore.main
    2. 代码调用：from ginkgo.livecore.main import LiveCore

    信号处理：
    - SIGINT (Ctrl+C): 优雅关闭
    - SIGTERM: 优雅关闭
    """
    import logging

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 创建并启动LiveCore
    livecore = LiveCore()

    try:
        livecore.start()
        print("LiveCore is running. Press Ctrl+C to stop.")
        livecore.wait()
    except KeyboardInterrupt:
        print("\n[INFO] Received keyboard interrupt, shutting down...")
    except Exception as e:
        print(f"[ERROR] LiveCore error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 确保清理资源（即使启动失败或运行时出错）
        if livecore.is_running:
            print("[INFO] Cleaning up LiveCore resources...")
            livecore.stop()
        print("[INFO] LiveCore shutdown complete")
