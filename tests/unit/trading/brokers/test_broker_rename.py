"""IBroker 分开设名后的契约测试（tracer bullet）。

ADR-022：async IBroker → Broker（实盘契约），sync IBroker → SyncBroker（回测/模拟契约）。
本测试验证改名后：
1. 新名 Broker/SyncBroker 可从权威位置 import
2. 继承关系保持（BaseBroker→Broker, OKXBroker→SyncBroker）
3. 两个契约为不同类（消歧成立）

注：本 issue 只改名不修继承错配（OKXBroker 实盘继承 sync 契约是历史遗留，
留 follow-up issue），此处仅断言「改名后继承关系与改名前一致」。
"""
from ginkgo.trading.brokers.interfaces import Broker as AsyncBrokerFromModule
from ginkgo.trading.brokers import Broker as AsyncBrokerFromExport
from ginkgo.trading.interfaces.broker_interface import SyncBroker
from ginkgo.trading.brokers.base_broker import BaseBroker
from ginkgo.trading.brokers.okx_broker import OKXBroker


def test_async_ibroker_renamed_to_broker():
    # async IBroker → Broker，权威定义在 brokers/interfaces.py
    # export（brokers/__init__.py）指向同一对象
    assert AsyncBrokerFromModule is AsyncBrokerFromExport


def test_basebroker_inherits_async_broker():
    # BaseBroker 仍是 async 契约（Broker）的子类（与改名前一致）
    assert issubclass(BaseBroker, AsyncBrokerFromModule)


def test_okx_broker_inherits_sync_broker():
    # OKXBroker 仍是 sync 契约（SyncBroker）的子类（与改名前一致）
    assert issubclass(OKXBroker, SyncBroker)


def test_async_and_sync_broker_are_distinct():
    # 分开设名的核心目的：两个契约为不同类，消除同名歧义
    assert AsyncBrokerFromModule is not SyncBroker
