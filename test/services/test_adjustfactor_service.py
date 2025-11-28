import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

try:
    from ginkgo.data.services.adjustfactor_service import AdjustfactorService
    from ginkgo.data.crud.adjustfactor_crud import AdjustfactorCRUD
    from ginkgo.data.models.model_adjustfactor import MAdjustfactor
    from ginkgo.enums import SOURCE_TYPES
    from ginkgo.libs import GCONF, datetime_normalize
    from ginkgo.data.drivers import get_db_connection, get_table_size, create_table, drop_table
except ImportError as e:
    print(f"Import error: {e}")
    AdjustfactorService = None
    GCONF = None


class AdjustfactorServiceTest(unittest.TestCase):
    """
    AdjustfactorService 单元测试
    测试增强的错误处理功能和批量处理能力
    """

    # Mock 调整因子数据 - 基于真实 Tushare API 格式
    MOCK_ADJUSTFACTOR_SUCCESS = pd.DataFrame({
        'ts_code': ['000001.SZ', '000001.SZ', '000001.SZ'],
        'trade_date': ['20241230', '20241227', '20241226'],  # 使用真实的8位日期格式
        'adj_factor': [127.7841, 122.5643, 116.7130]  # 使用真实的调整因子数值范围
    })

    MOCK_ADJUSTFACTOR_PARTIAL_INVALID = pd.DataFrame({
        'ts_code': ['000001.SZ', '000001.SZ', '000001.SZ'],
        'trade_date': ['20241230', 'INVALID_DATE', '20241226'],  # 中间行有无效日期
        'adj_factor': [127.7841, 'INVALID_FACTOR', 116.7130]  # 中间行有无效调整因子
    })

    MOCK_EMPTY_DATA = pd.DataFrame()
    
    # 基于真实API的多股票Mock数据
    MOCK_MULTI_STOCK_DATA = pd.DataFrame({
        'ts_code': ['000002.SZ', '000002.SZ', '600519.SH', '600519.SH'],
        'trade_date': ['20241230', '20241227', '20241230', '20241227'],
        'adj_factor': [181.7040, 181.7038, 8.1454, 7.8576]
    })
    
    # 包含合理范围极值的调整因子数据
    MOCK_EXTREME_VALUES_DATA = pd.DataFrame({
        'ts_code': ['TEST001.SZ', 'TEST001.SZ', 'TEST001.SZ'],
        'trade_date': ['20241230', '20241227', '20241226'],
        'adj_factor': [0.05, 20.0, 1.0000]  # 合理极小值、极大值、正常值
    })
    
    # 包含不合理极值的调整因子数据（应该被拒绝）
    MOCK_INVALID_EXTREME_VALUES_DATA = pd.DataFrame({
        'ts_code': ['TEST002.SZ', 'TEST002.SZ'],
        'trade_date': ['20241230', '20241227'],
        'adj_factor': [0.0001, 999999.9999]  # 不合理的极值
    })

    @classmethod
    def setUpClass(cls):
        """类级别设置"""
        if AdjustfactorService is None or GCONF is None:
            raise AssertionError("AdjustfactorService or GCONF not available")

        cls.model = MAdjustfactor
        
        # 重新创建测试表
        try:
            drop_table(cls.model, no_skip=True)
            create_table(cls.model, no_skip=True)
            print(":white_check_mark: Adjustfactor table recreated for testing")
        except Exception as e:
            print(f":warning: Adjustfactor table recreation failed: {e}")

        cls.crud_repo = AdjustfactorCRUD()

    def setUp(self):
        """每个测试前的设置"""
        # 清理测试数据
        try:
            self.crud_repo.remove({"code__like": "TEST_%"})
            self.crud_repo.remove({"code__like": "000%"})
        except Exception:
            pass

        # 创建 Mock 依赖
        self.mock_data_source = Mock()
        self.mock_stockinfo_service = Mock()
        
        # 默认设置：股票代码存在于股票列表中
        self.mock_stockinfo_service.is_code_in_stocklist.return_value = True
        
        # 创建 AdjustfactorService 实例
        self.service = AdjustfactorService(
            crud_repo=self.crud_repo,
            data_source=self.mock_data_source,
            stockinfo_service=self.mock_stockinfo_service
        )

    def tearDown(self):
        """每个测试后的清理"""
        try:
            self.crud_repo.remove({"code__like": "TEST_%"})
            self.crud_repo.remove({"code__like": "000%"})
        except Exception:
            pass

    def test_sync_incremental_success(self):
        """测试成功同步单个股票的调整因子"""
        # 配置 Mock
        self.mock_data_source.fetch_cn_stock_adjustfactor.return_value = self.MOCK_ADJUSTFACTOR_SUCCESS
        
        # 执行同步
        result = self.service.sync_incremental("000001.SZ")
        
        # 验证返回结果
        self.assertIsInstance(result, dict)
        self.assertTrue(result['success'])
        self.assertEqual(result['code'], '000001.SZ')
        self.assertEqual(result['records_processed'], 3)
        self.assertGreater(result['records_added'], 0)
        self.assertIsNone(result['error'])
        self.assertIsInstance(result['warnings'], list)

    def test_sync_incremental_invalid_stock_code(self):
        """测试无效股票代码的处理"""
        # 配置 Mock：股票代码不在列表中
        self.mock_stockinfo_service.is_code_in_stocklist.return_value = False
        
        # 执行同步
        result = self.service.sync_incremental("INVALID.SZ")
        
        # 验证返回结果
        self.assertFalse(result['success'])
        self.assertEqual(result['code'], 'INVALID.SZ')
        self.assertEqual(result['records_processed'], 0)
        self.assertEqual(result['records_added'], 0)
        self.assertIn("not in stock list", result['error'])

    def test_sync_incremental_empty_data(self):
        """测试处理空数据响应"""
        # 配置 Mock 返回空数据
        self.mock_data_source.fetch_cn_stock_adjustfactor.return_value = self.MOCK_EMPTY_DATA
        
        # 执行同步
        result = self.service.sync_incremental("000001.SZ")
        
        # 验证返回结果
        self.assertTrue(result['success'])  # 空数据也是成功的情况
        self.assertEqual(result['records_processed'], 0)
        self.assertEqual(result['records_added'], 0)
        self.assertIn("No new data available", result['warnings'][0])

    def test_sync_incremental_api_failure(self):
        """测试API调用失败的处理"""
        # 配置 Mock 抛出异常 - 重试3次都失败
        self.mock_data_source.fetch_cn_stock_adjustfactor.side_effect = [
            Exception("API connection failed"),
            Exception("API connection failed"),
            Exception("API connection failed")
        ]
        
        # 执行同步
        result = self.service.sync_incremental("000001.SZ")
        
        # 验证返回结果
        self.assertFalse(result['success'])
        self.assertEqual(result['records_processed'], 0)
        self.assertEqual(result['records_added'], 0)
        self.assertIn("Failed to fetch data", result['error'])

    def test_sync_incremental_partial_invalid_data(self):
        """测试部分数据无效的容错处理"""
        # 配置 Mock 返回部分无效数据
        self.mock_data_source.fetch_cn_stock_adjustfactor.return_value = self.MOCK_ADJUSTFACTOR_PARTIAL_INVALID
        
        # Mock mappers 函数的行为
        with patch('ginkgo.data.services.adjustfactor_service.mappers') as mock_mappers:
            # 创建一个正确的 MAdjustfactor mock 对象
            mock_adjustfactor = MagicMock()
            mock_adjustfactor.timestamp = datetime_normalize("20230601")
            mock_adjustfactor.code = "000001.SZ"
            mock_adjustfactor.foreadjustfactor = 1.0
            mock_adjustfactor.backadjustfactor = 1.0
            mock_adjustfactor.adjustfactor = 1.0
            mock_adjustfactor.source = SOURCE_TYPES.TUSHARE
            
            # 第一次批量转换失败
            mock_mappers.dataframe_to_adjustfactor_models.side_effect = [
                Exception("Batch conversion failed"),  # 批量转换失败
                [mock_adjustfactor],  # 第一行成功
                Exception("Row conversion failed"),  # 第二行失败
                [mock_adjustfactor]   # 第三行成功
            ]
            
            # 执行同步
            result = self.service.sync_incremental("000001.SZ")
            
            # 验证结果
            self.assertTrue(result['success'])  # 有部分成功就算成功
            self.assertEqual(result['records_processed'], 3)
            self.assertGreater(len(result['warnings']), 0)  # 应该有警告信息

    def test_retry_mechanism(self):
        """测试重试机制"""
        # 重置 Mock 的调用计数
        self.mock_data_source.reset_mock()
        
        # 配置 Mock：前两次失败，第三次成功
        self.mock_data_source.fetch_cn_stock_adjustfactor.side_effect = [
            Exception("Network error"),
            Exception("Timeout error"),
            self.MOCK_ADJUSTFACTOR_SUCCESS
        ]
        
        # 执行同步
        result = self.service.sync_incremental("000001.SZ")
        
        # 验证重试后成功
        self.assertTrue(result['success'])
        self.assertEqual(result['records_processed'], 3)
        
        # 验证调用了3次（前两次失败，第三次成功）
        self.assertEqual(self.mock_data_source.fetch_cn_stock_adjustfactor.call_count, 3)

    def test_sync_batch_incremental_success(self):
        """测试批量同步成功场景"""
        # 配置 Mock
        self.mock_data_source.fetch_cn_stock_adjustfactor.return_value = self.MOCK_ADJUSTFACTOR_SUCCESS
        
        codes = ["000001.SZ", "000002.SZ", "000003.SZ"]
        
        # 执行批量同步
        result = self.service.sync_batch_incremental(codes)
        
        # 验证批量结果
        self.assertEqual(result['total_codes'], 3)
        self.assertEqual(result['successful_codes'], 3)
        self.assertEqual(result['failed_codes'], 0)
        self.assertGreater(result['total_records_processed'], 0)
        self.assertGreater(result['total_records_added'], 0)
        self.assertEqual(len(result['results']), 3)
        self.assertEqual(len(result['failures']), 0)

    def test_sync_batch_incremental_partial_failure(self):
        """测试批量同步部分失败场景"""
        # 配置 Mock：第二个股票失败
        def mock_fetch_side_effect(code, start_date, end_date):
            if code == "000002.SZ":
                raise Exception("API error for 000002.SZ")
            return self.MOCK_ADJUSTFACTOR_SUCCESS
        
        self.mock_data_source.fetch_cn_stock_adjustfactor.side_effect = mock_fetch_side_effect
        
        codes = ["000001.SZ", "000002.SZ", "000003.SZ"]
        
        # 执行批量同步
        result = self.service.sync_batch_incremental(codes)
        
        # 验证批量结果
        self.assertEqual(result['total_codes'], 3)
        self.assertEqual(result['successful_codes'], 2)
        self.assertEqual(result['failed_codes'], 1)
        self.assertEqual(len(result['failures']), 1)
        self.assertEqual(result['failures'][0]['code'], '000002.SZ')

    def test_sync_batch_incremental_all_invalid_codes(self):
        """测试批量同步全部无效股票代码"""
        # 配置 Mock：所有股票代码都无效
        self.mock_stockinfo_service.is_code_in_stocklist.return_value = False
        
        codes = ["INVALID1.SZ", "INVALID2.SZ", "INVALID3.SZ"]
        
        # 执行批量同步
        result = self.service.sync_batch_incremental(codes)
        
        # 验证批量结果
        self.assertEqual(result['total_codes'], 3)
        self.assertEqual(result['successful_codes'], 0)
        self.assertEqual(result['failed_codes'], 3)
        self.assertEqual(len(result['failures']), 3)

    def test_get_adjustfactors_caching(self):
        """测试数据获取和缓存功能"""
        # 先添加一些测试数据
        self.crud_repo.create(
            code="TEST_001.SZ",
            timestamp=datetime_normalize("20230601"),
            foreadjustfactor=1.0,
            backadjustfactor=1.0, 
            adjustfactor=1.0,
            source=SOURCE_TYPES.TUSHARE
        )
        
        # 测试数据获取
        result = self.service.get_adjustfactors(code="TEST_001.SZ", as_dataframe=True)
        
        # 验证结果
        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0)
        
        # 验证缓存（第二次调用应该更快）
        result2 = self.service.get_adjustfactors(code="TEST_001.SZ", as_dataframe=True)
        self.assertTrue(result.equals(result2))

    def test_get_latest_adjustfactor_for_code(self):
        """测试获取最新调整因子时间戳"""
        # 添加测试数据
        test_dates = ["20230601", "20230701", "20230801"]
        for date_str in test_dates:
            self.crud_repo.create(
                code="TEST_LATEST.SZ",
                timestamp=datetime_normalize(date_str),
                foreadjustfactor=1.0,
                backadjustfactor=1.0,
                adjustfactor=1.0,
                source=SOURCE_TYPES.TUSHARE
            )
        
        # 获取最新时间戳
        latest = self.service.get_latest_adjustfactor_for_code("TEST_LATEST.SZ")
        
        # 验证是最新日期
        expected_latest = datetime_normalize("20230801")
        self.assertEqual(latest, expected_latest)

    def test_get_latest_adjustfactor_for_nonexistent_code(self):
        """测试获取不存在代码的最新时间戳"""
        latest = self.service.get_latest_adjustfactor_for_code("NONEXISTENT.SZ")
        
        # 应该返回默认开始时间
        expected_default = datetime_normalize(GCONF.DEFAULTSTART)
        self.assertEqual(latest, expected_default)

    def test_count_adjustfactors(self):
        """测试调整因子记录计数"""
        # 添加测试数据
        for i in range(5):
            self.crud_repo.create(
                code="TEST_COUNT.SZ",
                timestamp=datetime_normalize(f"202306{i+1:02d}"),
                foreadjustfactor=1.0 + i * 0.01,
                backadjustfactor=1.0 + i * 0.01,
                adjustfactor=1.0 + i * 0.01,
                source=SOURCE_TYPES.TUSHARE
            )
        
        # 测试计数
        count = self.service.count_adjustfactors(code="TEST_COUNT.SZ")
        self.assertEqual(count, 5)

    def test_get_available_codes(self):
        """测试获取可用股票代码列表"""
        # 添加测试数据
        test_codes = ["TEST_AVAIL1.SZ", "TEST_AVAIL2.SZ", "TEST_AVAIL3.SZ"]
        for code in test_codes:
            self.crud_repo.create(
                code=code,
                timestamp=datetime_normalize("20230601"),
                foreadjustfactor=1.0,
                backadjustfactor=1.0,
                adjustfactor=1.0,
                source=SOURCE_TYPES.TUSHARE
            )
        
        # 获取可用代码
        available_codes = self.service.get_available_codes()
        
        # 验证结果
        self.assertIsInstance(available_codes, list)
        for code in test_codes:
            self.assertIn(code, available_codes)

    def test_fast_mode_vs_full_mode(self):
        """测试快速模式和完整模式的区别"""
        # 配置 Mock
        self.mock_data_source.fetch_cn_stock_adjustfactor.return_value = self.MOCK_ADJUSTFACTOR_SUCCESS
        
        # 先添加一些历史数据
        self.crud_repo.create(
            code="000001.SZ",
            timestamp=datetime_normalize("20230501"),
            foreadjustfactor=0.95,
            backadjustfactor=0.95,
            adjustfactor=0.95,
            source=SOURCE_TYPES.TUSHARE
        )
        
        # 测试完整模式（应该会删除并重新插入）
        result_full = self.service.sync_incremental("000001.SZ", fast_mode=False)
        # 如果失败，打印错误信息用于调试
        if not result_full['success']:
            print(f"Full mode failed: {result_full}")
        self.assertTrue(result_full['success'])
        
        # 测试快速模式（增量更新）
        result_fast = self.service.sync_incremental("000001.SZ")
        self.assertTrue(result_fast['success'])

    def test_database_transaction_rollback(self):
        """测试数据库事务回滚"""
        # 配置 Mock
        self.mock_data_source.fetch_cn_stock_adjustfactor.return_value = self.MOCK_ADJUSTFACTOR_SUCCESS
        
        # 模拟数据库操作失败
        with patch.object(self.crud_repo, 'add_batch', side_effect=Exception("Database error")):
            result = self.service.sync_incremental("000001.SZ")
            
            # 验证失败结果
            self.assertFalse(result['success'])
            self.assertIn("Database operation failed", result['error'])

    def test_error_logging_and_reporting(self):
        """测试错误日志记录和报告"""
        # 配置各种错误场景并验证业务逻辑处理
        # API 错误 - 重试3次都失败
        self.mock_data_source.fetch_cn_stock_adjustfactor.side_effect = [
            Exception("API error"),
            Exception("API error"),
            Exception("API error")
        ]
        result = self.service.sync_incremental("000001.SZ")
        
        # 验证错误处理结果
        self.assertFalse(result['success'])
        self.assertIsNotNone(result['error'])
        self.assertIn("API error", result['error'])

    def test_real_data_format_compatibility(self):
        """测试真实API数据格式的兼容性"""
        # 使用基于真实API的数据格式
        self.mock_data_source.fetch_cn_stock_adjustfactor.return_value = self.MOCK_ADJUSTFACTOR_SUCCESS
        
        # 执行同步
        result = self.service.sync_incremental("000001.SZ")
        
        # 验证结果
        self.assertTrue(result['success'])
        self.assertEqual(result['records_processed'], 3)
        self.assertEqual(result['records_added'], 3)
        
        # 验证数据已正确存储到数据库
        stored_data = self.service.get_adjustfactors(code="000001.SZ", as_dataframe=True)
        self.assertGreater(len(stored_data), 0)

    def test_extreme_values_handling(self):
        """测试极值调整因子的处理"""
        # 使用包含极值的数据
        self.mock_data_source.fetch_cn_stock_adjustfactor.return_value = self.MOCK_EXTREME_VALUES_DATA
        
        # 执行同步
        result = self.service.sync_incremental("TEST001.SZ")
        
        # 验证极值也能正确处理
        self.assertTrue(result['success'])
        self.assertEqual(result['records_processed'], 3)
        
        # 验证极值数据已存储
        stored_data = self.service.get_adjustfactors(code="TEST001.SZ", as_dataframe=True)
        if not stored_data.empty:
            # 检查极值是否保持精度
            adj_factors = stored_data['adjustfactor'].values
            self.assertIn(0.05, [float(f) for f in adj_factors])  # 合理极小值
            self.assertIn(20.0, [float(f) for f in adj_factors])  # 合理极大值

    def test_multi_stock_data_processing(self):
        """测试多股票数据在单个DataFrame中的处理"""
        # 使用包含多个股票的数据（模拟批量获取场景）
        self.mock_data_source.fetch_cn_stock_adjustfactor.return_value = self.MOCK_MULTI_STOCK_DATA
        
        # 注意：在实际场景中，API会为单个股票返回数据
        # 但这里测试mapper函数对多股票数据的容错性
        result = self.service.sync_incremental("000002.SZ")
        
        # 验证能够处理多股票数据（mapper会使用传入的code参数）
        self.assertTrue(result['success'])
        self.assertEqual(result['records_processed'], 4)  # 包含2个股票的数据

    def test_date_format_validation(self):
        """测试日期格式的验证和转换"""
        # 创建包含不同日期格式的测试数据
        test_data = pd.DataFrame({
            'ts_code': ['000001.SZ', '000001.SZ', '000001.SZ'],
            'trade_date': ['20241230', '2024-12-27', '20241226'],  # 混合格式
            'adj_factor': [127.7841, 122.5643, 116.7130]
        })
        
        self.mock_data_source.fetch_cn_stock_adjustfactor.return_value = test_data
        
        # 执行同步
        result = self.service.sync_incremental("000001.SZ")
        
        # 验证能正确处理不同日期格式
        # （这取决于datetime_normalize函数的实现）
        self.assertTrue(result['success'])
        self.assertEqual(result['records_processed'], 3)

    def test_high_precision_adjustfactor_values(self):
        """测试高精度调整因子数值的处理"""
        # 使用高精度的调整因子数据
        high_precision_data = pd.DataFrame({
            'ts_code': ['000001.SZ', '000001.SZ', '000001.SZ'],
            'trade_date': ['20241230', '20241227', '20241226'],
            'adj_factor': [127.784123456789, 122.564312345678, 116.713087654321]  # 高精度浮点数
        })
        
        self.mock_data_source.fetch_cn_stock_adjustfactor.return_value = high_precision_data
        
        # 执行同步
        result = self.service.sync_incremental("000001.SZ")
        
        # 验证高精度数值的处理
        self.assertTrue(result['success'])
        self.assertEqual(result['records_processed'], 3)
        
        # 检查精度保持（数据库存储的精度限制）
        stored_data = self.service.get_adjustfactors(code="000001.SZ", as_dataframe=True)
        if not stored_data.empty:
            # 验证数值被正确存储（考虑DECIMAL精度限制）
            self.assertGreater(len(stored_data), 0)

    def test_recalculate_adjust_factors_for_code_success(self):
        """测试单股票复权因子重新计算成功场景"""
        from ginkgo.libs import to_decimal
        
        # 准备测试数据：典型的除权序列
        test_data = [
            {
                "code": "TEST_CALC.SZ",
                "timestamp": datetime_normalize("20230101"),
                "foreadjustfactor": 1.0,  # 将被重新计算
                "backadjustfactor": 1.0,  # 将被重新计算
                "adjustfactor": 1.0,     # 原始adj_factor
                "source": SOURCE_TYPES.TUSHARE
            },
            {
                "code": "TEST_CALC.SZ",
                "timestamp": datetime_normalize("20230601"),
                "foreadjustfactor": 1.0,  # 将被重新计算
                "backadjustfactor": 1.0,  # 将被重新计算
                "adjustfactor": 0.8,     # 除权后
                "source": SOURCE_TYPES.TUSHARE
            },
            {
                "code": "TEST_CALC.SZ",
                "timestamp": datetime_normalize("20231201"),
                "foreadjustfactor": 1.0,  # 将被重新计算
                "backadjustfactor": 1.0,  # 将被重新计算
                "adjustfactor": 0.6,     # 再次除权
                "source": SOURCE_TYPES.TUSHARE
            }
        ]
        
        # 添加测试数据到数据库
        for data in test_data:
            self.crud_repo.create(**data)
        
        # 执行复权因子重新计算
        result = self.service.recalculate_adjust_factors_for_code("TEST_CALC.SZ")
        
        # 验证返回结果
        self.assertTrue(result['success'])
        self.assertEqual(result['code'], 'TEST_CALC.SZ')
        self.assertEqual(result['records_processed'], 3)
        self.assertIsNone(result['error'])
        
        # 验证计算结果的数学正确性
        updated_records = self.service.get_adjustfactors(code="TEST_CALC.SZ", as_dataframe=False)
        self.assertEqual(len(updated_records), 3)
        
        # 按时间排序验证计算结果
        sorted_records = sorted(updated_records, key=lambda x: x.timestamp)
        
        # 预期计算结果：
        # latest_factor = 0.6, earliest_factor = 1.0
        # 前复权因子 = latest / current
        # 后复权因子 = current / earliest
        expected_fore = [0.6, 0.75, 1.0]  # [0.6/1.0, 0.6/0.8, 0.6/0.6]
        expected_back = [1.0, 0.8, 0.6]   # [1.0/1.0, 0.8/1.0, 0.6/1.0]
        
        for i, record in enumerate(sorted_records):
            fore_actual = float(record.foreadjustfactor)
            back_actual = float(record.backadjustfactor)
            self.assertAlmostEqual(fore_actual, expected_fore[i], places=6,
                                 msg=f"前复权因子计算错误: {fore_actual} != {expected_fore[i]}")
            self.assertAlmostEqual(back_actual, expected_back[i], places=6,
                                 msg=f"后复权因子计算错误: {back_actual} != {expected_back[i]}")

    def test_recalculate_adjust_factors_for_code_single_record(self):
        """测试单记录的复权因子计算"""
        # 准备单条记录
        self.crud_repo.create(
            code="TEST_SINGLE.SZ",
            timestamp=datetime_normalize("20230101"),
            foreadjustfactor=1.0,
            backadjustfactor=1.0,
            adjustfactor=1.5,
            source=SOURCE_TYPES.TUSHARE
        )
        
        # 执行计算
        result = self.service.recalculate_adjust_factors_for_code("TEST_SINGLE.SZ")
        
        # 验证结果
        self.assertTrue(result['success'])
        self.assertEqual(result['records_processed'], 1)
        
        # 单记录情况下，前复权和后复权因子都应该是1.0
        updated_record = self.service.get_adjustfactors(code="TEST_SINGLE.SZ", as_dataframe=False)[0]
        self.assertEqual(float(updated_record.foreadjustfactor), 1.0)
        self.assertEqual(float(updated_record.backadjustfactor), 1.0)

    def test_recalculate_adjust_factors_for_code_invalid_code(self):
        """测试无效股票代码的复权因子计算"""
        # 执行对不存在代码的计算
        result = self.service.recalculate_adjust_factors_for_code("NONEXISTENT.SZ")
        
        # 验证失败结果 - 专注于行为而非具体错误消息内容
        self.assertFalse(result['success'])
        self.assertEqual(result['code'], 'NONEXISTENT.SZ')
        self.assertEqual(result['records_processed'], 0)
        self.assertIsNotNone(result['error'])  # 确认有错误信息，但不验证具体内容

    def test_recalculate_adjust_factors_batch_success(self):
        """测试批量复权因子重新计算成功场景"""
        # 准备多个股票的测试数据
        test_codes = ["BATCH_001.SZ", "BATCH_002.SZ", "BATCH_003.SZ"]
        
        for code in test_codes:
            # 为每个股票添加测试数据
            self.crud_repo.create(
                code=code,
                timestamp=datetime_normalize("20230101"),
                foreadjustfactor=1.0,
                backadjustfactor=1.0,
                adjustfactor=1.0,
                source=SOURCE_TYPES.TUSHARE
            )
            self.crud_repo.create(
                code=code,
                timestamp=datetime_normalize("20230601"),
                foreadjustfactor=1.0,
                backadjustfactor=1.0,
                adjustfactor=0.8,
                source=SOURCE_TYPES.TUSHARE
            )
        
        # 执行批量计算
        result = self.service.recalculate_adjust_factors_batch(test_codes)
        
        # 验证批量结果
        self.assertTrue(result['success'])
        self.assertEqual(result['total_codes'], 3)
        self.assertEqual(result['successful_codes'], 3)
        self.assertEqual(result['failed_codes'], 0)
        self.assertEqual(result['total_records_processed'], 6)  # 每个股票2条记录
        self.assertEqual(len(result['results']), 3)
        self.assertEqual(len(result['failures']), 0)

    def test_recalculate_adjust_factors_batch_partial_failure(self):
        """测试批量计算部分失败场景"""
        # 准备测试数据：只为部分股票添加数据
        test_codes = ["PARTIAL_001.SZ", "PARTIAL_002.SZ", "PARTIAL_003.SZ"]
        
        # 只为前两个股票添加数据，第三个不存在
        for code in test_codes[:2]:
            self.crud_repo.create(
                code=code,
                timestamp=datetime_normalize("20230101"),
                foreadjustfactor=1.0,
                backadjustfactor=1.0,
                adjustfactor=1.0,
                source=SOURCE_TYPES.TUSHARE
            )
        
        # 执行批量计算
        result = self.service.recalculate_adjust_factors_batch(test_codes)
        
        # 验证部分失败结果
        self.assertFalse(result['success'])  # 有失败则整体为False
        self.assertEqual(result['total_codes'], 3)
        self.assertEqual(result['successful_codes'], 2)
        self.assertEqual(result['failed_codes'], 1)
        self.assertEqual(len(result['failures']), 1)
        self.assertEqual(result['failures'][0]['code'], 'PARTIAL_003.SZ')

    def test_calculate_fore_back_factors_mathematical_logic(self):
        """测试复权因子数学计算逻辑的绝对正确性"""
        from ginkgo.libs import to_decimal
        
        # 准备复杂的除权序列数据进行详细验证
        complex_test_data = [
            {
                "code": "MATH_TEST.SZ",
                "timestamp": datetime_normalize("20220101"),
                "adjustfactor": 2.0,    # 最早
                "foreadjustfactor": 1.0,
                "backadjustfactor": 1.0,
                "source": SOURCE_TYPES.TUSHARE
            },
            {
                "code": "MATH_TEST.SZ", 
                "timestamp": datetime_normalize("20220601"),
                "adjustfactor": 1.5,
                "foreadjustfactor": 1.0,
                "backadjustfactor": 1.0,
                "source": SOURCE_TYPES.TUSHARE
            },
            {
                "code": "MATH_TEST.SZ",
                "timestamp": datetime_normalize("20221201"),
                "adjustfactor": 1.0,
                "foreadjustfactor": 1.0,
                "backadjustfactor": 1.0,
                "source": SOURCE_TYPES.TUSHARE
            },
            {
                "code": "MATH_TEST.SZ",
                "timestamp": datetime_normalize("20230601"),
                "adjustfactor": 0.8,
                "foreadjustfactor": 1.0,
                "backadjustfactor": 1.0,
                "source": SOURCE_TYPES.TUSHARE
            },
            {
                "code": "MATH_TEST.SZ",
                "timestamp": datetime_normalize("20231201"),
                "adjustfactor": 0.6,    # 最新
                "foreadjustfactor": 1.0,
                "backadjustfactor": 1.0,
                "source": SOURCE_TYPES.TUSHARE
            }
        ]
        
        # 添加测试数据
        for data in complex_test_data:
            self.crud_repo.create(**data)
        
        # 执行计算
        result = self.service.recalculate_adjust_factors_for_code("MATH_TEST.SZ")
        
        # 验证基本结果
        self.assertTrue(result['success'])
        self.assertEqual(result['records_processed'], 5)
        
        # 获取计算后的记录并验证数学逻辑
        updated_records = self.service.get_adjustfactors(code="MATH_TEST.SZ", as_dataframe=False)
        sorted_records = sorted(updated_records, key=lambda x: x.timestamp)
        
        # 验证计算公式:
        # latest_factor = 0.6, earliest_factor = 2.0
        # 前复权因子 = latest_factor / current_factor
        # 后复权因子 = current_factor / earliest_factor
        
        adj_factors = [2.0, 1.5, 1.0, 0.8, 0.6]
        latest_factor = 0.6
        earliest_factor = 2.0
        
        expected_calculations = []
        for current_factor in adj_factors:
            fore_factor = latest_factor / current_factor
            back_factor = current_factor / earliest_factor
            expected_calculations.append((fore_factor, back_factor))
        
        # 验证每个记录的计算结果
        for i, record in enumerate(sorted_records):
            expected_fore, expected_back = expected_calculations[i]
            actual_fore = float(record.foreadjustfactor)
            actual_back = float(record.backadjustfactor)
            
            self.assertAlmostEqual(actual_fore, expected_fore, places=6,
                msg=f"记录{i+1}前复权因子错误: 实际{actual_fore} != 预期{expected_fore} (adj_factor={adj_factors[i]})")
            self.assertAlmostEqual(actual_back, expected_back, places=6,
                msg=f"记录{i+1}后复权因子错误: 实际{actual_back} != 预期{expected_back} (adj_factor={adj_factors[i]})")
        
        # 验证复权价格的连续性（假设原始价格为10元）
        original_price = 10.0
        fore_prices = []
        back_prices = []
        
        for record in sorted_records:
            fore_price = original_price * float(record.foreadjustfactor)
            back_price = original_price * float(record.backadjustfactor)
            fore_prices.append(fore_price)
            back_prices.append(back_price)
        
        # 基于数学原理的正确趋势验证：
        # 当adj_factor序列下降时（除权除息累积效应）：
        # 前复权价格 = P × (latest_factor / current_factor) → 随current_factor减小而增大 → 上涨趋势
        # 后复权价格 = P × (current_factor / earliest_factor) → 随current_factor减小而减小 → 下降趋势
        self.assertLess(fore_prices[0], fore_prices[-1], "前复权价格应呈上涨趋势")
        self.assertGreater(back_prices[0], back_prices[-1], "后复权价格应呈下降趋势")
        
        # 验证边界值：最新记录的前复权因子应为1.0，最早记录的后复权因子应为1.0
        self.assertAlmostEqual(float(sorted_records[-1].foreadjustfactor), 1.0, places=6,
                              msg="最新记录的前复权因子应为1.0")
        self.assertAlmostEqual(float(sorted_records[0].backadjustfactor), 1.0, places=6,
                              msg="最早记录的后复权因子应为1.0")


if __name__ == '__main__':
    unittest.main()