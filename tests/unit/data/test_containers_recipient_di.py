# Issue: #5624 — GET/POST notification recipients 500 (容器 lambda NameError)
# Upstream: ginkgo.data.containers.Container.notification_recipient_service
# Downstream: api.api.settings.get_notification_recipient_service → API 端点
# Role: 验证容器能解析 NotificationRecipientService，不抛 NameError

"""
notification_recipient_service 容器解析测试

根因：containers.py 原用 lambda 封装 NotificationRecipientService 实例化，
lambda 内引用同类作用域的 user_group_service / user_service —— 但 Python
类体不是闭包作用域，名字查找走模块全局找不到 → NameError。
（lambda lazy 执行，容器 import 不报错，首次取服务才崩 → 端点 500）

修复：改用声明式 DI（providers.Singleton(Service, dep=provider)），
由 dependency_injector 在调用时解析 provider，与其他 service 一致。
"""

import pytest


class TestNotificationRecipientContainerDI:
    """#5624: notification_recipient_service 容器解析不抛 NameError"""

    def test_container_resolves_recipient_service(self):
        """TDD Red: 容器应能解析 NotificationRecipientService，不抛 NameError"""
        from ginkgo.data.containers import container
        from ginkgo.notifier.services.notification_recipient_service import (
            NotificationRecipientService,
        )

        # 修复前：lambda 引用类作用域名 → NameError
        svc = container.notification_recipient_service()

        assert isinstance(svc, NotificationRecipientService)

    def test_recipient_service_has_injected_dependencies(self):
        """TDD Red: 声明式 DI 应注入 user_group_service / user_service"""
        from ginkgo.data.containers import container

        svc = container.notification_recipient_service()

        # NotificationRecipientService.__init__ 注入这些依赖
        assert svc.user_group_service is not None
        assert svc.user_service is not None
