import sys
import os
_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
if _path not in sys.path:
    sys.path.insert(0, _path)

import pytest
from unittest.mock import patch

from ginkgo.trading.brokers import sim_broker as sb_module
from ginkgo.trading.brokers.sim_broker import SimBroker
from ginkgo.enums import DIRECTION_TYPES, ATTITUDE_TYPES


class TestLimitBoardPriceGuard:
    """一字板（high == low）价格生成：价格确定，不应触发随机分布调用。

    #5491: std_dev = (high - low) / 6 在一字板为 0，scale=0 依赖 scipy 退化行为。
    加固后 high == low 时直接返回限价，跳过 scipy.rvs，消除隐式依赖。
    """

    @pytest.mark.parametrize("direction", [DIRECTION_TYPES.LONG, DIRECTION_TYPES.SHORT])
    def test_limit_board_random_skips_rvs(self, direction):
        """RANDOM 态度下一字板不调用 norm.rvs，直接返回限价"""
        broker = SimBroker(random_seed=42, attitude=ATTITUDE_TYPES.RANDOM)
        with patch.object(sb_module.stats.norm, "rvs", wraps=sb_module.stats.norm.rvs) as spy_norm:
            price = broker._get_random_transaction_price(
                direction, 10.0, 10.0, ATTITUDE_TYPES.RANDOM
            )
        assert float(price) == 10.0
        spy_norm.assert_not_called()

    @pytest.mark.parametrize("direction", [DIRECTION_TYPES.LONG, DIRECTION_TYPES.SHORT])
    @pytest.mark.parametrize("attitude", [ATTITUDE_TYPES.OPTIMISTIC, ATTITUDE_TYPES.PESSIMISTIC])
    def test_limit_board_skew_skips_rvs(self, direction, attitude):
        """OPTIMISTIC/PESSIMISTIC 态度下一字板不调用 skewnorm.rvs，直接返回限价"""
        broker = SimBroker(random_seed=42, attitude=attitude)
        with patch.object(sb_module.stats.skewnorm, "rvs", wraps=sb_module.stats.skewnorm.rvs) as spy_skew:
            price = broker._get_random_transaction_price(
                direction, 10.0, 10.0, attitude
            )
        assert float(price) == 10.0
        spy_skew.assert_not_called()

    def test_non_limit_board_still_uses_rvs(self):
        """非一字板（high != low）仍走随机分布——回归守护，防 guard 误吞正常区间"""
        broker = SimBroker(random_seed=42, attitude=ATTITUDE_TYPES.RANDOM)
        with patch.object(sb_module.stats.norm, "rvs", wraps=sb_module.stats.norm.rvs) as spy_norm:
            price = broker._get_random_transaction_price(
                DIRECTION_TYPES.LONG, 10.0, 11.0, ATTITUDE_TYPES.RANDOM
            )
        assert 10.0 <= float(price) <= 11.0
        spy_norm.assert_called_once()
