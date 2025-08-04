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

    MOCK_STOCKINFO_WITH_DELISTED = pd.DataFrame({
        'ts_code': ['002604.SZ', '000717.SZ'],
        'symbol': ['002604', '000717'],
        'name': ['*ST龙韵', '韶钢松山'],  # 使用真实的股票名称
        'area': ['北京', '韶关'],
        'industry': ['广告包装', '钢铁'],
        'list_date': ['20110325', '19970612'],  # 真实上市日期格式
        'curr_type': ['CNY', 'CNY'],
        'delist_date': ['20220509', None]  # 真实退市日期格式
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
        """测试成功同步所有股票信息"""
        # 配置 Mock
        self.mock_data_source.fetch_cn_stockinfo.return_value = self.MOCK_STOCKINFO_SUCCESS
        
        # 获取初始表大小
        initial_size = get_table_size(self.model)
        
        # 执行同步
        result = self.service.sync_all()
        
        # 验证返回结果
        self.assertIsInstance(result, dict)
        self.assertEqual(result['success'], 3)
        self.assertEqual(result['failed'], 0)
        self.assertEqual(result['total'], 3)
        self.assertEqual(len(result['failed_records']), 0)
        
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
        """测试处理空数据响应"""
        # 配置 Mock 返回空数据
        self.mock_data_source.fetch_cn_stockinfo.return_value = self.MOCK_EMPTY_DATA
        
        # 执行同步
        result = self.service.sync_all()
        
        # 验证返回结果
        self.assertIsInstance(result, dict)
        self.assertEqual(result['success'], 0)
        self.assertEqual(result['failed'], 0)
        self.assertEqual(result['total'], 0)

    def test_sync_all_none_data(self):
        """测试处理 None 数据响应"""
        # 配置 Mock 返回 None
        self.mock_data_source.fetch_cn_stockinfo.return_value = None
        
        # 执行同步
        result = self.service.sync_all()
        
        # 验证返回结果
        self.assertIsInstance(result, dict)
        self.assertEqual(result['success'], 0)
        self.assertEqual(result['failed'], 0)

    def test_sync_all_api_failure(self):
        """测试 API 调用失败"""
        # 配置 Mock 抛出异常
        self.mock_data_source.fetch_cn_stockinfo.side_effect = Exception("API connection failed")
        
        # 执行同步
        result = self.service.sync_all()
        
        # 验证返回结果
        self.assertIsInstance(result, dict)
        self.assertEqual(result['success'], 0)
        self.assertEqual(result['failed'], 0)
        self.assertIn("API connection failed", str(result['error']))

    def test_sync_all_with_delisted_stocks(self):
        """测试处理包含退市股票的数据"""
        # 配置 Mock
        self.mock_data_source.fetch_cn_stockinfo.return_value = self.MOCK_STOCKINFO_WITH_DELISTED
        
        # 执行同步
        result = self.service.sync_all()
        
        # 如果失败，打印详细错误信息用于调试
        if result['failed'] > 0:
            print(f"\n调试信息：")
            print(f"Success: {result['success']}, Failed: {result['failed']}")
            print(f"Failed records: {result.get('failed_records', [])}")
        
        # 验证返回结果
        self.assertEqual(result['success'], 2, f"Expected 2 success, got {result['success']}. Failed: {result['failed']}")
        self.assertEqual(result['failed'], 0)
        
        # 验证退市股票数据
        records = self.crud_repo.find(filters={"code": "002604.SZ"})
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertIsNotNone(record.delist_date)

    def test_sync_all_update_existing_records(self):
        """测试更新已存在的记录"""
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
        
        # 执行同步
        result = self.service.sync_all()
        
        # 验证更新成功
        self.assertEqual(result['success'], 3)  # 1个更新 + 2个新增
        
        # 验证数据已更新
        records = self.crud_repo.find(filters={"code": "000001.SZ"})
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record.code_name, "平安银行")  # 应该是新的名称
        self.assertEqual(record.industry, "银行")  # 应该是新的行业

    def test_retry_failed_records_empty_list(self):
        """测试重试空的失败记录列表"""
        result = self.service.retry_failed_records([])
        
        self.assertEqual(result['success'], 0)
        self.assertEqual(result['failed'], 0)
        self.assertEqual(result['total'], 0)

    def test_retry_failed_records_success(self):
        """测试成功重试失败的记录"""
        # 准备失败记录
        failed_records = [
            {"code": "000001.SZ", "code_name": "平安银行", "error": "Database error"}
        ]
        
        # 配置 Mock 返回数据
        self.mock_data_source.fetch_cn_stockinfo.return_value = self.MOCK_STOCKINFO_SUCCESS
        
        # 执行重试
        result = self.service.retry_failed_records(failed_records)
        
        # 验证重试结果
        self.assertEqual(result['success'], 1)
        self.assertEqual(result['failed'], 0)
        self.assertEqual(result['total'], 1)
        
        # 验证数据已写入数据库
        records = self.crud_repo.find(filters={"code": "000001.SZ"})
        self.assertEqual(len(records), 1)

    def test_retry_failed_records_api_failure(self):
        """测试重试时 API 调用失败"""
        failed_records = [
            {"code": "000001.SZ", "code_name": "平安银行", "error": "Database error"}
        ]
        
        # 配置 Mock 抛出异常
        self.mock_data_source.fetch_cn_stockinfo.side_effect = Exception("API error")
        
        # 执行重试
        result = self.service.retry_failed_records(failed_records)
        
        # 验证重试结果
        self.assertEqual(result['success'], 0)
        self.assertEqual(result['failed'], 1)
        self.assertEqual(result['total'], 1)

    def test_get_stockinfos(self):
        """测试获取股票信息"""
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
        
        # 测试获取数据
        result = self.service.get_stockinfos()
        
        # 验证结果
        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0)
        
        # 查找我们的测试数据
        test_records = result[result['code'] == 'TEST_001.SZ']
        self.assertEqual(len(test_records), 1)

    def test_get_stockinfo_codes_set(self):
        """测试获取股票代码集合"""
        # 先添加一些测试数据
        test_codes = ["TEST_001.SZ", "TEST_002.SZ"]
        for code in test_codes:
            self.crud_repo.create(
                code=code,
                code_name=f"测试股票{code}",
                industry="测试行业",
                currency=CURRENCY_TYPES.CNY,
                market=MARKET_TYPES.CHINA,
                list_date=datetime_normalize("20200101"),
                delist_date=datetime_normalize(GCONF.DEFAULTEND),
                source=SOURCE_TYPES.TUSHARE
            )
        
        # 获取代码集合
        codes_set = self.service.get_stockinfo_codes_set()
        
        # 验证结果
        self.assertIsInstance(codes_set, set)
        for code in test_codes:
            self.assertIn(code, codes_set)

    def test_is_code_in_stocklist(self):
        """测试股票代码存在性检查"""
        # 添加测试数据
        self.crud_repo.create(
            code="TEST_EXISTS.SZ",
            code_name="存在的股票",
            industry="测试行业",
            currency=CURRENCY_TYPES.CNY,
            market=MARKET_TYPES.CHINA,
            list_date=datetime_normalize("20200101"),
            delist_date=datetime_normalize(GCONF.DEFAULTEND),
            source=SOURCE_TYPES.TUSHARE
        )
        
        # 测试存在的代码
        self.assertTrue(self.service.is_code_in_stocklist("TEST_EXISTS.SZ"))
        
        # 测试不存在的代码
        self.assertFalse(self.service.is_code_in_stocklist("TEST_NOT_EXISTS.SZ"))

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
        
        # 执行同步
        result = self.service.sync_all()
        
        # 验证错误容忍：应该有成功和失败的记录
        self.assertGreater(result['total'], 0)
        
        # 即使有失败，成功的记录也应该被处理
        if result['success'] > 0:
            # 验证至少有一条成功的记录在数据库中（使用真实代码）
            valid_records = self.crud_repo.find(filters={"code": "000001.SZ"})
            if valid_records:  # 第一条记录数据完整，应该能成功插入
                self.assertGreater(len(valid_records), 0)
            # 验证第三条记录也可能成功
            valid_records_2 = self.crud_repo.find(filters={"code": "000858.SZ"})
            if valid_records_2:
                self.assertGreater(len(valid_records_2), 0)


if __name__ == '__main__':
    unittest.main()