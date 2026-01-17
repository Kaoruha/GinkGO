"""LiveDataFeeder单元测试（简化版，不测试实际网络连接）"""

import pytest
from unittest.mock import Mock, patch
from ginkgo.trading.feeders.eastmoney_feeder import EastMoneyFeeder
from ginkgo.trading.feeders.fushu_feeder import FuShuFeeder
from ginkgo.trading.feeders.alpaca_feeder import AlpacaFeeder


@pytest.mark.tdd
class TestEastMoneyFeeder:
    """EastMoneyFeeder单元测试"""

    @patch('ginkgo.trading.feeders.eastmoney_feeder.GCONF')
    def test_init_creates_feeder_instance(self, mock_gconf):
        """测试：EastMoneyFeeder可以初始化创建实例"""
        # Mock GCONF.get to return a dummy API key
        mock_gconf.get.return_value = "dummy_api_key"

        feeder = EastMoneyFeeder()
        assert feeder is not None
        assert feeder.api_key == "dummy_api_key"

    @patch('ginkgo.trading.feeders.eastmoney_feeder.GCONF')
    def test_init_with_default_api_key(self, mock_gconf):
        """测试：EastMoneyFeeder从GCONF读取API密钥"""
        mock_gconf.get.return_value = "test_api_key"

        feeder = EastMoneyFeeder()
        assert feeder.api_key == "test_api_key"
        mock_gconf.get.assert_called()


@pytest.mark.tdd
class TestFuShuFeeder:
    """FuShuFeeder单元测试"""

    @patch('ginkgo.trading.feeders.fushu_feeder.GCONF')
    def test_init_creates_feeder_instance(self, mock_gconf):
        """测试：FuShuFeeder可以初始化创建实例"""
        mock_gconf.get.return_value = "dummy_api_key"

        feeder = FuShuFeeder()
        assert feeder is not None
        assert feeder.api_key == "dummy_api_key"

    @patch('ginkgo.trading.feeders.fushu_feeder.GCONF')
    def test_init_with_default_api_key(self, mock_gconf):
        """测试：FuShuFeeder从GCONF读取API密钥"""
        mock_gconf.get.return_value = "test_api_key"

        feeder = FuShuFeeder()
        assert feeder.api_key == "test_api_key"
        mock_gconf.get.assert_called()


@pytest.mark.tdd
class TestAlpacaFeeder:
    """AlpacaFeeder单元测试"""

    @patch('ginkgo.trading.feeders.alpaca_feeder.GCONF')
    def test_init_creates_feeder_instance(self, mock_gconf):
        """测试：AlpacaFeeder可以初始化创建实例"""
        mock_gconf.get.return_value = "dummy_api_key"

        feeder = AlpacaFeeder()
        assert feeder is not None
        assert feeder.api_key == "dummy_api_key"

    @patch('ginkgo.trading.feeders.alpaca_feeder.GCONF')
    def test_init_with_default_api_key(self, mock_gconf):
        """测试：AlpacaFeeder从GCONF读取API密钥"""
        mock_gconf.get.return_value = "test_api_key"

        feeder = AlpacaFeeder()
        assert feeder.api_key == "test_api_key"
        mock_gconf.get.assert_called()


@pytest.mark.tdd
class TestFeederPolymorphism:
    """Feeder多态测试"""

    @patch('ginkgo.trading.feeders.eastmoney_feeder.GCONF')
    def test_eastmoney_feeder_type(self, mock_gconf):
        """测试：EastMoneyFeeder类型正确"""
        mock_gconf.get.return_value = "dummy_key"
        feeder = EastMoneyFeeder()
        assert type(feeder).__name__ == "EastMoneyFeeder"
        assert isinstance(feeder, EastMoneyFeeder)

    @patch('ginkgo.trading.feeders.fushu_feeder.GCONF')
    def test_fushu_feeder_type(self, mock_gconf):
        """测试：FuShuFeeder类型正确"""
        mock_gconf.get.return_value = "dummy_key"
        feeder = FuShuFeeder()
        assert type(feeder).__name__ == "FuShuFeeder"
        assert isinstance(feeder, FuShuFeeder)

    @patch('ginkgo.trading.feeders.alpaca_feeder.GCONF')
    def test_alpaca_feeder_type(self, mock_gconf):
        """测试：AlpacaFeeder类型正确"""
        mock_gconf.get.return_value = "dummy_key"
        feeder = AlpacaFeeder()
        assert type(feeder).__name__ == "AlpacaFeeder"
        assert isinstance(feeder, AlpacaFeeder)
