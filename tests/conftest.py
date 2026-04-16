"""
pytest配置文件 - TDD优化版本 + 安全检查

提供TDD开发所需的核心fixtures和配置：
1. 减少Mock依赖，使用真实对象
2. 标准化测试数据创建
3. 性能监控和TDD度量
4. DEBUG模式安全检查，防止在生产环境运行测试
5. 数据库连接验证和生产环境保护
"""

import os

import pytest
import warnings

# 使用pip install -e安装的ginkgo包，无需额外路径配置

# Ginkgo核心组件 - 使用已安装的包
try:
    import ginkgo
    GINKGO_AVAILABLE = True
except ImportError:
    GINKGO_AVAILABLE = False
    warnings.warn("Ginkgo modules not available, using mock objects")


# ===== TDD配置 =====

def pytest_configure(config):
    """pytest配置 - 添加TDD标记和DEBUG模式检查"""
    # CLI 单元测试通过环境变量豁免 DEBUG 检查
    if os.environ.get("GINKGO_SKIP_DEBUG_CHECK") == "1":
        return
    # 强制检查DEBUG模式
    if not check_debug_mode():
        pytest.exit(
            "❌ DEBUG模式未启用！测试无法继续。\n"
            "请运行以下命令启用DEBUG模式：\n"
            "   ginkgo system config set --debug on\n"
            "然后重新运行测试。\n\n"
            "这是为了保护生产环境数据库安全。"
        )

    # 添加TDD标记
    config.addinivalue_line("markers", "tdd: TDD开发的测试")
    config.addinivalue_line("markers", "integration: 集成测试")
    config.addinivalue_line("markers", "slow: 慢速测试")
    config.addinivalue_line("markers", "requires_db: 需要数据库的测试")
    config.addinivalue_line("markers", "financial: 金融精度测试")
    config.addinivalue_line("markers", "protocol: Protocol接口测试")
    config.addinivalue_line("markers", "mixin: Mixin功能测试")
    config.addinivalue_line("markers", "enhancement: 框架增强功能测试")
    config.addinivalue_line("markers", "event_system: 事件系统测试")
    config.addinivalue_line("markers", "time_provider: 时间提供者测试")


def check_debug_mode() -> bool:
    """
    检查DEBUG模式是否启用

    Returns:
        bool: True表示DEBUG模式已启用，False表示未启用
    """
    try:
        # 重新导入GCONF确保可用
        from ginkgo.libs import GCONF

        if not GINKGO_AVAILABLE:
            print("⚠️  Ginkgo模块不可用，跳过DEBUG模式检查")
            return True

        debug_mode = GCONF.DEBUGMODE
        print(f"🔍 检查DEBUG模式: {'✅ 已启用' if debug_mode else '❌ 未启用'}")

        if not debug_mode:
            print("\n" + "="*60)
            print("🚨 安全检查失败：DEBUG模式未启用")
            print("="*60)
            print("为了保护生产环境数据库安全，必须启用DEBUG模式才能运行测试。")
            print("")
            print("解决方案：")
            print("  1. 运行命令启用DEBUG模式：")
            print("     ginkgo system config set --debug on")
            print("  2. 重新运行pytest")
            print("")
            print("原因说明：")
            print("  - DEBUG模式会启用额外的安全检查")
            print("  - 防止测试意外操作生产数据库")
            print("  - 确保测试在安全环境中进行")
            print("="*60)
            return False

        return True

    except Exception as e:
        print(f"❌ 检查DEBUG模式时出错: {e}")
        print("请确保Ginkgo已正确安装和配置")
        return False


# ===== 数据库自动清理 =====

