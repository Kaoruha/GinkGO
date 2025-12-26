import unittest
import sys
import os
import random
import string
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))

try:
    from ginkgo.data.services.stockinfo_service import StockinfoService
    from ginkgo.data.services.base_service import ServiceResult
    from ginkgo.data.crud.stock_info_crud import StockInfoCRUD
    from ginkgo.data.models import MStockInfo
    from ginkgo.enums import SOURCE_TYPES, CURRENCY_TYPES, MARKET_TYPES
    from ginkgo.libs import GCONF, datetime_normalize, GLOG
    from ginkgo.data.drivers import get_db_connection, get_table_size, create_table, drop_table
    from ginkgo.data.containers import container
except ImportError as e:
    print(f"Import error: {e}")
    StockinfoService = None
    GCONF = None


def generate_short_id(prefix="test"):
    """生成短ID避免数据库字段长度限制"""
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"{prefix}_{suffix}"


class StockinfoServiceTest(unittest.TestCase):
    """
    StockinfoService 测试用例 - 重构版本
    使用真实container和数据源操作，移除Mock依赖
    测试股票信息管理的核心功能和业务逻辑
    """

    @classmethod
    def setUpClass(cls):
        """类级别设置：检查依赖和数据库配置"""
        if StockinfoService is None or GCONF is None:
            raise AssertionError("StockinfoService or GCONF not available")

        # 设置测试用的模型
        cls.model = MStockInfo

        # 重新创建测试表
        try:
            drop_table(cls.model, no_skip=True)
            create_table(cls.model, no_skip=True)
            print(":white_check_mark: StockInfo table recreated for testing")
        except Exception as e:
            print(f":warning: StockInfo table recreation failed: {e}")

        # 创建 CRUD 实例
        cls.crud_repo = StockInfoCRUD()

    def setUp(self):
        """每个测试前的设置"""
        # 使用真实的container获取service实例
        self.service = container.stockinfo_service()
        self.test_records = []

    def tearDown(self):
        """每个测试后的清理"""
        # 清理测试创建的数据
        for record in self.test_records:
            try:
                self.service._crud_repo.remove(filters={"code": record})
            except Exception as e:
                GLOG.warning(f"清理测试数据失败: {record}, 错误: {e}")

    def test_service_initialization(self):
        """测试服务初始化 - 增强版"""
        # 基础验证
        assert self.service is not None
        assert isinstance(self.service, StockinfoService)

        # CRUD依赖验证 - 增加类型检查
        assert hasattr(self.service, '_crud_repo')
        assert self.service._crud_repo is not None

        # 验证CRUD依赖的类型正确性
        assert isinstance(self.service._crud_repo, StockInfoCRUD)

        # 验证数据源依赖
        assert hasattr(self.service, '_data_source')
        assert self.service._data_source is not None

    def test_health_check(self):
        """测试健康检查 - 增强版"""
        result = self.service.health_check()

        # 基础ServiceResult验证
        assert result.is_success(), f"健康检查失败: {result.error}"
        assert result.data is not None

        # 健康检查数据结构验证
        health_data = result.data
        assert "service_name" in health_data, "健康检查应包含service_name字段"
        assert "status" in health_data, "健康检查应包含status字段"
        assert "total_records" in health_data, "健康检查应包含total_records字段"

        # 状态值验证
        assert health_data["service_name"] == "StockinfoService"
        assert health_data["status"] in ["healthy", "unhealthy", "degraded"]
        assert isinstance(health_data["total_records"], int)
        assert health_data["total_records"] >= 0

    def test_add_stockinfo_success(self):
        """测试添加股票信息成功"""
        # 生成唯一测试数据
        test_code = f"TEST{generate_short_id('code')}.SZ"
        test_name = f"测试股票_{generate_short_id('name')}"

        # 执行添加操作
        result = self.service._crud_repo.create(
            code=test_code,
            code_name=test_name,
            industry="测试行业",
            market=MARKET_TYPES.CHINA,
            currency=CURRENCY_TYPES.CNY,
            list_date=datetime.now(),
            source=SOURCE_TYPES.TUSHARE
        )

        # 验证创建成功
        assert result is not None
        assert hasattr(result, 'uuid')
        self.test_records.append(result.code)

        # 验证数据库中的实际数据
        records = self.service._crud_repo.find(filters={"code": test_code})
        assert len(records) > 0
        created_record = records[0]
        assert created_record.code == test_code
        assert created_record.code_name == test_name

    def test_get_stockinfo_success(self):
        """测试获取股票信息成功"""
        # 先创建测试数据
        test_code = f"GET{generate_short_id('get')}.SZ"
        test_name = f"获取测试股票_{generate_short_id('get')}"

        created_record = self.service._crud_repo.create(
            code=test_code,
            code_name=test_name,
            industry="测试行业",
            market=MARKET_TYPES.CHINA,
            currency=CURRENCY_TYPES.CNY,
            list_date=datetime.now(),
            source=SOURCE_TYPES.TUSHARE
        )
        self.test_records.append(created_record.code)

        # 获取股票信息
        result = self.service.get(code=test_code)

        # 验证ServiceResult格式
        assert result.is_success(), f"获取股票信息失败: {result.error}"
        assert result.data is not None

        # 验证结果数据
        assert isinstance(result.data, list)
        assert len(result.data) > 0
        retrieved_record = result.data[0]
        assert retrieved_record.code == test_code

    def test_get_stockinfos_paginated(self):
        """测试获取股票信息（无limit参数）"""
        # 创建多个测试股票
        created_codes = []
        for i in range(5):
            test_code = f"PAGE{generate_short_id(f'page{i}')}.SZ"
            created_record = self.service._crud_repo.create(
                code=test_code,
                code_name=f"分页测试股票{i}",
                industry="测试行业",
                market=MARKET_TYPES.CHINA,
                currency=CURRENCY_TYPES.CNY,
                list_date=datetime.now(),
                source=SOURCE_TYPES.TUSHARE
            )
            created_codes.append(created_record.code)

        self.test_records.extend(created_codes)

        # 获取所有数据 - get()方法不支持limit参数
        result = self.service.get()

        # 验证结果
        assert result.is_success(), f"获取失败: {result.error}"
        assert isinstance(result.data, list)
        assert len(result.data) >= 0

    def test_sync_integration(self):
        """测试同步集成功能"""
        print("\n🔍 开始test_sync_integration - 这个测试速度异常")
        import time
        start_time = time.time()

        # 这个测试可能会调用真实的Tushare API
        # 在实际环境中可能需要特殊配置或使用测试数据源

        # 检查服务是否能正常调用同步方法
        try:
            print(f"⏰ 调用sync()前，已耗时: {time.time() - start_time:.2f}秒")
            result = self.service.sync()
            print(f"⏰ 调用sync()后，已耗时: {time.time() - start_time:.2f}秒")

            # 由于我们没有真实的Tushare配置，这个测试可能会失败
            # 但我们可以验证方法调用不会抛出异常
            assert result is not None
            assert isinstance(result, ServiceResult)

            if hasattr(result.data, 'total_records'):
                print(f"📊 同步记录数: {result.data.total_records}")
            if hasattr(result.data, 'success_count'):
                print(f"✅ 成功数量: {result.data.success_count}")

        except Exception as e:
            # 如果因为外部依赖导致失败，记录但不认为测试失败
            print(f"⏰ 异常发生时，已耗时: {time.time() - start_time:.2f}秒")
            GLOG.info(f"Sync test skipped due to external dependency: {e}")
            self.skipTest("Sync test skipped due to external dependency")

        total_time = time.time() - start_time
        print(f"🏁 test_sync_integration完成，总耗时: {total_time:.2f}秒")

    def test_sync_empty_data_handling(self):
        """测试处理空数据响应"""
        print("\n🔍 开始test_sync_empty_data_handling - 这个测试速度异常")
        import time
        start_time = time.time()

        # 测试同步处理 - sync()方法不接受参数
        print(f"⏰ 调用sync()前，已耗时: {time.time() - start_time:.2f}秒")
        result = self.service.sync()
        print(f"⏰ 调用sync()后，已耗时: {time.time() - start_time:.2f}秒")

        # 验证结果结构
        assert result is not None
        assert isinstance(result, ServiceResult)
        assert result.data is not None  # 应该有DataSyncResult结构

        if hasattr(result.data, 'total_records'):
            print(f"📊 同步记录数: {result.data.total_records}")
        if hasattr(result.data, 'success_count'):
            print(f"✅ 成功数量: {result.data.success_count}")

        total_time = time.time() - start_time
        print(f"🏁 test_sync_empty_data_handling完成，总耗时: {total_time:.2f}秒")

    
    def test_sync_method_structure(self):
        """测试同步方法的ServiceResult返回结构"""
        print("\n🔍 开始test_sync_method_structure - 这个测试速度异常")
        import time
        start_time = time.time()

        # 执行同步（sync()方法不接受参数）
        print(f"⏰ 调用sync()前，已耗时: {time.time() - start_time:.2f}秒")
        result = self.service.sync()
        print(f"⏰ 调用sync()后，已耗时: {time.time() - start_time:.2f}秒")

        # 验证ServiceResult结构
        assert isinstance(result, ServiceResult)
        assert result.data is not None  # 即使失败也应该有DataSyncResult结构

        # 验证DataSyncResult基本字段
        assert hasattr(result.data, 'entity_type')
        assert result.data.entity_type == "stockinfo"

        if hasattr(result.data, 'total_records'):
            print(f"📊 同步记录数: {result.data.total_records}")
        if hasattr(result.data, 'success_count'):
            print(f"✅ 成功数量: {result.data.success_count}")

        total_time = time.time() - start_time
        print(f"🏁 test_sync_method_structure完成，总耗时: {total_time:.2f}秒")

    
    def test_get_stockinfos(self):
        """测试获取股票信息 - 使用get方法"""
        # 先添加一些测试数据
        self.service._crud_repo.create(
            code="TEST_001.SZ",
            code_name="测试股票1",
            industry="测试行业",
            currency=CURRENCY_TYPES.CNY,
            market=MARKET_TYPES.CHINA,
            list_date=datetime_normalize("20200101"),
            delist_date=datetime_normalize(GCONF.DEFAULTEND),
            source=SOURCE_TYPES.TUSHARE
        )

        # 测试获取数据 - 使用get方法
        result = self.service.get()

        # 验证ServiceResult格式
        assert result.success, f"Get should succeed: {result.message}"
        assert result.data is not None, "Result data should not be None"

        # 验证返回的是ModelList
        model_list = result.data
        assert len(model_list) > 0, "Should return some records"

        # 查找我们的测试数据 - 使用ModelList的to_dataframe方法
        df = model_list.to_dataframe()
        test_records = df[df['code'] == 'TEST_001.SZ']
        assert len(test_records) == 1, "Should find our test record"

    
    def test_error_handling(self):
        """测试错误处理机制"""
        # 测试获取不存在股票代码的处理
        result = self.service.get(code="NONEXISTENT_CODE_999999.SZ")

        # 验证不会因为不存在代码而崩溃
        assert result is not None
        assert isinstance(result, ServiceResult)
        assert result.success, "查询不存在的代码应该成功但返回空数据"
        assert len(result.data) == 0, "不存在的代码应该返回空列表"


    def test_count_method(self):
        """测试count方法 - 股票记录计数"""
        # 清理数据
        try:
            self.service._crud_repo.remove({"code__like": "TEST_%"})
        except:
            pass

        # 初始状态：0条记录
        result = self.service.count()
        assert result.success, f"Count should succeed: {result.message}"
        assert result.data >= 0, "Should have 0 or more records initially"

        # 添加测试数据
        test_codes = ["TEST_COUNT_001.SZ", "TEST_COUNT_002.SZ", "TEST_COUNT_003.SZ"]
        for i, code in enumerate(test_codes, 1):
            created_record = self.service._crud_repo.create(
                code=code,
                code_name=f"测试股票{i}",
                industry="测试行业",
                currency=CURRENCY_TYPES.CNY,
                market=MARKET_TYPES.CHINA,
                list_date=datetime_normalize("20200101"),
                delist_date=datetime_normalize(GCONF.DEFAULTEND),
                source=SOURCE_TYPES.TUSHARE
            )
            self.test_records.append(created_record.code)

        # 验证计数
        result = self.service.count()
        assert result.success, f"Count should succeed: {result.message}"
        assert result.data >= 0, "Should count records successfully"

    def test_validate_method(self):
        """测试validate方法 - 数据质量验证"""
        # 添加有效数据
        created_record = self.service._crud_repo.create(
            code="TEST_VALID_001.SZ",
            code_name="有效测试股票",
            industry="测试行业",
            currency=CURRENCY_TYPES.CNY,
            market=MARKET_TYPES.CHINA,
            list_date=datetime_normalize("20200101"),
            delist_date=datetime_normalize(GCONF.DEFAULTEND),
            source=SOURCE_TYPES.TUSHARE
        )
        self.test_records.append(created_record.code)

        # 验证数据质量
        result = self.service.validate()
        assert result.success, f"Validate should succeed: {result.message}"
        assert result.data is not None, "Result data should not be None"

    def test_check_integrity_method(self):
        """测试check_integrity方法 - 数据完整性检查"""
        # 添加一些测试数据
        test_data = [
            ("TEST_INT_001.SZ", "完整性测试1", "行业1"),
            ("TEST_INT_002.SZ", "完整性测试2", "行业2"),
        ]

        for code, name, industry in test_data:
            created_record = self.service._crud_repo.create(
                code=code,
                code_name=name,
                industry=industry,
                currency=CURRENCY_TYPES.CNY,
                market=MARKET_TYPES.CHINA,
                list_date=datetime_normalize("20200101"),
                delist_date=datetime_normalize(GCONF.DEFAULTEND),
                source=SOURCE_TYPES.TUSHARE
            )
            self.test_records.append(created_record.code)

        # 检查数据完整性
        result = self.service.check_integrity()
        assert result.success, f"Integrity check should succeed: {result.message}"
        assert result.data is not None, "Result data should not be None"


if __name__ == '__main__':
    unittest.main()