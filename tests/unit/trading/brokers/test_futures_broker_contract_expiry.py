# Related: #5542
# _is_contract_expired 不得用硬编码日期截止（2024-12）。
# 应按合约到期月份末 vs 当前真实日期判断；today 可注入以便测试不依赖系统时钟。
import sys
from datetime import date
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.trading.brokers.futures_broker import FuturesBroker


def _make_broker():
    """绕过 __init__；_is_contract_expired 仅依赖 self/code/today，不碰实例属性。"""
    return FuturesBroker.__new__(FuturesBroker)


class TestFuturesContractExpiry:

    def test_current_month_contract_not_expired(self):
        """#5542: 当月合约在月末前不应判到期。
        硬编码 `year==2024 and month<12 → 到期` 会误判 IF2406 在 2024-06 到期，
        拒绝当月合约交易。"""
        broker = _make_broker()
        assert broker._is_contract_expired("IF2406", today=date(2024, 6, 15)) is False

    def test_past_contract_is_expired(self):
        """#5542: 合约月份已过 → 到期（IF2406 在 2024-07 已过 6 月末）"""
        broker = _make_broker()
        assert broker._is_contract_expired("IF2406", today=date(2024, 7, 1)) is True

    def test_future_contract_not_expired(self):
        """#5542: 未来合约未到期（IF2612 在 2026-06 远未到 12 月末）"""
        broker = _make_broker()
        assert broker._is_contract_expired("IF2612", today=date(2026, 6, 22)) is False

    def test_short_code_returns_false(self):
        """#5542: 长度不足 4 的 code 视为无效，不判到期（安全降级）"""
        broker = _make_broker()
        assert broker._is_contract_expired("IF", today=date(2026, 6, 22)) is False

    def test_invalid_month_returns_false(self):
        """#5542: 非法月份（IF2499 → 99 月）解析失败时安全降级返回 False"""
        broker = _make_broker()
        assert broker._is_contract_expired("IF2499", today=date(2026, 6, 22)) is False