@pytest.fixture(scope="function", autouse=True)
def configured_crud_cleanup(request):
    """
    基于类配置的精确CRUD清理 - 带验证的异步等待版本

    每个测试类只需要添加一行配置即可自动清理：
        CRUD_TEST_CONFIG = {'crud_class': YourCRUDClass}

    这个fixture会：
    1. 读取类的CRUD_TEST_CONFIG配置
    2. 删除前查询数据条数，记录清理前的数据量
    3. 自动创建带清理接口的CRUD实例
    4. 执行清理操作
    5. 删除后查询数据条数，确认清理有效
    6. 使用异步等待确保清理完成
    7. 输出详细的清理验证日志
    """
    from ginkgo.enums import SOURCE_TYPES

    # 检查测试类是否有CRUD配置
    crud_config = getattr(request.cls, 'CRUD_TEST_CONFIG', None)
    if not crud_config:
        yield
        return

    # 获取CRUD类和默认filters
    crud_class = crud_config.get('crud_class')
    default_filters = crud_config.get('filters', {})

    # 自动添加source字段（如果不存在）
    if 'source' not in default_filters:
        default_filters['source'] = SOURCE_TYPES.TEST.value
    if not crud_class:
        yield
        return

    # 导入依赖
    from ginkgo.enums import SOURCE_TYPES

    # 延迟导入异步清理工具
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent
    _path_to_add = str(project_root / "unit" / "libs" / "utils")
    if _path_to_add not in sys.path:
        sys.path.insert(0, _path_to_add)

    try:
        from async_cleanup import AsyncCleanupMixin, async_cleanup_with_wait
    except ImportError:
        # 如果异步清理工具不可用，使用简单清理
        yield
        return

    # 创建带清理接口的CRUD类
    class CleanupCRUD(crud_class, AsyncCleanupMixin):
        pass

    crud_obj = CleanupCRUD()
    filters = default_filters

    # Setup：测试前清理残留数据并验证
    # 对 TickCRUD 使用更安全的表检查
    if crud_class.__name__ == 'TickCRUD':
        try:
            before_count = len(crud_obj.find(filters=filters))
        except Exception as e:
            # 表不存在时跳过清理
            if "Unknown table" in str(e):
                before_count = 0
            else:
                raise
    else:
        before_count = len(crud_obj.find(filters=filters))

    if before_count > 0:
        print(f"\n🧹 Pre-test cleanup for {crud_class.__name__}: {before_count} records found")

        async_cleanup_with_wait(
            crud_obj,
            filters,
            f"{crud_class.__name__} test data (pre-test)"
        )

        # 对 TickCRUD 使用更安全的表检查
        if crud_class.__name__ == 'TickCRUD':
            try:
                after_count = len(crud_obj.find(filters=filters))
            except Exception as e:
                if "Unknown table" in str(e):
                    after_count = 0
                else:
                    raise
        else:
            after_count = len(crud_obj.find(filters=filters))

        if after_count == 0:
            print(f"✓ Pre-test cleanup successful: {before_count} → 0 records (deleted {before_count} records)")
        else:
            print(f"⚠️ Pre-test cleanup partial: {before_count} → {after_count} records (deleted {before_count - after_count} records)")
    else:
        print(f"✓ No {crud_class.__name__} test data to clean (pre-test)")

    yield  # 执行测试

    # Teardown：测试后清理本次测试数据并验证
    # 对 TickCRUD 使用更安全的表检查
    if crud_class.__name__ == 'TickCRUD':
        try:
            before_count = len(crud_obj.find(filters=filters))
        except Exception as e:
            if "Unknown table" in str(e):
                before_count = 0
            else:
                raise
    else:
        before_count = len(crud_obj.find(filters=filters))

    if before_count > 0:
        print(f"\n🧹 Post-test cleanup for {crud_class.__name__}: {before_count} records found")

        async_cleanup_with_wait(
            crud_obj,
            filters,
            f"{crud_class.__name__} test data (post-test)"
        )

        # 对 TickCRUD 使用更安全的表检查
        if crud_class.__name__ == 'TickCRUD':
            try:
                after_count = len(crud_obj.find(filters=filters))
            except Exception as e:
                if "Unknown table" in str(e):
                    after_count = 0
                else:
                    raise
        else:
            after_count = len(crud_obj.find(filters=filters))

        if after_count == 0:
            print(f"✓ Post-test cleanup successful: {before_count} → 0 records (deleted {before_count} records)")
        else:
            print(f"⚠️ Post-test cleanup partial: {before_count} → {after_count} records (deleted {before_count - after_count} records)")
    else:
        print(f"✓ No {crud_class.__name__} test data to clean (post-test)")

    # 特殊处理：TickCRUD 使用模块级清理，这里跳过
    if crud_class.__name__ == 'TickCRUD':
        print(f"⏭️ Skipping TickCRUD cleanup (handled by module-level fixture)")
        return


@pytest.fixture(scope="module", autouse=True)
def tick_crud_module_cleanup(request):
    """
    模块级别的TickCRUD清理fixture

    只在整个测试模块开始前和结束后各清理一次，提高性能。
    适用于TickCRUD这种需要动态创建表的测试场景。
    """
    # 检查模块是否包含TickCRUD测试
    if not hasattr(request.module, '__dict__'):
        yield
        return

    # 检查模块中是否有TickCRUD的引用
    module_content = str(request.module.__dict__.values())
    if 'TickCRUD' not in module_content:
        yield
        return

    # 导入TickCRUD
    try:
        from ginkgo.data.crud.tick_crud import TickCRUD
    except ImportError:
        yield
        return

    print(f"\n🧹 Module-level TickCRUD cleanup for {request.module.__name__}")

    # 模块开始前清理
    try:
        tick_crud = TickCRUD()
        deleted_tables = tick_crud.drop_all_test_tables()
        if deleted_tables > 0:
            print(f"✓ Pre-module cleanup: removed {deleted_tables} test tables")
    except Exception as e:
        print(f"⚠️ Pre-module cleanup failed: {e}")

    yield

    # 模块结束后清理
    try:
        tick_crud = TickCRUD()
        deleted_tables = tick_crud.drop_all_test_tables()
        if deleted_tables > 0:
            print(f"✓ Post-module cleanup: removed {deleted_tables} test tables")
    except Exception as e:
        print(f"⚠️ Post-module cleanup failed: {e}")


