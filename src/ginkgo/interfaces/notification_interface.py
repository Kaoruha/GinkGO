# Upstream: 业务逻辑层(依赖注入INotificationService接口实现通知解耦)
# Downstream: 具体通知实现(GinkgoNotifier/MockNotificationService通过工厂创建)
# Role: INotificationService通知服务接口定义消息/长信号/短信号/提醒等方法支持交易系统功能和组件集成提供完整业务支持






"""
通知接口 - 解耦通知功能与具体实现

这个接口定义了通知系统的抽象，使得业务逻辑不依赖于具体的通知实现。
在测试环境中可以注入空实现，在生产环境中注入真实的通知服务。
"""

import sys
from abc import ABC, abstractmethod
from typing import Optional


class INotificationService(ABC):
    """通知服务接口"""

    @abstractmethod
    def beep(self) -> None:
        """发送简单的提示音"""
        pass

    @abstractmethod
    def send_message(self, message: str, target: Optional[str] = None) -> None:
        """发送消息通知"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查通知服务是否可用"""
        pass


class MockNotificationService(INotificationService):
    """测试用的空通知服务实现"""

    def beep(self) -> None:
        """测试环境中的空实现"""
        pass

    def send_message(self, message: str, target: Optional[str] = None) -> None:
        """测试环境中的空实现"""
        pass

    def is_available(self) -> bool:
        """测试环境中总是不可用"""
        return False


class NotificationServiceFactory:
    """通知服务工厂"""

    @staticmethod
    def create_service(service_type: str = "auto") -> INotificationService:
        """
        创建通知服务实例

        Args:
            service_type: 服务类型 ("auto", "mock", "real")

        Returns:
            INotificationService: 通知服务实例
        """
        if service_type == "mock":
            return MockNotificationService()

        elif service_type == "real":
            # 尝试创建真实的通知服务
            try:
                from ginkgo.notifier.ginkgo_notifier import GNOTIFIER
                return GNOTIFIER
            except ImportError:
                # 如果导入失败，返回空实现
                return MockNotificationService()

        else:  # auto
            # 根据环境自动选择
            # 检查是否在测试环境中（通过sys.modules中是否有pytest）
            if 'pytest' in sys.modules or '_pytest' in sys.modules:
                return MockNotificationService()

            # 否则尝试使用真实服务
            try:
                from ginkgo.notifier.ginkgo_notifier import GNOTIFIER
                return GNOTIFIER
            except ImportError:
                return MockNotificationService()