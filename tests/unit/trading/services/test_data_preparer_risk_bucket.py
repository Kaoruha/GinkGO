"""
#6102: data_preparer._get_portfolio_components 的 risk 类型分桶回归

file_type == FILE_TYPES.RISKMANAGER (3) 的 mapping 应进 risk_managers。
历史 bug：判定写成 7（ENGINE），导致 risk 组件落入 else 警告分支被静默丢弃。
"""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.enums import FILE_TYPES


def _make_mapping(file_type, name="m"):
    """构造带 .type/.name 的 mapping 对象（模拟 portfolio_file_mapping 记录）"""
    return SimpleNamespace(type=file_type, name=name)


@pytest.mark.unit
class TestGetPortfolioComponentsRiskBucket:
    """risk 组件(type=RISKMANAGER=3)应被正确分到 risk_managers，不落空"""

    @patch("ginkgo.data.containers.container")
    def test_risk_manager_bucketed_correctly(self, mock_container):
        """type=3(RISKMANAGER) 进 risk_managers；type=6(STRATEGY) 进 strategies 作对照"""
        from ginkgo.trading.services._assembly.data_preparer import DataPreparer

        mappings = [
            _make_mapping(FILE_TYPES.RISKMANAGER.value, "risk-1"),
            _make_mapping(FILE_TYPES.STRATEGY.value, "strat-1"),
        ]
        # _get_portfolio_components 内: container.cruds.portfolio_file_mapping().find(...)
        mock_container.cruds.portfolio_file_mapping.return_value.find.return_value = mappings

        preparer = DataPreparer()
        components = preparer._get_portfolio_components("pf-1")

        # risk 组件不再丢失
        assert len(components["risk_managers"]) == 1
        assert components["risk_managers"][0].name == "risk-1"
        # 对照：strategy 正常分桶
        assert len(components["strategies"]) == 1
        assert components["strategies"][0].name == "strat-1"
