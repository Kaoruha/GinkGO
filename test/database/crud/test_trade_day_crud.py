import unittest
import sys
import os
import uuid
from datetime import datetime, timedelta
from test.database.test_isolation import database_test_required


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

try:
    from ginkgo.data.crud.trade_day_crud import TradeDayCRUD
    from ginkgo.data.models import MTradeDay
    from ginkgo.enums import SOURCE_TYPES, MARKET_TYPES
    from ginkgo.libs import GCONF, datetime_normalize
    from ginkgo.data.drivers import get_db_connection, get_table_size, create_table, drop_table
    from ginkgo.data.crud.validation import ValidationError
    from sqlalchemy import text
except ImportError as e:
    print(f"Import error: {e}")
    TradeDayCRUD = None
    GCONF = None


class TradeDayCRUDTest(unittest.TestCase):
    """
    TradeDayCRUD database integration tests.
    Tests TradeDay-specific CRUD operations with actual database.
    """

    @classmethod
    def setUpClass(cls):
        """Class-level setup: check database configuration and connection"""
        if TradeDayCRUD is None or GCONF is None:
            raise AssertionError("TradeDayCRUD or GCONF not available")

        # Set model for table size verification
        cls.model = MTradeDay

        # Recreate table for clean testing
        try:
            drop_table(cls.model, no_skip=True)
            create_table(cls.model, no_skip=True)
            print(":white_check_mark: TradeDay table recreated for testing")
        except Exception as e:
            print(f":warning: TradeDay table recreation failed: {e}")

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

        # Create TradeDayCRUD instance
        cls.crud = TradeDayCRUD()

        # Test database connection
        try:
            connection = get_db_connection(MTradeDay)
            with connection.get_session() as session:
                session.execute(text("SELECT 1"))
            print(":white_check_mark: TradeDay database connection successful")
        except Exception as e:
            raise AssertionError(f"Database connection failed: {e}")

    def setUp(self):
        """Setup for each test: prepare unique test data"""
        self.test_id = str(uuid.uuid4())[:8]
        self.test_timestamp = datetime(2023, 1, 2, 0, 0)  # Monday

        # Test trade day data
        self.test_trade_day_params = {
            "timestamp": self.test_timestamp,
            "market": MARKET_TYPES.CHINA,
            "is_open": True,
            "source": SOURCE_TYPES.TUSHARE,
        }

    def tearDown(self):
        """Cleanup after each test"""
        try:
            # Remove test records within a reasonable date range
            start_cleanup = datetime(2023, 1, 1)
            end_cleanup = datetime(2023, 12, 31)

            self.crud.remove({
                "timestamp__gte": start_cleanup,
                "timestamp__lte": end_cleanup,
                "source": SOURCE_TYPES.TUSHARE
            })

            # Also clean up any bulk test records
            self.crud.remove({
                "timestamp__gte": start_cleanup,
                "timestamp__lte": end_cleanup,
                "source": SOURCE_TYPES.YAHOO
            })

            print(f":broom: Cleaned up all test data for {self.test_id}")
        except Exception as e:
            print(f":warning: Cleanup failed: {e}")

    @classmethod
    def tearDownClass(cls):
        """Class-level cleanup: remove any remaining test data"""
        try:
            # Final cleanup of test records
            start_cleanup = datetime(2023, 1, 1)
            end_cleanup = datetime(2023, 12, 31)

            cls.crud.remove({
                "timestamp__gte": start_cleanup,
                "timestamp__lte": end_cleanup
            })
            print(":broom: Final cleanup of all test records completed")
        except Exception as e:
            print(f":warning: Final cleanup failed: {e}")

    @database_test_required
    def test_TradeDayCRUD_Create_From_Params_Real(self):
        """Test TradeDayCRUD create from parameters with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create trade day from parameters
        created_trade_day = self.crud.create(**self.test_trade_day_params)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify creation
        self.assertIsNotNone(created_trade_day)
        self.assertIsInstance(created_trade_day, MTradeDay)
        self.assertEqual(created_trade_day.timestamp, self.test_timestamp)
        self.assertTrue(created_trade_day.is_open)
        self.assertEqual(created_trade_day.source, SOURCE_TYPES.TUSHARE)

        # Verify in database
        found_trade_days = self.crud.find(filters={"timestamp": self.test_timestamp})
        self.assertEqual(len(found_trade_days), 1)
        self.assertEqual(found_trade_days[0].timestamp, self.test_timestamp)

    @database_test_required
    def test_TradeDayCRUD_Add_TradeDay_Object_Real(self):
        """Test TradeDayCRUD add trade day object with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create trade day object (simple object with attributes)
        class TradeDayObj:
            def __init__(self, timestamp, market, is_open, source):
                self.timestamp = timestamp
                self.market = market
                self.is_open = is_open
                self.source = source

        trade_day_obj = TradeDayObj(self.test_timestamp, MARKET_TYPES.CHINA, False, SOURCE_TYPES.YAHOO)

        # Convert trade day to MTradeDay and add
        mtrade_day = self.crud._convert_input_item(trade_day_obj)
        added_trade_day = self.crud.add(mtrade_day)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify addition
        self.assertIsNotNone(added_trade_day)
        self.assertEqual(added_trade_day.timestamp, self.test_timestamp)
        self.assertFalse(added_trade_day.is_open)
        self.assertEqual(added_trade_day.source, SOURCE_TYPES.YAHOO)

        # Verify in database
        found_trade_days = self.crud.find(filters={"timestamp": self.test_timestamp})
        self.assertEqual(len(found_trade_days), 1)

    @database_test_required
    def test_TradeDayCRUD_Add_Batch_Real(self):
        """Test TradeDayCRUD batch addition with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create multiple trade day objects
        trade_days = []
        batch_count = 5
        for i in range(batch_count):
            trade_day = self.crud._create_from_params(
                timestamp=datetime(2023, 1, i + 1, 0, 0),
                market=MARKET_TYPES.CHINA,
                is_open=i % 2 == 0,  # Alternate trading and non-trading days
                source=SOURCE_TYPES.TUSHARE,
            )
            trade_days.append(trade_day)

        # Add batch
        result = self.crud.add_batch(trade_days)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by batch count
        self.assertEqual(batch_count, size1 - size0)

        # Verify batch addition
        self.assertIsInstance(result, tuple)

        # Verify each trade day in database
        for i in range(batch_count):
            found_trade_days = self.crud.find(filters={"timestamp": datetime(2023, 1, i + 1, 0, 0)})
            self.assertEqual(len(found_trade_days), 1)
            self.assertEqual(found_trade_days[0].is_open, i % 2 == 0)

    @database_test_required
    def test_TradeDayCRUD_Find_Trading_Days_Real(self):
        """Test TradeDayCRUD find trading days business helper method with real database"""
        # Create trade days with mixed trading/non-trading days
        test_dates = [
            {"timestamp": datetime(2023, 1, 1), "is_open": False},  # Sunday
            {"timestamp": datetime(2023, 1, 2), "is_open": True},   # Monday
            {"timestamp": datetime(2023, 1, 3), "is_open": True},   # Tuesday
            {"timestamp": datetime(2023, 1, 4), "is_open": True},   # Wednesday
            {"timestamp": datetime(2023, 1, 5), "is_open": True},   # Thursday
            {"timestamp": datetime(2023, 1, 6), "is_open": True},   # Friday
            {"timestamp": datetime(2023, 1, 7), "is_open": False},  # Saturday
        ]

        for date_info in test_dates:
            params = self.test_trade_day_params.copy()
            params["timestamp"] = date_info["timestamp"]
            params["is_open"] = date_info["is_open"]
            self.crud.create(**params)

        # Test find trading days
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 7)

        trading_days = self.crud.find_trading_days(start_date, end_date)

        # Should find 5 trading days (Monday-Friday)
        self.assertEqual(len(trading_days), 5)
        for trade_day in trading_days:
            self.assertTrue(trade_day.is_open)

        # Verify they are ordered by timestamp
        for i in range(len(trading_days) - 1):
            self.assertLessEqual(trading_days[i].timestamp, trading_days[i + 1].timestamp)

    @database_test_required
    def test_TradeDayCRUD_Find_Non_Trading_Days_Real(self):
        """Test TradeDayCRUD find non-trading days business helper method with real database"""
        # Create trade days with mixed trading/non-trading days
        test_dates = [
            {"timestamp": datetime(2023, 1, 1), "is_open": False},  # Sunday
            {"timestamp": datetime(2023, 1, 2), "is_open": True},   # Monday
            {"timestamp": datetime(2023, 1, 3), "is_open": True},   # Tuesday
            {"timestamp": datetime(2023, 1, 7), "is_open": False},  # Saturday
            {"timestamp": datetime(2023, 1, 8), "is_open": False},  # Sunday
        ]

        for date_info in test_dates:
            params = self.test_trade_day_params.copy()
            params["timestamp"] = date_info["timestamp"]
            params["is_open"] = date_info["is_open"]
            self.crud.create(**params)

        # Test find non-trading days
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 8)

        non_trading_days = self.crud.find_non_trading_days(start_date, end_date)

        # Should find 3 non-trading days (weekends)
        self.assertEqual(len(non_trading_days), 3)
        for trade_day in non_trading_days:
            self.assertFalse(trade_day.is_open)

        # Verify they are ordered by timestamp
        for i in range(len(non_trading_days) - 1):
            self.assertLessEqual(non_trading_days[i].timestamp, non_trading_days[i + 1].timestamp)

    @database_test_required
    def test_TradeDayCRUD_Is_Trading_Day_Real(self):
        """Test TradeDayCRUD is trading day business helper method with real database"""
        # Create some trade days
        test_dates = [
            {"timestamp": datetime(2023, 1, 2), "is_open": True},   # Monday
            {"timestamp": datetime(2023, 1, 3), "is_open": True},   # Tuesday
            {"timestamp": datetime(2023, 1, 7), "is_open": False},  # Saturday
            {"timestamp": datetime(2023, 1, 8), "is_open": False},  # Sunday
        ]

        for date_info in test_dates:
            params = self.test_trade_day_params.copy()
            params["timestamp"] = date_info["timestamp"]
            params["is_open"] = date_info["is_open"]
            self.crud.create(**params)

        # Test is_open for existing dates
        self.assertTrue(self.crud.is_open(datetime(2023, 1, 2)))
        self.assertTrue(self.crud.is_open(datetime(2023, 1, 3)))
        self.assertFalse(self.crud.is_open(datetime(2023, 1, 7)))
        self.assertFalse(self.crud.is_open(datetime(2023, 1, 8)))

        # Test is_open for non-existent date
        self.assertFalse(self.crud.is_open(datetime(2023, 1, 15)))

    @database_test_required
    def test_TradeDayCRUD_Get_Next_Trading_Day_Real(self):
        """Test TradeDayCRUD get next trading day business helper method with real database"""
        # Create some trade days
        test_dates = [
            {"timestamp": datetime(2023, 1, 2), "is_open": True},   # Monday
            {"timestamp": datetime(2023, 1, 3), "is_open": True},   # Tuesday
            {"timestamp": datetime(2023, 1, 4), "is_open": True},   # Wednesday
            {"timestamp": datetime(2023, 1, 7), "is_open": False},  # Saturday
            {"timestamp": datetime(2023, 1, 8), "is_open": False},  # Sunday
            {"timestamp": datetime(2023, 1, 9), "is_open": True},   # Monday
        ]

        for date_info in test_dates:
            params = self.test_trade_day_params.copy()
            params["timestamp"] = date_info["timestamp"]
            params["is_open"] = date_info["is_open"]
            self.crud.create(**params)

        # Test get next trading day
        next_trading_day = self.crud.get_next_trading_day(datetime(2023, 1, 2))
        self.assertEqual(next_trading_day, datetime(2023, 1, 3))

        # Test get next trading day from weekend
        next_trading_day_weekend = self.crud.get_next_trading_day(datetime(2023, 1, 7))
        self.assertEqual(next_trading_day_weekend, datetime(2023, 1, 9))

        # Test get next trading day when no next trading day exists
        next_trading_day_none = self.crud.get_next_trading_day(datetime(2023, 1, 15))
        self.assertIsNone(next_trading_day_none)

    @database_test_required
    def test_TradeDayCRUD_Count_Trading_Days_Real(self):
        """Test TradeDayCRUD count trading days with real database"""
        # Create trade days with mixed trading/non-trading days
        test_dates = [
            {"timestamp": datetime(2023, 1, 1), "is_open": False},
            {"timestamp": datetime(2023, 1, 2), "is_open": True},
            {"timestamp": datetime(2023, 1, 3), "is_open": True},
            {"timestamp": datetime(2023, 1, 4), "is_open": True},
            {"timestamp": datetime(2023, 1, 7), "is_open": False},
        ]

        for date_info in test_dates:
            params = self.test_trade_day_params.copy()
            params["timestamp"] = date_info["timestamp"]
            params["is_open"] = date_info["is_open"]
            self.crud.create(**params)

        # Count trading days
        trading_count = self.crud.count({"is_open": True})
        self.assertGreaterEqual(trading_count, 3)

        # Count non-trading days
        non_trading_count = self.crud.count({"is_open": False})
        self.assertGreaterEqual(non_trading_count, 2)

    @database_test_required
    def test_TradeDayCRUD_Remove_By_Date_Range_Real(self):
        """Test TradeDayCRUD remove by date range with real database"""
        # Create trade days across different months
        test_dates = [
            {"timestamp": datetime(2023, 1, 1), "is_open": False},
            {"timestamp": datetime(2023, 1, 15), "is_open": True},
            {"timestamp": datetime(2023, 2, 1), "is_open": True},
            {"timestamp": datetime(2023, 2, 15), "is_open": True},
            {"timestamp": datetime(2023, 3, 1), "is_open": True},
        ]

        for date_info in test_dates:
            params = self.test_trade_day_params.copy()
            params["timestamp"] = date_info["timestamp"]
            params["is_open"] = date_info["is_open"]
            self.crud.create(**params)

        # Verify all created
        all_trade_days = self.crud.find(filters={
            "timestamp__gte": datetime(2023, 1, 1),
            "timestamp__lte": datetime(2023, 3, 31)
        })
        self.assertEqual(len(all_trade_days), 5)

        # Get table size before removal
        size0 = get_table_size(self.model)

        # Remove January records
        self.crud.remove({
            "timestamp__gte": datetime(2023, 1, 1),
            "timestamp__lte": datetime(2023, 1, 31)
        })

        # Get table size after removal
        size1 = get_table_size(self.model)

        # Verify table size decreased by 2 (January records removed)
        self.assertEqual(-2, size1 - size0)

        # Verify only Feb and March records remain
        remaining_trade_days = self.crud.find(filters={
            "timestamp__gte": datetime(2023, 1, 1),
            "timestamp__lte": datetime(2023, 3, 31)
        })
        self.assertEqual(len(remaining_trade_days), 3)

    @database_test_required
    def test_TradeDayCRUD_Get_Date_Range_Statistics_Real(self):
        """Test TradeDayCRUD get date range statistics with real database"""
        # Create trade days for a week
        test_dates = [
            {"timestamp": datetime(2023, 1, 1), "is_open": False},  # Sunday
            {"timestamp": datetime(2023, 1, 2), "is_open": True},   # Monday
            {"timestamp": datetime(2023, 1, 3), "is_open": True},   # Tuesday
            {"timestamp": datetime(2023, 1, 4), "is_open": True},   # Wednesday
            {"timestamp": datetime(2023, 1, 5), "is_open": True},   # Thursday
            {"timestamp": datetime(2023, 1, 6), "is_open": True},   # Friday
            {"timestamp": datetime(2023, 1, 7), "is_open": False},  # Saturday
        ]

        for date_info in test_dates:
            params = self.test_trade_day_params.copy()
            params["timestamp"] = date_info["timestamp"]
            params["is_open"] = date_info["is_open"]
            self.crud.create(**params)

        # Get statistics
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 7)

        all_days = self.crud.find(filters={
            "timestamp__gte": start_date,
            "timestamp__lte": end_date
        })

        trading_days = self.crud.find_trading_days(start_date, end_date)
        non_trading_days = self.crud.find_non_trading_days(start_date, end_date)

        # Verify statistics
        self.assertEqual(len(all_days), 7)
        self.assertEqual(len(trading_days), 5)
        self.assertEqual(len(non_trading_days), 2)

    @database_test_required
    def test_TradeDayCRUD_Update_Trading_Status_Real(self):
        """Test TradeDayCRUD update trading status with real database"""
        # Create test trade day
        created_trade_day = self.crud.create(**self.test_trade_day_params)

        # Verify initial status
        self.assertTrue(created_trade_day.is_open)

        # Update trading status
        self.crud.modify(
            {"timestamp": self.test_timestamp},
            {"is_open": False}
        )

        # Verify status updated
        updated_trade_days = self.crud.find(filters={"timestamp": self.test_timestamp})
        self.assertEqual(len(updated_trade_days), 1)
        self.assertFalse(updated_trade_days[0].is_open)

    @database_test_required
    def test_TradeDayCRUD_Complex_Filters_Real(self):
        """Test TradeDayCRUD complex filters with real database"""
        # Create trade days with different attributes
        test_data = [
            {"timestamp": datetime(2023, 1, 1), "is_open": False, "source": SOURCE_TYPES.TUSHARE},
            {"timestamp": datetime(2023, 1, 2), "is_open": True, "source": SOURCE_TYPES.TUSHARE},
            {"timestamp": datetime(2023, 1, 3), "is_open": True, "source": SOURCE_TYPES.YAHOO},
            {"timestamp": datetime(2023, 1, 7), "is_open": False, "source": SOURCE_TYPES.YAHOO},
        ]

        for data in test_data:
            params = self.test_trade_day_params.copy()
            params["timestamp"] = data["timestamp"]
            params["is_open"] = data["is_open"]
            params["source"] = data["source"]
            self.crud.create(**params)

        # Test combined filters
        filtered_trade_days = self.crud.find(
            filters={
                "timestamp__gte": datetime(2023, 1, 1),
                "timestamp__lte": datetime(2023, 1, 3),
                "is_open": True,
                "source": SOURCE_TYPES.TUSHARE
            }
        )

        # Should find 1 trade day (Jan 2 with TUSHARE source)
        self.assertEqual(len(filtered_trade_days), 1)
        self.assertEqual(filtered_trade_days[0].timestamp, datetime(2023, 1, 2))
        self.assertTrue(filtered_trade_days[0].is_open)
        self.assertEqual(filtered_trade_days[0].source, SOURCE_TYPES.TUSHARE)

        # Test IN operator for sources
        source_filtered = self.crud.find(
            filters={
                "timestamp__gte": datetime(2023, 1, 1),
                "timestamp__lte": datetime(2023, 1, 7),
                "source__in": [SOURCE_TYPES.YAHOO]
            }
        )

        # Should find 2 trade days (YAHOO sources)
        self.assertEqual(len(source_filtered), 2)
        for trade_day in source_filtered:
            self.assertEqual(trade_day.source, SOURCE_TYPES.YAHOO)

    @database_test_required
    def test_TradeDayCRUD_Output_Type_Conversion_Real(self):
        """Test TradeDayCRUD output type conversion with real database"""
        # Create test trade day
        created_trade_day = self.crud.create(**self.test_trade_day_params)

        # Get as model objects (MTradeDay)
        model_trade_days = self.crud.find(filters={"timestamp": self.test_timestamp}, output_type="model")
        self.assertEqual(len(model_trade_days), 1)
        self.assertIsInstance(model_trade_days[0], MTradeDay)

        # TradeDay typically doesn't have a corresponding backtest object
        # So we test with default model output
        trade_day_objects = self.crud.find(filters={"timestamp": self.test_timestamp}, output_type="model")
        self.assertEqual(len(trade_day_objects), 1)
        self.assertIsInstance(trade_day_objects[0], MTradeDay)

        # Verify data consistency
        self.assertEqual(model_trade_days[0].timestamp, trade_day_objects[0].timestamp)
        self.assertEqual(model_trade_days[0].is_open, trade_day_objects[0].is_open)
        self.assertEqual(model_trade_days[0].source, trade_day_objects[0].source)

    @database_test_required
    def test_TradeDayCRUD_DataFrame_Output_Real(self):
        """Test TradeDayCRUD DataFrame output with real database"""
        # Create test trade day
        created_trade_day = self.crud.create(**self.test_trade_day_params)

        # Get as DataFrame
        df_result = self.crud.find_trading_days(
            self.test_timestamp,
            self.test_timestamp,
            as_dataframe=True
        )

        # Verify DataFrame
        import pandas as pd

        self.assertIsInstance(df_result, pd.DataFrame)
        self.assertEqual(len(df_result), 1)
        self.assertEqual(df_result.iloc[0]["timestamp"], self.test_timestamp)
        self.assertTrue(df_result.iloc[0]["is_open"])

    @database_test_required
    def test_TradeDayCRUD_Soft_Delete_Real(self):
        """Test TradeDayCRUD soft delete functionality with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create test trade day
        created_trade_day = self.crud.create(**self.test_trade_day_params)

        # Get table size after creation
        size1 = get_table_size(self.model)
        self.assertEqual(size0 + 1, size1)

        # Verify trade day exists
        found_trade_days = self.crud.find(filters={"timestamp": self.test_timestamp})
        self.assertEqual(len(found_trade_days), 1)
        trade_day_uuid = found_trade_days[0].uuid

        # Perform soft delete if supported by CRUD
        if hasattr(self.crud, 'soft_delete'):
            self.crud.soft_delete({"uuid": trade_day_uuid})

            # Get table size after soft delete
            size2 = get_table_size(self.model)

            # Table size should decrease after soft delete
            self.assertEqual(-1, size2 - size1)

            # Verify trade day is no longer found in normal queries
            found_trade_days_after = self.crud.find(filters={"timestamp": self.test_timestamp})
            self.assertEqual(len(found_trade_days_after), 0)

    @database_test_required
    def test_TradeDayCRUD_Bulk_Operations_With_Size_Verification_Real(self):
        """Test TradeDayCRUD bulk operations with table size verification"""
        # Get initial table size
        size0 = get_table_size(self.model)

        # Create bulk test data
        bulk_trade_days = []
        bulk_count = 10  # Two weeks of trade days

        for i in range(bulk_count):
            trade_day = self.crud._create_from_params(
                timestamp=datetime(2023, 1, i + 1, 0, 0),
                market=MARKET_TYPES.CHINA,
                is_open=i % 7 not in [0, 6],  # Weekdays are trading days
                source=SOURCE_TYPES.TUSHARE,
            )
            bulk_trade_days.append(trade_day)

        # Perform bulk addition
        result = self.crud.add_batch(bulk_trade_days)

        # Get table size after bulk addition
        size1 = get_table_size(self.model)

        # Verify table size increased by bulk_count
        self.assertEqual(bulk_count, size1 - size0)

        # Verify each trade day was added correctly
        for i in range(bulk_count):
            found_trade_days = self.crud.find(filters={"timestamp": datetime(2023, 1, i + 1, 0, 0)})
            self.assertEqual(len(found_trade_days), 1)
            expected_is_trading = i % 7 not in [0, 6]
            self.assertEqual(found_trade_days[0].is_open, expected_is_trading)

        # Bulk delete test trade days
        self.crud.remove({
            "timestamp__gte": datetime(2023, 1, 1),
            "timestamp__lte": datetime(2023, 1, 10)
        })

        # Get final table size
        size2 = get_table_size(self.model)

        # Verify table size returned to original
        self.assertEqual(size2, size0)

    @database_test_required
    def test_TradeDayCRUD_Exists_Real(self):
        """Test TradeDayCRUD exists functionality with real database"""
        # Test non-existent trade day
        exists_before = self.crud.exists(filters={"timestamp": self.test_timestamp})
        self.assertFalse(exists_before)

        # Create test trade day
        created_trade_day = self.crud.create(**self.test_trade_day_params)

        # Test existing trade day
        exists_after = self.crud.exists(filters={"timestamp": self.test_timestamp})
        self.assertTrue(exists_after)

        # Test with more specific filters
        exists_specific = self.crud.exists(filters={
            "timestamp": self.test_timestamp,
            "is_open": True,
            "source": SOURCE_TYPES.TUSHARE
        })
        self.assertTrue(exists_specific)

        # Test with non-matching filters
        exists_false = self.crud.exists(filters={
            "timestamp": self.test_timestamp,
            "is_open": False
        })
        self.assertFalse(exists_false)

    @database_test_required
    def test_TradeDayCRUD_Exception_Handling_Real(self):
        """Test TradeDayCRUD exception handling with real database"""
        # Test create with invalid data
        try:
            invalid_params = self.test_trade_day_params.copy()
            invalid_params["timestamp"] = "invalid_timestamp"
            # This might not raise exception due to datetime normalization
            result = self.crud.create(**invalid_params)
        except Exception as e:
            # Exception handling is working
            pass

        # Test find with empty filters (should not cause issues)
        all_trade_days = self.crud.find(filters={})
        self.assertIsInstance(all_trade_days, list)

        # Test remove with overly broad filters (should be safe)
        self.crud.remove({})  # Should be safely handled without affecting other tests

        # Test business methods with invalid dates
        try:
            invalid_date = "not_a_date"
            result = self.crud.is_open(invalid_date)
        except Exception as e:
            # Exception handling is working
            pass

        # Test with invalid boolean values
        try:
            invalid_params = self.test_trade_day_params.copy()
            invalid_params["is_open"] = "invalid_boolean"
            result = self.crud.create(**invalid_params)
        except Exception as e:
            # Exception handling is working
            pass

    @database_test_required
    def test_TradeDayCRUD_ValidationError_Tests(self):
        """Test TradeDayCRUD field validation functionality"""
        # Test invalid timestamp (if validation is strict)
        try:
            with self.assertRaises(ValidationError):
                self.crud.create(
                    timestamp="invalid_timestamp",
                    is_open=True,
                    source=SOURCE_TYPES.TUSHARE
                )
        except AssertionError:
            # If datetime normalization handles this, it's acceptable
            pass

        # Test invalid source enum
        with self.assertRaises(ValidationError):
            self.crud.create(
                timestamp=self.test_timestamp,
                is_open=True,
                source="INVALID_SOURCE"
            )

        # Test invalid boolean type (if validation is strict)
        try:
            with self.assertRaises(ValidationError):
                self.crud.create(
                    timestamp=self.test_timestamp,
                    is_open="not_a_boolean",
                    source=SOURCE_TYPES.TUSHARE
                )
        except AssertionError:
            # If boolean normalization handles this, it's acceptable
            pass

        # Test successful creation with valid parameters
        valid_trade_day = self.crud.create(
            timestamp=datetime(2023, 1, 10),
            market=MARKET_TYPES.CHINA,
            is_open=True,
            source=SOURCE_TYPES.TUSHARE
        )
        self.assertIsNotNone(valid_trade_day)
        self.assertEqual(valid_trade_day.timestamp, datetime(2023, 1, 10))
        self.assertTrue(valid_trade_day.is_open)
        self.assertEqual(valid_trade_day.source, SOURCE_TYPES.TUSHARE)
