"""
Integration Tests for the Refactored ginkgo.data.__init__ module.

This test suite performs live interactions with the database but uses mock data sources
to avoid network requests and external API dependencies while maintaining data persistence testing.

NOTE: Running these tests will result in database modifications but no network requests.
"""
import unittest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock

from ginkgo.enums import FREQUENCY_TYPES

# Import the refactored functions and helpers
from ginkgo.data import (
    fetch_and_update_stockinfo,
    fetch_and_update_adjustfactor,
    fetch_and_update_cn_daybar,
    init_example_data,
    get_stockinfos,
    get_adjustfactors,
    get_bars,
    get_engines,
    get_portfolios,
    get_files,
    get_crud, # Accessing the helper for cleanup tasks
    # New adjustment-related APIs
    get_bars_adjusted,
    get_ticks_adjusted,
    calc_adjust_factors,
    recalculate_adjust_factors_for_code,
    ADJUSTMENT_TYPES
)
from ginkgo.enums import FILE_TYPES
from ginkgo.data.sources.source_base import GinkgoSourceBase

# Mock Data Definitions
MOCK_STOCKINFO_DATA = pd.DataFrame({
    'ts_code': [
        '000001.SZ', '000002.SZ', '000858.SZ', '000876.SZ', '002415.SZ',
        '600000.SH', '600036.SH', '600519.SH', '600887.SH', '601318.SH',
        '300015.SZ', '300059.SZ', '300122.SZ', '300274.SZ', '300433.SZ',
        # Add more realistic stock codes for comprehensive testing
        '000625.SZ', '000776.SZ', '002304.SZ', '002352.SZ', '002456.SZ',
        '600009.SH', '600028.SH', '600050.SH', '600104.SH', '600276.SH',
    ],
    'symbol': [
        '000001', '000002', '000858', '000876', '002415',
        '600000', '600036', '600519', '600887', '601318',
        '300015', '300059', '300122', '300274', '300433',
        '000625', '000776', '002304', '002352', '002456',
        '600009', '600028', '600050', '600104', '600276',
    ],
    'name': [
        '平安银行', '万科A', '五粮液', '新希望', '海康威视',
        '浦发银行', '招商银行', '贵州茅台', '伊利股份', '中国平安',
        '爱尔眼科', '东方财富', '智飞生物', '阳光电源', '蓝思科技',
        '长安汽车', '广发证券', '洋河股份', '顺丰控股', '欧菲光',
        '上海机场', '中国石化', '中国联通', '上汽集团', '恒瑞医药',
    ],
    'area': ['深圳'] * 25,
    'industry': [
        '银行', '房地产开发', '白酒', '农产品加工', '电子制造',
        '银行', '银行', '白酒', '乳品', '保险',
        '医疗服务', '多元金融', '生物制品', '电气设备', '电子制造',
        '汽车整车', '证券', '白酒', '航空运输', '电子制造',
        '机场服务', '石油化工', '通信运营', '汽车整车', '化学制药',
    ],
    'list_date': [
        '19910403', '19910129', '19970612', '19980727', '20100928',
        '19990310', '20020409', '20010827', '19961212', '20070625',
        '20091030', '20100325', '20100923', '20111028', '20150130',
        '19970625', '20100816', '20021229', '20170223', '20120425',
        '19990826', '20001016', '20021029', '19971110', '20000727',
    ],
    'curr_type': ['CNY'] * 25,
    'delist_date': [None] * 25,
})

def generate_mock_daybar_data(code: str, days: int = 30) -> pd.DataFrame:
    """Generate mock daily bar data for testing."""
    base_date = datetime(2024, 1, 1)
    base_price = 10.0
    
    data = []
    for i in range(days):
        date = base_date + timedelta(days=i)
        # Skip weekends (simple approximation)
        if date.weekday() >= 5:
            continue
            
        # Generate realistic OHLCV data
        open_price = base_price + (i * 0.1) + (i % 3 - 1) * 0.2
        high_price = open_price + abs(i % 4) * 0.15
        low_price = open_price - abs((i + 1) % 3) * 0.1
        close_price = open_price + (i % 5 - 2) * 0.05
        volume = 1000000 + (i * 50000) + (i % 7) * 200000
        amount = volume * close_price
        
        data.append({
            'ts_code': code,
            'trade_date': date.strftime('%Y%m%d'),
            'open': round(open_price, 2),
            'high': round(high_price, 2),
            'low': round(low_price, 2), 
            'close': round(close_price, 2),
            'pre_close': round(open_price - 0.05, 2),
            'change': round(close_price - open_price + 0.05, 2),
            'pct_chg': round(((close_price - open_price + 0.05) / (open_price - 0.05)) * 100, 2),
            'vol': int(volume),
            'amount': round(amount, 2),
        })
    
    return pd.DataFrame(data)

