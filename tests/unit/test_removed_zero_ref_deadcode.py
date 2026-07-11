"""回归守卫：零引用死代码删除（#6111）。

#6111 经 grep 实测确认以下 5 项为零引用死代码并已删除。本测试锁定该删除——
防止 careless revert / merge 静默重新引入这些无人调用的桩，再次堆积成死代码。

被删项（详见 issue #6111 triage brief 2026-07-07）：
- ginkgo.interfaces.dtos.live_trading_dto（254L，7 类全 0 外部引用；KafkaTopics 与
  interfaces.kafka_topics 重复定义的死副本）
- ginkgo.notifier.notifier_wechat（纯注释空 stub，未导出）
- ginkgo.notifier.notifier_base（纯注释空 stub，未导出）
- BarService.sync_full（空方法体，仅 docstring，0 调用）
- BarService.sync_incremental（空方法体，仅 docstring，0 调用）

正向守卫：同位置的其他活跃符号（sync_full_batch / sync_incremental_batch /
notifier_beep / notifier_telegram / backtest_assignment_dto）必须仍在——brief
明确点名这些「禁止触碰」（实测有引用），锁住防过度删除。
"""
import importlib.util

import pytest

from ginkgo.data.services.bar_service import BarService


# ---------- 被删模块必须不可 import ----------

@pytest.mark.unit
def test_live_trading_dto_module_removed():
    """live_trading_dto 已删：find_spec 应返回 None。"""
    assert importlib.util.find_spec("ginkgo.interfaces.dtos.live_trading_dto") is None


@pytest.mark.unit
def test_notifier_wechat_module_removed():
    """notifier_wechat 空 stub 已删。"""
    assert importlib.util.find_spec("ginkgo.notifier.notifier_wechat") is None


@pytest.mark.unit
def test_notifier_base_module_removed():
    """notifier_base 空 stub 已删。"""
    assert importlib.util.find_spec("ginkgo.notifier.notifier_base") is None


# ---------- 被删方法必须不再是 BarService 属性 ----------

@pytest.mark.unit
def test_bar_service_sync_full_removed():
    """sync_full 空方法体已删，不再是 BarService 公开面。"""
    assert not hasattr(BarService, "sync_full")


@pytest.mark.unit
def test_bar_service_sync_incremental_removed():
    """sync_incremental 空方法体已删，不再是 BarService 公开面。"""
    assert not hasattr(BarService, "sync_incremental")


# ---------- 正向守卫：DO-NOT-TOUCH 项仍在（防过度删除）----------

@pytest.mark.unit
def test_batch_sync_methods_still_exist():
    """sync_full_batch / sync_incremental_batch 是活跃方法，必须保留。"""
    assert hasattr(BarService, "sync_full_batch")
    assert hasattr(BarService, "sync_incremental_batch")


@pytest.mark.unit
def test_active_notifier_and_dto_modules_untouched():
    """brief 点名「禁止触碰」的模块（实测有引用）必须仍可 import。"""
    for mod in (
        "ginkgo.notifier.notifier_beep",
        "ginkgo.notifier.notifier_telegram",
        "ginkgo.interfaces.dtos.backtest_assignment_dto",
    ):
        assert importlib.util.find_spec(mod) is not None, f"{mod} 不应被删除"
