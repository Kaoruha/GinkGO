# #5330 Assembly 日志应包含 selectors 组件
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

import pytest
from unittest.mock import MagicMock, patch
from ginkgo.enums import FILE_TYPES


class TestLoadPortfolioComponentsAssemblyLog:
    """#5330 load_portfolio_components 的 Assembly 日志应包含 selectors"""

    @patch("ginkgo.workers.backtest_worker.task_helpers.GLOG")
    @patch("ginkgo.workers.backtest_worker.task_helpers.data_container")
    def test_assembly_log_includes_selectors(self, mock_container, mock_glog):
        """#5330 Assembly 日志应包含 selectors 组件名称"""
        from ginkgo.workers.backtest_worker.task_helpers import load_portfolio_components

        # Mock portfolio_file_mapping CRUD
        mock_mapping_crud = MagicMock()

        selector_mapping = MagicMock()
        selector_mapping.type = FILE_TYPES.SELECTOR.value
        selector_mapping.file_id = "file-selector-001"
        selector_mapping.uuid = "map-001"

        strategy_mapping = MagicMock()
        strategy_mapping.type = FILE_TYPES.STRATEGY.value
        strategy_mapping.file_id = "file-strategy-001"
        strategy_mapping.uuid = "map-002"

        mock_mapping_crud.find.return_value = [selector_mapping, strategy_mapping]
        mock_container.cruds.portfolio_file_mapping.return_value = mock_mapping_crud

        # Mock file CRUD
        mock_file_crud = MagicMock()

        selector_file = MagicMock()
        selector_file.name = "fixed_selector"

        strategy_file = MagicMock()
        strategy_file.name = "random_signal"

        mock_file_crud.find.side_effect = [
            [selector_file],   # selector 查询
            [strategy_file],   # strategy 查询
        ]
        mock_container.cruds.file.return_value = mock_file_crud

        result = load_portfolio_components(
            portfolio_id="port-001",
            task_uuid="test-uuid-12345678",
        )

        # 验证 GLOG.INFO 被调用且参数包含 selectors
        info_calls = [c for c in mock_glog.INFO.call_args_list]
        assembly_call = None
        for c in info_calls:
            if "Assembly" in str(c):
                assembly_call = c
                break

        assert assembly_call is not None, "Assembly log line should exist"
        log_msg = str(assembly_call)
        assert "selectors=" in log_msg, f"Assembly log should contain selectors=, got: {log_msg}"
        assert "fixed_selector" in log_msg, f"Assembly log should contain selector name, got: {log_msg}"
