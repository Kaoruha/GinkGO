import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

try:
    from ginkgo.data.services.tick_service import TickService
    from ginkgo.data.crud.tick_crud import TickCRUD
    from ginkgo.data.models import MTick
    from ginkgo.enums import SOURCE_TYPES, TICKDIRECTION_TYPES, ADJUSTMENT_TYPES
    from ginkgo.libs import GCONF, datetime_normalize
    from ginkgo.data.drivers import create_table, drop_table
    from ginkgo.backtest import Tick
except ImportError as e:
    print(f"Import error: {e}")
    TickService = None
    GCONF = None


class TickServiceTest(unittest.TestCase):
    """
    TickService 单元测试
    测试增强的错误处理功能和高频数据处理能力
    """

    # Mock tick数据 - 基于真实 TDX API 格式（从真实API收集的格式）
    MOCK_TICK_SUCCESS = pd.DataFrame({
        'time': ['09:25', '09:30', '09:30', '09:31', '09:31'],
        'price': [9.16, 9.16, 9.16, 9.17, 9.17],  # float64类型，基于真实数据
        'vol': [4966, 1049, 38, 200, 150],  # int64类型，包含集合竞价大量
        'buyorsell': [2, 0, 0, 1, 0],  # int64类型：0=买盘，1=卖盘，2=其他
        'volume': [4966, 1049, 38, 200, 150],  # 与vol相同，真实TDX格式
        'timestamp': [
            pd.Timestamp('2024-01-15 09:25:00'),
            pd.Timestamp('2024-01-15 09:30:00'), 
            pd.Timestamp('2024-01-15 09:30:00'),
            pd.Timestamp('2024-01-15 09:31:00'),
            pd.Timestamp('2024-01-15 09:31:00')
        ]
    })

    MOCK_TICK_INVALID_DATA = pd.DataFrame({
        'time': ['09:30', '09:31', '09:32'],
        'price': [9.16, -1.0, 9.18],  # 包含负价格
        'vol': [100, 200, -50],  # 包含负成交量
        'buyorsell': [0, 9, 1],  # 包含无效方向值（9）- 真实TDX只有0,1,2有效
        'volume': [100, 200, -50],
        'timestamp': [
            pd.Timestamp('2024-01-17 09:30:00'),
            pd.Timestamp('2024-01-17 09:31:00'),
            pd.Timestamp('2024-01-17 09:32:00')
        ]
    })

    MOCK_EMPTY_DATA = pd.DataFrame()
    
    # 时间范围Mock数据 - 基于真实TDX格式的多日期数据集
    MOCK_TICK_DATE_RANGE_DATA = {
        "2024-01-15": pd.DataFrame({
            'time': ['09:25', '09:30', '09:30', '09:31', '09:31'],
            'price': [9.16, 9.16, 9.16, 9.17, 9.17],
            'vol': [4966, 1049, 38, 200, 150],
            'buyorsell': [2, 0, 0, 1, 0],  # 集合竞价=2, 买盘=0, 卖盘=1
            'volume': [4966, 1049, 38, 200, 150],
            'timestamp': [
                pd.Timestamp('2024-01-15 09:25:00'),
                pd.Timestamp('2024-01-15 09:30:00'),
                pd.Timestamp('2024-01-15 09:30:00'),
                pd.Timestamp('2024-01-15 09:31:00'),
                pd.Timestamp('2024-01-15 09:31:00')
            ]
        }),
        "2024-01-16": pd.DataFrame({
            'time': ['09:25', '09:30', '09:31', '09:32'],
            'price': [9.18, 9.18, 9.19, 9.18],
            'vol': [5200, 800, 150, 300],
            'buyorsell': [2, 0, 1, 0],
            'volume': [5200, 800, 150, 300],
            'timestamp': [
                pd.Timestamp('2024-01-16 09:25:00'),
                pd.Timestamp('2024-01-16 09:30:00'),
                pd.Timestamp('2024-01-16 09:31:00'),
                pd.Timestamp('2024-01-16 09:32:00')
            ]
        }),
        "2024-01-17": MOCK_TICK_INVALID_DATA,  # 使用含数据质量问题的数据
        "2024-01-18": MOCK_EMPTY_DATA,        # 无数据日期（如周末）
        "2024-01-19": pd.DataFrame({
            'time': ['09:25', '09:30', '09:31'],
            'price': [9.20, 9.21, 9.20],
            'vol': [4800, 600, 200],
            'buyorsell': [2, 0, 1],
            'volume': [4800, 600, 200],
            'timestamp': [
                pd.Timestamp('2024-01-19 09:25:00'),
                pd.Timestamp('2024-01-19 09:30:00'),
                pd.Timestamp('2024-01-19 09:31:00')
            ]
        }),
        "2024-01-20": MOCK_EMPTY_DATA,        # 周末无数据
    }
    
    # 大批量tick数据（模拟真实单日数据量）
    MOCK_LARGE_TICK_DATA = pd.DataFrame({
        'time': [f"09:{15+i//100:02d}" for i in range(5000)],  # 模拟5000条tick
        'price': [12.35 + (i % 50) * 0.01 for i in range(5000)],  # 价格在合理范围波动
        'vol': [100 + i % 500 for i in range(5000)],  # 成交量变化
        'buyorsell': [i % 2 for i in range(5000)],  # 买卖方向交替
        'volume': [100 + i % 500 for i in range(5000)],
        'timestamp': [pd.Timestamp('2025-07-25 09:15:00') + timedelta(seconds=i) for i in range(5000)]
    })
    
    # 跨多日期数据（数据质量问题）
    MOCK_MULTI_DATE_DATA = pd.DataFrame({
        'time': ['09:15', '09:16', '14:30'],
        'price': [12.35, 12.36, 12.37],
        'vol': [100, 200, 150],
        'buyorsell': [0, 1, 0],
        'volume': [100, 200, 150],
        'timestamp': [
            pd.Timestamp('2025-07-25 09:15:00'),
            pd.Timestamp('2025-07-25 09:16:00'),
            pd.Timestamp('2025-07-26 14:30:00')  # 不同日期
        ]
    })

    @classmethod
    def setUpClass(cls):
        """类级别设置"""
        if TickService is None or GCONF is None:
            raise AssertionError("TickService or GCONF not available")

        # 不需要预创建tick表，因为是动态按股票代码创建的
        print(":white_check_mark: TickService test setup completed")

    def setUp(self):
        """每个测试前的设置"""
        # 创建 Mock 依赖
        self.mock_crud_repo = Mock()
        self.mock_data_source = Mock()
        self.mock_stockinfo_service = Mock()
        
        # 默认设置：股票代码存在于股票列表中
        self.mock_stockinfo_service.is_code_in_stocklist.return_value = True
        
        # Mock股票信息服务返回
        mock_stock_info = pd.DataFrame({
            'code': ['000001.SZ'],
            'list_date': ['20100101'],
            'delist_date': ['20991231']
        })
        self.mock_stockinfo_service.get_stockinfos.return_value = mock_stock_info
        
        # 创建 Mock AdjustfactorService
        self.mock_adjustfactor_service = Mock()
        
        # 创建 TickService 实例
        self.service = TickService(
            crud_repo=self.mock_crud_repo,
            data_source=self.mock_data_source,
            stockinfo_service=self.mock_stockinfo_service,
            adjustfactor_service=self.mock_adjustfactor_service
        )
        
    def _mock_fetch_tick_by_date(self, code: str, date: datetime):
        """根据日期返回对应的Mock tick数据"""
        date_str = date.strftime("%Y-%m-%d")
        return self.MOCK_TICK_DATE_RANGE_DATA.get(date_str, pd.DataFrame())

    def test_sync_incremental_on_date_success(self):
        """测试成功同步单个股票单日的tick数据"""
        # 配置 Mock
        self.mock_data_source.fetch_history_transaction_detail.return_value = self.MOCK_TICK_SUCCESS
        
        test_date = datetime(2025, 7, 25)
        
        # 执行同步
        result = self.service.sync_for_code_on_date("000001.SZ", test_date)
        
        # 验证返回结果
        self.assertIsInstance(result, dict)
        self.assertTrue(result['success'])
        self.assertEqual(result['code'], '000001.SZ')
        self.assertEqual(result['records_processed'], 5)
        self.assertGreater(result['records_added'], 0)
        self.assertIsNone(result['error'])
        self.assertIsInstance(result['warnings'], list)
        self.assertFalse(result['skipped'])

    def test_sync_incremental_on_date_invalid_stock_code(self):
        """测试无效股票代码的处理"""
        # 配置 Mock：股票代码不在列表中
        self.mock_stockinfo_service.is_code_in_stocklist.return_value = False
        
        test_date = datetime(2025, 7, 25)
        
        # 执行同步
        result = self.service.sync_for_code_on_date("INVALID.SZ", test_date)
        
        # 验证返回结果
        self.assertFalse(result['success'])
        self.assertEqual(result['code'], 'INVALID.SZ')
        self.assertEqual(result['records_processed'], 0)
        self.assertEqual(result['records_added'], 0)
        self.assertIn("not in stock list", result['error'])

    def test_sync_incremental_on_date_empty_data(self):
        """测试处理空数据响应"""
        # 配置 Mock 返回空数据
        self.mock_data_source.fetch_history_transaction_detail.return_value = self.MOCK_EMPTY_DATA
        
        test_date = datetime(2025, 7, 25)
        
        # 执行同步
        result = self.service.sync_for_code_on_date("000001.SZ", test_date)
        
        # 验证返回结果
        self.assertTrue(result['success'])  # 空数据也是成功的情况
        self.assertEqual(result['records_processed'], 0)
        self.assertEqual(result['records_added'], 0)
        self.assertIn("No data available from source", result['warnings'][0])

    def test_sync_incremental_on_date_api_failure(self):
        """测试API调用失败的处理（重试3次）"""
        # 配置 Mock 抛出异常 - 重试3次都失败
        self.mock_data_source.fetch_history_transaction_detail.side_effect = [
            Exception("TDX connection failed"),
            Exception("TDX connection failed"),
            Exception("TDX connection failed")
        ]
        
        test_date = datetime(2025, 7, 25)
        
        # 执行同步
        result = self.service.sync_for_code_on_date("000001.SZ", test_date)
        
        # 验证返回结果
        self.assertFalse(result['success'])
        self.assertEqual(result['records_processed'], 0)
        self.assertEqual(result['records_added'], 0)
        self.assertIn("Failed to fetch data from source", result['error'])

    def test_sync_incremental_on_date_data_validation_failure(self):
        """测试数据验证检测到严重问题 - 实现会直接返回失败"""
        # 配置 Mock 返回包含严重无效数据的结果
        self.mock_data_source.fetch_history_transaction_detail.return_value = self.MOCK_TICK_INVALID_DATA
        
        test_date = datetime(2025, 7, 25)
        
        # 执行同步
        result = self.service.sync_for_code_on_date("000001.SZ", test_date)
        
        # 验证结果 - 数据质量验证失败应该导致处理失败
        self.assertFalse(result['success'], "数据质量验证失败应该导致处理失败")
        self.assertEqual(result['records_processed'], 3, "仍然会统计处理的记录数")
        self.assertIsNotNone(result['error'], "应该有错误信息")
        self.assertEqual(result['error'], "Data quality validation failed", "错误信息应该指明验证失败")
        
        # 验证记录未被添加到数据库
        self.assertEqual(result['records_added'], 0, "验证失败时不应该添加任何记录")
        
        # TODO: 考虑在未来版本中添加strict_validation参数，
        # 允许用户选择是否在遇到严重数据质量问题时停止处理
        # 严重问题包括：负价格、负成交量、无效买卖方向等


    def test_sync_incremental_on_date_fast_mode_skip(self):
        """测试快速模式下跳过已存在数据"""
        # 配置 Mock：get_ticks返回已存在的数据
        existing_data = pd.DataFrame({
            'code': ['000001.SZ'] * 3,
            'price': [12.35, 12.36, 12.37],
            'volume': [100, 200, 150],
            'timestamp': [
                datetime(2025, 7, 25, 9, 15),
                datetime(2025, 7, 25, 9, 16),
                datetime(2025, 7, 25, 9, 17)
            ]
        })
        
        # Mock get_ticks方法
        with patch.object(self.service, 'get_ticks', return_value=existing_data):
            test_date = datetime(2025, 7, 25)
            
            # 执行同步（快速模式）
            result = self.service.sync_for_code_on_date("000001.SZ", test_date)
            
            # 验证跳过结果
            self.assertTrue(result['success'])
            self.assertTrue(result['skipped'])
            self.assertEqual(result['records_processed'], 0)
            self.assertEqual(result['records_added'], 0)
            self.assertIn("Data already exists in DB", result['warnings'][0])

    def test_sync_incremental_on_date_partial_mapping_failure(self):
        """测试部分数据映射失败的容错处理"""
        # 配置 Mock 返回数据
        self.mock_data_source.fetch_history_transaction_detail.return_value = self.MOCK_TICK_SUCCESS
        
        test_date = datetime(2025, 7, 25)
        
        # Mock mappers 函数的行为
        with patch('ginkgo.data.services.tick_service.mappers') as mock_mappers:
            # 创建正确的 Tick mock 对象
            mock_tick = MagicMock()
            mock_tick.code = "000001.SZ"
            mock_tick.price = 12.35
            mock_tick.volume = 100
            mock_tick.direction = TICKDIRECTION_TYPES.OTHER
            mock_tick.timestamp = datetime(2025, 7, 25, 9, 15)
            mock_tick.source = SOURCE_TYPES.TDX
            
            # 第一次批量转换失败，然后逐行转换成功
            mock_mappers.dataframe_to_tick_models.side_effect = [
                Exception("Batch conversion failed"),  # 批量转换失败
                [mock_tick],  # 第一行成功
                [mock_tick],  # 第二行成功  
                [mock_tick],  # 第三行成功
                [mock_tick],  # 第四行成功
                [mock_tick]   # 第五行成功
            ]
            
            # 执行同步
            result = self.service.sync_for_code_on_date("000001.SZ", test_date)
            
            # 验证结果
            self.assertTrue(result['success'])  # 有部分成功就算成功
            self.assertEqual(result['records_processed'], 5)
            self.assertGreater(len(result['warnings']), 0)  # 应该有警告信息

    def test_retry_mechanism(self):
        """测试重试机制"""
        # 重置 Mock 的调用计数
        self.mock_data_source.reset_mock()
        
        # 配置 Mock：前两次失败，第三次成功
        self.mock_data_source.fetch_history_transaction_detail.side_effect = [
            Exception("Network error"),
            Exception("Timeout error"),
            self.MOCK_TICK_SUCCESS
        ]
        
        test_date = datetime(2025, 7, 25)
        
        # 执行同步
        result = self.service.sync_for_code_on_date("000001.SZ", test_date)
        
        # 验证重试后成功
        self.assertTrue(result['success'])
        self.assertEqual(result['records_processed'], 5)
        
        # 验证调用了3次（前两次失败，第三次成功）
        self.assertEqual(self.mock_data_source.fetch_history_transaction_detail.call_count, 3)

    def test_large_tick_data_processing(self):
        """测试大批量tick数据的处理能力"""
        # 配置 Mock 返回大量数据
        self.mock_data_source.fetch_history_transaction_detail.return_value = self.MOCK_LARGE_TICK_DATA
        
        test_date = datetime(2025, 7, 25)
        
        # 执行同步
        result = self.service.sync_for_code_on_date("000001.SZ", test_date)
        
        # 验证大批量数据处理
        self.assertTrue(result['success'])
        self.assertEqual(result['records_processed'], 5000)
        self.assertEqual(result['records_added'], 5000)

    def test_database_transaction_error(self):
        """测试数据库操作错误处理"""
        # 配置 Mock
        self.mock_data_source.fetch_history_transaction_detail.return_value = self.MOCK_TICK_SUCCESS
        
        test_date = datetime(2025, 7, 25)
        
        # Mock TickCRUD 以模拟数据库错误
        with patch('ginkgo.data.crud.tick_crud.TickCRUD') as mock_tick_crud_class:
            mock_tick_crud = Mock()
            mock_tick_crud.remove.return_value = 0
            mock_tick_crud.add_batch.side_effect = Exception("Database error")
            mock_tick_crud_class.return_value = mock_tick_crud
            
            result = self.service.sync_for_code_on_date("000001.SZ", test_date)
            
            # 验证失败结果
            self.assertFalse(result['success'])
            self.assertIn("Database operation failed", result['error'])

    def test_sync_incremental_batch_success(self):
        """测试多日期批量同步成功场景"""
        # 配置 Mock
        self.mock_data_source.fetch_history_transaction_detail.return_value = self.MOCK_TICK_SUCCESS
        
        # 执行批量同步（限制3天避免测试时间过长）
        result = self.service.sync_incremental("000001.SZ", max_backtrack_days=3)
        
        # 验证批量结果
        self.assertIsInstance(result, dict)
        self.assertEqual(result['code'], '000001.SZ')
        # max_backtrack_days 参数可能包含当天，所以实际处理的天数可能会有变化
        self.assertGreaterEqual(result['total_dates_processed'], 3)
        self.assertLessEqual(result['total_dates_processed'], 4)
        self.assertGreaterEqual(result['successful_dates'], 0)
        self.assertIsInstance(result['results'], list)
        self.assertIsInstance(result['failures'], list)

    def test_sync_incremental_invalid_stock_code(self):
        """测试批量同步无效股票代码"""
        # 配置 Mock：股票代码无效
        self.mock_stockinfo_service.is_code_in_stocklist.return_value = False
        
        # 执行批量同步
        result = self.service.sync_incremental("INVALID.SZ", max_backtrack_days=1)
        
        # 验证批量结果
        self.assertEqual(result['code'], 'INVALID.SZ')
        self.assertEqual(result['total_dates_processed'], 0)
        self.assertEqual(len(result['failures']), 1)
        self.assertIn("not in stock list", result['failures'][0]['error'])

    def test_sync_incremental_no_stock_info(self):
        """测试无法获取股票信息的情况"""
        # 配置 Mock：无股票信息
        self.mock_stockinfo_service.get_stockinfos.return_value = pd.DataFrame()
        
        # 执行批量同步
        result = self.service.sync_incremental("000001.SZ", max_backtrack_days=1)
        
        # 验证结果
        self.assertEqual(result['code'], '000001.SZ')
        self.assertEqual(result['total_dates_processed'], 0)
        self.assertEqual(len(result['failures']), 1)
        self.assertIn("No stock info found", result['failures'][0]['error'])

    def test_get_ticks_caching(self):
        """测试tick数据获取和缓存功能"""
        # Mock crud_repo的find方法
        mock_tick_data = pd.DataFrame({
            'code': ['000001.SZ'] * 3,
            'price': [12.35, 12.36, 12.37],
            'volume': [100, 200, 150],
            'timestamp': [
                datetime(2025, 7, 25, 9, 15),
                datetime(2025, 7, 25, 9, 16),
                datetime(2025, 7, 25, 9, 17)
            ]
        })
        self.mock_crud_repo.find.return_value = mock_tick_data
        
        # 测试数据获取
        result = self.service.get_ticks(code="000001.SZ", as_dataframe=True)
        
        # 验证结果
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 3)
        
        # 验证缓存（第二次调用）
        result2 = self.service.get_ticks(code="000001.SZ", as_dataframe=True)
        self.assertTrue(result.equals(result2))

    def test_count_ticks(self):
        """测试tick记录计数"""
        # Mock crud_repo的count方法
        self.mock_crud_repo.count.return_value = 1500
        
        test_date = datetime(2025, 7, 25)
        
        # 测试计数
        count = self.service.count_ticks(code="000001.SZ", date=test_date)
        self.assertEqual(count, 1500)

    def test_is_tick_data_available(self):
        """测试tick数据可用性检查"""
        # Mock count_ticks方法
        with patch.object(self.service, 'count_ticks', return_value=1500):
            test_date = datetime(2025, 7, 25)
            
            # 测试数据可用性
            available = self.service.is_tick_data_available("000001.SZ", test_date)
            self.assertTrue(available)
        
        # 测试无数据情况
        with patch.object(self.service, 'count_ticks', return_value=0):
            available = self.service.is_tick_data_available("000001.SZ", test_date)
            self.assertFalse(available)

    def test_get_available_codes(self):
        """测试获取可用股票代码列表"""
        # Mock crud_repo的find方法
        mock_codes = ["000001.SZ", "000002.SZ", "600519.SH"]
        self.mock_crud_repo.find.return_value = mock_codes
        
        # 获取可用代码
        available_codes = self.service.get_available_codes()
        
        # 验证结果
        self.assertIsInstance(available_codes, list)
        self.assertEqual(len(available_codes), 3)
        self.assertIn("000001.SZ", available_codes)

    def test_get_available_codes_error_handling(self):
        """测试获取可用代码时的错误处理"""
        # Mock crud_repo抛出异常
        self.mock_crud_repo.find.side_effect = Exception("Database error")
        
        # 获取可用代码
        available_codes = self.service.get_available_codes()
        
        # 验证错误处理
        self.assertEqual(available_codes, [])

    def test_clear_cache_for_code(self):
        """测试清除Redis缓存 - 适配RedisService集成"""
        # Mock RedisService的clear_sync_progress方法
        with patch.object(self.service.redis_service, 'clear_sync_progress', return_value=True) as mock_clear:
            # 执行缓存清除
            self.service.clear_cache_for_code("000001.SZ")
            
            # 验证RedisService调用
            mock_clear.assert_called_with("000001.SZ", "tick")

    def test_clear_cache_redis_failure(self):
        """测试Redis缓存清除失败的处理 - 适配RedisService集成"""
        # Mock RedisService的clear_sync_progress方法失败
        with patch.object(self.service.redis_service, 'clear_sync_progress', return_value=False) as mock_clear:
            # 执行缓存清除（不应该抛出异常）
            try:
                self.service.clear_cache_for_code("000001.SZ")
                # 验证方法被调用
                mock_clear.assert_called_with("000001.SZ", "tick")
            except Exception:
                self.fail("clear_cache_for_code raised an exception when it shouldn't")

    def test_validate_tick_data(self):
        """测试tick数据验证逻辑"""
        # 测试正常数据验证
        valid_result = self.service._validate_tick_data(self.MOCK_TICK_SUCCESS)
        self.assertTrue(valid_result)
        
        # 测试包含问题的数据
        invalid_result = self.service._validate_tick_data(self.MOCK_TICK_INVALID_DATA)
        self.assertFalse(invalid_result)  # 包含关键数据质量问题时返回False
        
        # 测试空数据
        empty_result = self.service._validate_tick_data(self.MOCK_EMPTY_DATA)
        self.assertTrue(empty_result)  # 空数据被认为是有效的
        
        # 测试跨日期数据
        multi_date_result = self.service._validate_tick_data(self.MOCK_MULTI_DATE_DATA)
        self.assertTrue(multi_date_result)  # 会有警告但返回True

    def test_convert_ticks_individually_fallback(self):
        """测试逐行转换的fallback机制"""
        # 创建测试数据
        test_df = self.MOCK_TICK_SUCCESS.copy()
        
        # 调用逐行转换方法
        models = self.service._convert_ticks_individually(test_df, "000001.SZ")
        
        # 由于mappers.dataframe_to_tick_models没有Mock，这里主要测试方法不会抛异常
        self.assertIsInstance(models, list)

    def test_fetch_tick_data_with_validation(self):
        """测试带验证的数据获取"""
        # 配置 Mock
        self.mock_data_source.fetch_history_transaction_detail.return_value = self.MOCK_TICK_SUCCESS
        
        test_date = datetime(2025, 7, 25)
        
        # 调用获取方法
        data = self.service._fetch_tick_data_with_validation("000001.SZ", test_date)
        
        # 验证结果
        self.assertIsInstance(data, pd.DataFrame)
        self.assertEqual(len(data), 5)

    def test_real_data_format_compatibility(self):
        """测试真实TDX API数据格式的兼容性"""
        # 使用基于真实API的数据格式
        self.mock_data_source.fetch_history_transaction_detail.return_value = self.MOCK_TICK_SUCCESS
        
        test_date = datetime(2025, 7, 25)
        
        # 执行同步
        result = self.service.sync_for_code_on_date("000001.SZ", test_date)
        
        # 验证结果
        self.assertTrue(result['success'])
        self.assertEqual(result['records_processed'], 5)
        # 注意：某些数据可能在映射过程中被过滤（如集合竞价数据）
        self.assertGreaterEqual(result['records_added'], 4)
        self.assertLessEqual(result['records_added'], 5)

    def test_buyorsell_direction_handling(self):
        """测试买卖方向字段的处理"""
        # 创建包含所有有效买卖方向的数据
        direction_test_data = pd.DataFrame({
            'time': ['09:15', '09:16', '09:17', '09:18'],
            'price': [12.35, 12.36, 12.37, 12.38],
            'vol': [100, 200, 150, 250],
            'buyorsell': [0, 1, 2, 8],  # 所有有效方向值
            'volume': [100, 200, 150, 250],
            'timestamp': [
                pd.Timestamp('2025-07-25 09:15:00'),
                pd.Timestamp('2025-07-25 09:16:00'),
                pd.Timestamp('2025-07-25 09:17:00'),
                pd.Timestamp('2025-07-25 09:18:00')
            ]
        })
        
        # 配置 Mock
        self.mock_data_source.fetch_history_transaction_detail.return_value = direction_test_data
        
        test_date = datetime(2025, 7, 25)
        
        # 执行同步
        result = self.service.sync_for_code_on_date("000001.SZ", test_date)
        
        # 验证买卖方向数据处理
        self.assertTrue(result['success'])
        self.assertEqual(result['records_processed'], 4)

    def test_high_frequency_timestamp_handling(self):
        """测试高频时间戳的处理"""
        # 创建高频tick数据（秒级时间戳）
        high_freq_data = pd.DataFrame({
            'time': ['09:15', '09:15', '09:15'],  # 同一分钟内多笔
            'price': [12.35, 12.36, 12.35],
            'vol': [100, 50, 200],
            'buyorsell': [0, 1, 0],
            'volume': [100, 50, 200],
            'timestamp': [
                pd.Timestamp('2025-07-25 09:15:01'),
                pd.Timestamp('2025-07-25 09:15:02'),
                pd.Timestamp('2025-07-25 09:15:03')
            ]
        })
        
        # 配置 Mock
        self.mock_data_source.fetch_history_transaction_detail.return_value = high_freq_data
        
        test_date = datetime(2025, 7, 25)
        
        # 执行同步
        result = self.service.sync_for_code_on_date("000001.SZ", test_date)
        
        # 验证高频数据处理
        self.assertTrue(result['success'])
        self.assertEqual(result['records_processed'], 3)

    def test_error_logging_and_reporting(self):
        """测试错误日志记录和报告"""
        # 配置各种错误场景并验证业务逻辑处理
        # API 错误 - 重试3次都失败
        self.mock_data_source.fetch_history_transaction_detail.side_effect = [
            Exception("TDX error"),
            Exception("TDX error"),  
            Exception("TDX error")
        ]
        
        test_date = datetime(2025, 7, 25)
        result = self.service.sync_for_code_on_date("000001.SZ", test_date)
        
        # 验证错误处理结果
        self.assertFalse(result['success'])
        self.assertIsNotNone(result['error'])
        self.assertIn("TDX error", result['error'])

    # ==================== 时间范围更新测试 ====================
    
    def test_sync_incremental_with_date_range_real_format(self):
        """测试使用真实TDX格式的时间范围同步"""
        # 配置Mock：根据日期返回对应数据
        self.mock_data_source.fetch_history_transaction_detail.side_effect = self._mock_fetch_tick_by_date
        
        # 测试时间范围：2024-01-15 到 2024-01-17
        start_date = datetime(2024, 1, 15)
        end_date = datetime(2024, 1, 17)
        
        # 执行时间范围同步
        result = self.service.sync_for_code_with_date_range(
            code="000001.SZ", 
            start_date=start_date, 
            end_date=end_date,
            fast_mode=True,
            use_cache=True
        )
        
        # 验证返回结果结构
        self.assertIsInstance(result, dict)
        self.assertEqual(result['code'], '000001.SZ')
        self.assertEqual(result['start_date'], start_date.date())
        self.assertEqual(result['end_date'], end_date.date())
        self.assertEqual(result['total_dates'], 3)  # 3天范围
        
        # 验证统计信息（考虑缓存情况）
        total_processed = result['successful_dates'] + result['resumed_from_cache']
        self.assertEqual(total_processed, 2)  # 总计2天成功处理（2024-01-15, 2024-01-16）
        self.assertEqual(result['failed_dates'], 1)  # 1天失败（2024-01-17数据质量问题）
        
        # 如果有新数据处理，验证记录数
        if result['successful_dates'] > 0:
            self.assertGreater(result['total_records_added'], 0)
        
        # 验证结果包含每日处理情况
        self.assertIsInstance(result['results'], list)
        # 当从缓存恢复时，results可能为空，这是正常的
        if result['successful_dates'] > 0:
            self.assertGreater(len(result['results']), 0)
        
        # 验证缓存信息
        self.assertIn('cache_info', result)
    
    def test_sync_incremental_with_date_range_cache_resume(self):
        """测试时间范围同步的缓存中断恢复功能"""
        # 配置Mock
        self.mock_data_source.fetch_history_transaction_detail.side_effect = self._mock_fetch_tick_by_date
        
        # Mock Redis缓存：模拟2024-01-15已经同步过
        with patch.object(self.service.redis_service, 'check_date_synced') as mock_check_synced:
            mock_check_synced.side_effect = lambda code, date, data_type: date.strftime("%Y-%m-%d") == "2024-01-15"
            
            # 测试时间范围：2024-01-15 到 2024-01-17
            start_date = datetime(2024, 1, 15)
            end_date = datetime(2024, 1, 17)
            
            result = self.service.sync_for_code_with_date_range(
                code="000001.SZ",
                start_date=start_date,
                end_date=end_date,
                fast_mode=True,
                use_cache=True
            )
            
            # 验证中断恢复功能
            self.assertEqual(result['resumed_from_cache'], 1)  # 2024-01-15从缓存恢复
            self.assertEqual(len(result['results']), 2)  # 只处理16和17日
    
    def test_sync_batch_incremental_with_date_range_real_format(self):
        """测试批量股票的时间范围同步"""
        # 配置Mock
        self.mock_data_source.fetch_history_transaction_detail.side_effect = self._mock_fetch_tick_by_date
        
        # 测试批量股票代码（避开2024-01-17的问题数据）
        codes = ["000001.SZ", "000002.SZ"]
        start_date = datetime(2024, 1, 15)
        end_date = datetime(2024, 1, 16)  # 只测试有正常数据的日期
        
        # 执行批量时间范围同步
        result = self.service.sync_batch_codes_with_date_range(
            codes=codes,
            start_date=start_date,
            end_date=end_date,
            fast_mode=True,
            use_cache=True
        )
        
        # 验证批量结果结构
        self.assertIsInstance(result, dict)
        self.assertEqual(result['total_codes'], 2)
        self.assertGreaterEqual(result['successful_codes'], 1)  # 至少一个股票成功
        self.assertIsInstance(result['results'], list)
        self.assertEqual(len(result['results']), 2)  # 两个股票的结果
        
        # 验证每个股票的结果
        for code_result in result['results']:
            self.assertIn('code', code_result)
            self.assertIn('successful_dates', code_result)
            self.assertIn('total_records_added', code_result)
    
    def test_sync_incremental_with_date_range_mixed_scenarios(self):
        """测试混合场景：有数据、无数据、数据质量问题"""
        # 配置Mock
        self.mock_data_source.fetch_history_transaction_detail.side_effect = self._mock_fetch_tick_by_date
        
        # 测试完整时间范围：包含各种场景
        start_date = datetime(2024, 1, 15)  # 有正常数据
        end_date = datetime(2024, 1, 20)    # 包含无数据的周末
        
        result = self.service.sync_for_code_with_date_range(
            code="000001.SZ",
            start_date=start_date,
            end_date=end_date,
            fast_mode=True,
            use_cache=False  # 禁用缓存测试
        )
        
        # 验证混合场景处理
        self.assertIsInstance(result, dict)
        self.assertEqual(result['total_dates'], 6)  # 6天范围
        self.assertGreater(result['successful_dates'], 0)  # 至少有成功的
        self.assertGreater(result['skipped_dates'] + result['failed_dates'], 0)  # 有跳过或失败的
        
        # 验证无缓存恢复
        self.assertEqual(result['resumed_from_cache'], 0)
    
    def test_sync_incremental_with_date_range_invalid_date_range(self):
        """测试无效日期范围处理"""
        # 结束日期早于开始日期
        start_date = datetime(2024, 1, 20)
        end_date = datetime(2024, 1, 15)
        
        result = self.service.sync_for_code_with_date_range(
            code="000001.SZ",
            start_date=start_date,
            end_date=end_date,
            fast_mode=True
        )
        
        # 应该处理0天（因为日期范围无效）
        self.assertEqual(result['total_dates'], 0)
    
    def test_check_sync_progress_integration(self):
        """测试同步进度检查的集成功能"""
        # Mock Redis服务的进度摘要
        mock_progress = {
            "code": "000001.SZ",
            "data_type": "tick",
            "total_dates": 5,
            "synced_count": 3,
            "missing_count": 2,
            "completion_rate": 0.6,
            "missing_dates": ["2024-01-17", "2024-01-20"],
            "first_missing_date": datetime(2024, 1, 17).date()
        }
        
        with patch.object(self.service.redis_service, 'get_progress_summary', return_value=mock_progress):
            start_date = datetime(2024, 1, 15)
            end_date = datetime(2024, 1, 20)
            
            progress = self.service.check_sync_progress("000001.SZ", start_date, end_date)
            
            # 验证进度检查结果
            self.assertEqual(progress['completion_rate'], 0.6)
            self.assertEqual(progress['missing_count'], 2)
            self.assertEqual(progress['synced_count'], 3)
    
    def test_clear_sync_cache_integration(self):
        """测试同步缓存清理的集成功能"""
        # Mock Redis服务的缓存清理
        with patch.object(self.service.redis_service, 'clear_sync_progress', return_value=True) as mock_clear:
            result = self.service.clear_sync_cache("000001.SZ")
            
            # 验证缓存清理调用
            self.assertTrue(result)
            mock_clear.assert_called_with("000001.SZ", "tick")

    def test_get_ticks_no_adjustment(self):
        """测试获取未复权的tick数据"""
        # Mock tick数据
        mock_tick_data = pd.DataFrame({
            'code': ['TEST_ADJ.SZ'] * 3,
            'timestamp': [
                datetime(2025, 7, 25, 9, 30, 0),
                datetime(2025, 7, 25, 9, 30, 30),
                datetime(2025, 7, 25, 9, 31, 0)
            ],
            'price': [10.50, 10.52, 10.48],
            'volume': [1000, 1500, 800],
            'direction': [1, 2, 1]  # 买盘/卖盘
        })
        
        self.mock_crud_repo.find.return_value = mock_tick_data
        
        # 测试获取未复权数据
        result = self.service.get_ticks(
            code="TEST_ADJ.SZ", 
            adjustment_type=ADJUSTMENT_TYPES.NONE,
            as_dataframe=True
        )
        
        # 验证结果
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 3)
        self.assertEqual(result.iloc[0]['price'], 10.50)
        self.assertEqual(result.iloc[1]['price'], 10.52)
        self.assertEqual(result.iloc[2]['price'], 10.48)

    def test_get_ticks_fore_adjustment(self):
        """测试获取前复权的tick数据"""
        # Mock tick数据
        mock_tick_data = pd.DataFrame({
            'code': ['TEST_FORE.SZ'] * 2,
            'timestamp': [
                datetime(2025, 7, 25, 9, 30, 0),
                datetime(2025, 7, 25, 9, 31, 0)
            ],
            'price': [12.00, 12.05],
            'volume': [2000, 1800],
            'direction': [1, 2]
        })
        
        self.mock_crud_repo.find.return_value = mock_tick_data
        
        # Mock 复权因子数据
        mock_adjustfactor_df = pd.DataFrame({
            'timestamp': [datetime(2025, 7, 25)],
            'foreadjustfactor': [1.3],  # 前复权因子
            'backadjustfactor': [0.7]   # 后复权因子
        })
        
        self.mock_adjustfactor_service.get_adjustfactors.return_value = mock_adjustfactor_df
        
        # 测试获取前复权数据
        result = self.service.get_ticks(
            code="TEST_FORE.SZ", 
            adjustment_type=ADJUSTMENT_TYPES.FORE,
            as_dataframe=True
        )
        
        # 验证结果
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        # 验证价格被正确调整 (原价格 * 复权因子)
        self.assertAlmostEqual(result.iloc[0]['price'], 15.60, places=4)  # 12.00 * 1.3
        self.assertAlmostEqual(result.iloc[1]['price'], 15.665, places=3) # 12.05 * 1.3
        # 验证成交量和方向保持不变
        self.assertEqual(result.iloc[0]['volume'], 2000)
        self.assertEqual(result.iloc[1]['direction'], 2)
        
        # 验证调用了复权因子服务
        self.mock_adjustfactor_service.get_adjustfactors.assert_called_once()

    def test_get_ticks_back_adjustment(self):
        """测试获取后复权的tick数据"""
        # Mock tick数据
        mock_tick_data = pd.DataFrame({
            'code': ['TEST_BACK.SZ'] * 3,
            'timestamp': [
                datetime(2025, 7, 25, 14, 30, 0),
                datetime(2025, 7, 25, 14, 30, 30),
                datetime(2025, 7, 25, 14, 31, 0)
            ],
            'price': [8.50, 8.48, 8.52],
            'volume': [1200, 1000, 1500],
            'direction': [2, 1, 2]
        })
        
        self.mock_crud_repo.find.return_value = mock_tick_data
        
        # Mock 复权因子数据
        mock_adjustfactor_df = pd.DataFrame({
            'timestamp': [datetime(2025, 7, 25)],
            'foreadjustfactor': [1.4],
            'backadjustfactor': [0.8]   # 后复权因子
        })
        
        self.mock_adjustfactor_service.get_adjustfactors.return_value = mock_adjustfactor_df
        
        # 测试获取后复权数据
        result = self.service.get_ticks(
            code="TEST_BACK.SZ", 
            adjustment_type=ADJUSTMENT_TYPES.BACK,
            as_dataframe=True
        )
        
        # 验证结果
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 3)
        # 验证价格被正确调整 (原价格 * 后复权因子)
        self.assertAlmostEqual(result.iloc[0]['price'], 6.80, places=4)   # 8.50 * 0.8
        self.assertAlmostEqual(result.iloc[1]['price'], 6.784, places=3)  # 8.48 * 0.8
        self.assertAlmostEqual(result.iloc[2]['price'], 6.816, places=3)  # 8.52 * 0.8

    def test_get_ticks_adjusted_convenience_method(self):
        """测试get_ticks_adjusted便捷方法"""
        # Mock tick数据
        mock_tick_data = pd.DataFrame({
            'code': ['TEST_CONV.SZ'] * 2,
            'timestamp': [
                datetime(2025, 7, 25, 10, 0, 0),
                datetime(2025, 7, 25, 10, 0, 30)
            ],
            'price': [15.20, 15.25],
            'volume': [800, 1200],
            'direction': [1, 1]
        })
        
        self.mock_crud_repo.find.return_value = mock_tick_data
        
        # Mock 复权因子数据
        mock_adjustfactor_df = pd.DataFrame({
            'timestamp': [datetime(2025, 7, 25)],
            'foreadjustfactor': [1.1],
            'backadjustfactor': [0.9]
        })
        
        self.mock_adjustfactor_service.get_adjustfactors.return_value = mock_adjustfactor_df
        
        # 测试便捷方法（默认前复权）
        result = self.service.get_ticks_adjusted(
            code="TEST_CONV.SZ",
            as_dataframe=True
        )
        
        # 验证结果
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        # 验证使用了前复权因子
        self.assertAlmostEqual(result.iloc[0]['price'], 16.72, places=4)  # 15.20 * 1.1
        self.assertAlmostEqual(result.iloc[1]['price'], 16.775, places=3) # 15.25 * 1.1

    def test_get_ticks_adjustment_no_factors(self):
        """测试没有复权因子时的处理"""
        # Mock tick数据
        mock_tick_data = pd.DataFrame({
            'code': ['TEST_NOFACTOR.SZ'],
            'timestamp': [datetime(2025, 7, 25, 11, 0, 0)],
            'price': [9.80],
            'volume': [500],
            'direction': [2]
        })
        
        self.mock_crud_repo.find.return_value = mock_tick_data
        
        # Mock 空的复权因子数据
        self.mock_adjustfactor_service.get_adjustfactors.return_value = pd.DataFrame()
        
        # 测试获取复权数据（没有复权因子）
        result = self.service.get_ticks(
            code="TEST_NOFACTOR.SZ", 
            adjustment_type=ADJUSTMENT_TYPES.FORE,
            as_dataframe=True
        )
        
        # 验证返回原始数据（没有调整）
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['price'], 9.80)   # 原始价格

    def test_get_ticks_adjustment_empty_data(self):
        """测试空数据的复权处理"""
        # Mock 空的tick数据
        self.mock_crud_repo.find.return_value = pd.DataFrame()
        
        # Mock 空的复权因子数据
        self.mock_adjustfactor_service.get_adjustfactors.return_value = pd.DataFrame()
        
        # 测试获取不存在股票的复权数据
        result = self.service.get_ticks(
            code="NONEXISTENT.SZ", 
            adjustment_type=ADJUSTMENT_TYPES.FORE,
            as_dataframe=True
        )
        
        # 验证返回空DataFrame
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty)

    def test_get_ticks_adjustment_model_format(self):
        """测试返回模型格式的复权数据"""
        # Mock tick数据
        mock_tick_models = [
            Mock(code="TEST_MODEL.SZ", timestamp=datetime(2025, 7, 25, 13, 0, 0), 
                 price=11.20, volume=600, direction=1),
            Mock(code="TEST_MODEL.SZ", timestamp=datetime(2025, 7, 25, 13, 0, 30), 
                 price=11.25, volume=800, direction=2)
        ]
        
        self.mock_crud_repo.find.return_value = mock_tick_models
        
        # Mock 复权因子数据
        mock_adjustfactor_df = pd.DataFrame({
            'timestamp': [datetime(2025, 7, 25)],
            'foreadjustfactor': [1.15],
            'backadjustfactor': [0.85]
        })
        
        self.mock_adjustfactor_service.get_adjustfactors.return_value = mock_adjustfactor_df
        
        # 测试获取模型格式的复权数据
        result = self.service.get_ticks(
            code="TEST_MODEL.SZ", 
            adjustment_type=ADJUSTMENT_TYPES.FORE,
            as_dataframe=False  # 返回模型列表
        )
        
        # 验证结果
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        
        # 验证模型属性（价格复权调整）
        tick_model = result[0]
        self.assertEqual(tick_model.code, "TEST_MODEL.SZ")
        self.assertAlmostEqual(float(tick_model.price), 12.88, places=4)  # 11.20 * 1.15
        self.assertEqual(tick_model.volume, 600)  # 成交量不变
        self.assertEqual(tick_model.direction, 1)  # 方向不变

    def test_tick_price_adjustment_calculation_accuracy(self):
        """测试tick价格复权计算的准确性"""
        # 创建包含多个时间点的tick数据
        mock_tick_data = pd.DataFrame({
            'code': ['TEST_CALCACC.SZ'] * 4,
            'timestamp': [
                datetime(2025, 7, 25, 9, 30, 0),
                datetime(2025, 7, 25, 9, 30, 30),
                datetime(2025, 7, 25, 9, 31, 0),
                datetime(2025, 7, 25, 9, 31, 30)
            ],
            'price': [10.10, 10.15, 10.08, 10.12],
            'volume': [1000, 1200, 800, 1500],
            'direction': [1, 2, 1, 2]
        })
        
        self.mock_crud_repo.find.return_value = mock_tick_data
        
        # Mock 复权因子数据（单日数据使用同一复权因子）
        mock_adjustfactor_df = pd.DataFrame({
            'timestamp': [datetime(2025, 7, 25)],
            'foreadjustfactor': [1.25],  # 前复权因子
            'backadjustfactor': [0.75]   # 后复权因子
        })
        
        self.mock_adjustfactor_service.get_adjustfactors.return_value = mock_adjustfactor_df
        
        # 测试前复权计算
        fore_result = self.service.get_ticks(
            code="TEST_CALCACC.SZ", 
            adjustment_type=ADJUSTMENT_TYPES.FORE,
            as_dataframe=True
        )
        
        self.assertEqual(len(fore_result), 4)
        
        # 验证前复权计算准确性
        self.assertAlmostEqual(fore_result.iloc[0]['price'], 12.625, places=4)  # 10.10 * 1.25
        self.assertAlmostEqual(fore_result.iloc[1]['price'], 12.6875, places=4) # 10.15 * 1.25
        self.assertAlmostEqual(fore_result.iloc[2]['price'], 12.60, places=4)   # 10.08 * 1.25
        self.assertAlmostEqual(fore_result.iloc[3]['price'], 12.65, places=4)   # 10.12 * 1.25
        
        # 验证成交量和方向保持不变
        self.assertEqual(fore_result.iloc[0]['volume'], 1000)
        self.assertEqual(fore_result.iloc[1]['direction'], 2)
        
        # 测试后复权计算
        back_result = self.service.get_ticks(
            code="TEST_CALCACC.SZ", 
            adjustment_type=ADJUSTMENT_TYPES.BACK,
            as_dataframe=True
        )
        
        # 验证后复权计算准确性
        self.assertAlmostEqual(back_result.iloc[0]['price'], 7.575, places=4)  # 10.10 * 0.75
        self.assertAlmostEqual(back_result.iloc[1]['price'], 7.6125, places=4) # 10.15 * 0.75
        self.assertAlmostEqual(back_result.iloc[2]['price'], 7.56, places=4)   # 10.08 * 0.75
        self.assertAlmostEqual(back_result.iloc[3]['price'], 7.59, places=4)   # 10.12 * 0.75
        
        # 验证成交量和方向保持不变
        self.assertEqual(back_result.iloc[2]['volume'], 800)
        self.assertEqual(back_result.iloc[3]['direction'], 2)

    def test_tick_adjustment_error_handling(self):
        """测试tick复权过程中的错误处理"""
        # Mock tick数据
        mock_tick_data = pd.DataFrame({
            'code': ['TEST_ERROR.SZ'],
            'timestamp': [datetime(2025, 7, 25, 15, 0, 0)],
            'price': [13.50],
            'volume': [1000],
            'direction': [1]
        })
        
        self.mock_crud_repo.find.return_value = mock_tick_data
        
        # Mock 复权因子服务抛出异常
        self.mock_adjustfactor_service.get_adjustfactors.side_effect = Exception("AdjustFactor service error")
        
        # 测试错误处理
        result = self.service.get_ticks(
            code="TEST_ERROR.SZ", 
            adjustment_type=ADJUSTMENT_TYPES.FORE,
            as_dataframe=True
        )
        
        # 验证在错误情况下返回原始数据
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 1)
        # 应该返回原始数据（未调整）
        self.assertEqual(result.iloc[0]['price'], 13.50)

    def test_tick_adjustment_missing_code_parameter(self):
        """测试缺少股票代码参数时的复权处理"""
        # Mock 空的tick数据
        self.mock_crud_repo.find.return_value = pd.DataFrame()
        
        # 测试没有股票代码的复权请求
        result = self.service.get_ticks(
            code=None,  # 没有股票代码
            adjustment_type=ADJUSTMENT_TYPES.FORE,
            as_dataframe=True
        )
        
        # 验证返回空结果
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty)

    def test_tick_adjustment_date_matching(self):
        """测试tick数据与复权因子的日期匹配逻辑"""
        # Mock tick数据（包含多个交易日的tick）
        mock_tick_data = pd.DataFrame({
            'code': ['TEST_DATEMATCH.SZ'] * 6,
            'timestamp': [
                datetime(2025, 7, 23, 9, 30, 0),  # 第一个交易日
                datetime(2025, 7, 23, 14, 30, 0),
                datetime(2025, 7, 24, 9, 30, 0),  # 第二个交易日
                datetime(2025, 7, 24, 14, 30, 0),
                datetime(2025, 7, 25, 9, 30, 0),  # 第三个交易日
                datetime(2025, 7, 25, 14, 30, 0)
            ],
            'price': [11.00, 11.05, 11.10, 11.15, 11.20, 11.25],
            'volume': [1000, 1200, 1100, 1300, 1050, 1250],
            'direction': [1, 2, 1, 2, 1, 2]
        })
        
        self.mock_crud_repo.find.return_value = mock_tick_data
        
        # Mock 复权因子数据（多个交易日不同的复权因子）
        mock_adjustfactor_df = pd.DataFrame({
            'timestamp': [
                datetime(2025, 7, 23),
                datetime(2025, 7, 24),
                datetime(2025, 7, 25)
            ],
            'foreadjustfactor': [1.0, 1.1, 1.2],  # 不同日期的前复权因子
            'backadjustfactor': [1.2, 1.1, 1.0]   # 不同日期的后复权因子
        })
        
        self.mock_adjustfactor_service.get_adjustfactors.return_value = mock_adjustfactor_df
        
        # 测试复权计算
        result = self.service.get_ticks(
            code="TEST_DATEMATCH.SZ", 
            adjustment_type=ADJUSTMENT_TYPES.FORE,
            as_dataframe=True
        )
        
        # 验证日期匹配和复权计算准确性
        self.assertEqual(len(result), 6)
        
        # 验证不同日期使用了正确的复权因子
        # 7月23日的tick：11.00 * 1.0 = 11.00, 11.05 * 1.0 = 11.05
        self.assertAlmostEqual(result.iloc[0]['price'], 11.00, places=4)
        self.assertAlmostEqual(result.iloc[1]['price'], 11.05, places=4)
        
        # 7月24日的tick：11.10 * 1.1 = 12.21, 11.15 * 1.1 = 12.265
        self.assertAlmostEqual(result.iloc[2]['price'], 12.21, places=4)
        self.assertAlmostEqual(result.iloc[3]['price'], 12.265, places=3)
        
        # 7月25日的tick：11.20 * 1.2 = 13.44, 11.25 * 1.2 = 13.50
        self.assertAlmostEqual(result.iloc[4]['price'], 13.44, places=4)
        self.assertAlmostEqual(result.iloc[5]['price'], 13.50, places=4)

    def test_tick_adjustment_type_edge_cases(self):
        """测试tick复权中adjustment_type参数的边界情况"""
        # Mock tick数据
        mock_tick_data = pd.DataFrame({
            'code': ['TEST_TICKEDGE.SZ'],
            'timestamp': [datetime(2025, 7, 25, 10, 30, 0)],
            'price': [8.88],
            'volume': [1888],
            'direction': [1]
        })
        
        self.mock_crud_repo.find.return_value = mock_tick_data
        
        # Mock 极端复权因子数据
        mock_adjustfactor_df = pd.DataFrame({
            'timestamp': [datetime(2025, 7, 25)],
            'foreadjustfactor': [0.1],  # 极小的复权因子
            'backadjustfactor': [10.0]  # 极大的复权因子
        })
        
        self.mock_adjustfactor_service.get_adjustfactors.return_value = mock_adjustfactor_df
        
        # 测试极小复权因子
        fore_result = self.service.get_ticks(
            code="TEST_TICKEDGE.SZ",
            adjustment_type=ADJUSTMENT_TYPES.FORE,
            as_dataframe=True
        )
        
        # 验证极小因子计算
        self.assertAlmostEqual(fore_result.iloc[0]['price'], 0.888, places=4)  # 8.88 * 0.1
        self.assertEqual(fore_result.iloc[0]['volume'], 1888)  # 成交量不变
        
        # 测试极大复权因子
        back_result = self.service.get_ticks(
            code="TEST_TICKEDGE.SZ",
            adjustment_type=ADJUSTMENT_TYPES.BACK,
            as_dataframe=True
        )
        
        # 验证极大因子计算
        self.assertAlmostEqual(back_result.iloc[0]['price'], 88.8, places=4)  # 8.88 * 10.0
        self.assertEqual(back_result.iloc[0]['direction'], 1)  # 方向不变

    def test_tick_adjustment_high_precision(self):
        """测试tick复权中的精度计算"""
        # Mock 现实场景的tick数据
        mock_tick_data = pd.DataFrame({
            'code': ['TEST_PRECISION.SZ'] * 2,
            'timestamp': [
                datetime(2025, 7, 25, 14, 59, 58),
                datetime(2025, 7, 25, 14, 59, 59)
            ],
            'price': [8.50, 8.65],  # 实际场景中的价格精度
            'volume': [1500, 2000],
            'direction': [1, 2]
        })
        
        self.mock_crud_repo.find.return_value = mock_tick_data
        
        # Mock 现实场景中的复权因子精度
        mock_adjustfactor_df = pd.DataFrame({
            'timestamp': [datetime(2025, 7, 25)],
            'foreadjustfactor': [1.234567],  # 实际场景中的因子精度
            'backadjustfactor': [0.765432]   # 实际场景中的因子精度
        })
        
        self.mock_adjustfactor_service.get_adjustfactors.return_value = mock_adjustfactor_df
        
        # 测试前复权计算
        fore_result = self.service.get_ticks(
            code="TEST_PRECISION.SZ",
            adjustment_type=ADJUSTMENT_TYPES.FORE,
            as_dataframe=True
        )
        
        # 验证前复权计算结果
        expected_price1 = 8.50 * 1.234567   # 10.493820
        expected_price2 = 8.65 * 1.234567   # 10.678904
        
        self.assertAlmostEqual(fore_result.iloc[0]['price'], expected_price1, places=4)
        self.assertAlmostEqual(fore_result.iloc[1]['price'], expected_price2, places=4)
        
        # 测试后复权计算
        back_result = self.service.get_ticks(
            code="TEST_PRECISION.SZ",
            adjustment_type=ADJUSTMENT_TYPES.BACK,
            as_dataframe=True
        )
        
        # 验证后复权计算结果
        expected_back1 = 8.50 * 0.765432   # 6.506172
        expected_back2 = 8.65 * 0.765432   # 6.620987
        
        self.assertAlmostEqual(back_result.iloc[0]['price'], expected_back1, places=4)
        self.assertAlmostEqual(back_result.iloc[1]['price'], expected_back2, places=4)
        
        # 验证计算方向正确性
        self.assertGreater(fore_result.iloc[0]['price'], 8.50)  # 前复权应该增大
        self.assertLess(back_result.iloc[0]['price'], 8.50)     # 后复权应该减小
        
        # 验证成交量和方向保持不变
        self.assertEqual(fore_result.iloc[0]['volume'], 1500)
        self.assertEqual(fore_result.iloc[1]['direction'], 2)
        self.assertEqual(back_result.iloc[0]['volume'], 1500)
        self.assertEqual(back_result.iloc[1]['direction'], 2)

    def test_tick_adjustment_zero_and_negative_factors(self):
        """测试tick复权中零值和异常复权因子的处理"""
        # Mock tick数据
        mock_tick_data = pd.DataFrame({
            'code': ['TEST_ZERO.SZ'],
            'timestamp': [datetime(2025, 7, 25, 11, 30, 0)],
            'price': [6.66],
            'volume': [666],
            'direction': [2]
        })
        
        self.mock_crud_repo.find.return_value = mock_tick_data
        
        # Mock 包含零值的复权因子
        mock_adjustfactor_df = pd.DataFrame({
            'timestamp': [datetime(2025, 7, 25)],
            'foreadjustfactor': [0.0],  # 零复权因子
            'backadjustfactor': [1.0]
        })
        
        self.mock_adjustfactor_service.get_adjustfactors.return_value = mock_adjustfactor_df
        
        # 测试零复权因子的处理
        result = self.service.get_ticks(
            code="TEST_ZERO.SZ",
            adjustment_type=ADJUSTMENT_TYPES.FORE,
            as_dataframe=True
        )
        
        # 验证零因子计算（价格变为0）
        self.assertEqual(result.iloc[0]['price'], 0.0)  # 6.66 * 0.0 = 0.0
        self.assertEqual(result.iloc[0]['volume'], 666)  # 成交量保持不变


if __name__ == '__main__':
    unittest.main()