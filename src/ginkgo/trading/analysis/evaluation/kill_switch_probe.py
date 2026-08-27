# Upstream: livecore / BrokerManager (P1 kill switch 落地后能力面变化)
# Downstream: FunnelEvaluator (g3_kill_switch gate)
# Role: G3 kill switch 能力探针 — 运行时探测熔断四件套是否就位, P1 落地后自动翻转


"""
KillSwitchProbe — 实盘风控熔断能力探针 (G3)

kill switch = 出事时把暴露降到零的最后手段, 四件套:
- flatten:           全仓市价平仓
- cancel_all:        全部挂单撤单
- daily_loss_breaker: 日内亏损自动熔断
- manual_trigger:    独立手动开关 (不经策略/风控链)

现状 (P1 未落地): BrokerManager.emergency_stop_all 只断 broker 连接 —
已发挂单仍留在交易所, 仓位仍敞口, 停连 ≠ 停损。四件套全缺。

探测方式: 能力存在性检查 (方法/属性面), 不实发指令。
livecore P1 落地补齐能力后探针自动翻转, 评估侧零改动 —
这是 M4 "联动显示" 的含义: 报告如实反映 kill switch 状态, 不实现 kill switch 本体。
"""

from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass
class KillSwitchCapability:
    """熔断四件套就位情况"""

    flatten: bool = False
    cancel_all: bool = False
    daily_loss_breaker: bool = False
    manual_trigger: bool = False

    @property
    def ready(self) -> bool:
        return (
            self.flatten
            and self.cancel_all
            and self.daily_loss_breaker
            and self.manual_trigger
        )

    @property
    def gaps(self) -> List[str]:
        names = [
            ("flatten", "全仓平仓 (flatten)"),
            ("cancel_all", "全撤单 (cancel-all)"),
            ("daily_loss_breaker", "日损熔断 (daily loss breaker)"),
            ("manual_trigger", "独立手动开关"),
        ]
        return [label for attr, label in names if not getattr(self, attr)]


# 探测目标: (模块, 类/对象名) — livecore P1 落地后在对应对象上补能力即可被探到
_PROBE_TARGETS = (
    ("ginkgo.trading.brokers.broker_manager", "BrokerManager"),
    ("ginkgo.livecore.live_engine", "LiveEngine"),
)

# 各能力探测的方法/属性名 (任一命中即视为该能力就位)
_CAPABILITY_PROBES = {
    "flatten": ("flatten_all", "flatten_positions", "close_all_positions"),
    "cancel_all": ("cancel_all_orders", "cancel_all"),
    "daily_loss_breaker": ("daily_loss_breaker", "trigger_daily_loss_break"),
    "manual_trigger": ("kill_switch", "emergency_kill"),
}


def _import_target(module_name: str, attr_name: str) -> Optional[Any]:
    try:
        import importlib

        module = importlib.import_module(module_name)
        return getattr(module, attr_name, None)
    except Exception:
        return None


def probe_kill_switch() -> KillSwitchCapability:
    """探测 kill switch 四件套能力是否就位

    静态能力面检查 (hasattr), 不实发指令、不碰 DB。
    """
    cap = KillSwitchCapability()
    targets = [
        obj
        for module_name, attr_name in _PROBE_TARGETS
        if (obj := _import_target(module_name, attr_name)) is not None
    ]
    if not targets:
        return cap

    for capability, probe_names in _CAPABILITY_PROBES.items():
        found = any(
            hasattr(obj, name)
            for obj in targets
            for name in probe_names
        )
        setattr(cap, capability, found)
    return cap


def gate_detail(cap: KillSwitchCapability) -> str:
    """gate detail 文案: 就位列全件, 未位列缺口"""
    if cap.ready:
        return "flatten / cancel-all / 日损熔断 / 手动开关 全部就位"
    return "未就位: " + ", ".join(cap.gaps)
