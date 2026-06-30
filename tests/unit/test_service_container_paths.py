"""#6489: services 容器 provider 解析路径回归守护。

DynamicContainer 没有 .services 中间层聚合 provider。service provider（bar/signal/
order/analyzer/portfolio 等）直接注册在 services.data 顶层，必须用 services.data.<svc>()
直调。本测试锁定正确路径，防止再回退到 services.data.services.<svc>()（抛 AttributeError）。
"""
import pytest


class TestServiceContainerDirectPath:
    """services.data.<svc> 直调路径回归。"""

    @pytest.mark.parametrize("svc_name", [
        "bar_service",
        "signal_service",
        "order_service",
        "analyzer_service",
        "portfolio_service",
    ])
    def test_data_service_provider_resolves_directly(self, svc_name):
        """五个核心 service provider 必须通过 services.data.<svc> 直调解析（无 AttributeError）。

        这是 #6489 的根因守护：DynamicContainer 上访问 .services 中间层会抛
        AttributeError，被 worker 的 except 吞成 'Data sync error' → 部署 0 signal。
        """
        from ginkgo import services

        # 访问 provider（不调用，仅断言可解析）。直调返回 Singleton/Callable provider。
        provider = getattr(services.data, svc_name)
        assert provider is not None, f"services.data.{svc_name} 未解析"

    def test_data_has_no_services_aggregate(self):
        """services.data 不应有 .services 中间层聚合 provider。

        DynamicContainer 的 __getattr__ 对未注册名返回占位对象，再取属性必抛
        AttributeError。.services 不是注册名，访问其下的 _service 必抛错。
        断言 buggy 路径确实不可用，固化"直调是唯一正确路径"这一契约。
        """
        from ginkgo import services

        with pytest.raises(AttributeError):
            # noqa: 故意访问错误路径，证明它确实抛错
            _ = services.data.services.bar_service  # type: ignore[attr-defined]