@pytest.fixture(scope="function", autouse=True)
def auto_clean_test_data(request):
    """
    通用智能清理fixture：根据@pytest.mark.db_cleanup标记自动清理数据库

    使用方式：
    1. 在测试类上添加 @pytest.mark.db_cleanup 标记
    2. 定义 CLEANUP_CONFIG 类变量指定清理规则

    配置示例：
        @pytest.mark.db_cleanup
        class TestSomething:
            # 单个CRUD清理
            CLEANUP_CONFIG = {
                'bar': {'code__like': 'TEST_HIST_%'}
            }

            # 多个CRUD + 不同字段
            CLEANUP_CONFIG = {
                'bar': {'code__like': 'TEST_%'},
                'order': {'portfolio_id__like': 'TEST_PORT_%'},
                'position': {'symbol__like': 'TEST_%', 'status': 1}
            }

    清理策略：
    - Setup阶段：清理可能残留的测试数据
    - Teardown阶段：清理本次测试产生的数据
    """
    # 检查是否需要清理
    needs_cleanup = request.node.get_closest_marker("db_cleanup") is not None
    if not needs_cleanup:
        yield
        return

    # 获取清理配置
    cleanup_config = getattr(request.cls, 'CLEANUP_CONFIG', None)
    if not cleanup_config:
        warnings.warn(
            f"{request.cls.__name__} 使用了 @pytest.mark.db_cleanup "
            f"但未定义 CLEANUP_CONFIG，跳过数据库清理。"
            f"请添加 CLEANUP_CONFIG 类变量指定清理规则。"
        )
        yield
        return

    # 延迟导入CRUD类（避免循环导入）
    from ginkgo.data.crud.bar_crud import BarCRUD
    try:
        from ginkgo.data.crud.tick_crud import TickCRUD
    except ImportError:
        TickCRUD = None
    try:
        from ginkgo.data.crud.order_crud import OrderCRUD
    except ImportError:
        OrderCRUD = None
    try:
        from ginkgo.data.crud.position_crud import PositionCRUD
    except ImportError:
        PositionCRUD = None
    try:
        from ginkgo.data.crud.signal_tracker_crud import SignalTrackerCRUD
    except ImportError:
        SignalTrackerCRUD = None
    try:
        from ginkgo.data.crud.param_crud import ParamCRUD
    except ImportError:
        ParamCRUD = None
    try:
        from ginkgo.data.crud.file_crud import FileCRUD
    except ImportError:
        FileCRUD = None
    try:
        from ginkgo.data.crud.portfolio_crud import PortfolioCRUD
    except ImportError:
        PortfolioCRUD = None

    crud_map = {
        'bar': BarCRUD,
        'tick': TickCRUD,
        'order': OrderCRUD,
        'position': PositionCRUD,
        'signal_tracker': SignalTrackerCRUD,
        'param': ParamCRUD,
        'file': FileCRUD,
        'portfolio': PortfolioCRUD,
    }

    # 清理函数
    def do_cleanup():
        for crud_type, filters in cleanup_config.items():
            crud_class = crud_map.get(crud_type)
            if crud_class is None:
                warnings.warn(f"CRUD类型 '{crud_type}' 不可用，跳过清理")
                continue
            try:
                crud_class().remove(filters=filters)
            except Exception as e:
                warnings.warn(f"清理 {crud_type} 数据失败: {e}")

    # Setup：测试前清理残留数据
    do_cleanup()

    yield

    # Teardown：测试后清理本次测试数据
    do_cleanup()


# ===== Mock数据源fixtures =====

@pytest.fixture(scope="session", autouse=True)
def mock_tushare_data_source():
    """
    全局Mock Tushare数据源fixture

    使用patch自动替换GinkgoTushare类实例化，让所有调用GinkgoTushare()的地方
    都返回MockGinkgoTushare实例，无需手动设置data_source属性。
    """
    try:
        # 导入Mock数据源和patch工具
        import sys
        import os
        _path_to_add = os.path.join(os.path.dirname(__file__), 'fixtures')
        if _path_to_add not in sys.path:
            sys.path.insert(0, _path_to_add)

        from unittest.mock import patch
        from mock_data.mock_ginkgo_tushare import MockGinkgoTushare

        # 使用patch自动替换GinkgoTushare类 - 修复导入路径
        with patch('ginkgo.data.sources.GinkgoTushare', MockGinkgoTushare):
            print("✅ 全局Mock数据源已启用 - 自动patch GinkgoTushare类")
            yield

    except ImportError as e:
        print(f"⚠️ Mock数据源导入失败，使用真实数据源: {e}")
        yield
    except Exception as e:
        print(f"⚠️ Mock数据源patch失败，使用真实数据源: {e}")
        yield
