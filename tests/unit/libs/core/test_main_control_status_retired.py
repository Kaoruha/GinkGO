"""
#6727: main_control 远控总线退役后,RedisService 的进程注册 helper 与
GinkgoThreadManager 的 main_status / watch_dog_status 属性应从接口移除。

#6726 已删消费链(threading.py 的 consume + watch_dog 整链)。#6727 清理 #6726 遗留的
helper 定义与属性声明——它们是孤儿:#6726 删消费链后,仅剩 redis_service 内部定义 +
threading 属性自调用,无任何外部调用方。
"""
import pytest

from ginkgo.data.services.redis_service import RedisService
from ginkgo.libs.core.threading import GinkgoThreadManager


# ===========================================================================
# #6727 — RedisService 进程注册 helper 退役(6 个孤儿)
# ===========================================================================

class TestRedisProcessHelpersRetired:
    """远控消费链 #6726 已删,无进程再 register,六个进程 helper 成孤儿,应移除。"""

    @pytest.mark.unit
    def test_main_process_helpers_removed(self):
        """register/unregister/get_main_process_pid 三个 helper 已移除。"""
        assert not hasattr(RedisService, "register_main_process")
        assert not hasattr(RedisService, "unregister_main_process")
        assert not hasattr(RedisService, "get_main_process_pid")

    @pytest.mark.unit
    def test_watchdog_helpers_removed(self):
        """register/unregister/get_watchdog_pid 三个 helper 已移除。"""
        assert not hasattr(RedisService, "register_watchdog")
        assert not hasattr(RedisService, "unregister_watchdog")
        assert not hasattr(RedisService, "get_watchdog_pid")


# ===========================================================================
# #6727 — GinkgoThreadManager main_status / watch_dog_status 属性退役
# ===========================================================================

class TestGTMMainControlPropertiesRetired:
    """两个 property 内部仅自调已删的 redis helper,属性成孤儿,应移除。"""

    @pytest.mark.unit
    def test_main_status_property_removed(self):
        """main_status property 已移除(原读 redis main_process_pid 并查进程状态)。"""
        assert not hasattr(GinkgoThreadManager, "main_status")

    @pytest.mark.unit
    def test_watch_dog_status_property_removed(self):
        """watch_dog_status property 已移除(原读 redis watchdog_pid 并查进程状态)。"""
        assert not hasattr(GinkgoThreadManager, "watch_dog_status")
