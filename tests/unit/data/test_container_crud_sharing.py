"""#5509 DI 容器 CRUD 接线契约测试

核心契约：service provider 的 CRUD 依赖必须【引用】顶层具名 provider，
不能 inline `providers.Singleton(get_crud, name)` 重新创建独立 provider。

inline 写法在每个 service 上新建独立 provider 对象——当前 `get_crud` 的全局
`_crud_instances` 缓存恰好掩盖了实例层面的后果（所有 provider 解析出同一 CRUD
实例），但接线层面仍是错的：一旦缓存策略变化（如按 session 区分），inline
立即产生独立 CRUD 实例 → 独立 DB session → "同事务写 A 读 B 不可见"。

因此本测试在【provider 身份】层面断言接线正确性：service provider 的
`kwargs[<crud_arg>]` 必须 `is` 顶层具名 CRUD provider 对象。
"""
import pytest

from dependency_injector import providers as di


def _fresh_container():
    """新建 Container 实例，避免 module-level singleton 缓存污染。"""
    from ginkgo.data.containers import Container

    return Container()


class TestContainerCRUDWiring:
    """service provider 必须引用具名 CRUD provider（#5509 AC2）。"""

    @pytest.mark.parametrize(
        "service_attr,crud_attr,arg_name",
        [
            ("position_service", "position_crud", "crud_repo"),
            ("signal_service", "signal_crud", "crud_repo"),
            ("order_service", "order_crud", "crud_repo"),
            ("signal_tracking_service", "signal_tracker_crud", "tracker_crud"),
            ("live_account_service", "live_account_crud", "live_account_crud"),
            ("validation_service", "analyzer_record_crud", "analyzer_record_crud"),
        ],
    )
    def test_service_references_named_crud_provider(
        self, service_attr, crud_attr, arg_name
    ):
        """service 的 CRUD 依赖 provider 必须 identity 等于具名 CRUD provider。"""
        c = _fresh_container()
        service_provider = getattr(c, service_attr)
        named_provider = getattr(c, crud_attr)
        assert service_provider.kwargs.get(arg_name) is named_provider, (
            f"{service_attr}.{arg_name} 未引用具名 {crud_attr} provider（疑似 inline Singleton）"
        )

    def test_backtest_task_service_references_all_named_crud_providers(self):
        """backtest_task_service 内部 8 个 CRUD 依赖全部引用具名 provider（#5509 AC2）。"""
        c = _fresh_container()
        bt_provider = c.backtest_task_service
        pairs = [
            ("signal_crud", "signal_crud"),
            ("order_crud", "order_crud"),
            ("position_crud", "position_crud"),
            ("position_record_crud", "position_record_crud"),
            ("order_record_crud", "order_record_crud"),
            ("transfer_record_crud", "transfer_record_crud"),
            ("transfer_crud", "transfer_crud"),
            ("signal_tracker_crud", "signal_tracker_crud"),
        ]
        for arg_name, crud_attr in pairs:
            assert bt_provider.kwargs.get(arg_name) is getattr(c, crud_attr), (
                f"backtest_task_service.{arg_name} 未引用具名 {crud_attr} provider"
            )

    def test_tick_crud_is_lazy_provider_not_eager_instance(self):
        """TickCRUD 应作为 provider 懒注入，非容器定义期 eager 实例（#5509 AC3）。"""
        c = _fresh_container()
        crud_arg = c.tick_service.kwargs.get("crud_repo")
        assert isinstance(crud_arg, di.Provider), (
            f"crud_repo 应为 provider（懒注入），实为 {type(crud_arg).__name__}（eager 实例）"
        )

    def test_crud_instances_shared_end_to_end(self):
        """端到端契约：所有路径解析的同名 CRUD 是同一实例（get_crud 缓存下成立）。

        此测试防御 get_crud 缓存被移除后的回归——届时 inline 接线会立刻让本测试红。
        """
        c = _fresh_container()
        assert c.position_service()._crud_repo is c.position_crud()
        assert c.signal_service()._crud_repo is c.signal_crud()
        assert c.order_service()._crud_repo is c.order_crud()
        bt = c.backtest_task_service()
        assert bt._signal_crud is c.signal_crud()
        assert bt._position_crud is c.position_crud()
