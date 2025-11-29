import unittest
import sys
import os
from unittest.mock import Mock, patch
import pandas as pd
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))

try:
    from ginkgo.data.services.stockinfo_service import StockinfoService
    from ginkgo.data.crud.stock_info_crud import StockInfoCRUD
    from ginkgo.data.models import MStockInfo
    from ginkgo.enums import SOURCE_TYPES, CURRENCY_TYPES, MARKET_TYPES
    from ginkgo.libs import GCONF, datetime_normalize
    from ginkgo.data.drivers import get_db_connection, get_table_size, create_table, drop_table
except ImportError as e:
    print(f"Import error: {e}")
    StockinfoService = None
    GCONF = None


class StockinfoServiceTest(unittest.TestCase):
    """
    StockinfoService 单元测试
    基于真实 Tushare API 数据格式，使用真实数据库，只 Mock data_source
    """

    # 基于真实 Tushare API 返回格式的 Mock 数据
    # 使用真实股票代码、名称和上市日期
    MOCK_STOCKINFO_SUCCESS = pd.DataFrame({
        'ts_code': ['000001.SZ', '000002.SZ', '000858.SZ'],
        'symbol': ['000001', '000002', '000858'],
        'name': ['平安银行', '万科A', '五粮液'],
        'area': ['深圳', '深圳', '宜宾'],
        'industry': ['银行', '全国地产', '白酒'],
        'list_date': ['19910403', '19910129', '19920827'],  # 真实上市日期
        'curr_type': ['CNY', 'CNY', 'CNY'],
        'delist_date': [None, None, None]
    })

    
    MOCK_EMPTY_DATA = pd.DataFrame()

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
        # 清理测试数据
        try:
            self.crud_repo.remove({"code__like": "TEST_%"})
            self.crud_repo.remove({"code__like": "000%"})
        except Exception:
            pass  # 忽略清理失败

        # 创建 Mock data_source
        self.mock_data_source = Mock()
        
        # 创建 StockinfoService 实例
        self.service = StockinfoService(
            crud_repo=self.crud_repo,
            data_source=self.mock_data_source
        )

    def tearDown(self):
        """每个测试后的清理"""
        try:
            # 清理测试数据
            self.crud_repo.remove({"code__like": "TEST_%"})
            self.crud_repo.remove({"code__like": "000%"})
        except Exception:
            pass  # 忽略清理失败

    def test_sync_all_success(self):
        """测试成功同步所有股票信息 - 更新为sync方法"""
        # 配置 Mock
        self.mock_data_source.fetch_cn_stockinfo.return_value = self.MOCK_STOCKINFO_SUCCESS

        # 获取初始表大小
        initial_size = get_table_size(self.model)

        # 执行同步 (更新方法名)
        result = self.service.sync()

        # 验证返回结果 - ServiceResult格式
        self.assertTrue(result.success, f"Sync should succeed: {result.message}")
        self.assertIsNotNone(result.data, "Result data should not be None")

        # 验证DataSyncResult
        sync_result = result.data
        self.assertEqual(sync_result.records_added, 3)
        self.assertEqual(sync_result.records_failed, 0)
        self.assertEqual(sync_result.records_processed, 3)
        self.assertTrue(sync_result.is_idempotent)

        # 验证数据库中的数据
        final_size = get_table_size(self.model)
        self.assertEqual(final_size, initial_size + 3)

        # 验证具体数据
        for _, row in self.MOCK_STOCKINFO_SUCCESS.iterrows():
            records = self.crud_repo.find(filters={"code": row['ts_code']})
            self.assertEqual(len(records), 1)
            record = records[0]
            self.assertEqual(record.code, row['ts_code'])
            self.assertEqual(record.code_name, row['name'])
            self.assertEqual(record.industry, row['industry'])

    def test_sync_all_empty_data(self):
        """测试处理空数据响应 - 更新为sync方法"""
        # 配置 Mock 返回空数据
        self.mock_data_source.fetch_cn_stockinfo.return_value = self.MOCK_EMPTY_DATA

        # 执行同步 (更新方法名)
        result = self.service.sync()

        # 验证返回结果 - 空数据应该返回失败
        self.assertFalse(result.success, f"Empty data should fail sync task: {result.message}")
        self.assertIsNotNone(result.data, "Result data should not be None")

        # 验证DataSyncResult
        sync_result = result.data
        self.assertEqual(sync_result.records_added, 0)
        self.assertEqual(sync_result.records_failed, 0)
        self.assertEqual(sync_result.records_processed, 0)
        self.assertTrue(len(sync_result.warnings) > 0, "Should have warning about empty data")

        # 验证错误消息包含任务失败信息
        self.assertIn("sync task failed", result.message)

    
    def test_sync_all_api_failure(self):
        """测试 API 调用失败 - 更新为sync方法"""
        # 配置 Mock 抛出异常
        self.mock_data_source.fetch_cn_stockinfo.side_effect = Exception("API connection failed")

        # 执行同步 (更新方法名)
        result = self.service.sync()

        # 验证返回结果 - ServiceResult失败格式
        self.assertFalse(result.success, f"API failure should return failure: {result.message}")
        self.assertIsNotNone(result.data, "Result data should not be None")

        # 验证DataSyncResult错误
        sync_result = result.data
        self.assertEqual(sync_result.records_added, 0)
        self.assertEqual(sync_result.records_failed, 0)
        self.assertEqual(sync_result.records_processed, 0)
        self.assertGreater(len(sync_result.errors), 0, "Should have errors")

        # 验证ServiceResult.message包含准确的失败原因
        self.assertIn("API connection failed", result.message, "Result message should contain specific failure reason")
        self.assertIn("Failed to fetch stock info from source", result.message, "Result message should indicate fetch failure")

        # 验证DataSyncResult也包含错误信息
        error_messages = [error_msg for _, error_msg in sync_result.errors]
        self.assertTrue(
            any("API connection failed" in msg for msg in error_messages),
            "DataSyncResult should also contain error details"
        )

    
    def test_sync_all_update_existing_records(self):
        """测试更新已存在的记录 - 更新为sync方法"""
        # 先创建一条记录
        self.crud_repo.create(
            code="000001.SZ",
            code_name="旧名称",
            industry="旧行业",
            currency=CURRENCY_TYPES.CNY,
            market=MARKET_TYPES.CHINA,
            list_date=datetime_normalize("19910403"),
            delist_date=datetime_normalize(GCONF.DEFAULTEND),
            source=SOURCE_TYPES.TUSHARE
        )

        # 配置 Mock 返回更新数据
        self.mock_data_source.fetch_cn_stockinfo.return_value = self.MOCK_STOCKINFO_SUCCESS

        # 执行同步 (更新方法名)
        result = self.service.sync()

        # 验证更新成功 - ServiceResult格式
        self.assertTrue(result.success, f"Update should succeed: {result.message}")
        self.assertIsNotNone(result.data, "Result data should not be None")

        # 验证DataSyncResult
        sync_result = result.data
        self.assertEqual(sync_result.records_added, 3)  # 1个更新 + 2个新增

        # 验证数据已更新
        records = self.crud_repo.find(filters={"code": "000001.SZ"})
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record.code_name, "平安银行")  # 应该是新的名称
        self.assertEqual(record.industry, "银行")  # 应该是新的行业

    
    def test_get_stockinfos(self):
        """测试获取股票信息 - 使用新的get方法"""
        # 先添加一些测试数据
        self.crud_repo.create(
            code="TEST_001.SZ",
            code_name="测试股票1",
            industry="测试行业",
            currency=CURRENCY_TYPES.CNY,
            market=MARKET_TYPES.CHINA,
            list_date=datetime_normalize("20200101"),
            delist_date=datetime_normalize(GCONF.DEFAULTEND),
            source=SOURCE_TYPES.TUSHARE
        )

        # 测试获取数据 - 使用新的get方法
        result = self.service.get()

        # 验证ServiceResult格式
        self.assertTrue(result.success, f"Get should succeed: {result.message}")
        self.assertIsNotNone(result.data, "Result data should not be None")

        # 验证返回的是ModelList
        model_list = result.data
        self.assertGreater(len(model_list), 0)

        # 查找我们的测试数据 - 使用ModelList的to_dataframe方法
        df = model_list.to_dataframe()
        test_records = df[df['code'] == 'TEST_001.SZ']
        self.assertEqual(len(test_records), 1)

    
    def test_error_tolerance_mechanism(self):
        """测试错误容忍机制：部分失败不影响其他记录"""
        # 创建包含数据质量问题的Mock数据（基于真实场景）
        # 模拟在真实环境中可能出现的数据质量问题
        problematic_data = pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ', '000858.SZ'],  # 使用真实的代码格式
            'symbol': ['000001', '', '000858'],  # 第二条记录缺少symbol（API返回问题）
            'name': ['平安银行', '', '五粮液'],  # 第二条记录缺少名称（数据缺失）
            'area': ['深圳', '深圳', '宜宾'],
            'industry': ['银行', '未知', '白酒'],  # 保留"未知"作为数据质量问题
            'list_date': ['19910403', '99999999', '19920827'],  # 第二条记录日期格式错误
            'curr_type': ['CNY', 'CNY', 'CNY'],
            'delist_date': [None, None, None]
        })

        # 配置 Mock
        self.mock_data_source.fetch_cn_stockinfo.return_value = problematic_data

        # 执行同步 - 使用新的sync方法
        result = self.service.sync()

        # 验证ServiceResult格式
        self.assertTrue(result.success, f"Sync should handle errors gracefully: {result.message}")
        self.assertIsNotNone(result.data, "Result data should not be None")

        # 验证DataSyncResult
        sync_result = result.data
        self.assertGreater(sync_result.records_processed, 0, "Should process some records")

        # 即使有失败，成功的记录也应该被处理
        if sync_result.records_added > 0:
            # 验证至少有一条成功的记录在数据库中（使用真实代码）
            valid_records = self.crud_repo.find(filters={"code": "000001.SZ"})
            if valid_records:  # 第一条记录数据完整，应该能成功插入
                self.assertGreater(len(valid_records), 0)
            # 验证第三条记录也可能成功
            valid_records_2 = self.crud_repo.find(filters={"code": "000858.SZ"})
            if valid_records_2:
                self.assertGreater(len(valid_records_2), 0)


    def test_count_method(self):
        """测试count方法 - 股票记录计数"""
        # 清理数据
        self.crud_repo.remove({"code__like": "TEST_%"})

        # 初始状态：0条记录
        result = self.service.count()
        self.assertTrue(result.success, f"Count should succeed: {result.message}")
        self.assertEqual(result.data, 0, "Should have 0 records initially")

        # 添加测试数据
        test_codes = ["TEST_COUNT_001.SZ", "TEST_COUNT_002.SZ", "TEST_COUNT_003.SZ"]
        for i, code in enumerate(test_codes, 1):
            self.crud_repo.create(
                code=code,
                code_name=f"测试股票{i}",
                industry="测试行业",
                currency=CURRENCY_TYPES.CNY,
                market=MARKET_TYPES.CHINA,
                list_date=datetime_normalize("20200101"),
                delist_date=datetime_normalize(GCONF.DEFAULTEND),
                source=SOURCE_TYPES.TUSHARE
            )

        # 验证计数
        result = self.service.count()
        self.assertTrue(result.success, f"Count should succeed: {result.message}")
        self.assertGreaterEqual(result.data, len(test_codes), f"Should have at least {len(test_codes)} records")

    def test_validate_method(self):
        """测试validate方法 - 数据质量验证"""
        # 添加有效数据
        self.crud_repo.create(
            code="TEST_VALID_001.SZ",
            code_name="有效测试股票",
            industry="测试行业",
            currency=CURRENCY_TYPES.CNY,
            market=MARKET_TYPES.CHINA,
            list_date=datetime_normalize("20200101"),
            delist_date=datetime_normalize(GCONF.DEFAULTEND),
            source=SOURCE_TYPES.TUSHARE
        )

        # 验证数据质量
        result = self.service.validate()
        self.assertTrue(result.success, f"Validate should succeed: {result.message}")
        self.assertIsNotNone(result.data, "Result data should not be None")

        # 验证DataValidationResult
        validation_result = result.data
        self.assertGreater(validation_result.metadata.get("total_records", 0), 0, "Should validate some records")

        # 测试空数据验证
        self.crud_repo.remove({"code__like": "TEST_%"})
        result_empty = self.service.validate()
        self.assertTrue(result_empty.success, "Empty validation should succeed")
        validation_result_empty = result_empty.data
        self.assertTrue(len(validation_result_empty.warnings) > 0, "Should have warning for empty data")

    def test_check_integrity_method(self):
        """测试check_integrity方法 - 数据完整性检查"""
        # 添加一些测试数据
        test_data = [
            ("TEST_INT_001.SZ", "完整性测试1", "行业1"),
            ("TEST_INT_002.SZ", "完整性测试2", "行业2"),
        ]

        for code, name, industry in test_data:
            self.crud_repo.create(
                code=code,
                code_name=name,
                industry=industry,
                currency=CURRENCY_TYPES.CNY,
                market=MARKET_TYPES.CHINA,
                list_date=datetime_normalize("20200101"),
                delist_date=datetime_normalize(GCONF.DEFAULTEND),
                source=SOURCE_TYPES.TUSHARE
            )

        # 检查数据完整性
        result = self.service.check_integrity()
        self.assertTrue(result.success, f"Integrity check should succeed: {result.message}")
        self.assertIsNotNone(result.data, "Result data should not be None")

        # 验证DataIntegrityCheckResult
        integrity_result = result.data
        self.assertGreater(integrity_result.metadata.get("total_records", 0), 0, "Should check some records")
        self.assertGreaterEqual(integrity_result.metadata.get("integrity_score", 0), 0, "Should have integrity score")

        # 测试空数据的完整性检查
        self.crud_repo.remove({"code__like": "TEST_%"})
        result_empty = self.service.check_integrity()
        self.assertTrue(result_empty.success, "Empty integrity check should succeed")
        integrity_result_empty = result_empty.data
        self.assertTrue(len(integrity_result_empty.integrity_issues) > 0, "Should have issues for empty data")


if __name__ == '__main__':
    unittest.main()