import unittest
import sys
import os
import uuid
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

try:
    from ginkgo.data.crud.stock_info_crud import StockInfoCRUD
    from ginkgo.data.models import MStockInfo
    from ginkgo.enums import SOURCE_TYPES, CURRENCY_TYPES, MARKET_TYPES
    from ginkgo.libs import GCONF, datetime_normalize
    from ginkgo.data.drivers import get_db_connection, get_table_size, create_table, drop_table
    from sqlalchemy import text
except ImportError as e:
    print(f"Import error: {e}")
    StockInfoCRUD = None
    GCONF = None


class StockInfoCRUDTest(unittest.TestCase):
    """
    StockInfoCRUD database integration tests.
    Tests StockInfo-specific CRUD operations with actual database.
    """

    @classmethod
    def setUpClass(cls):
        """Class-level setup: check database configuration and connection"""
        if StockInfoCRUD is None or GCONF is None:
            raise AssertionError("StockInfoCRUD or GCONF not available")

        # Set model for table size verification
        cls.model = MStockInfo

        # Recreate table for clean testing
        try:
            drop_table(cls.model, no_skip=True)
            create_table(cls.model, no_skip=True)
            print(":white_check_mark: StockInfo table recreated for testing")
        except Exception as e:
            print(f":warning: StockInfo table recreation failed: {e}")

        # Verify database configuration
        try:
            cls.mysql_config = {
                "user": GCONF.MYSQLUSER,
                "pwd": GCONF.MYSQLPWD,
                "host": GCONF.MYSQLHOST,
                "port": str(GCONF.MYSQLPORT),
                "db": GCONF.MYSQLDB,
            }

            for key, value in cls.mysql_config.items():
                if not value:
                    raise AssertionError(f"MySQL configuration missing: {key}")

        except Exception as e:
            raise AssertionError(f"Failed to read MySQL configuration: {e}")

        # Create StockInfoCRUD instance
        cls.crud = StockInfoCRUD()

        # Test database connection
        try:
            connection = get_db_connection(MStockInfo)
            with connection.get_session() as session:
                session.execute(text("SELECT 1"))
            print(":white_check_mark: StockInfo database connection successful")
        except Exception as e:
            raise AssertionError(f"Database connection failed: {e}")

    def setUp(self):
        """Setup for each test: prepare unique test data"""
        self.test_id = str(uuid.uuid4())[:8]
        self.test_code = f"STOCKTEST{self.test_id}.SZ"
        self.test_timestamp = datetime(2023, 1, 1, 9, 30)

        # Test stock info data
        self.test_stock_info_params = {
            "code": self.test_code,
            "code_name": f"Test Stock {self.test_id}",
            "industry": "Test Industry",
            "market": MARKET_TYPES.CHINA,
            "list_date": self.test_timestamp,
            "delist_date": datetime(2030, 12, 31),
            "currency": CURRENCY_TYPES.CNY,
            "source": SOURCE_TYPES.TUSHARE,
        }

    def tearDown(self):
        """Cleanup after each test"""
        try:
            # Remove all test records by test code pattern
            self.crud.remove({"code__like": f"STOCKTEST{self.test_id}%"})

            # Also clean up any bulk test records
            self.crud.remove({"code__like": f"STOCKTEST{self.test_id}_bulk%"})

            # Clean up by name pattern
            self.crud.remove({"code_name__like": f"Test Stock {self.test_id}%"})

            print(f":broom: Cleaned up all test data for STOCKTEST{self.test_id}")
        except Exception as e:
            print(f":warning: Cleanup failed: {e}")

    @classmethod
    def tearDownClass(cls):
        """Class-level cleanup: remove any remaining test data"""
        try:
            # Final cleanup of any remaining test records
            cls.crud.remove({"code__like": "STOCKTEST%"})
            cls.crud.remove({"code_name__like": "Test Stock%"})
            print(":broom: Final cleanup of all STOCKTEST records completed")
        except Exception as e:
            print(f":warning: Final cleanup failed: {e}")

    def test_StockInfoCRUD_Create_From_Params_Real(self):
        """Test StockInfoCRUD create from parameters with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create stock info from parameters
        created_stock_info = self.crud.create(**self.test_stock_info_params)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify creation
        self.assertIsNotNone(created_stock_info)
        self.assertIsInstance(created_stock_info, MStockInfo)
        self.assertEqual(created_stock_info.code, self.test_code)
        self.assertEqual(created_stock_info.code_name, f"Test Stock {self.test_id}")
        self.assertEqual(created_stock_info.industry, "Test Industry")
        self.assertEqual(created_stock_info.market, MARKET_TYPES.CHINA)
        self.assertEqual(created_stock_info.currency, CURRENCY_TYPES.CNY)

        # Verify in database
        found_stock_infos = self.crud.find(filters={"code": self.test_code})
        self.assertEqual(len(found_stock_infos), 1)
        self.assertEqual(found_stock_infos[0].code, self.test_code)

    def test_StockInfoCRUD_Add_StockInfo_Object_Real(self):
        """Test StockInfoCRUD add stock info object with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create stock info object (simple object with attributes)
        class StockInfoObj:
            def __init__(self, test_code, test_id, test_timestamp):
                self.code = test_code
                self.code_name = f"StockObj_{test_id}"
                self.industry = "Tech"
                self.market = MARKET_TYPES.NASDAQ
                self.list_date = test_timestamp
                self.delist_date = datetime(2030, 12, 31)
                self.currency = CURRENCY_TYPES.USD
                self.source = SOURCE_TYPES.YAHOO

        stock_info_obj = StockInfoObj(self.test_code, self.test_id, self.test_timestamp)

        # Convert stock info to MStockInfo and add
        mstock_info = self.crud._convert_input_item(stock_info_obj)
        added_stock_info = self.crud.add(mstock_info)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify addition
        self.assertIsNotNone(added_stock_info)
        self.assertEqual(added_stock_info.code, self.test_code)
        self.assertEqual(added_stock_info.code_name, f"StockObj_{self.test_id}")
        self.assertEqual(added_stock_info.industry, "Tech")
        self.assertEqual(added_stock_info.market, MARKET_TYPES.NASDAQ)
        self.assertEqual(added_stock_info.currency, CURRENCY_TYPES.USD)

        # Verify in database
        found_stock_infos = self.crud.find(filters={"code": self.test_code})
        self.assertEqual(len(found_stock_infos), 1)

    def test_StockInfoCRUD_Add_Batch_Real(self):
        """Test StockInfoCRUD batch addition with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create multiple stock info objects
        stock_infos = []
        batch_count = 3
        for i in range(batch_count):
            stock_info = self.crud._create_from_params(
                code=f"{self.test_code}_{i}",
                code_name=f"Test Stock {self.test_id}_{i}",
                industry=f"Industry_{i}",
                market=MARKET_TYPES.CHINA,
                list_date=self.test_timestamp,
                delist_date=datetime(2030, 12, 31),
                currency=CURRENCY_TYPES.CNY,
                source=SOURCE_TYPES.TUSHARE,
            )
            stock_infos.append(stock_info)

        # Add batch
        result = self.crud.add_batch(stock_infos)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by batch count
        self.assertEqual(batch_count, size1 - size0)

        # Verify batch addition
        self.assertIsInstance(result, tuple)

        # Verify each stock info in database
        for i in range(batch_count):
            found_stock_infos = self.crud.find(filters={"code": f"{self.test_code}_{i}"})
            self.assertEqual(len(found_stock_infos), 1)
            self.assertEqual(found_stock_infos[0].code_name, f"Test Stock {self.test_id}_{i}")
            self.assertEqual(found_stock_infos[0].industry, f"Industry_{i}")

    def test_StockInfoCRUD_Find_By_Market_Real(self):
        """Test StockInfoCRUD find by market business helper method with real database"""
        # Create stock infos with different markets
        markets = [MARKET_TYPES.CHINA, MARKET_TYPES.NASDAQ, MARKET_TYPES.OTHER]

        for i, market in enumerate(markets):
            params = self.test_stock_info_params.copy()
            params["code"] = f"{self.test_code}_{i}"
            params["market"] = market
            params["code_name"] = f"Stock{market.value}_{self.test_id}"
            self.crud.create(**params)

        # Test find by specific market
        sse_stocks = self.crud.find_by_market(MARKET_TYPES.CHINA)

        # Should find 1 SSE stock
        matching_sse = [s for s in sse_stocks if s.code.startswith(self.test_code)]
        self.assertEqual(len(matching_sse), 1)
        self.assertEqual(matching_sse[0].market, MARKET_TYPES.CHINA)

        # Test find by another market
        nasdaq_stocks = self.crud.find_by_market(MARKET_TYPES.NASDAQ)
        matching_nasdaq = [s for s in nasdaq_stocks if s.code.startswith(self.test_code)]
        self.assertEqual(len(matching_nasdaq), 1)
        self.assertEqual(matching_nasdaq[0].market, MARKET_TYPES.NASDAQ)

    def test_StockInfoCRUD_Find_By_Industry_Real(self):
        """Test StockInfoCRUD find by industry business helper method with real database"""
        # Create stock infos with different industries
        industries = ["Technology", "Finance", "Healthcare"]

        for i, industry in enumerate(industries):
            params = self.test_stock_info_params.copy()
            params["code"] = f"{self.test_code}_{i}"
            params["industry"] = industry
            params["code_name"] = f"{industry}_{self.test_id}"
            self.crud.create(**params)

        # Test find by specific industry
        tech_stocks = self.crud.find_by_industry("Technology")

        # Should find 1 Technology stock
        matching_tech = [s for s in tech_stocks if s.code.startswith(self.test_code)]
        self.assertEqual(len(matching_tech), 1)
        self.assertEqual(matching_tech[0].industry, "Technology")

        # Test find by another industry
        finance_stocks = self.crud.find_by_industry("Finance")
        matching_finance = [s for s in finance_stocks if s.code.startswith(self.test_code)]
        self.assertEqual(len(matching_finance), 1)
        self.assertEqual(matching_finance[0].industry, "Finance")

    def test_StockInfoCRUD_Search_By_Name_Real(self):
        """Test StockInfoCRUD search by name business helper method with real database"""
        # Create stock infos with different names
        names = ["Apple Inc", "Microsoft Corp", "Google LLC"]

        for i, name in enumerate(names):
            params = self.test_stock_info_params.copy()
            params["code"] = f"{self.test_code}_{i}"
            params["code_name"] = f"{name} {self.test_id}"
            self.crud.create(**params)

        # Test search by name pattern
        apple_stocks = self.crud.search_by_name("Apple%")

        # Should find 1 Apple stock
        matching_apple = [s for s in apple_stocks if s.code.startswith(self.test_code)]
        self.assertEqual(len(matching_apple), 1)
        self.assertTrue(matching_apple[0].code_name.startswith("Apple"))

        # Test search by partial name
        corp_stocks = self.crud.search_by_name("%Corp%")
        matching_corp = [s for s in corp_stocks if s.code.startswith(self.test_code)]
        self.assertEqual(len(matching_corp), 1)
        self.assertTrue("Corp" in matching_corp[0].code_name)

    def test_StockInfoCRUD_Get_All_Codes_Real(self):
        """Test StockInfoCRUD get all codes business helper method with real database"""
        # Create stock infos with different codes
        test_codes = [f"{self.test_code}_{i}" for i in range(3)]

        for i, code in enumerate(test_codes):
            params = self.test_stock_info_params.copy()
            params["code"] = code
            params["code_name"] = f"Test Stock {self.test_id}_{i}"
            self.crud.create(**params)

        # Get all codes
        all_codes = self.crud.get_all_codes()

        # Verify our test codes are included
        for test_code in test_codes:
            self.assertIn(test_code, all_codes)

        # Test get codes by market
        # First create stocks with specific market
        for i, code in enumerate(test_codes):
            params = self.test_stock_info_params.copy()
            params["code"] = f"{code}_market"
            params["market"] = MARKET_TYPES.OTHER
            params["code_name"] = f"Test Market Stock {self.test_id}_{i}"
            self.crud.create(**params)

        market_codes = self.crud.get_all_codes(market=MARKET_TYPES.OTHER)

        # Should find 3 codes in OTHER market
        test_market_codes = [c for c in market_codes if c.startswith(self.test_code)]
        self.assertEqual(len(test_market_codes), 3)

    def test_StockInfoCRUD_Get_Listed_Stocks_Real(self):
        """Test StockInfoCRUD get listed stocks with real database"""
        # Create stock infos with different list dates
        dates = [
            datetime(2020, 1, 1),
            datetime(2021, 6, 15),
            datetime(2022, 12, 31),
        ]

        for i, date in enumerate(dates):
            params = self.test_stock_info_params.copy()
            params["code"] = f"{self.test_code}_{i}"
            params["list_date"] = date
            params["code_name"] = f"Test Stock {self.test_id}_{i}"
            self.crud.create(**params)

        # Test find stocks listed after specific date
        recent_stocks = self.crud.find(filters={"list_date__gte": datetime(2021, 1, 1)})

        # Should find 2 stocks listed after 2021-01-01
        matching_recent = [s for s in recent_stocks if s.code.startswith(self.test_code)]
        self.assertEqual(len(matching_recent), 2)

        # Test find stocks listed before specific date
        old_stocks = self.crud.find(filters={"list_date__lte": datetime(2020, 12, 31)})

        # Should find 1 stock listed before 2020-12-31
        matching_old = [s for s in old_stocks if s.code.startswith(self.test_code)]
        self.assertEqual(len(matching_old), 1)

    def test_StockInfoCRUD_Count_By_Market_Real(self):
        """Test StockInfoCRUD count by market with real database"""
        # Create stock infos with different markets
        markets = [MARKET_TYPES.CHINA, MARKET_TYPES.OTHER, MARKET_TYPES.CHINA, MARKET_TYPES.NASDAQ]

        for i, market in enumerate(markets):
            params = self.test_stock_info_params.copy()
            params["code"] = f"{self.test_code}_{i}"
            params["market"] = market
            self.crud.create(**params)

        # Count SSE stocks
        sse_count = self.crud.count({"market": MARKET_TYPES.CHINA})
        # Should be at least 2 (our test records)
        self.assertGreaterEqual(sse_count, 2)

        # Count OTHER stocks
        other_count = self.crud.count({"market": MARKET_TYPES.OTHER})
        # Should be at least 1 (our test record)
        self.assertGreaterEqual(other_count, 1)

        # Count NASDAQ stocks
        nasdaq_count = self.crud.count({"market": MARKET_TYPES.NASDAQ})
        # Should be at least 1 (our test record)
        self.assertGreaterEqual(nasdaq_count, 1)

    def test_StockInfoCRUD_Count_By_Industry_Real(self):
        """Test StockInfoCRUD count by industry with real database"""
        # Create stock infos with different industries
        industries = ["Technology", "Finance", "Technology", "Healthcare"]

        for i, industry in enumerate(industries):
            params = self.test_stock_info_params.copy()
            params["code"] = f"{self.test_code}_{i}"
            params["industry"] = industry
            self.crud.create(**params)

        # Count Technology stocks
        tech_count = self.crud.count({"industry": "Technology"})
        # Should be at least 2 (our test records)
        self.assertGreaterEqual(tech_count, 2)

        # Count Finance stocks
        finance_count = self.crud.count({"industry": "Finance"})
        # Should be at least 1 (our test record)
        self.assertGreaterEqual(finance_count, 1)

    def test_StockInfoCRUD_Remove_By_Market_Real(self):
        """Test StockInfoCRUD remove by market with real database"""
        # Create stock infos with different markets
        markets = [MARKET_TYPES.CHINA, MARKET_TYPES.NASDAQ, MARKET_TYPES.OTHER]

        for i, market in enumerate(markets):
            params = self.test_stock_info_params.copy()
            params["code"] = f"{self.test_code}_{i}"
            params["market"] = market
            self.crud.create(**params)

        # Verify all created
        all_stocks = self.crud.find(filters={"code__like": f"{self.test_code}_"})
        self.assertEqual(len(all_stocks), 3)

        # Get table size before removal
        size0 = get_table_size(self.model)

        # Remove OTHER stocks
        self.crud.remove({"market": MARKET_TYPES.OTHER, "code__like": f"{self.test_code}_"})

        # Get table size after removal
        size1 = get_table_size(self.model)

        # Verify table size decreased by 1
        self.assertEqual(-1, size1 - size0)

        # Verify only SSE and NASDAQ stocks remain
        remaining_stocks = self.crud.find(filters={"code__like": f"{self.test_code}_"})
        self.assertEqual(len(remaining_stocks), 2)

        remaining_markets = [s.market for s in remaining_stocks]
        self.assertIn(MARKET_TYPES.CHINA, remaining_markets)
        self.assertIn(MARKET_TYPES.NASDAQ, remaining_markets)
        self.assertNotIn(MARKET_TYPES.OTHER, remaining_markets)

    def test_StockInfoCRUD_Get_Market_Statistics_Real(self):
        """Test StockInfoCRUD get market statistics with real database"""
        # Create stock infos with different markets
        markets = [MARKET_TYPES.CHINA, MARKET_TYPES.OTHER, MARKET_TYPES.OTHER, MARKET_TYPES.NASDAQ]

        for i, market in enumerate(markets):
            params = self.test_stock_info_params.copy()
            params["code"] = f"{self.test_code}_{i}"
            params["market"] = market
            self.crud.create(**params)

        # Get market statistics
        market_stats = {}
        for market in [MARKET_TYPES.CHINA, MARKET_TYPES.OTHER, MARKET_TYPES.NASDAQ]:
            count = self.crud.count({"market": market, "code__like": f"{self.test_code}_"})
            market_stats[market] = count

        # Verify statistics
        self.assertEqual(market_stats[MARKET_TYPES.CHINA], 1)
        self.assertEqual(market_stats[MARKET_TYPES.OTHER], 2)
        self.assertEqual(market_stats[MARKET_TYPES.NASDAQ], 1)

    def test_StockInfoCRUD_Output_Type_Conversion_Real(self):
        """Test StockInfoCRUD output type conversion with real database"""
        # Create test stock info
        created_stock_info = self.crud.create(**self.test_stock_info_params)

        # Get as model objects (MStockInfo)
        model_stock_infos = self.crud.find(filters={"code": self.test_code}, output_type="model")
        self.assertEqual(len(model_stock_infos), 1)
        self.assertIsInstance(model_stock_infos[0], MStockInfo)

        # StockInfo typically doesn't have a corresponding backtest object
        # So we test with default model output
        stock_info_objects = self.crud.find(filters={"code": self.test_code}, output_type="model")
        self.assertEqual(len(stock_info_objects), 1)
        self.assertIsInstance(stock_info_objects[0], MStockInfo)

        # Verify data consistency
        self.assertEqual(model_stock_infos[0].code, stock_info_objects[0].code)
        self.assertEqual(model_stock_infos[0].code_name, stock_info_objects[0].code_name)
        self.assertEqual(model_stock_infos[0].industry, stock_info_objects[0].industry)

    def test_StockInfoCRUD_DataFrame_Output_Real(self):
        """Test StockInfoCRUD DataFrame output with real database"""
        # Create test stock info
        created_stock_info = self.crud.create(**self.test_stock_info_params)

        # Get as DataFrame
        df_result = self.crud.find_by_market(MARKET_TYPES.CHINA, as_dataframe=True)

        # Verify DataFrame
        import pandas as pd

        self.assertIsInstance(df_result, pd.DataFrame)
        self.assertEqual(len(df_result), 1)
        self.assertEqual(df_result.iloc[0]["code"], self.test_code)
        self.assertEqual(df_result.iloc[0]["code_name"], f"Test Stock {self.test_id}")

    def test_StockInfoCRUD_Complex_Filters_Real(self):
        """Test StockInfoCRUD complex filters with real database"""
        # Create stock infos with different attributes
        test_data = [
            {"market": MARKET_TYPES.CHINA, "industry": "Technology", "currency": CURRENCY_TYPES.CNY},
            {"market": MARKET_TYPES.OTHER, "industry": "Finance", "currency": CURRENCY_TYPES.CNY},
            {"market": MARKET_TYPES.NASDAQ, "industry": "Technology", "currency": CURRENCY_TYPES.USD},
            {"market": MARKET_TYPES.OTHER, "industry": "Healthcare", "currency": CURRENCY_TYPES.USD},
        ]

        for i, data in enumerate(test_data):
            params = self.test_stock_info_params.copy()
            params["code"] = f"{self.test_code}_{i}"
            params["market"] = data["market"]
            params["industry"] = data["industry"]
            params["currency"] = data["currency"]
            self.crud.create(**params)

        # Test combined filters
        tech_cny_stocks = self.crud.find(
            filters={"code__like": f"{self.test_code}_", "industry": "Technology", "currency": CURRENCY_TYPES.CNY}
        )

        # Should find 1 stock (SSE Technology with CNY)
        self.assertEqual(len(tech_cny_stocks), 1)
        self.assertEqual(tech_cny_stocks[0].market, MARKET_TYPES.CHINA)
        self.assertEqual(tech_cny_stocks[0].industry, "Technology")

        # Test IN operator for markets
        us_market_stocks = self.crud.find(
            filters={"code__like": f"{self.test_code}_", "market__in": [MARKET_TYPES.NASDAQ, MARKET_TYPES.OTHER]}
        )

        # Should find 3 stocks (1 NASDAQ and 2 OTHER)
        self.assertEqual(len(us_market_stocks), 3)
        markets = [s.market for s in us_market_stocks]
        self.assertIn(MARKET_TYPES.NASDAQ, markets)
        self.assertIn(MARKET_TYPES.OTHER, markets)

    def test_StockInfoCRUD_Soft_Delete_Real(self):
        """Test StockInfoCRUD soft delete functionality with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create test stock info
        created_stock_info = self.crud.create(**self.test_stock_info_params)

        # Get table size after creation
        size1 = get_table_size(self.model)
        self.assertEqual(size0 + 1, size1)

        # Verify stock info exists
        found_stock_infos = self.crud.find(filters={"code": self.test_code})
        self.assertEqual(len(found_stock_infos), 1)
        stock_info_uuid = found_stock_infos[0].uuid

        # Perform soft delete if supported by CRUD
        if hasattr(self.crud, "soft_delete"):
            self.crud.soft_delete({"uuid": stock_info_uuid})

            # Get table size after soft delete
            size2 = get_table_size(self.model)

            # Table size should decrease after soft delete
            self.assertEqual(-1, size2 - size1)

            # Verify stock info is no longer found in normal queries
            found_stock_infos_after = self.crud.find(filters={"code": self.test_code})
            self.assertEqual(len(found_stock_infos_after), 0)

    def test_StockInfoCRUD_Bulk_Operations_With_Size_Verification_Real(self):
        """Test StockInfoCRUD bulk operations with table size verification"""
        # Get initial table size
        size0 = get_table_size(self.model)

        # Create bulk test data
        bulk_stock_infos = []
        bulk_count = 5

        for i in range(bulk_count):
            stock_info = self.crud._create_from_params(
                code=f"{self.test_code}_bulk_{i}",
                code_name=f"Bulk Test Stock {i}",
                industry=f"Industry_{i}",
                market=MARKET_TYPES.CHINA,
                list_date=datetime(2023, 1, i + 1),
                delist_date=datetime(2030, 12, 31),
                currency=CURRENCY_TYPES.CNY,
                source=SOURCE_TYPES.TUSHARE,
            )
            bulk_stock_infos.append(stock_info)

        # Perform bulk addition
        result = self.crud.add_batch(bulk_stock_infos)

        # Get table size after bulk addition
        size1 = get_table_size(self.model)

        # Verify table size increased by bulk_count
        self.assertEqual(bulk_count, size1 - size0)

        # Verify each stock info was added correctly
        for i in range(bulk_count):
            found_stock_infos = self.crud.find(filters={"code": f"{self.test_code}_bulk_{i}"})
            self.assertEqual(len(found_stock_infos), 1)
            self.assertEqual(found_stock_infos[0].code_name, f"Bulk Test Stock {i}")
            self.assertEqual(found_stock_infos[0].industry, f"Industry_{i}")

        # Bulk delete test stock infos
        self.crud.remove({"code__like": f"{self.test_code}_bulk_%"})

        # Get final table size
        size2 = get_table_size(self.model)

        # Verify table size returned to original
        self.assertEqual(size2, size0)

    def test_StockInfoCRUD_Exists_Real(self):
        """Test StockInfoCRUD exists functionality with real database"""
        # Test non-existent stock info
        exists_before = self.crud.exists(filters={"code": self.test_code})
        self.assertFalse(exists_before)

        # Create test stock info
        created_stock_info = self.crud.create(**self.test_stock_info_params)

        # Test existing stock info
        exists_after = self.crud.exists(filters={"code": self.test_code})
        self.assertTrue(exists_after)

        # Test with more specific filters
        exists_specific = self.crud.exists(
            filters={"code": self.test_code, "market": MARKET_TYPES.CHINA, "industry": "Test Industry"}
        )
        self.assertTrue(exists_specific)

        # Test with non-matching filters
        exists_false = self.crud.exists(filters={"code": self.test_code, "market": MARKET_TYPES.OTHER})
        self.assertFalse(exists_false)


    def test_StockInfoCRUD_Exception_Handling_Real(self):
        """Test StockInfoCRUD exception handling with real database"""
        # Test create with invalid data
        try:
            invalid_params = self.test_stock_info_params.copy()
            invalid_params["list_date"] = "invalid_date"
            # This might not raise exception due to datetime normalization
            result = self.crud.create(**invalid_params)
        except Exception as e:
            # Exception handling is working
            pass

        # Test find with empty filters (should not cause issues)
        all_stock_infos = self.crud.find(filters={})
        self.assertIsInstance(all_stock_infos, list)

        # Test remove with overly broad filters (should be safe)
        self.crud.remove({})  # Should be safely handled without affecting other tests

        # Test with invalid currency enum
        try:
            invalid_params = self.test_stock_info_params.copy()
            invalid_params["currency"] = "INVALID_CURRENCY"
            result = self.crud.create(**invalid_params)
        except Exception as e:
            # Exception handling is working
            pass
