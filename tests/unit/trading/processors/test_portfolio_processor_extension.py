"""PortfolioProcessor扩展单元测试 - ControlCommand处理和Selector触发机制"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from queue import Queue
from datetime import datetime

from ginkgo.workers.execution_node.portfolio_processor import PortfolioProcessor, PortfolioState
from ginkgo.trading.portfolios.portfolio_live import PortfolioLive
from ginkgo.interfaces.dtos import ControlCommandDTO


@pytest.mark.tdd
class TestPortfolioProcessorExtension:
    """PortfolioProcessor扩展测试 - ControlCommand处理和Selector触发机制"""

    @pytest.fixture
    def mock_portfolio(self):
        """Mock PortfolioLive实例"""
        portfolio = Mock(spec=PortfolioLive)
        portfolio.portfolio_id = "test_portfolio_001"
        portfolio._selectors = []
        return portfolio

    @pytest.fixture
    def portfolio_processor(self, mock_portfolio):
        """创建PortfolioProcessor实例用于测试"""
        input_queue = Queue()
        output_queue = Queue()
        processor = PortfolioProcessor(
            portfolio=mock_portfolio,
            input_queue=input_queue,
            output_queue=output_queue,
            max_queue_size=1000
        )
        return processor

    # ===== _handle_control_command方法测试 =====

    def test_handle_control_command_valid_update_selector(self, portfolio_processor):
        """测试：_handle_control_command处理有效的update_selector命令"""
        # Mock _update_selectors方法
        portfolio_processor._update_selectors = Mock()

        # 创建update_selector命令
        command_dto = ControlCommandDTO(
            command=ControlCommandDTO.Commands.UPDATE_SELECTOR
        )
        message = command_dto.model_dump_json().encode('utf-8')

        # 执行
        portfolio_processor._handle_control_command(message)

        # 验证_update_selectors被调用
        portfolio_processor._update_selectors.assert_called_once()

    def test_handle_control_command_ignores_bar_snapshot(self, portfolio_processor):
        """测试：_handle_control_command忽略bar_snapshot命令（由DataManager处理）"""
        # Mock _update_selectors方法
        portfolio_processor._update_selectors = Mock()

        # 创建bar_snapshot命令
        command_dto = ControlCommandDTO(
            command=ControlCommandDTO.Commands.BAR_SNAPSHOT
        )
        message = command_dto.model_dump_json().encode('utf-8')

        # 执行
        portfolio_processor._handle_control_command(message)

        # 验证_update_selectors未被调用
        portfolio_processor._update_selectors.assert_not_called()

    def test_handle_control_command_ignores_update_data(self, portfolio_processor):
        """测试：_handle_control_command忽略update_data命令（由DataManager处理）"""
        # Mock _update_selectors方法
        portfolio_processor._update_selectors = Mock()

        # 创建update_data命令
        command_dto = ControlCommandDTO(
            command=ControlCommandDTO.Commands.UPDATE_DATA
        )
        message = command_dto.model_dump_json().encode('utf-8')

        # 执行
        portfolio_processor._handle_control_command(message)

        # 验证_update_selectors未被调用
        portfolio_processor._update_selectors.assert_not_called()

    def test_handle_control_command_invalid_json(self, portfolio_processor):
        """测试：_handle_control_command处理无效JSON"""
        # 无效JSON消息
        invalid_message = b"invalid json content"

        # 执行（不应抛异常）
        portfolio_processor._handle_control_command(invalid_message)

    def test_handle_control_command_empty_message(self, portfolio_processor):
        """测试：_handle_control_command处理空消息"""
        # 空消息
        empty_message = b""

        # 执行（不应抛异常）
        portfolio_processor._handle_control_command(empty_message)

    # ===== _update_selectors方法测试 =====

    def test_update_selectors_calls_all_selectors(self, portfolio_processor, mock_portfolio):
        """测试：_update_selectors调用所有selectors"""
        # 创建mock selectors
        mock_selector1 = Mock()
        mock_selector1.pick.return_value = ["000001.SZ"]
        mock_selector2 = Mock()
        mock_selector2.pick.return_value = ["600000.SH"]

        mock_portfolio._selectors = [mock_selector1, mock_selector2]

        # 执行
        portfolio_processor._update_selectors()

        # 验证所有selector的pick被调用
        mock_selector1.pick.assert_called_once()
        mock_selector2.pick.assert_called_once()

    def test_update_selectors_creates_event_interest_update(self, portfolio_processor, mock_portfolio):
        """测试：_update_selectors创建EventInterestUpdate"""
        # 创建mock selector
        mock_selector = Mock()
        mock_selector.pick.return_value = ["000001.SZ", "600000.SH"]
        mock_portfolio._selectors = [mock_selector]

        # 执行
        portfolio_processor._update_selectors()

        # 验证output_queue收到消息
        assert not portfolio_processor.output_queue.empty()
        event = portfolio_processor.output_queue.get()
        assert event is not None

    def test_update_selectors_publishes_to_output_queue(self, portfolio_processor, mock_portfolio):
        """测试：_update_selectors发布EventInterestUpdate到output_queue"""
        # 创建mock selectors
        mock_selector1 = Mock()
        mock_selector1.pick.return_value = ["000001.SZ"]
        mock_selector2 = Mock()
        mock_selector2.pick.return_value = ["600000.SH"]

        mock_portfolio._selectors = [mock_selector1, mock_selector2]

        # 执行
        portfolio_processor._update_selectors()

        # 验证output_queue非空
        assert not portfolio_processor.output_queue.empty()

    def test_update_selectors_empty_selector_list(self, portfolio_processor, mock_portfolio):
        """测试：_update_selectors处理空selector列表"""
        # 空selector列表
        mock_portfolio._selectors = []

        # 执行（不应抛异常）
        portfolio_processor._update_selectors()

        # 验证output_queue仍然有消息（EventInterestUpdate with empty codes）
        assert not portfolio_processor.output_queue.empty()
        event = portfolio_processor.output_queue.get()
        assert event is not None
        # 验证codes为空列表
        assert event.codes == []

    def test_update_selectors_selector_pick_exception(self, portfolio_processor, mock_portfolio):
        """测试：_update_selectors处理selector.pick抛异常"""
        # 创建mock selector，一个抛异常，一个正常
        mock_selector_error = Mock()
        mock_selector_error.pick.side_effect = Exception("Selector error")
        mock_selector_ok = Mock()
        mock_selector_ok.pick.return_value = ["000001.SZ"]

        mock_portfolio._selectors = [mock_selector_error, mock_selector_ok]

        # 执行（不应抛异常）
        portfolio_processor._update_selectors()

        # 验证正常的selector仍然被调用
        mock_selector_ok.pick.assert_called_once()
        # 验证output_queue有消息
        assert not portfolio_processor.output_queue.empty()

    def test_update_selectors_selector_returns_empty_list(self, portfolio_processor, mock_portfolio):
        """测试：selector.pick返回空列表"""
        # 创建返回空列表的selector
        mock_selector = Mock()
        mock_selector.pick.return_value = []
        mock_portfolio._selectors = [mock_selector]

        # 执行（不应抛异常）
        portfolio_processor._update_selectors()

        # 验证selector被调用
        mock_selector.pick.assert_called_once()
        # 验证output_queue仍然有消息（EventInterestUpdate with empty codes）
        assert not portfolio_processor.output_queue.empty()
        event = portfolio_processor.output_queue.get()
        assert event.codes == []

    def test_update_selectors_selector_returns_none(self, portfolio_processor, mock_portfolio):
        """测试：selector.pick返回None"""
        # 创建返回None的selector
        mock_selector = Mock()
        mock_selector.pick.return_value = None
        mock_portfolio._selectors = [mock_selector]

        # 执行（不应抛异常）
        portfolio_processor._update_selectors()

        # 验证selector被调用
        mock_selector.pick.assert_called_once()
