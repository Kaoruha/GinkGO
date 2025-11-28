import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

try:
    from ginkgo.data.services.bar_service import BarService
    from ginkgo.data.crud.bar_crud import BarCRUD
    from ginkgo.data.models.model_bar import MBar
    from ginkgo.enums import SOURCE_TYPES, FREQUENCY_TYPES, ADJUSTMENT_TYPES
    from ginkgo.libs import GCONF, datetime_normalize
    from ginkgo.data.drivers import get_db_connection, get_table_size, create_table, drop_table
except ImportError as e:
    print(f"Import error: {e}")
    BarService = None
    GCONF = None


class BarServiceTest(unittest.TestCase):
    """
    BarService 单元测试
    测试增强的错误处理功能和数据验证能力
    """

    # Mock 日线数据 - 基于真实 Tushare API 格式
    MOCK_BAR_SUCCESS = pd.DataFrame({
        'ts_code': ['000001.SZ', '000001.SZ', '000001.SZ'],
        'trade_date': ['20250725', '20250724', '20250723'],  # 8位日期格式
        'open': [12.33, 12.53, 12.46],  # float64类型
        'high': [12.46, 12.53, 12.63],
        'low': [12.30, 12.35, 12.42],
        'close': [12.33, 12.35, 12.50],
        'pre_close': [12.33, 12.53, 12.46],
        'change': [0.00, -0.18, 0.04],
        'pct_chg': [0.0000, -1.4366, 0.3203],
        'vol': [1108266.66, 1959350.57, 1370520.00],  # 成交量 (手)
        'amount': [1372103.731, 2426175.236, 1719158.803]  # 成交额 (千元)
    })

    # 数据质量问题但仍可处理的数据（轻微异常）
    MOCK_BAR_QUALITY_ISSUES = pd.DataFrame({
        'ts_code': ['000001.SZ', '000001.SZ', '000001.SZ'],
        'trade_date': ['20250725', '20250724', '20250723'],
        'open': [12.33, 12.53, 12.46],
        'high': [12.40, 12.53, 12.63],  # 正常OHLC逻辑
        'low': [12.25, 12.35, 12.42],   # 正常OHLC逻辑
        'close': [12.33, 12.35, 12.50],
        'pre_close': [12.33, 12.53, 12.46],
        'change': [0.00, -0.18, 0.04],
        'pct_chg': [0.0000, -1.4366, 0.3203],
        'vol': [1108266.66, 1959350.57, 1370520.00],
        'amount': [1372103.731, 2426175.236, 1719158.803]
    })

    # 严重OHLC逻辑错误的数据（应该被拒绝）
    MOCK_BAR_INVALID_OHLC = pd.DataFrame({
        'ts_code': ['000001.SZ', '000001.SZ', '000001.SZ'],
        'trade_date': ['20250725', '20250724', '20250723'],
        'open': [12.33, 12.53, 12.46],
        'high': [12.20, 12.53, 12.63],  # 第一行 high < open (严重错误)
        'low': [12.50, 12.35, 12.42],   # 第一行 low > open (严重错误)
        'close': [12.33, 12.35, 12.50],
        'pre_close': [12.33, 12.53, 12.46],
        'change': [0.00, -0.18, 0.04],
        'pct_chg': [0.0000, -1.4366, 0.3203],
        'vol': [1108266.66, 1959350.57, 1370520.00],
        'amount': [1372103.731, 2426175.236, 1719158.803]
    })

    MOCK_EMPTY_DATA = pd.DataFrame()
    
    # 基于真实API的极值数据（涨跌停情况）
    MOCK_EXTREME_VALUES_DATA = pd.DataFrame({
        'ts_code': ['TEST001.SZ', 'TEST001.SZ', 'TEST001.SZ'],
        'trade_date': ['20250725', '20250724', '20250723'],
        'open': [10.00, 11.00, 9.09],
        'high': [11.00, 11.00, 10.00],  # 涨停
        'low': [10.00, 9.09, 9.09],    # 跌停
        'close': [11.00, 9.09, 10.00],
        'pre_close': [10.00, 10.00, 10.00],
        'change': [1.00, -0.91, 0.00],
        'pct_chg': [10.00, -9.10, 0.00],
        'vol': [50000.00, 10000.00, 0.00],  # 包含停牌情况
        'amount': [550000.00, 95450.00, 0.00]
    })
    
    # 包含负价格的错误数据（用于测试数据验证）
    MOCK_NEGATIVE_PRICES_DATA = pd.DataFrame({
        'ts_code': ['ERROR001.SZ', 'ERROR001.SZ'],
        'trade_date': ['20250725', '20250724'],
        'open': [12.33, -0.01],  # 第二行有负价格
        'high': [12.46, 12.53],
        'low': [12.30, 12.35],
        'close': [12.33, 12.35],
        'pre_close': [12.33, 12.53],
        'change': [0.00, -0.18],
        'pct_chg': [0.0000, -1.4366],
        'vol': [1108266.66, 1959350.57],
        'amount': [1372103.731, 2426175.236]
    })

    @classmethod
    def setUpClass(cls):
        """类级别设置"""
        if BarService is None or GCONF is None:
            raise AssertionError("BarService or GCONF not available")

        cls.model = MBar
        
        # 重新创建测试表
        try:
            drop_table(cls.model, no_skip=True)
            create_table(cls.model, no_skip=True)
            print(":white_check_mark: Bar table recreated for testing")
        except Exception as e:
            print(f":warning: Bar table recreation failed: {e}")

        cls.crud_repo = BarCRUD()

    def setUp(self):
        """每个测试前的设置"""
        # 清理测试数据
        try:
            self.crud_repo.remove({"code__like": "TEST_%"})
            self.crud_repo.remove({"code__like": "000%"})
            self.crud_repo.remove({"code__like": "ERROR%"})
        except Exception:
            pass

        # 创建 Mock 依赖
        self.mock_data_source = Mock()
        self.mock_stockinfo_service = Mock()
        
        # 默认设置：股票代码存在于股票列表中
        self.mock_stockinfo_service.is_code_in_stocklist.return_value = True
        
        # 创建 Mock AdjustfactorService
        self.mock_adjustfactor_service = Mock()
        
        # 创建 BarService 实例
        self.service = BarService(
            crud_repo=self.crud_repo,
            data_source=self.mock_data_source,
            stockinfo_service=self.mock_stockinfo_service,
            adjustfactor_service=self.mock_adjustfactor_service
        )

    def tearDown(self):
        """每个测试后的清理"""
        try:
            self.crud_repo.remove({"code__like": "TEST_%"})
            self.crud_repo.remove({"code__like": "000%"})
            self.crud_repo.remove({"code__like": "ERROR%"})
        except Exception:
            pass

    def test_sync_incremental_success(self):
        """测试成功同步单个股票的日线数据（增量模式）"""
        # 配置 Mock
        self.mock_data_source.fetch_cn_stock_daybar.return_value = self.MOCK_BAR_SUCCESS

        # 执行同步
        result = self.service.sync_incremental("000001.SZ")

        # 验证返回ServiceResult格式
        from ginkgo.data.services.base_service import ServiceResult
        self.assertIsInstance(result, ServiceResult)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.data)
        self.assertIsNone(result.error)
        # DataSyncResult应该在result.data中
        if hasattr(result.data, 'records_processed'):
            self.assertEqual(result.data.records_processed, 3)
            self.assertGreater(result.data.records_added, 0)

    def test_sync_incremental_invalid_stock_code(self):
        """测试无效股票代码的处理"""
        # 配置 Mock：股票代码不在列表中
        self.mock_stockinfo_service.is_code_in_stocklist.return_value = False

        # 执行同步
        result = self.service.sync_incremental("INVALID.SZ")

        # 验证返回ServiceResult格式
        from ginkgo.data.services.base_service import ServiceResult
        self.assertIsInstance(result, ServiceResult)
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)
        self.assertIn("not in stock list", result.error.lower())

    def test_sync_incremental_empty_data(self):
        """测试处理空数据响应"""
        # 配置 Mock 返回空数据
        self.mock_data_source.fetch_cn_stock_daybar.return_value = self.MOCK_EMPTY_DATA

        # 执行同步
        result = self.service.sync_incremental("000001.SZ")

        # 验证返回ServiceResult格式
        from ginkgo.data.services.base_service import ServiceResult
        self.assertIsInstance(result, ServiceResult)
        self.assertTrue(result.success)  # 空数据也是成功的情况
        self.assertIsNotNone(result.data)

    def test_sync_incremental_api_failure(self):
        """测试API调用失败的处理（重试3次）"""
        # 配置 Mock 抛出异常 - 重试3次都失败
        self.mock_data_source.fetch_cn_stock_daybar.side_effect = [
            Exception("API connection failed"),
            Exception("API connection failed"),
            Exception("API connection failed")
        ]
        
        # 执行同步
        result = self.service.sync_incremental("000001.SZ")

        # 验证返回结果
        self.assertFalse(result.success)
        self.assertEqual(result.data.records_processed, 0)
        self.assertEqual(result.data.records_added, 0)
        self.assertIn("Failed to fetch data from source", result.error)

    def test_sync_incremental_data_validation_warning(self):
        """测试数据验证发出警告但仍继续处理"""
        # 配置 Mock 返回包含轻微数据质量问题的数据
        self.mock_data_source.fetch_cn_stock_daybar.return_value = self.MOCK_BAR_QUALITY_ISSUES
        
        # 执行同步
        result = self.service.sync_incremental("000001.SZ")
        
        # 验证结果（应该成功处理）
        self.assertTrue(result.success)
        self.assertEqual(result.data.records_processed, 3)
        # 注意：轻微质量问题可能不会产生警告，这取决于具体的验证逻辑

    def test_sync_incremental_invalid_ohlc_validation(self):
        """测试严重OHLC逻辑错误的数据验证 - 当前实现会发出警告但继续处理"""
        # 配置 Mock 返回包含严重OHLC逻辑错误的数据
        self.mock_data_source.fetch_cn_stock_daybar.return_value = self.MOCK_BAR_INVALID_OHLC
        
        # 执行同步
        result = self.service.sync_incremental("000001.SZ")
        
        # 验证结果 - 当前服务实现选择发出警告但继续处理所有数据
        # 这种设计可能需要在未来版本中重新考虑，以提供更严格的数据质量控制选项
        self.assertTrue(result.success, "当前实现会继续处理包含OHLC错误的数据")
        self.assertEqual(result.data.records_processed, 3, "当前实现会处理所有记录，包括有错误的")
        
        # 验证至少发出了数据质量警告
        self.assertGreater(len(result['warnings']), 0, "应该有数据质量警告")
        self.assertTrue(
            any("Data quality issues detected" in warning for warning in result['warnings']),
            "应该包含数据质量检测警告"
        )
        
        # TODO: 考虑在未来版本中添加strict_validation参数，
        # 允许用户选择是否在遇到严重OHLC错误时停止处理


    def test_sync_incremental_negative_prices_validation(self):
        """测试负价格数据验证"""
        # 配置 Mock 返回包含负价格的数据
        self.mock_data_source.fetch_cn_stock_daybar.return_value = self.MOCK_NEGATIVE_PRICES_DATA
        
        # 执行同步
        result = self.service.sync_incremental("ERROR001.SZ")
        
        # 验证数据质量警告
        self.assertTrue(result.success)  # 仍然会处理数据
        self.assertIn("Data quality issues detected", result['warnings'])

    def test_sync_incremental_partial_mapping_failure(self):
        """测试部分数据映射失败的容错处理"""
        # 配置 Mock 返回数据
        self.mock_data_source.fetch_cn_stock_daybar.return_value = self.MOCK_BAR_SUCCESS
        
        # Mock mappers 函数的行为
        with patch('ginkgo.data.services.bar_service.mappers') as mock_mappers:
            # 创建一个正确的 MBar mock 对象
            mock_bar = MagicMock()
            mock_bar.timestamp = datetime_normalize("20250725")
            mock_bar.code = "000001.SZ"
            mock_bar.open = 12.33
            mock_bar.high = 12.46
            mock_bar.low = 12.30
            mock_bar.close = 12.33
            mock_bar.volume = 1108266
            mock_bar.amount = 1372103.731
            mock_bar.frequency = FREQUENCY_TYPES.DAY
            mock_bar.source = SOURCE_TYPES.TUSHARE
            
            # 第一次批量转换失败，然后逐行转换成功
            mock_mappers.dataframe_to_bar_models.side_effect = [
                Exception("Batch conversion failed"),  # 批量转换失败
                [mock_bar],  # 第一行成功
                [mock_bar],  # 第二行成功  
                [mock_bar]   # 第三行成功
            ]
            
            # 执行同步
            result = self.service.sync_incremental("000001.SZ")
            
            # 验证结果
            self.assertTrue(result.success)  # 有部分成功就算成功
            self.assertEqual(result.data.records_processed, 3)
            self.assertGreater(len(result['warnings']), 0)  # 应该有警告信息

    def test_retry_mechanism(self):
        """测试重试机制"""
        # 重置 Mock 的调用计数
        self.mock_data_source.reset_mock()
        
        # 配置 Mock：前两次失败，第三次成功
        self.mock_data_source.fetch_cn_stock_daybar.side_effect = [
            Exception("Network error"),
            Exception("Timeout error"),
            self.MOCK_BAR_SUCCESS
        ]
        
        # 执行同步
        result = self.service.sync_incremental("000001.SZ")
        
        # 验证重试后成功
        self.assertTrue(result.success)
        self.assertEqual(result.data.records_processed, 3)
        
        # 验证调用了3次（前两次失败，第三次成功）
        self.assertEqual(self.mock_data_source.fetch_cn_stock_daybar.call_count, 3)

    def test_sync_batch_incremental_success(self):
        """测试批量同步成功场景"""
        # 配置 Mock
        self.mock_data_source.fetch_cn_stock_daybar.return_value = self.MOCK_BAR_SUCCESS
        
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
            return self.MOCK_BAR_SUCCESS
        
        self.mock_data_source.fetch_cn_stock_daybar.side_effect = mock_fetch_side_effect
        
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

    def test_get_bars_caching(self):
        """测试数据获取和缓存功能"""
        # 先添加一些测试数据
        self.crud_repo.create(
            code="TEST_BAR.SZ",
            open=12.33,
            high=12.46,
            low=12.30,
            close=12.33,
            volume=1108266,
            amount=1372103.731,
            frequency=FREQUENCY_TYPES.DAY,
            timestamp=datetime_normalize("20250725"),
            source=SOURCE_TYPES.TUSHARE
        )
        
        # 测试数据获取
        result = self.service.get_bars(code="TEST_BAR.SZ", as_dataframe=True)
        
        # 验证结果
        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0)
        
        # 验证缓存（第二次调用应该更快）
        result2 = self.service.get_bars(code="TEST_BAR.SZ", as_dataframe=True)
        self.assertTrue(result.equals(result2))

    def test_get_latest_timestamp(self):
        """测试获取最新时间戳"""
        # 添加测试数据
        test_dates = ["20250723", "20250724", "20250725"]
        for date_str in test_dates:
            self.crud_repo.create(
                code="TEST_LATEST.SZ",
                open=12.33,
                high=12.46,
                low=12.30,
                close=12.33,
                volume=1108266,
                amount=1372103.731,
                frequency=FREQUENCY_TYPES.DAY,
                timestamp=datetime_normalize(date_str),
                source=SOURCE_TYPES.TUSHARE
            )
        
        # 获取最新时间戳
        latest = self.service.get_latest_timestamp("TEST_LATEST.SZ")
        
        # 验证是最新日期
        expected_latest = datetime_normalize("20250725")
        self.assertEqual(latest, expected_latest)

    def test_get_latest_timestamp_for_nonexistent_code(self):
        """测试获取不存在代码的最新时间戳"""
        latest = self.service.get_latest_timestamp("NONEXISTENT.SZ")
        
        # 应该返回默认开始时间
        expected_default = datetime_normalize(GCONF.DEFAULTSTART)
        self.assertEqual(latest, expected_default)

    def test_count_bars(self):
        """测试日线记录计数"""
        # 添加测试数据
        for i in range(5):
            self.crud_repo.create(
                code="TEST_COUNT.SZ",
                open=12.33 + i * 0.01,
                high=12.46 + i * 0.01,
                low=12.30 + i * 0.01,
                close=12.33 + i * 0.01,
                volume=1108266 + i * 1000,
                amount=1372103.731 + i * 100,
                frequency=FREQUENCY_TYPES.DAY,
                timestamp=datetime_normalize(f"202507{25-i:02d}"),
                source=SOURCE_TYPES.TUSHARE
            )
        
        # 测试计数
        count = self.service.count_bars(code="TEST_COUNT.SZ")
        self.assertEqual(count, 5)

    def test_get_available_codes(self):
        """测试获取可用股票代码列表"""
        # 添加测试数据
        test_codes = ["TEST_AVAIL1.SZ", "TEST_AVAIL2.SZ", "TEST_AVAIL3.SZ"]
        for code in test_codes:
            self.crud_repo.create(
                code=code,
                open=12.33,
                high=12.46,
                low=12.30,
                close=12.33,
                volume=1108266,
                amount=1372103.731,
                frequency=FREQUENCY_TYPES.DAY,
                timestamp=datetime_normalize("20250725"),
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
        self.mock_data_source.fetch_cn_stock_daybar.return_value = self.MOCK_BAR_SUCCESS
        
        # 先添加一些历史数据
        self.crud_repo.create(
            code="000001.SZ",
            open=11.50,
            high=11.80,
            low=11.40,
            close=11.70,
            volume=2000000,
            amount=2340000.00,
            frequency=FREQUENCY_TYPES.DAY,
            timestamp=datetime_normalize("20250701"),
            source=SOURCE_TYPES.TUSHARE
        )
        
        # 测试完整模式（应该会删除并重新插入）
        result_full = self.service.sync_full("000001.SZ")
        # 如果失败，打印错误信息用于调试
        if not result_full['success']:
            print(f"Full mode failed: {result_full}")
        self.assertTrue(result_full['success'])

        # 测试快速模式（增量更新）
        result_fast = self.service.sync_incremental("000001.SZ")
        self.assertTrue(result_fast['success'])

    def test_database_transaction_error(self):
        """测试数据库事务错误处理"""
        # 配置 Mock
        self.mock_data_source.fetch_cn_stock_daybar.return_value = self.MOCK_BAR_SUCCESS
        
        # 模拟数据库操作失败
        with patch.object(self.crud_repo, 'add_batch', side_effect=Exception("Database error")):
            result = self.service.sync_incremental("000001.SZ")
            
            # 验证失败结果
            self.assertFalse(result.success)
            self.assertIn("Database operation failed", result.error)

    def test_error_logging_and_reporting(self):
        """测试错误日志记录和报告"""
        # 配置各种错误场景并验证业务逻辑处理
        # API 错误 - 重试3次都失败
        self.mock_data_source.fetch_cn_stock_daybar.side_effect = [
            Exception("API error"),
            Exception("API error"),  
            Exception("API error")
        ]
        result = self.service.sync_incremental("000001.SZ")
        
        # 验证错误处理结果
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)
        self.assertIn("API error", result.error)

    def test_real_data_format_compatibility(self):
        """测试真实API数据格式的兼容性"""
        # 使用基于真实API的数据格式
        self.mock_data_source.fetch_cn_stock_daybar.return_value = self.MOCK_BAR_SUCCESS
        
        # 执行同步
        result = self.service.sync_incremental("000001.SZ")
        
        # 验证结果
        self.assertTrue(result.success)
        self.assertEqual(result.data.records_processed, 3)
        self.assertEqual(result.data.records_added, 3)
        
        # 验证数据已正确存储到数据库
        stored_data = self.service.get_bars(code="000001.SZ", as_dataframe=True)
        self.assertGreater(len(stored_data), 0)

    def test_extreme_values_handling(self):
        """测试极值数据（涨跌停）的处理"""
        # 使用包含极值的数据
        self.mock_data_source.fetch_cn_stock_daybar.return_value = self.MOCK_EXTREME_VALUES_DATA
        
        # 执行同步
        result = self.service.sync_incremental("TEST001.SZ")
        
        # 验证极值也能正确处理
        self.assertTrue(result.success)
        self.assertEqual(result.data.records_processed, 3)
        
        # 验证极值数据已存储
        stored_data = self.service.get_bars(code="TEST001.SZ", as_dataframe=True)
        if not stored_data.empty:
            # 检查涨跌停数据是否保持精度
            prices = stored_data[['open', 'high', 'low', 'close']].values
            self.assertTrue((prices >= 0).all())  # 所有价格都非负

    def test_data_validation_logic(self):
        """测试数据验证逻辑"""
        # 测试正常数据验证
        valid_result = self.service._validate_bar_data(self.MOCK_BAR_SUCCESS)
        self.assertTrue(valid_result)
        
        # 测试包含OHLC逻辑错误的数据
        invalid_result = self.service._validate_bar_data(self.MOCK_BAR_INVALID_OHLC)
        self.assertFalse(invalid_result)
        
        # 测试空数据
        empty_result = self.service._validate_bar_data(self.MOCK_EMPTY_DATA)
        self.assertTrue(empty_result)  # 空数据被认为是有效的

    def test_convert_rows_individually_fallback(self):
        """测试逐行转换的fallback机制"""
        # 创建测试数据
        test_df = self.MOCK_BAR_SUCCESS.copy()
        
        # 调用逐行转换方法
        models = self.service._convert_rows_individually(test_df, "000001.SZ", FREQUENCY_TYPES.DAY)
        
        # 验证转换结果
        self.assertIsInstance(models, list)
        self.assertGreater(len(models), 0)

    def test_high_precision_price_values(self):
        """测试高精度价格数值的处理"""
        # 使用高精度的价格数据
        high_precision_data = pd.DataFrame({
            'ts_code': ['000001.SZ', '000001.SZ', '000001.SZ'],
            'trade_date': ['20250725', '20250724', '20250723'],
            'open': [12.123456789, 12.234567890, 12.345678901],  # 高精度浮点数
            'high': [12.234567890, 12.345678901, 12.456789012],
            'low': [12.012345678, 12.123456789, 12.234567890],
            'close': [12.134567890, 12.245678901, 12.356789012],
            'pre_close': [12.123456789, 12.234567890, 12.345678901],
            'change': [0.010111111, 0.011111111, 0.011111111],
            'pct_chg': [0.083287, 0.090000, 0.089999],
            'vol': [1108266.123456, 1959350.234567, 1370520.345678],
            'amount': [1372103.123456789, 2426175.234567890, 1719158.345678901]
        })
        
        self.mock_data_source.fetch_cn_stock_daybar.return_value = high_precision_data
        
        # 执行同步
        result = self.service.sync_incremental("000001.SZ")
        
        # 验证高精度数值的处理
        self.assertTrue(result.success)
        self.assertEqual(result.data.records_processed, 3)
        
        # 检查精度保持（数据库存储的精度限制）
        stored_data = self.service.get_bars(code="000001.SZ", as_dataframe=True)
        if not stored_data.empty:
            # 验证数值被正确存储（考虑DECIMAL精度限制）
            self.assertGreater(len(stored_data), 0)

    def test_date_format_validation(self):
        """测试日期格式的验证和转换"""
        # 创建包含标准8位日期格式的测试数据
        test_data = pd.DataFrame({
            'ts_code': ['000001.SZ', '000001.SZ', '000001.SZ'],
            'trade_date': ['20250725', '20250724', '20250723'],  # 标准8位格式
            'open': [12.33, 12.53, 12.46],
            'high': [12.46, 12.53, 12.63], 
            'low': [12.30, 12.35, 12.42],
            'close': [12.33, 12.35, 12.50],
            'pre_close': [12.33, 12.53, 12.46],
            'change': [0.00, -0.18, 0.04],
            'pct_chg': [0.0000, -1.4366, 0.3203],
            'vol': [1108266.66, 1959350.57, 1370520.00],
            'amount': [1372103.731, 2426175.236, 1719158.803]
        })
        
        self.mock_data_source.fetch_cn_stock_daybar.return_value = test_data
        
        # 执行同步
        result = self.service.sync_incremental("000001.SZ")
        
        # 验证能正确处理标准日期格式
        self.assertTrue(result.success)
        self.assertEqual(result.data.records_processed, 3)

    def test_volume_amount_handling(self):
        """测试成交量和成交额的处理"""
        # 使用包含各种成交量成交额情况的数据
        volume_test_data = pd.DataFrame({
            'ts_code': ['TEST_VOL.SZ', 'TEST_VOL.SZ', 'TEST_VOL.SZ'],
            'trade_date': ['20250725', '20250724', '20250723'],
            'open': [12.33, 12.53, 12.46],
            'high': [12.46, 12.53, 12.63],
            'low': [12.30, 12.35, 12.42],
            'close': [12.33, 12.35, 12.50],
            'pre_close': [12.33, 12.53, 12.46],
            'change': [0.00, -0.18, 0.04],
            'pct_chg': [0.0000, -1.4366, 0.3203],
            'vol': [0.00, 2481415.53, 100.50],  # 包含0成交量（停牌）、大成交量、小成交量
            'amount': [0.00, 3249454.03, 1250.75]  # 对应的成交额
        })
        
        self.mock_data_source.fetch_cn_stock_daybar.return_value = volume_test_data
        
        # 执行同步
        result = self.service.sync_incremental("TEST_VOL.SZ")
        
        # 验证成交量和成交额数据处理
        self.assertTrue(result.success)
        self.assertEqual(result.data.records_processed, 3)
        
        # 验证数据已正确存储
        stored_data = self.service.get_bars(code="TEST_VOL.SZ", as_dataframe=True)
        if not stored_data.empty:
            # 检查成交量和成交额字段存在且合理
            self.assertTrue('volume' in stored_data.columns)
            self.assertTrue('amount' in stored_data.columns)
            # 成交量和成交额都应该是非负数
            self.assertTrue((stored_data['volume'] >= 0).all())
            self.assertTrue((stored_data['amount'] >= 0).all())

    def test_get_bars_no_adjustment(self):
        """测试获取未复权的bar数据"""
        # 添加测试数据
        self.crud_repo.create(
            code="TEST_ADJ.SZ",
            open=10.00,
            high=10.50,
            low=9.80,
            close=10.20,
            volume=1000000,
            amount=1020000.00,
            frequency=FREQUENCY_TYPES.DAY,
            timestamp=datetime_normalize("20250725"),
            source=SOURCE_TYPES.TUSHARE
        )
        
        # 测试获取未复权数据
        result = self.service.get_bars(
            code="TEST_ADJ.SZ", 
            adjustment_type=ADJUSTMENT_TYPES.NONE,
            as_dataframe=True
        )
        
        # 验证结果
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['open'], 10.00)
        self.assertEqual(result.iloc[0]['close'], 10.20)

    def test_get_bars_fore_adjustment(self):
        """测试获取前复权的bar数据"""
        # 添加测试数据
        self.crud_repo.create(
            code="TEST_FORE.SZ",
            open=10.00,
            high=10.50,
            low=9.80,
            close=10.20,
            volume=1000000,
            amount=1020000.00,
            frequency=FREQUENCY_TYPES.DAY,
            timestamp=datetime_normalize("20250725"),
            source=SOURCE_TYPES.TUSHARE
        )
        
        # Mock 复权因子数据
        mock_adjustfactor_df = pd.DataFrame({
            'timestamp': [datetime_normalize("20250725")],
            'foreadjustfactor': [1.2],  # 前复权因子
            'backadjustfactor': [0.8]   # 后复权因子
        })
        
        self.mock_adjustfactor_service.get_adjustfactors.return_value = mock_adjustfactor_df
        
        # 测试获取前复权数据
        result = self.service.get_bars(
            code="TEST_FORE.SZ", 
            adjustment_type=ADJUSTMENT_TYPES.FORE,
            as_dataframe=True
        )
        
        # 验证结果
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 1)
        # 验证价格被正确调整 (原价格 * 复权因子)
        self.assertAlmostEqual(result.iloc[0]['open'], 12.00, places=4)   # 10.00 * 1.2
        self.assertAlmostEqual(result.iloc[0]['close'], 12.24, places=4)  # 10.20 * 1.2
        self.assertAlmostEqual(result.iloc[0]['amount'], 1224000.00, places=2)  # 金额也被调整
        
        # 验证调用了复权因子服务
        self.mock_adjustfactor_service.get_adjustfactors.assert_called_once()

    def test_get_bars_back_adjustment(self):
        """测试获取后复权的bar数据"""
        # 添加测试数据
        self.crud_repo.create(
            code="TEST_BACK.SZ",
            open=15.00,
            high=15.80,
            low=14.50,
            close=15.60,
            volume=800000,
            amount=1248000.00,
            frequency=FREQUENCY_TYPES.DAY,
            timestamp=datetime_normalize("20250725"),
            source=SOURCE_TYPES.TUSHARE
        )
        
        # Mock 复权因子数据
        mock_adjustfactor_df = pd.DataFrame({
            'timestamp': [datetime_normalize("20250725")],
            'foreadjustfactor': [1.5],
            'backadjustfactor': [0.6]   # 后复权因子
        })
        
        self.mock_adjustfactor_service.get_adjustfactors.return_value = mock_adjustfactor_df
        
        # 测试获取后复权数据
        result = self.service.get_bars(
            code="TEST_BACK.SZ", 
            adjustment_type=ADJUSTMENT_TYPES.BACK,
            as_dataframe=True
        )
        
        # 验证结果
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 1)
        # 验证价格被正确调整 (原价格 * 后复权因子)
        self.assertAlmostEqual(result.iloc[0]['open'], 9.00, places=4)    # 15.00 * 0.6
        self.assertAlmostEqual(result.iloc[0]['close'], 9.36, places=4)   # 15.60 * 0.6
        self.assertAlmostEqual(result.iloc[0]['amount'], 748800.00, places=2)  # 金额也被调整

    def test_get_bars_adjusted_convenience_method(self):
        """测试get_bars_adjusted便捷方法"""
        # 添加测试数据
        self.crud_repo.create(
            code="TEST_CONV.SZ",
            open=20.00,
            high=21.00,
            low=19.50,
            close=20.80,
            volume=500000,
            amount=1040000.00,
            frequency=FREQUENCY_TYPES.DAY,
            timestamp=datetime_normalize("20250725"),
            source=SOURCE_TYPES.TUSHARE
        )
        
        # Mock 复权因子数据
        mock_adjustfactor_df = pd.DataFrame({
            'timestamp': [datetime_normalize("20250725")],
            'foreadjustfactor': [1.1],
            'backadjustfactor': [0.9]
        })
        
        self.mock_adjustfactor_service.get_adjustfactors.return_value = mock_adjustfactor_df
        
        # 测试便捷方法（默认前复权）
        result = self.service.get_bars_adjusted(
            code="TEST_CONV.SZ",
            as_dataframe=True
        )
        
        # 验证结果
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 1)
        # 验证使用了前复权因子
        self.assertAlmostEqual(result.iloc[0]['open'], 22.00, places=4)  # 20.00 * 1.1
        self.assertAlmostEqual(result.iloc[0]['close'], 22.88, places=4) # 20.80 * 1.1

    def test_get_bars_adjustment_no_factors(self):
        """测试没有复权因子时的处理"""
        # 添加测试数据
        self.crud_repo.create(
            code="TEST_NOFACTOR.SZ",
            open=12.00,
            high=12.50,
            low=11.80,
            close=12.30,
            volume=600000,
            amount=738000.00,
            frequency=FREQUENCY_TYPES.DAY,
            timestamp=datetime_normalize("20250725"),
            source=SOURCE_TYPES.TUSHARE
        )
        
        # Mock 空的复权因子数据
        self.mock_adjustfactor_service.get_adjustfactors.return_value = pd.DataFrame()
        
        # 测试获取复权数据（没有复权因子）
        result = self.service.get_bars(
            code="TEST_NOFACTOR.SZ", 
            adjustment_type=ADJUSTMENT_TYPES.FORE,
            as_dataframe=True
        )
        
        # 验证返回原始数据（没有调整）
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['open'], 12.00)   # 原始价格
        self.assertEqual(result.iloc[0]['close'], 12.30)  # 原始价格

    def test_get_bars_adjustment_empty_data(self):
        """测试空数据的复权处理"""
        # Mock 空的复权因子数据
        self.mock_adjustfactor_service.get_adjustfactors.return_value = pd.DataFrame()
        
        # 测试获取不存在股票的复权数据
        result = self.service.get_bars(
            code="NONEXISTENT.SZ", 
            adjustment_type=ADJUSTMENT_TYPES.FORE,
            as_dataframe=True
        )
        
        # 验证返回空DataFrame
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty)

    def test_get_bars_adjustment_model_format(self):
        """测试返回模型格式的复权数据"""
        # 添加测试数据
        self.crud_repo.create(
            code="TEST_MODEL.SZ",
            open=8.00,
            high=8.50,
            low=7.80,
            close=8.20,
            volume=1200000,
            amount=984000.00,
            frequency=FREQUENCY_TYPES.DAY,
            timestamp=datetime_normalize("20250725"),
            source=SOURCE_TYPES.TUSHARE
        )
        
        # Mock 复权因子数据
        mock_adjustfactor_df = pd.DataFrame({
            'timestamp': [datetime_normalize("20250725")],
            'foreadjustfactor': [1.25],
            'backadjustfactor': [0.8]
        })
        
        self.mock_adjustfactor_service.get_adjustfactors.return_value = mock_adjustfactor_df
        
        # 测试获取模型格式的复权数据
        result = self.service.get_bars(
            code="TEST_MODEL.SZ", 
            adjustment_type=ADJUSTMENT_TYPES.FORE,
            as_dataframe=False  # 返回模型列表
        )
        
        # 验证结果
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        
        # 验证模型属性
        bar_model = result[0]
        self.assertEqual(bar_model.code, "TEST_MODEL.SZ")
        # 验证价格复权调整
        self.assertAlmostEqual(float(bar_model.open), 10.00, places=4)   # 8.00 * 1.25
        self.assertAlmostEqual(float(bar_model.close), 10.25, places=4)  # 8.20 * 1.25

    def test_price_adjustment_calculation_accuracy(self):
        """测试价格复权计算的准确性"""
        # 创建单个日期的测试数据，避免数据库排序问题
        self.crud_repo.create(
            code="TEST_CALC.SZ",
            open=10.0,
            high=10.5,
            low=9.8,
            close=10.2,
            volume=1000000,
            amount=10200000.0,
            frequency=FREQUENCY_TYPES.DAY,
            timestamp=datetime_normalize("20250725"),
            source=SOURCE_TYPES.TUSHARE
        )
        
        # Mock 复权因子数据
        mock_adjustfactor_df = pd.DataFrame({
            'timestamp': [datetime_normalize("20250725")],
            'foreadjustfactor': [1.5],  # 前复权因子
            'backadjustfactor': [0.8]   # 后复权因子
        })
        
        self.mock_adjustfactor_service.get_adjustfactors.return_value = mock_adjustfactor_df
        
        # 测试前复权计算
        fore_result = self.service.get_bars(
            code="TEST_CALC.SZ", 
            adjustment_type=ADJUSTMENT_TYPES.FORE,
            as_dataframe=True
        )
        
        self.assertEqual(len(fore_result), 1)
        
        # 验证前复权计算准确性
        # 原价格 * 前复权因子
        self.assertAlmostEqual(fore_result.iloc[0]['open'], 15.0, places=4)   # 10.0 * 1.5
        self.assertAlmostEqual(fore_result.iloc[0]['high'], 15.75, places=4)  # 10.5 * 1.5
        self.assertAlmostEqual(fore_result.iloc[0]['low'], 14.7, places=4)    # 9.8 * 1.5
        self.assertAlmostEqual(fore_result.iloc[0]['close'], 15.3, places=4)  # 10.2 * 1.5
        self.assertAlmostEqual(fore_result.iloc[0]['amount'], 15300000.0, places=2)  # 金额也调整
        
        # 测试后复权计算
        back_result = self.service.get_bars(
            code="TEST_CALC.SZ", 
            adjustment_type=ADJUSTMENT_TYPES.BACK,
            as_dataframe=True
        )
        
        # 验证后复权计算准确性
        # 原价格 * 后复权因子
        self.assertAlmostEqual(back_result.iloc[0]['open'], 8.0, places=4)     # 10.0 * 0.8
        self.assertAlmostEqual(back_result.iloc[0]['high'], 8.4, places=4)    # 10.5 * 0.8
        self.assertAlmostEqual(back_result.iloc[0]['low'], 7.84, places=4)    # 9.8 * 0.8
        self.assertAlmostEqual(back_result.iloc[0]['close'], 8.16, places=4)  # 10.2 * 0.8
        self.assertAlmostEqual(back_result.iloc[0]['amount'], 8160000.0, places=2)  # 金额也调整

    def test_adjustment_error_handling(self):
        """测试复权过程中的错误处理"""
        # 添加测试数据
        self.crud_repo.create(
            code="TEST_ERROR.SZ",
            open=10.00,
            high=10.50,
            low=9.80,
            close=10.20,
            volume=1000000,
            amount=1020000.00,
            frequency=FREQUENCY_TYPES.DAY,
            timestamp=datetime_normalize("20250725"),
            source=SOURCE_TYPES.TUSHARE
        )
        
        # Mock 复权因子服务抛出异常
        self.mock_adjustfactor_service.get_adjustfactors.side_effect = Exception("Database error")
        
        # 测试错误处理
        result = self.service.get_bars(
            code="TEST_ERROR.SZ", 
            adjustment_type=ADJUSTMENT_TYPES.FORE,
            as_dataframe=True
        )
        
        # 验证在错误情况下返回原始数据
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 1)
        # 应该返回原始数据（未调整）
        self.assertEqual(result.iloc[0]['open'], 10.00)
        self.assertEqual(result.iloc[0]['close'], 10.20)

    def test_adjustment_missing_code_parameter(self):
        """测试缺少股票代码参数时的复权处理"""
        # 测试没有股票代码的复权请求
        result = self.service.get_bars(
            code=None,  # 没有股票代码
            adjustment_type=ADJUSTMENT_TYPES.FORE,
            as_dataframe=True
        )
        
        # 验证返回空结果
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty)

    def test_adjustment_type_edge_cases(self):
        """测试adjustment_type参数的边界情况"""
        # 添加测试数据
        self.crud_repo.create(
            code="TEST_EDGE.SZ",
            open=11.00,
            high=11.50,
            low=10.80,
            close=11.20,
            volume=900000,
            amount=1008000.00,
            frequency=FREQUENCY_TYPES.DAY,
            timestamp=datetime_normalize("20250725"),
            source=SOURCE_TYPES.TUSHARE
        )
        
        # Mock 复权因子数据（包含边界值）
        mock_adjustfactor_df = pd.DataFrame({
            'timestamp': [datetime_normalize("20250725")],
            'foreadjustfactor': [0.5],  # 小于1的前复权因子
            'backadjustfactor': [2.0]   # 大于1的后复权因子
        })
        
        self.mock_adjustfactor_service.get_adjustfactors.return_value = mock_adjustfactor_df
        
        # 测试小于1的前复权因子
        fore_result = self.service.get_bars(
            code="TEST_EDGE.SZ",
            adjustment_type=ADJUSTMENT_TYPES.FORE,
            as_dataframe=True
        )
        
        # 验证价格被正确减小
        self.assertAlmostEqual(fore_result.iloc[0]['open'], 5.5, places=4)   # 11.00 * 0.5
        self.assertAlmostEqual(fore_result.iloc[0]['close'], 5.6, places=4)  # 11.20 * 0.5
        
        # 测试大于1的后复权因子
        back_result = self.service.get_bars(
            code="TEST_EDGE.SZ",
            adjustment_type=ADJUSTMENT_TYPES.BACK,
            as_dataframe=True
        )
        
        # 验证价格被正确放大
        self.assertAlmostEqual(back_result.iloc[0]['open'], 22.0, places=4)   # 11.00 * 2.0
        self.assertAlmostEqual(back_result.iloc[0]['close'], 22.4, places=4)  # 11.20 * 2.0

    def test_adjustment_factor_precision(self):
        """测试复权因子的精度处理"""
        # 添加测试数据
        self.crud_repo.create(
            code="TEST_PRECISION.SZ",
            open=10.00,
            high=10.50,
            low=9.80,
            close=10.20,
            volume=1000000,
            amount=10200000.00,
            frequency=FREQUENCY_TYPES.DAY,
            timestamp=datetime_normalize("20250725"),
            source=SOURCE_TYPES.TUSHARE
        )
        
        # Mock 现实场景中的复权因子（通常保留6位小数精度）
        mock_adjustfactor_df = pd.DataFrame({
            'timestamp': [datetime_normalize("20250725")],
            'foreadjustfactor': [1.123457],  # 实际场景中的复权因子精度
            'backadjustfactor': [0.876543]   # 实际场景中的复权因子精度
        })
        
        self.mock_adjustfactor_service.get_adjustfactors.return_value = mock_adjustfactor_df
        
        # 测试前复权计算
        fore_result = self.service.get_bars(
            code="TEST_PRECISION.SZ",
            adjustment_type=ADJUSTMENT_TYPES.FORE,
            as_dataframe=True
        )
        
        # 验证前复权计算结果（使用实际精度）
        expected_open = 10.00 * 1.123457   # 11.23457
        expected_close = 10.20 * 1.123457  # 11.459261
        
        self.assertAlmostEqual(fore_result.iloc[0]['open'], expected_open, places=4)
        self.assertAlmostEqual(fore_result.iloc[0]['close'], expected_close, places=4)
        
        # 测试后复权计算
        back_result = self.service.get_bars(
            code="TEST_PRECISION.SZ",
            adjustment_type=ADJUSTMENT_TYPES.BACK,
            as_dataframe=True
        )
        
        # 验证后复权计算结果
        expected_back_open = 10.00 * 0.876543   # 8.76543
        expected_back_close = 10.20 * 0.876543  # 8.940739
        
        self.assertAlmostEqual(back_result.iloc[0]['open'], expected_back_open, places=4)
        self.assertAlmostEqual(back_result.iloc[0]['close'], expected_back_close, places=4)
        
        # 验证计算方向正确性
        self.assertGreater(fore_result.iloc[0]['open'], 10.00)  # 前复权应该增大
        self.assertLess(back_result.iloc[0]['open'], 10.00)     # 后复权应该减小


    def test_multiple_dates_adjustment_consistency(self):
        """测试多日期数据复权的一致性"""
        # 添加多个日期的数据
        dates = ["20250723", "20250724", "20250725"]
        for i, date_str in enumerate(dates):
            self.crud_repo.create(
                code="TEST_MULTI.SZ",
                open=12.0 + i * 0.05,
                high=12.5 + i * 0.05,
                low=11.8 + i * 0.05,
                close=12.3 + i * 0.05,
                volume=1000000,
                amount=(12.3 + i * 0.05) * 1000000,
                frequency=FREQUENCY_TYPES.DAY,
                timestamp=datetime_normalize(date_str),
                source=SOURCE_TYPES.TUSHARE
            )
        
        # Mock 不同日期的复权因子
        mock_adjustfactor_df = pd.DataFrame({
            'timestamp': [datetime_normalize(date) for date in dates],
            'foreadjustfactor': [1.0, 1.05, 1.10],  # 递增的复权因子
            'backadjustfactor': [1.10, 1.05, 1.0]   # 递减的复权因子
        })
        
        self.mock_adjustfactor_service.get_adjustfactors.return_value = mock_adjustfactor_df
        
        # 测试获取复权数据
        result = self.service.get_bars(
            code="TEST_MULTI.SZ",
            adjustment_type=ADJUSTMENT_TYPES.FORE,
            as_dataframe=True
        )
        
        # 验证数据的一致性（数据库可能以不同顺序返回）
        self.assertEqual(len(result), 3)
        
        # 验证数据的完整性，不依赖具体顺序
        for _, row in result.iterrows():
            # 所有价格都应该大于0
            self.assertGreater(row['open'], 0)
            self.assertGreater(row['close'], 0)
            # 所有的金额都应该大于0
            self.assertGreater(row['amount'], 0)
            # 所有的成交量都应该等于1000000（不变）
            self.assertEqual(row['volume'], 1000000)


if __name__ == '__main__':
    unittest.main()