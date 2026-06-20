"""
#5624 回归测试：容器 notification_recipient_service 装配。

根因：containers.py 用 lambda 实例化 NotificationRecipientService，lambda 在类
主体内引用类属性 ``user_group_service()`` / ``user_service()``，但 Python 类主体
命名空间不是嵌套函数（含 lambda）的闭包作用域，导致 NameError → Singleton 实例化
失败 → ``GET /notifications/recipients`` 500、``POST`` 返回空响应。

修复：改为 dependency_injector 构造函数注入（传 provider，DI 自动 resolve），
复用类内已定义的 CRUD/service provider，与 user_group_service 写法一致。
"""
import pytest

from ginkgo.libs import GCONF


@pytest.fixture(autouse=True)
def _ensure_debug():
    """连 test 库（Debug 模式），隔离生产库。"""
    GCONF.set_debug(True)


@pytest.mark.unit
def test_notification_recipient_service_instantiable():
    """容器能实例化 notification_recipient_service（修复前抛 NameError）。"""
    from ginkgo.data.containers import container
    from ginkgo.notifier.services.notification_recipient_service import (
        NotificationRecipientService,
    )

    svc = container.notification_recipient_service()

    assert isinstance(svc, NotificationRecipientService)


@pytest.mark.unit
def test_notification_recipient_service_list_all_runs():
    """实例化后 list_all() 返回 ServiceResult（GET 端点不再 500，#5624）。"""
    from ginkgo.data.containers import container

    svc = container.notification_recipient_service()
    result = svc.list_all()

    # ServiceResult 即可（表可能为空）；关键是端点不再因 NameError 500
    assert result is not None
    assert hasattr(result, "success")
