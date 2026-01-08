"""
LiveCore 主入口单元测试

测试 LiveCore 类的核心功能：
1. 初始化和配置管理
2. 启动和停止生命周期
3. 状态管理
4. 配置访问

注意：这些测试只测试LiveCore的实际行为，不验证方法调用。
"""

import pytest
from ginkgo.livecore.main import LiveCore


@pytest.mark.unit
class TestLiveCoreInitialization:
    """测试 LiveCore 初始化"""

    def test_livecore_init_with_default_config(self):
        """测试使用默认配置初始化"""
        livecore = LiveCore()

        # 验证初始状态
        assert livecore.is_running is False
        assert livecore.threads == []
        assert livecore.config == {}

        # 验证组件初始为 None
        assert livecore.data_manager is None
        assert livecore.trade_gateway_adapter is None
        assert livecore.scheduler is None

        print(f"✅ LiveCore 使用默认配置初始化成功")

    def test_livecore_init_with_custom_config(self):
        """测试使用自定义配置初始化"""
        custom_config = {
            "data_manager": {"enabled": True},
            "scheduler": {"interval": 5}
        }
        livecore = LiveCore(config=custom_config)

        assert livecore.config == custom_config

        print(f"✅ LiveCore 使用自定义配置初始化成功")


@pytest.mark.unit
class TestLiveCoreLifecycle:
    """测试 LiveCore 生命周期管理"""

    def test_start_sets_is_running_flag(self):
        """测试 start() 设置运行标志"""
        livecore = LiveCore()
        livecore.start()

        assert livecore.is_running is True
        print(f"✅ start() 正确设置 is_running=True")

        # 清理
        livecore.stop()

    def test_stop_sets_is_running_false(self):
        """测试 stop() 清除运行标志"""
        livecore = LiveCore()
        livecore.start()
        livecore.stop()

        assert livecore.is_running is False
        print(f"✅ stop() 正确设置 is_running=False")

    def test_start_stop_cycle(self):
        """测试多次启动-停止"""
        livecore = LiveCore()

        # 第一次启动
        livecore.start()
        assert livecore.is_running is True

        # 停止
        livecore.stop()
        assert livecore.is_running is False

        # 第二次启动
        livecore.start()
        assert livecore.is_running is True

        # 再次停止
        livecore.stop()
        assert livecore.is_running is False

        print(f"✅ 可以多次启动-停止")


@pytest.mark.unit
class TestLiveCoreComponents:
    """测试 LiveCore 组件管理"""

    def test_components_initially_none(self):
        """测试组件初始为None"""
        livecore = LiveCore()

        assert livecore.data_manager is None
        assert livecore.trade_gateway_adapter is None
        assert livecore.scheduler is None

        print(f"✅ 组件初始为None")

    def test_threads_list_initially_empty(self):
        """测试threads列表初始为空"""
        livecore = LiveCore()

        assert livecore.threads == []
        assert isinstance(livecore.threads, list)

        print(f"✅ threads列表初始为空")


@pytest.mark.unit
class TestLiveCoreConfig:
    """测试 LiveCore 配置管理"""

    def test_config_accessible(self):
        """测试config可访问"""
        config = {"test": "value"}
        livecore = LiveCore(config=config)

        assert livecore.config == config
        assert "test" in livecore.config

        print(f"✅ config可访问")

    def test_config_mutable(self):
        """测试config可修改"""
        livecore = LiveCore()

        # 修改config
        livecore.config["new_key"] = "new_value"

        assert "new_key" in livecore.config
        assert livecore.config["new_key"] == "new_value"

        print(f"✅ config可修改")
