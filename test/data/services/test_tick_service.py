"""
TickService数据服务TDD测试

通过TDD方式开发TickService的完整测试套件
覆盖数据查询、复权、同步和数据库CRUD操作
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, date
import pandas as pd

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.services.tick_service import TickService
from ginkgo.data.services.base_service import BaseService
from ginkgo.data.containers import container
from ginkgo.enums import ADJUSTMENT_TYPES


@pytest.mark.unit
class TestTickServiceConstruction:
    """1. 构造和初始化测试"""

    def test_tick_service_initialization(self):
        """
        测试TickService基本初始化

        评审不足：
        - 在测试方法内进行import，应该移到文件顶部
        - 依赖创建较复杂，可能可以考虑使用mock
        """
        from ginkgo.data.sources.ginkgo_tdx import GinkgoTDX
        from ginkgo.data.services.stockinfo_service import StockinfoService
        from ginkgo.data.crud.stock_info_crud import StockInfoCRUD
        from ginkgo.data.sources.ginkgo_tushare import GinkgoTushare

        data_source = GinkgoTDX()
        stockinfo_service = StockinfoService(
            crud_repo=StockInfoCRUD(),
            data_source=GinkgoTushare()
        )

        from ginkgo.data.crud.tick_crud import TickCRUD
        tick_service = TickService(
            crud_repo=TickCRUD(),
            data_source=data_source,
            stockinfo_service=stockinfo_service
        )

        assert isinstance(tick_service, TickService)
        assert isinstance(tick_service, BaseService)
        assert hasattr(tick_service, '_logger')
        assert tick_service._data_source is data_source
        assert tick_service._stockinfo_service is stockinfo_service


@pytest.mark.database
@pytest.mark.db_cleanup
class TestTickServiceSyncMethods:
    """2. 同步方法测试"""

    CLEANUP_CONFIG = {
        'tick': {'code': '000001.SZ'}
    }

    def test_sync_date_data_increment(self):
        """
        测试sync_date数据增量

        评审不足：
        - 这是一个集成测试而非纯单元测试，更适合作为集成测试
        - 测试执行时间可能较长
        - 在测试方法内进行大量重复的依赖创建代码
        """
        from ginkgo.data.services.tick_service import TickService
        from ginkgo.data.services.stockinfo_service import StockinfoService
        from ginkgo.data.crud.stock_info_crud import StockInfoCRUD
        from ginkgo.data.sources.ginkgo_tushare import GinkgoTushare
        from ginkgo.data.sources.ginkgo_tdx import GinkgoTDX

        # 正确初始化依赖
        tushare_source = GinkgoTushare()
        tdx_source = GinkgoTDX()
        stockinfo_service = StockinfoService(
            crud_repo=StockInfoCRUD(),
            data_source=tushare_source
        )
        from ginkgo.data.crud.tick_crud import TickCRUD
        tick_service = TickService(
            crud_repo=TickCRUD(),
            data_source=tdx_source,
            stockinfo_service=stockinfo_service
        )

        test_date = datetime(2024, 1, 2)

        # 同步前检查表内数据数量
        before_count = len(tick_service._crud_repo.find({
            "code": "000001.SZ",
            "timestamp__gte": test_date,
            "timestamp__lte": test_date.replace(hour=23, minute=59, second=59)
        }))

        # 执行同步
        result = tick_service.sync_date("000001.SZ", test_date)
        assert result.success, f"同步失败: {result.message}"

        # 同步后检查表内数据数量
        after_count = len(tick_service._crud_repo.find({
            "code": "000001.SZ",
            "timestamp__gte": test_date,
            "timestamp__lte": test_date.replace(hour=23, minute=59, second=59)
        }))

        # 验证数据确实增加了
        assert after_count > before_count, f"同步后数据应该增加，但同步前:{before_count}, 同步后:{after_count}"

        increment = after_count - before_count
        assert increment > 0, f"应该新增数据，实际新增: {increment}"
        print(f"✅ sync_date成功，新增了 {increment} 条tick数据")

    def test_sync_range_date_range(self):
        """
        测试sync_range日期范围同步

        评审不足：
        - 测试覆盖有限：只测试了单日范围，没有测试真正的多日范围
        - 缺少数据增量验证：没有验证同步前后的数据变化
        - 与前一个测试有大量重复的依赖创建代码
        """
        from ginkgo.data.services.tick_service import TickService
        from ginkgo.data.services.stockinfo_service import StockinfoService
        from ginkgo.data.crud.stock_info_crud import StockInfoCRUD
        from ginkgo.data.sources.ginkgo_tushare import GinkgoTushare
        from ginkgo.data.sources.ginkgo_tdx import GinkgoTDX

        # 初始化依赖
        tushare_source = GinkgoTushare()
        tdx_source = GinkgoTDX()
        stockinfo_service = StockinfoService(
            crud_repo=StockInfoCRUD(),
            data_source=tushare_source
        )
        from ginkgo.data.crud.tick_crud import TickCRUD
        tick_service = TickService(
            crud_repo=TickCRUD(),
            data_source=tdx_source,
            stockinfo_service=stockinfo_service
        )

        # 日期范围同步
        start_date = datetime(2024, 1, 2)
        end_date = datetime(2024, 1, 3)  # 结束日期应该晚于开始日期

        result = tick_service.sync_range("000001.SZ", start_date, end_date)
        assert result.success, f"范围同步失败: {result.message}"
        print(f"✅ sync_range验证成功")

    def test_sync_batch_multiple_codes(self):
        """
        测试sync_batch多股票同步

        评审不足：
        - 缺少详细的验证：没有验证每个股票的同步结果
        - 没有测试部分成功的情况（如某个股票同步失败）
        - 同样存在大量重复的依赖创建代码
        """
        from ginkgo.data.services.tick_service import TickService
        from ginkgo.data.services.stockinfo_service import StockinfoService
        from ginkgo.data.crud.stock_info_crud import StockInfoCRUD
        from ginkgo.data.sources.ginkgo_tushare import GinkgoTushare
        from ginkgo.data.sources.ginkgo_tdx import GinkgoTDX

        # 初始化依赖
        tushare_source = GinkgoTushare()
        tdx_source = GinkgoTDX()
        stockinfo_service = StockinfoService(
            crud_repo=StockInfoCRUD(),
            data_source=tushare_source
        )
        from ginkgo.data.crud.tick_crud import TickCRUD
        tick_service = TickService(
            crud_repo=TickCRUD(),
            data_source=tdx_source,
            stockinfo_service=stockinfo_service
        )

        test_codes = ["000001.SZ", "000002.SZ"]
        test_date = datetime(2024, 1, 2)

        # 批量同步
        batch_result = tick_service.sync_batch(
            codes=test_codes,
            start_date=test_date,
            end_date=test_date
        )
        assert batch_result.success, f"批量同步失败: {batch_result.message}"
        print(f"✅ sync_batch验证成功")

    def test_sync_smart_functionality(self):
        """
        测试sync_smart智能同步

        评审不足：
        - 测试相对简单，只验证了执行成功，没有验证智能逻辑
        - 缺少对智能同步策略的验证（如自动选择同步日期范围）
        - 没有测试边界情况（如max_backtrack_days=0或负数）
        """
        from ginkgo.data.services.tick_service import TickService
        from ginkgo.data.services.stockinfo_service import StockinfoService
        from ginkgo.data.crud.stock_info_crud import StockInfoCRUD
        from ginkgo.data.sources.ginkgo_tushare import GinkgoTushare
        from ginkgo.data.sources.ginkgo_tdx import GinkgoTDX

        # 初始化依赖
        tushare_source = GinkgoTushare()
        tdx_source = GinkgoTDX()
        stockinfo_service = StockinfoService(
            crud_repo=StockInfoCRUD(),
            data_source=tushare_source
        )
        from ginkgo.data.crud.tick_crud import TickCRUD
        tick_service = TickService(
            crud_repo=TickCRUD(),
            data_source=tdx_source,
            stockinfo_service=stockinfo_service
        )

        # 智能同步
        result = tick_service.sync_smart("000001.SZ", max_backtrack_days=7)
        assert result.success, f"智能同步失败: {result.message}"
        print(f"✅ sync_smart验证成功")


@pytest.mark.database
@pytest.mark.db_cleanup
class TestTickServiceGet:
    """3. 查询方法测试"""

    CLEANUP_CONFIG = {
        'tick': {'code': '000001.SZ'}
    }

    def test_get_after_sync_increment(self):
        """
        测试get方法 - 同步前后数据对比

        评审不足：
        - 测试方法较长，逻辑相对复杂，但覆盖完整
        - 无明显不足，设计合理
        """
        from ginkgo.data.services.tick_service import TickService
        from ginkgo.data.services.stockinfo_service import StockinfoService
        from ginkgo.data.crud.stock_info_crud import StockInfoCRUD
        from ginkgo.data.sources.ginkgo_tushare import GinkgoTushare
        from ginkgo.data.sources.ginkgo_tdx import GinkgoTDX

        data_source = GinkgoTDX()
        stockinfo_service = StockinfoService(
            crud_repo=StockInfoCRUD(),
            data_source=GinkgoTushare()
        )
        from ginkgo.data.crud.tick_crud import TickCRUD
        tick_service = TickService(
            crud_repo=TickCRUD(),
            data_source=data_source,
            stockinfo_service=stockinfo_service
        )

        test_date = datetime(2024, 1, 2)

        # 同步前get查询 - 使用更宽的时间范围
        get_before = tick_service.get(code="000001.SZ", start_date=test_date, end_date=test_date.replace(hour=23, minute=59, second=59))
        before_records = len(get_before.data) if get_before.success and get_before.data else 0

        # 同步数据
        sync_result = tick_service.sync_date("000001.SZ", test_date)
        assert sync_result.success, f"数据同步失败: {sync_result.message}"

        # 同步后get查询 - 使用相同的时间范围
        get_after = tick_service.get(code="000001.SZ", start_date=test_date, end_date=test_date.replace(hour=23, minute=59, second=59))
        assert get_after.success, f"同步后get查询失败: {get_after.message}"
        assert get_after.data is not None, "同步后data不能为空"

        after_records = len(get_after.data)

        # 验证数据增加
        assert after_records > before_records, f"get查询返回数据应该增加，同步前:{before_records}, 同步后:{after_records}"

        # 验证数据结构 - ModelList功能
        model_list = get_after.data
        assert hasattr(model_list, 'to_dataframe'), "ModelList应该有to_dataframe方法"
        assert hasattr(model_list, 'to_entities'), "ModelList应该有to_entities方法"

        # 验证to_dataframe方法
        df = model_list.to_dataframe()
        assert isinstance(df, pd.DataFrame), "应该能转换为DataFrame"
        assert len(df) == after_records, "DataFrame记录数应该匹配"

        # 验证to_entities方法
        entities = model_list.to_entities()
        assert isinstance(entities, list), "应该能转换为实体列表"
        assert len(entities) == after_records, "实体列表记录数应该匹配"

        # 验证实体属性
        if entities:  # 如果有数据
            first_entity = entities[0]
            assert hasattr(first_entity, 'code'), "Tick实体应该有code属性"
            assert hasattr(first_entity, 'timestamp'), "Tick实体应该有timestamp属性"
            assert hasattr(first_entity, 'price'), "Tick实体应该有price属性"

        print(f"✅ get方法验证成功，记录数: {before_records} → {after_records}")
        print(f"✅ ModelList方法验证成功 - to_dataframe: {len(df)}行, to_entities: {len(entities)}个实体")

    def test_get_price_adjustment(self):
        """
        测试get方法价格调整功能

        评审不足：
        - 测试相对简单，只验证了查询成功，没有验证复权计算的正确性
        - 没有对比不同复权类型的价格差异
        - 缺少对复权结果数据结构的验证
        """
        from ginkgo.data.services.tick_service import TickService
        from ginkgo.data.services.stockinfo_service import StockinfoService
        from ginkgo.data.crud.stock_info_crud import StockInfoCRUD
        from ginkgo.data.sources.ginkgo_tushare import GinkgoTushare
        from ginkgo.data.sources.ginkgo_tdx import GinkgoTDX

        data_source = GinkgoTDX()
        stockinfo_service = StockinfoService(
            crud_repo=StockInfoCRUD(),
            data_source=GinkgoTushare()
        )
        from ginkgo.data.crud.tick_crud import TickCRUD
        tick_service = TickService(
            crud_repo=TickCRUD(),
            data_source=data_source,
            stockinfo_service=stockinfo_service
        )

        test_date = datetime(2024, 1, 2)

        # 先同步数据
        sync_result = tick_service.sync_date("000001.SZ", test_date)
        if sync_result.success:
            # 测试价格调整查询
            get_adjusted = tick_service.get(
                code="000001.SZ",
                start_date=test_date,
                end_date=test_date,
                adjustment_type=ADJUSTMENT_TYPES.FORE
            )
            assert get_adjusted.success, f"价格调整查询失败: {get_adjusted.message}"
            print(f"✅ get价格调整验证成功")


@pytest.mark.database
@pytest.mark.db_cleanup
class TestTickServiceCount:
    """4. 计数方法测试"""

    CLEANUP_CONFIG = {
        'tick': {'code': '000001.SZ'}
    }

    def test_count_data_increment(self):
        """
        测试count方法 - 同步前后计数对比

        评审不足：
        - 与其他测试有重复的依赖创建代码，但在当前结构下是合理的
        - 测试设计简洁有效，无明显不足
        """
        from ginkgo.data.services.tick_service import TickService
        from ginkgo.data.services.stockinfo_service import StockinfoService
        from ginkgo.data.crud.stock_info_crud import StockInfoCRUD
        from ginkgo.data.sources.ginkgo_tushare import GinkgoTushare
        from ginkgo.data.sources.ginkgo_tdx import GinkgoTDX

        # 正确初始化依赖
        tushare_source = GinkgoTushare()
        tdx_source = GinkgoTDX()
        stockinfo_service = StockinfoService(
            crud_repo=StockInfoCRUD(),
            data_source=tushare_source
        )
        from ginkgo.data.crud.tick_crud import TickCRUD
        tick_service = TickService(
            crud_repo=TickCRUD(),
            data_source=tdx_source,
            stockinfo_service=stockinfo_service
        )

        test_date = datetime(2024, 1, 2)

        # 同步前计数
        count_before = tick_service.count(code="000001.SZ", date=test_date)
        assert count_before.success, f"同步前count失败: {count_before.message}"
        before_records = count_before.data if count_before.data else 0

        # 同步数据
        sync_result = tick_service.sync_date("000001.SZ", test_date)
        assert sync_result.success, f"数据同步失败: {sync_result.message}"

        # 同步后计数
        count_after = tick_service.count(code="000001.SZ", date=test_date)
        assert count_after.success, f"同步后count失败: {count_after.message}"
        after_records = count_after.data

        # 验证计数增加
        assert after_records > before_records, f"count应该增加，同步前:{before_records}, 同步后:{after_records}"
        assert isinstance(after_records, int), "count应该返回整数"

        print(f"✅ count方法验证成功，记录数: {before_records} → {after_records}")


@pytest.mark.database
@pytest.mark.db_cleanup
class TestTickServiceDataValidation:
    """5. 数据验证测试"""

    CLEANUP_CONFIG = {
        'tick': {'code': '000001.SZ'}
    }

    def test_validate_data_quality(self):
        """
        测试数据质量验证

        评审不足：
        - 测试相对基础，没有验证具体的质量评分逻辑
        - 没有测试不同质量数据场景（如低质量数据）
        - 缺少对验证失败场景的测试
        """
        from ginkgo.data.services.tick_service import TickService
        from ginkgo.data.services.stockinfo_service import StockinfoService
        from ginkgo.data.crud.stock_info_crud import StockInfoCRUD
        from ginkgo.data.sources.ginkgo_tushare import GinkgoTushare
        from ginkgo.data.sources.ginkgo_tdx import GinkgoTDX

        # 初始化依赖
        tushare_source = GinkgoTushare()
        tdx_source = GinkgoTDX()
        stockinfo_service = StockinfoService(
            crud_repo=StockInfoCRUD(),
            data_source=tushare_source
        )
        from ginkgo.data.crud.tick_crud import TickCRUD
        tick_service = TickService(
            crud_repo=TickCRUD(),
            data_source=tdx_source,
            stockinfo_service=stockinfo_service
        )

        # 同步数据
        sync_result = tick_service.sync_date("000001.SZ", datetime(2024, 1, 2))
        assert sync_result.success

        # 验证数据质量
        # 先获取数据，然后验证数据质量
        from ginkgo.data.crud.tick_crud import TickCRUD
        tick_crud = TickCRUD()
        tick_data = tick_crud.find(filters={"code": "000001.SZ"})

        validation_result = tick_service.validate(tick_data)
        assert validation_result.success, f"验证失败: {validation_result.message}"
        assert hasattr(validation_result.data, 'is_valid'), "应该返回验证结果"
        assert hasattr(validation_result.data, 'data_quality_score'), "应该包含质量评分"
        print(f"✅ validate验证成功")

    def test_check_integrity_completeness(self):
        """
        测试数据完整性检查

        评审不足：
        - 测试相对基础，没有测试不同完整性场景
        - 没有同步数据就直接检查完整性，可能缺少数据基础
        - 缺少对完整性评分逻辑的验证
        """
        from ginkgo.data.services.tick_service import TickService
        from ginkgo.data.services.stockinfo_service import StockinfoService
        from ginkgo.data.crud.stock_info_crud import StockInfoCRUD
        from ginkgo.data.sources.ginkgo_tushare import GinkgoTushare
        from ginkgo.data.sources.ginkgo_tdx import GinkgoTDX

        # 初始化依赖
        tushare_source = GinkgoTushare()
        tdx_source = GinkgoTDX()
        stockinfo_service = StockinfoService(
            crud_repo=StockInfoCRUD(),
            data_source=tushare_source
        )
        from ginkgo.data.crud.tick_crud import TickCRUD
        tick_service = TickService(
            crud_repo=TickCRUD(),
            data_source=tdx_source,
            stockinfo_service=stockinfo_service
        )

        # 完整性检查
        integrity_result = tick_service.check_integrity(
            "000001.SZ",
            datetime(2024, 1, 2),
            datetime(2024, 1, 2)
        )
        assert integrity_result.success, f"完整性检查失败: {integrity_result.message}"
        assert hasattr(integrity_result.data, 'integrity_score'), "应该包含完整性评分"
        # DataIntegrityCheckResult使用is_healthy()方法而不是is_integrity_passed属性
        assert hasattr(integrity_result.data, 'is_healthy'), "应该包含健康状态检查"
        print(f"✅ check_integrity验证成功")


@pytest.mark.unit
class TestTickServiceErrorHandling:
    """6. 错误处理测试"""

    def test_invalid_code_handling(self):
        """
        测试无效股票代码的错误处理

        评审不足：
        - 测试设计合理，覆盖了核心错误处理逻辑
        - 可以增加更多边界情况测试（如None值、特殊字符等）
        - 无明显不足，设计优秀
        """
        from ginkgo import service_hub

        # 使用真实的服务实例，会自动检查股票列表
        tick_service = service_hub.data.tick_service()

        # 测试get空代码 - 这个是BaseService级别的验证
        result = tick_service.get(code="")
        assert result.success == False, "应该失败"
        assert "required" in result.message.lower(), "错误信息应该提到必需"

        # 测试count空代码 - 这个也是BaseService级别的验证
        result = tick_service.count(code="")
        assert result.success == False, "应该失败"
        assert "required" in result.message.lower(), "错误信息应该提到必需"

        print(f"✅ 错误处理验证成功")


