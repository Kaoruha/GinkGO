"""DataManager单元测试"""

import pytest
from unittest.mock import Mock, patch
from ginkgo.livecore.data_manager import DataManager
from ginkgo.interfaces.dtos import InterestUpdateDTO, ControlCommandDTO


@pytest.mark.tdd
class TestDataManager:
    """DataManager单元测试"""

    @patch('ginkgo.livecore.data_manager.EastMoneyFeeder')
    def test_init_with_default_feeder_type(self, mock_feeder):
        """测试：使用默认feeder_type初始化DataManager"""
        mock_feeder.return_value = Mock()
        data_manager = DataManager()
        assert data_manager._feeder_type == "eastmoney"
        assert data_manager.live_feeder is not None
        assert data_manager.all_symbols == set()

    @patch('ginkgo.livecore.data_manager.FuShuFeeder')
    def test_init_with_custom_feeder_type(self, mock_feeder):
        """测试：使用自定义feeder_type初始化DataManager"""
        mock_feeder.return_value = Mock()
        data_manager = DataManager(feeder_type="fushu")
        assert data_manager._feeder_type == "fushu"
        assert data_manager.live_feeder is not None

    @patch('ginkgo.livecore.data_manager.EastMoneyFeeder')
    @patch('ginkgo.livecore.data_manager.FuShuFeeder')
    @patch('ginkgo.livecore.data_manager.AlpacaFeeder')
    def test_create_feeder_eastmoney(self, mock_alpaca, mock_fushu, mock_eastmoney):
        """测试：_create_feeder创建EastMoneyFeeder"""
        mock_eastmoney.return_value = Mock()
        mock_fushu.return_value = Mock()
        mock_alpaca.return_value = Mock()

        data_manager = DataManager(feeder_type="fushu")  # Use fushu to avoid creating default
        feeder = data_manager._create_feeder("eastmoney")
        assert feeder is not None
        mock_eastmoney.assert_called_once()

    @patch('ginkgo.livecore.data_manager.EastMoneyFeeder')
    @patch('ginkgo.livecore.data_manager.FuShuFeeder')
    @patch('ginkgo.livecore.data_manager.AlpacaFeeder')
    def test_create_feeder_fushu(self, mock_alpaca, mock_fushu, mock_eastmoney):
        """测试：_create_feeder创建FuShuFeeder"""
        mock_eastmoney.return_value = Mock()
        mock_fushu.return_value = Mock()
        mock_alpaca.return_value = Mock()

        data_manager = DataManager(feeder_type="alpaca")
        feeder = data_manager._create_feeder("fushu")
        assert feeder is not None
        mock_fushu.assert_called_once()

    @patch('ginkgo.livecore.data_manager.EastMoneyFeeder')
    @patch('ginkgo.livecore.data_manager.FuShuFeeder')
    @patch('ginkgo.livecore.data_manager.AlpacaFeeder')
    def test_create_feeder_alpaca(self, mock_alpaca, mock_fushu, mock_eastmoney):
        """测试：_create_feeder创建AlpacaFeeder"""
        mock_eastmoney.return_value = Mock()
        mock_fushu.return_value = Mock()
        mock_alpaca.return_value = Mock()

        data_manager = DataManager(feeder_type="fushu")
        feeder = data_manager._create_feeder("alpaca")
        assert feeder is not None
        mock_alpaca.assert_called_once()

    @patch('ginkgo.livecore.data_manager.EastMoneyFeeder')
    def test_create_feeder_invalid_type(self, mock_feeder):
        """测试：_create_feeder处理无效类型抛出ValueError"""
        mock_feeder.return_value = Mock()
        data_manager = DataManager()
        with pytest.raises(ValueError, match="Unknown feeder_type"):
            data_manager._create_feeder("invalid_type")

    @patch('ginkgo.livecore.data_manager.EastMoneyFeeder')
    def test_update_subscriptions_replace(self, mock_feeder):
        """测试：update_subscriptions处理replace类型更新"""
        mock_feeder_instance = Mock()
        mock_feeder_instance.subscribe_symbols = Mock()
        mock_feeder_instance.start_subscription = Mock()
        mock_feeder.return_value = mock_feeder_instance

        data_manager = DataManager()

        # 创建InterestUpdateDTO (replace类型)
        dto = InterestUpdateDTO(
            portfolio_id="test_portfolio",
            node_id="test_node",
            update_type="replace",
            symbols=["000001.SZ", "600000.SH"]
        )

        data_manager.update_subscriptions(dto)

        # 验证订阅集合被替换
        assert len(data_manager.all_symbols) == 2
        assert "000001.SZ" in data_manager.all_symbols
        assert "600000.SH" in data_manager.all_symbols

    @patch('ginkgo.livecore.data_manager.EastMoneyFeeder')
    def test_update_subscriptions_add(self, mock_feeder):
        """测试：update_subscriptions处理add类型更新"""
        mock_feeder_instance = Mock()
        mock_feeder_instance.subscribe_symbols = Mock()
        mock_feeder_instance.start_subscription = Mock()
        mock_feeder.return_value = mock_feeder_instance

        data_manager = DataManager()
        data_manager.all_symbols = {"000001.SZ"}

        # 创建InterestUpdateDTO (add类型)
        dto = InterestUpdateDTO(
            portfolio_id="test_portfolio",
            node_id="test_node",
            update_type="add",
            symbols=["600000.SH"]
        )

        data_manager.update_subscriptions(dto)

        # 验证新的symbol被添加
        assert len(data_manager.all_symbols) == 2
        assert "000001.SZ" in data_manager.all_symbols
        assert "600000.SH" in data_manager.all_symbols

    @patch('ginkgo.livecore.data_manager.EastMoneyFeeder')
    def test_update_subscriptions_remove(self, mock_feeder):
        """测试：update_subscriptions处理remove类型更新"""
        mock_feeder_instance = Mock()
        mock_feeder_instance.subscribe_symbols = Mock()
        mock_feeder_instance.start_subscription = Mock()
        mock_feeder.return_value = mock_feeder_instance

        data_manager = DataManager()
        data_manager.all_symbols = {"000001.SZ", "600000.SH"}

        # 创建InterestUpdateDTO (remove类型)
        dto = InterestUpdateDTO(
            portfolio_id="test_portfolio",
            node_id="test_node",
            update_type="remove",
            symbols=["000001.SZ"]
        )

        data_manager.update_subscriptions(dto)

        # 验证symbol被移除
        assert len(data_manager.all_symbols) == 1
        assert "000001.SZ" not in data_manager.all_symbols
        assert "600000.SH" in data_manager.all_symbols

    @patch('ginkgo.livecore.data_manager.EastMoneyFeeder')
    def test_handle_control_command_bar_snapshot(self, mock_feeder):
        """测试：_handle_control_command处理bar_snapshot命令"""
        mock_feeder.return_value = Mock()
        data_manager = DataManager()
        data_manager.all_symbols = {"000001.SZ"}

        # Mock _send_daily_bars方法
        data_manager._send_daily_bars = Mock()

        # 创建bar_snapshot命令
        command_dto = ControlCommandDTO(
            command=ControlCommandDTO.Commands.BAR_SNAPSHOT
        )

        data_manager._handle_control_command(command_dto)

        # 验证_send_daily_bars被调用
        data_manager._send_daily_bars.assert_called_once()

    @patch('ginkgo.livecore.data_manager.EastMoneyFeeder')
    def test_handle_control_command_update_selector_ignored(self, mock_feeder):
        """测试：_handle_control_command忽略update_selector命令"""
        mock_feeder.return_value = Mock()
        data_manager = DataManager()

        # Mock _send_daily_bars方法
        data_manager._send_daily_bars = Mock()

        # 创建update_selector命令
        command_dto = ControlCommandDTO(
            command=ControlCommandDTO.Commands.UPDATE_SELECTOR
        )

        data_manager._handle_control_command(command_dto)

        # 验证_send_daily_bars未被调用
        data_manager._send_daily_bars.assert_not_called()

    @patch('ginkgo.livecore.data_manager.AlpacaFeeder')
    def test_feeder_type_property(self, mock_feeder):
        """测试：feeder_type属性正确设置"""
        mock_feeder.return_value = Mock()
        data_manager = DataManager(feeder_type="alpaca")
        assert data_manager._feeder_type == "alpaca"

    @patch('ginkgo.livecore.data_manager.EastMoneyFeeder')
    def test_all_symbols_initially_empty(self, mock_feeder):
        """测试：all_symbols初始为空集合"""
        mock_feeder.return_value = Mock()
        data_manager = DataManager()
        assert isinstance(data_manager.all_symbols, set)
        assert len(data_manager.all_symbols) == 0

    @patch('ginkgo.livecore.data_manager.EastMoneyFeeder')
    def test_stopped_event_initially_unset(self, mock_feeder):
        """测试：_stopped事件初始未设置"""
        mock_feeder.return_value = Mock()
        data_manager = DataManager()
        assert not data_manager._stopped.is_set()

    @patch('ginkgo.livecore.data_manager.EastMoneyFeeder')
    def test_running_event_initially_unset(self, mock_feeder):
        """测试：_running事件初始未设置"""
        mock_feeder.return_value = Mock()
        data_manager = DataManager()
        assert not data_manager._running.is_set()