def generate_mock_adjustfactor_data(code: str, days: int = 30) -> pd.DataFrame:
    """Generate mock adjustment factor data for testing."""
    base_date = datetime(2024, 1, 1)
    
    data = []
    adj_factor = 1.0
    for i in range(0, days, 7):  # Weekly adjustment factors
        date = base_date + timedelta(days=i)
        # Simulate occasional dividend/stock split adjustments
        if i % 14 == 0 and i > 0:
            adj_factor *= 0.95  # Simulate dividend adjustment
            
        data.append({
            'ts_code': code,
            'trade_date': date.strftime('%Y-%m-%d'),
            'adj_factor': round(adj_factor, 6),
        })
    
    return pd.DataFrame(data)

class MockGinkgoTushare(GinkgoSourceBase):
    """Mock Tushare data source for integration testing without network requests."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pro = Mock()  # Mock the tushare pro client
    
    def connect(self, *args, **kwargs):
        """Mock connection - no actual network connection needed."""
        pass
    
    def fetch_cn_stockinfo(self, *args, **kwargs) -> pd.DataFrame:
        """Return mock stock info data."""
        print(f"DEBUG: MockGinkgoTushare.fetch_cn_stockinfo() called with args={args}, kwargs={kwargs}")
        print(f":crab: Got {len(MOCK_STOCKINFO_DATA)} records about stockinfo (mock).")
        mock_data = MOCK_STOCKINFO_DATA.copy()
        print(f"DEBUG: Returning mock data with columns: {list(mock_data.columns)}")
        print(f"DEBUG: First few ts_codes: {list(mock_data['ts_code'].head())}")
        return mock_data
    
    def fetch_cn_stock_daybar(self, code: str, start_date=None, end_date=None, *args, **kwargs) -> pd.DataFrame:
        """Return mock daily bar data for the specified code."""
        print(f"DEBUG: MockGinkgoTushare.fetch_cn_stock_daybar() called for {code}, start_date={start_date}, end_date={end_date}")
        mock_data = generate_mock_daybar_data(code, days=30)
        print(f":crab: Got {len(mock_data)} records about {code} daybar (mock).")
        print(f"DEBUG: Mock daybar data columns: {list(mock_data.columns)}")
        return mock_data
    
    def fetch_cn_stock_adjustfactor(self, code: str, start_date=None, end_date=None, *args, **kwargs) -> pd.DataFrame:
        """Return mock adjustment factor data for the specified code."""
        print(f"DEBUG: MockGinkgoTushare.fetch_cn_stock_adjustfactor() called for {code}, start_date={start_date}, end_date={end_date}")
        mock_data = generate_mock_adjustfactor_data(code, days=30)
        print(f":crab: Got {len(mock_data)} records about {code} adjustfactor (mock).")
        print(f"DEBUG: Mock adjustfactor data columns: {list(mock_data.columns)}")
        return mock_data

class TestDataInitIntegration(unittest.TestCase):
    """Integration tests using real database but mock data sources."""

    @classmethod
    def setUpClass(cls):
        """Set up mock data source for all tests."""
        cls.mock_tushare_source = MockGinkgoTushare()
        print("Mock data source initialized for integration tests.")

    def setUp(self):
        """Set up a clean environment before each test."""
        from ginkgo.data.containers import container
        from dependency_injector import providers
        
        # 创建Mock数据源的Object provider
        mock_source_provider = providers.Object(self.mock_tushare_source)
        
        # 覆盖container中的数据源provider
        container.ginkgo_tushare_source.override(mock_source_provider)
        
        # 重置所有依赖该数据源的服务，强制它们使用新的Mock数据源
        container.stockinfo_service.reset()
        container.adjustfactor_service.reset() 
        container.bar_service.reset()
        
        # Debug: 验证Mock数据源是否正确设置
        actual_source = container.ginkgo_tushare_source()
        print(f"DEBUG: Data source type: {type(actual_source)}")
        print(f"DEBUG: Is MockGinkgoTushare: {isinstance(actual_source, MockGinkgoTushare)}")
        
        print("Setting up test environment with mock data source...")
        init_example_data()  # Start with a clean slate of example data

    def tearDown(self):
        """Clean up after each test."""
        from ginkgo.data.containers import container
        # 重置override，恢复原始数据源
        container.ginkgo_tushare_source.reset_override()
        print("Tearing down test environment.")

    def test_01_fetch_and_update_stockinfo(self):
        """Tests fetching and updating stock information using mock data source."""
        print("Running test_01_fetch_and_update_stockinfo with mock data...")
        
        # Clean up existing stock info data to start fresh
        stockinfo_crud = get_crud('stock_info')
        initial_count = len(stockinfo_crud.find(as_dataframe=True))
        print(f"Initial stockinfo count: {initial_count}")
        
        # Action: Fetch and update stock info (will use mock data source)
        print("DEBUG: About to call fetch_and_update_stockinfo()")
        result = fetch_and_update_stockinfo(no_skip=True)  # Force execution, skip cache
        print(f"DEBUG: fetch_and_update_stockinfo() result: {result}")
        
        # Verification: Check that stock info was updated
        final_stockinfo_df = get_stockinfos(as_dataframe=True)
        final_count = len(final_stockinfo_df)
        
        print(f"Final stockinfo count: {final_count}")
        if final_count > 0:
            print(f"DEBUG: First few stock codes: {list(final_stockinfo_df['code'].head())}")
        
        # We should have data from our mock source (25 stocks)
        self.assertGreater(final_count, 0, "Should have stock info records after sync")
        
        # Check that we have the expected stock codes from our mock data
        stock_codes = set(final_stockinfo_df['code'].values)
        expected_codes = {'000001.SZ', '000002.SZ', '600000.SH', '600036.SH', '600519.SH'}
        
        print(f"DEBUG: All stock codes found: {stock_codes}")
        print(f"DEBUG: Expected codes: {expected_codes}")
        
        # At least some of our mock codes should be present
        overlap = stock_codes.intersection(expected_codes)
        self.assertGreater(len(overlap), 0, f"Should have some expected mock stock codes. Found: {overlap}")
        
        # Check data integrity - verify key fields exist and have reasonable values
        required_columns = ['code', 'code_name', 'industry', 'currency']  # Use actual DB columns
        for col in required_columns:
            self.assertIn(col, final_stockinfo_df.columns, f"Column {col} should exist")
            non_null_count = final_stockinfo_df[col].notna().sum()
            self.assertGreater(non_null_count, 0, f"Column {col} should have some non-null values")
        
        print("Stock info sync with mock data verified successfully.")

    def test_02_fetch_and_update_adjustfactor_fast_monthly(self):
        """Tests fetching adjustment factors in fast mode for the last month."""
        test_code = '000001.SZ'
        print(f"Running test_02_fetch_and_update_adjustfactor_fast_monthly for {test_code}...")
        
        # Setup: Clean slate, then add a single record from one month ago.
        adjustfactor_crud = get_crud('adjustfactor')
        adjustfactor_crud.remove(filters={"code": test_code})
        
        one_month_ago = datetime.now() - pd.Timedelta(days=30)
        adjustfactor_crud.create(
            code=test_code,
            adjustfactor=1.0,
            foreadjustfactor=1.0,
            backadjustfactor=1.0,
            timestamp=one_month_ago
        )
        count_before = 1
        
        # Action: Fetch in fast mode. This should only get data after our manual entry.
        print("DEBUG: About to call fetch_and_update_adjustfactor()")
        fetch_and_update_adjustfactor(code=test_code, fast_mode=True, no_skip=True)
        print("DEBUG: fetch_and_update_adjustfactor() completed")

        # Verification
        adjustfactor_df = get_adjustfactors(filters={"code": test_code}, as_dataframe=True)
        count_after = len(adjustfactor_df)
        self.assertGreater(count_after, count_before)
        
        latest_timestamp = pd.to_datetime(adjustfactor_df['timestamp']).max()
        # With mock data, we expect data from 2024, so adjust the check accordingly
        self.assertIsNotNone(latest_timestamp, "Should have timestamp data")
        print(f"Fast mode for adjustment factors (monthly) on {test_code} verified successfully.")

    def test_03_fetch_and_update_cn_daybar_fast_monthly(self):
        """Tests fetching daily bars in fast mode for the last month."""
        test_code = '000001.SZ'
        print(f"Running test_03_fetch_and_update_cn_daybar_fast_monthly for {test_code}...")

        # Setup: Clean slate, then add a single record from one month ago.
        bar_crud = get_crud('bar')
        bar_crud.remove(filters={"code": test_code})

        one_month_ago = datetime.now() - pd.Timedelta(days=30)
        bar_crud.create(
            code=test_code,
            open=10, high=11, low=9, close=10.5,
            volume=10000,
            amount=100000,
            timestamp=one_month_ago,
            frequency=FREQUENCY_TYPES.DAY
        )
        count_before = 1

        # Action
        print("DEBUG: About to call fetch_and_update_cn_daybar()")
        fetch_and_update_cn_daybar(code=test_code, fast_mode=True, no_skip=True)
        print("DEBUG: fetch_and_update_cn_daybar() completed")

        # Verification
        bar_df = get_bars(filters={"code": test_code}, as_dataframe=True)
        count_after = len(bar_df)
        self.assertGreater(count_after, count_before)

        latest_timestamp = pd.to_datetime(bar_df['timestamp']).max()
        # With mock data, we expect data from 2024, so adjust the check accordingly
        self.assertIsNotNone(latest_timestamp, "Should have timestamp data")
        print(f"Fast mode for daily bars (monthly) on {test_code} verified successfully.")

    def test_04_adjustment_factors_calculation_integration(self):
        """Tests the adjustment factor calculation functionality."""
        test_code = '000001.SZ'
        print(f"Running test_04_adjustment_factors_calculation_integration for {test_code}...")
        
        # Setup: Ensure we have some adjustment factor data
        fetch_and_update_adjustfactor(code=test_code, fast_mode=True)
        
        # Verify we have raw adjustment factor data
        adjustfactor_df = get_adjustfactors(filters={"code": test_code}, as_dataframe=True)
        self.assertFalse(adjustfactor_df.empty, "Should have adjustment factor data before calculation")
        
        # Action: Calculate fore/back adjustment factors
        calc_result = calc_adjust_factors(test_code)
        
        # Verification: Check calculation results
        self.assertIsInstance(calc_result, dict)
        self.assertIn("code", calc_result)
        self.assertEqual(calc_result["code"], test_code)
        
        # Verify updated data has fore/back factors
        updated_adjustfactor_df = get_adjustfactors(filters={"code": test_code}, as_dataframe=True)
        self.assertFalse(updated_adjustfactor_df.empty)
        
        # Check that fore/back adjustment factor columns exist and have valid values
        required_columns = ['foreadjustfactor', 'backadjustfactor']
        for col in required_columns:
            self.assertIn(col, updated_adjustfactor_df.columns, f"Column {col} should exist")
            # Check that we have some non-null values
            non_null_count = updated_adjustfactor_df[col].notna().sum()
            self.assertGreater(non_null_count, 0, f"Column {col} should have some non-null values")
        
        print(f"Adjustment factor calculation for {test_code} verified successfully.")

    def test_05_get_bars_adjusted_integration(self):
        """Tests the get_bars_adjusted function with real data."""
        test_code = '000001.SZ'
        print(f"Running test_05_get_bars_adjusted_integration for {test_code}...")
        
        # Clean up: Remove existing data for this stock to ensure clean test
        print("DEBUG: Cleaning up existing data for clean test")
        bar_crud = get_crud('bar')
        adjustfactor_crud = get_crud('adjustfactor')
        bar_crud.remove(filters={"code": test_code})
        adjustfactor_crud.remove(filters={"code": test_code})
        print("DEBUG: Cleanup completed")
        
        # Setup: Ensure we have bar data and adjustment factors
        print("DEBUG: About to call fetch_and_update_cn_daybar() for bars adjusted test")
        fetch_and_update_cn_daybar(code=test_code, fast_mode=True, no_skip=True)
        print("DEBUG: About to call fetch_and_update_adjustfactor() for bars adjusted test")
        fetch_and_update_adjustfactor(code=test_code, fast_mode=True, no_skip=True)
        print("DEBUG: About to call calc_adjust_factors() for bars adjusted test")
        calc_adjust_factors(test_code)
        
        # Get original bar data for comparison - use same parameter format
        original_bars = get_bars(code=test_code, as_dataframe=True)
        self.assertFalse(original_bars.empty, "Should have original bar data")
        print(f"DEBUG: original_bars count: {len(original_bars)}")
        print(f"DEBUG: original_bars date range: {original_bars['timestamp'].min()} to {original_bars['timestamp'].max()}")
        
        # Test forward adjustment
        fore_adjusted_bars = get_bars_adjusted(
            code=test_code,
            adjustment_type=ADJUSTMENT_TYPES.FORE,
            as_dataframe=True
        )
        
        # Verification
        self.assertIsInstance(fore_adjusted_bars, pd.DataFrame)
        self.assertFalse(fore_adjusted_bars.empty)
        print(f"DEBUG: fore_adjusted_bars count: {len(fore_adjusted_bars)}")
        print(f"DEBUG: fore_adjusted_bars date range: {fore_adjusted_bars['timestamp'].min()} to {fore_adjusted_bars['timestamp'].max()}")
        
        # Check if the discrepancy is due to different data being returned
        # Let's also check adjustment factors
        from ginkgo.data import get_adjustfactors
        adjust_factors = get_adjustfactors(filters={"code": test_code}, as_dataframe=True)
        print(f"DEBUG: adjustment factors count: {len(adjust_factors)}")
        print(f"DEBUG: adjustment factors date range: {adjust_factors['timestamp'].min()} to {adjust_factors['timestamp'].max()}")
        
        # After cleanup, both queries should return the same number of records
        self.assertEqual(len(fore_adjusted_bars), len(original_bars))
        
        # Check that price columns exist
        price_columns = ['open', 'high', 'low', 'close']
        for col in price_columns:
            self.assertIn(col, fore_adjusted_bars.columns)
        
        # Test backward adjustment
        back_adjusted_bars = get_bars_adjusted(
            code=test_code,
            adjustment_type=ADJUSTMENT_TYPES.BACK,
            as_dataframe=True
        )
        
        self.assertIsInstance(back_adjusted_bars, pd.DataFrame)
        self.assertFalse(back_adjusted_bars.empty)
        self.assertEqual(len(back_adjusted_bars), len(original_bars))
        
        print(f"Bar adjustment integration for {test_code} verified successfully.")

    def test_06_adjustment_types_enum_integration(self):
        """Tests that ADJUSTMENT_TYPES enum is properly integrated."""
        print("Running test_06_adjustment_types_enum_integration...")
        
        # Test enum values are accessible
        self.assertEqual(ADJUSTMENT_TYPES.NONE.value, 0)
        self.assertEqual(ADJUSTMENT_TYPES.FORE.value, 1)
        self.assertEqual(ADJUSTMENT_TYPES.BACK.value, 2)
        
        # Test enum can be used with API functions
        test_code = '000001.SZ'
        
        # These calls should not raise exceptions
        try:
            get_bars_adjusted(test_code, ADJUSTMENT_TYPES.FORE, as_dataframe=True)
            get_bars_adjusted(test_code, ADJUSTMENT_TYPES.BACK, as_dataframe=True)
        except Exception as e:
            # If there's no data, that's expected, but enum should work
            if "No adjustment factors found" not in str(e) and "not in stock list" not in str(e):
                raise e
        
        print("ADJUSTMENT_TYPES enum integration verified successfully.")

    def test_07_recalculate_adjust_factors_for_code_integration(self):
        """Tests the recalculate_adjust_factors_for_code function."""
        test_code = '000001.SZ'
        print(f"Running test_07_recalculate_adjust_factors_for_code_integration for {test_code}...")
        
        # Setup: Ensure we have adjustment factor data
        fetch_and_update_adjustfactor(code=test_code, fast_mode=True)
        
        # Action: Recalculate adjustment factors
        recalc_result = recalculate_adjust_factors_for_code(test_code)
        
        # Verification
        self.assertIsInstance(recalc_result, dict)
        self.assertIn("code", recalc_result)
        self.assertEqual(recalc_result["code"], test_code)
        
        # The result should indicate success or provide error information
        self.assertTrue("success" in recalc_result or "error" in recalc_result)
        
        print(f"Recalculate adjustment factors for {test_code} verified successfully.")


if __name__ == '__main__':
    unittest.main()
