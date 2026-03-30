# Upstream: TaskTimer (Kafka control commands), CLI deploy command
# Downstream: PaperTradingController (daily cycle execution)
# Role: 纸上交易 Worker — 持有所有活跃的纸上交易引擎，接收 Kafka 命令推进


import threading
from typing import Dict

from ginkgo.libs import GLOG


class PaperTradingWorker:
    """
    纸上交易 Worker

    长驻进程，持有所有活跃的纸上交易引擎实例。
    通过 Kafka 接收 TaskTimer 的 paper_trading 控制命令，
    调用所有 PaperTradingController 的 run_daily_cycle() 推进引擎。

    架构模式与 DataWorker 一致。
    """

    def __init__(self):
        self._controllers: Dict[str, object] = {}
        self._lock = threading.Lock()
        self._running = False

    def register_controller(self, portfolio_id: str, controller) -> None:
        """注册纸上交易控制器"""
        with self._lock:
            self._controllers[portfolio_id] = controller
            GLOG.INFO(f"[PAPER-WORKER] Registered controller for {portfolio_id}")

    def unregister_controller(self, portfolio_id: str) -> None:
        """注销纸上交易控制器"""
        with self._lock:
            self._controllers.pop(portfolio_id, None)
            GLOG.INFO(f"[PAPER-WORKER] Unregistered controller for {portfolio_id}")

    def _handle_command(self, command: str, params: Dict) -> bool:
        """处理 Kafka 控制命令"""
        if command == "paper_trading":
            return self._handle_paper_trading(params)
        return False

    def _handle_paper_trading(self, params: Dict) -> bool:
        """处理 paper_trading 命令：推进所有引擎"""
        GLOG.INFO(
            f"[PAPER-WORKER] Paper trading advance triggered, "
            f"active controllers: {len(self._controllers)}"
        )

        with self._lock:
            for portfolio_id, controller in self._controllers.items():
                try:
                    result = controller.run_daily_cycle()
                    GLOG.INFO(
                        f"[PAPER-WORKER] {portfolio_id}: "
                        f"skipped={result.skipped}, advanced={result.advanced}"
                    )
                except Exception as e:
                    GLOG.ERROR(f"[PAPER-WORKER] {portfolio_id} failed: {e}")

        return True

    def start(self) -> None:
        """启动 Worker（订阅 Kafka topic）"""
        # TODO: Kafka 订阅逻辑，类似 DataWorker
        # 当前版本通过 CLI deploy 直接调用 register_controller
        self._running = True
        GLOG.INFO("[PAPER-WORKER] Worker started")

    def stop(self) -> None:
        """停止 Worker"""
        self._running = False
        GLOG.INFO("[PAPER-WORKER] Worker stopped")
