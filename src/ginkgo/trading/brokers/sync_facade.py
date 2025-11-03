"""
SyncBrokerFacade

为回测模式提供的同步调用封装：
- 保持 Broker `async` 接口不变的前提下，提供等价的同步方法，便于在纯同步回测管线中使用。
- 内部会在需要时创建/管理临时事件循环，或在线程中执行，以避免嵌套事件循环报错。
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any, Optional, List

from .base_broker import ExecutionResult


class SyncBrokerFacade:
    """将异步 Broker 封装为同步接口（仅建议回测模式使用）。"""

    def __init__(self, broker: Any):
        self._broker = broker

    # ============= 同步运行辅助 =============
    def _run(self, coro):
        """以同步方式执行协程，兼容当前线程已有/无事件循环的情况。"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                result_box: dict = {}
                exc_box: dict = {}

                def _runner():
                    _loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(_loop)
                    try:
                        result_box["result"] = _loop.run_until_complete(coro)
                    except Exception as e:  # noqa: BLE001 - 透传异常
                        exc_box["exc"] = e
                    finally:
                        _loop.close()

                t = threading.Thread(target=_runner, name="SyncBrokerFacadeRunner", daemon=True)
                t.start()
                t.join()
                if exc_box:
                    raise exc_box["exc"]
                return result_box.get("result")
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            # 当前线程没有事件循环
            _loop = asyncio.new_event_loop()
            try:
                return _loop.run_until_complete(coro)
            finally:
                _loop.close()

    # ============= 对外同步方法（名称与语义直观） =============
    def connect(self) -> bool:
        return bool(self._run(self._broker.connect()))

    def disconnect(self) -> bool:
        return bool(self._run(self._broker.disconnect()))

    def submit_order(self, order: Any) -> ExecutionResult:
        return self._run(self._broker.submit_order(order))

    def cancel_order(self, order_id: str):
        return self._run(self._broker.cancel_order(order_id))

    def query_order(self, order_id: str) -> ExecutionResult:
        return self._run(self._broker.query_order(order_id))

    def get_positions(self) -> List[Any]:
        return self._run(self._broker.get_positions())

    def get_account_info(self) -> Any:
        return self._run(self._broker.get_account_info())

