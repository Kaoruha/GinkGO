import unittest
import sys
import os
import uuid
from decimal import Decimal
from datetime import datetime
from sqlalchemy import text
from test.database.test_isolation import database_test_required


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

try:
    from ginkgo.data.crud.tick_crud import TickCRUD, get_tick_model
    from ginkgo.data.models import MTick
    from ginkgo.backtest import Tick
    from ginkgo.enums import TICKDIRECTION_TYPES, SOURCE_TYPES
    from ginkgo.libs import GCONF, datetime_normalize, to_decimal
    from ginkgo.data.drivers import get_db_connection, get_table_size, create_table, drop_table
except ImportError as e:
    print(f"Import error: {e}")
    TickCRUD = None
    GCONF = None


class TickCRUDTest(unittest.TestCase):
    """
    TickCRUD database integration tests.
    Tests Tick-specific CRUD operations with dynamic table partitioning.
    """

    @classmethod
    def setUpClass(cls):
        """Class-level setup: check database configuration and connection"""
        if TickCRUD is None or GCONF is None:
            raise AssertionError("TickCRUD or GCONF not available")

        # Test stock codes for dynamic table testing
        cls.test_code_primary = "TEST001.SZ"
        cls.test_code_secondary = "TEST002.SH"

        # Get dynamic models for both test codes
        cls.model_primary = get_tick_model(cls.test_code_primary)
        cls.model_secondary = get_tick_model(cls.test_code_secondary)

        # Recreate tables for clean testing
        for code, model in [(cls.test_code_primary, cls.model_primary),
                           (cls.test_code_secondary, cls.model_secondary)]:
            try:
                drop_table(model, no_skip=True)
                create_table(model, no_skip=True)
                print(f":white_check_mark: Tick table for {code} recreated for testing")
            except Exception as e:
                print(f":warning: Tick table for {code} recreation failed: {e}")

        # Verify ClickHouse database configuration (MTick uses ClickHouse)
        try:
            cls.clickhouse_config = {
                "user": GCONF.CLICKUSER,
                "pwd": GCONF.CLICKPWD,
                "host": GCONF.CLICKHOST,
                "port": str(GCONF.CLICKPORT),
                "db": GCONF.CLICKDB,
            }

            for key, value in cls.clickhouse_config.items():
                if not value:
                    raise AssertionError(f"ClickHouse configuration missing: {key}")

        except Exception as e:
            raise AssertionError(f"Failed to read ClickHouse configuration: {e}")

        # Create TickCRUD instances for both test codes
        cls.crud_primary = TickCRUD(cls.test_code_primary)
        cls.crud_secondary = TickCRUD(cls.test_code_secondary)

        # Test database connection
        try:
            connection = get_db_connection(cls.model_primary)
            with connection.get_session() as session:
                session.execute(text("SELECT 1"))
            print(":white_check_mark: Tick database connection successful")
        except Exception as e:
            raise AssertionError(f"Database connection failed: {e}")

    def setUp(self):
        """Setup for each test: prepare unique test data"""
        self.test_id = str(uuid.uuid4())[:8]
        self.test_timestamp = datetime(2023, 6, 15, 14, 30, 0)

        # Test tick data based on actual MTick fields
        self.test_tick_params = {
            "code": self.test_code_primary,
            "price": to_decimal(10.50),
            "volume": 1000,
            "direction": TICKDIRECTION_TYPES.BUY,
            "timestamp": self.test_timestamp,
            "source": SOURCE_TYPES.TDX,
        }

    def tearDown(self):
        """Cleanup after each test"""
        try:
            # Clean up both test tables using delete_all method
            for crud in [self.crud_primary, self.crud_secondary]:
                crud.delete_all()  # Remove all test data for each stock
            print(f":broom: Cleaned up test data for {self.test_code_primary} and {self.test_code_secondary}")
        except Exception as e:
            print(f":warning: Cleanup failed: {e}")
            # Fallback: try table recreation if delete_all fails
            try:
                for code, model in [(self.test_code_primary, self.model_primary),
                                   (self.test_code_secondary, self.model_secondary)]:
                    drop_table(model, no_skip=True)
                    create_table(model, no_skip=True)
                print(f":arrows_counterclockwise: Fallback cleanup: recreated tables for {self.test_code_primary} and {self.test_code_secondary}")
            except Exception as fallback_error:
                print(f":warning: Fallback cleanup also failed: {fallback_error}")

    @classmethod
    def tearDownClass(cls):
        """Class-level cleanup: remove any remaining test data"""
        try:
            # Final cleanup of both test tables using delete_all method
            for crud in [cls.crud_primary, cls.crud_secondary]:
                crud.delete_all()
            print(":broom: Final cleanup of all tick test data completed")
        except Exception as e:
            print(f":warning: Final cleanup failed: {e}")
            # Fallback: try table recreation for final cleanup
            try:
                for code, model in [(cls.test_code_primary, cls.model_primary),
                                   (cls.test_code_secondary, cls.model_secondary)]:
                    drop_table(model, no_skip=True)
                    create_table(model, no_skip=True)
                print(f":arrows_counterclockwise: Final fallback cleanup: recreated tables for {cls.test_code_primary} and {cls.test_code_secondary}")
            except Exception as fallback_error:
                print(f":warning: Final fallback cleanup also failed: {fallback_error}")

    @database_test_required
    def test_TickCRUD_Constructor_And_Dynamic_Model_Real(self):
        """Test TickCRUD constructor and dynamic model creation with real database"""
        # Test normal constructor
        crud = TickCRUD("000001.SZ")
        self.assertEqual(crud.code, "000001.SZ")
        self.assertIsNotNone(crud.model_class)
        self.assertEqual(crud.model_class.__tablename__, "000001_SZ_Tick")

        # Test different code creates different model
        crud2 = TickCRUD("000002.SH")
        self.assertEqual(crud2.code, "000002.SH")
        self.assertEqual(crud2.model_class.__tablename__, "000002_SH_Tick")
        self.assertNotEqual(crud.model_class, crud2.model_class)

        # Test invalid constructor parameters
        with self.assertRaises(ValueError):
            TickCRUD("")  # Empty code

        with self.assertRaises(ValueError):
            TickCRUD(None)  # None code

    @database_test_required
    def test_TickCRUD_Model_Registry_Caching_Real(self):
        """Test dynamic model registry and caching with real database"""
        # First call creates model
        model1 = get_tick_model("CACHE001.SZ")
        self.assertIsNotNone(model1)
        self.assertEqual(model1.__tablename__, "CACHE001_SZ_Tick")

        # Second call should return cached model
        model2 = get_tick_model("CACHE001.SZ")
        self.assertIs(model1, model2)  # Same object reference

        # Different code creates different model
        model3 = get_tick_model("CACHE002.SH")
        self.assertIsNot(model1, model3)  # Different object reference
        self.assertNotEqual(model1.__tablename__, model3.__tablename__)

    @database_test_required
    def test_TickCRUD_Create_From_Params_Real(self):
        """Test TickCRUD create from parameters with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model_primary)

        # Create tick from parameters
        created_tick = self.crud_primary.create(**self.test_tick_params)

        # Get table size after operation
        size1 = get_table_size(self.model_primary)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify creation
        self.assertIsNotNone(created_tick)
        self.assertIsInstance(created_tick, self.model_primary)
        self.assertEqual(created_tick.code, self.test_code_primary)
        self.assertEqual(created_tick.price, to_decimal(10.50))
        self.assertEqual(created_tick.volume, 1000)
        self.assertEqual(created_tick.direction, TICKDIRECTION_TYPES.BUY)
        self.assertEqual(created_tick.source, SOURCE_TYPES.TDX)

        # Verify in database
        found_ticks = self.crud_primary.find(filters={"code": self.test_code_primary})
        self.assertEqual(len(found_ticks), 1)
        self.assertEqual(found_ticks[0].code, self.test_code_primary)

    @database_test_required
    def test_TickCRUD_Add_Tick_Object_Real(self):
        """Test TickCRUD add Tick object with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model_primary)

        # Create Tick object
        tick = Tick(
            code=self.test_code_primary,
            price=15.75,
            volume=2000,
            direction=TICKDIRECTION_TYPES.SELL,
            timestamp=datetime(2023, 6, 16, 10, 0, 0),
            source=SOURCE_TYPES.REALTIME,
        )

        # Convert Tick to MTick and add
        mtick = self.crud_primary._convert_input_item(tick)
        added_tick = self.crud_primary.add(mtick)

        # Get table size after operation
        size1 = get_table_size(self.model_primary)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify addition
        self.assertIsNotNone(added_tick)
        self.assertEqual(added_tick.code, self.test_code_primary)
        self.assertEqual(added_tick.price, to_decimal(15.75))
        self.assertEqual(added_tick.volume, 2000)
        self.assertEqual(added_tick.direction, TICKDIRECTION_TYPES.SELL)

        # Verify in database
        found_ticks = self.crud_primary.find(filters={"price": to_decimal(15.75)})
        self.assertEqual(len(found_ticks), 1)

    @database_test_required
    def test_TickCRUD_Add_Batch_Real(self):
        """Test TickCRUD batch addition with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model_primary)

        # Create multiple Tick objects
        ticks = []
        batch_count = 3
        prices = [10.10, 10.20, 10.30]
        volumes = [1000, 1500, 2000]
        directions = [TICKDIRECTION_TYPES.BUY, TICKDIRECTION_TYPES.SELL, TICKDIRECTION_TYPES.OTHER]

        for i in range(batch_count):
            tick = Tick(
                code=self.test_code_primary,
                price=prices[i],
                volume=volumes[i],
                direction=directions[i],
                timestamp=datetime(2023, 6, 15 + i, 10, 0, 0),
                source=SOURCE_TYPES.TDX,
            )
            ticks.append(tick)

        # Add batch
        result = self.crud_primary.add_batch(ticks)

        # Get table size after operation
        size1 = get_table_size(self.model_primary)

        # Verify table size increased by batch count
        self.assertEqual(batch_count, size1 - size0)

        # Verify batch addition
        self.assertIsInstance(result, tuple)

        # Verify each tick in database
        for i in range(batch_count):
            found_ticks = self.crud_primary.find(filters={"price": to_decimal(prices[i])})
            self.assertEqual(len(found_ticks), 1)
            self.assertEqual(found_ticks[0].volume, volumes[i])
            self.assertEqual(found_ticks[0].direction, directions[i])

    @database_test_required
    def test_TickCRUD_Find_By_Time_Range_Real(self):
        """Test TickCRUD find by time range business helper method with real database"""
        # Create test ticks with different timestamps
        test_times = [
            datetime(2023, 6, 15, 10, 0, 0),
            datetime(2023, 6, 16, 11, 0, 0),
            datetime(2023, 6, 17, 12, 0, 0),
            datetime(2023, 6, 18, 13, 0, 0),
        ]

        for i, timestamp in enumerate(test_times):
            params = self.test_tick_params.copy()
            params["price"] = to_decimal(10.00 + i * 0.10)
            params["volume"] = 1000 + i * 100
            params["timestamp"] = timestamp
            self.crud_primary.create(**params)

        # Test find by time range (June 16-17)
        time_ticks = self.crud_primary.find_by_time_range(
            start_time=datetime(2023, 6, 16),
            end_time=datetime(2023, 6, 18)  # Next day to include full June 17
        )
        self.assertEqual(len(time_ticks), 2)  # Records from June 16-17

        # Test find with direction filter
        buy_ticks = self.crud_primary.find_by_time_range(
            start_time=datetime(2023, 6, 15),
            end_time=datetime(2023, 6, 19),
            direction=TICKDIRECTION_TYPES.BUY
        )
        self.assertEqual(len(buy_ticks), 4)  # All our test ticks are BUY

        # Test find with volume filter
        large_volume_ticks = self.crud_primary.find_by_time_range(
            start_time=datetime(2023, 6, 15),
            end_time=datetime(2023, 6, 19),
            min_volume=1200
        )
        self.assertEqual(len(large_volume_ticks), 2)  # Volume >= 1200

    @database_test_required
    def test_TickCRUD_Find_By_Price_Range_Real(self):
        """Test TickCRUD find by price range business helper method with real database"""
        # Create test ticks with different prices
        test_prices = [9.50, 10.00, 10.50, 11.00, 11.50]

        for i, price in enumerate(test_prices):
            params = self.test_tick_params.copy()
            params["price"] = to_decimal(price)
            params["volume"] = 1000 + i * 100
            params["timestamp"] = datetime(2023, 6, 15, 10, i, 0)
            self.crud_primary.create(**params)

        # Test find by price range
        price_ticks = self.crud_primary.find_by_price_range(
            min_price=10.00,
            max_price=11.00
        )
        self.assertEqual(len(price_ticks), 3)  # Prices 10.00, 10.50, 11.00

        # Test find by price range with time filter
        price_time_ticks = self.crud_primary.find_by_price_range(
            min_price=10.25,
            max_price=11.25,
            start_time=datetime(2023, 6, 15, 10, 2),
            end_time=datetime(2023, 6, 15, 10, 4)
        )
        self.assertEqual(len(price_time_ticks), 2)  # Prices 10.50, 11.00 in time range

        # Test find with only min_price
        min_price_ticks = self.crud_primary.find_by_price_range(min_price=10.75)
        self.assertEqual(len(min_price_ticks), 2)  # Prices 11.00, 11.50

    @database_test_required
    def test_TickCRUD_Find_Large_Volume_Ticks_Real(self):
        """Test TickCRUD find large volume ticks business helper method with real database"""
        # Create test ticks with different volumes
        test_volumes = [500, 1000, 1500, 2000, 2500]

        for i, volume in enumerate(test_volumes):
            params = self.test_tick_params.copy()
            params["volume"] = volume
            params["price"] = to_decimal(10.00 + i * 0.05)
            params["timestamp"] = datetime(2023, 6, 15, 10, i, 0)
            self.crud_primary.create(**params)

        # Test find large volume ticks
        large_ticks = self.crud_primary.find_large_volume_ticks(min_volume=1500)
        self.assertEqual(len(large_ticks), 3)  # Volumes 1500, 2000, 2500

        # Test find with time range
        large_time_ticks = self.crud_primary.find_large_volume_ticks(
            min_volume=1200,
            start_time=datetime(2023, 6, 15, 10, 2),
            end_time=datetime(2023, 6, 15, 10, 4)
        )
        self.assertEqual(len(large_time_ticks), 3)  # Volumes 1500, 2000, 2500 in time range

        # Test with limit
        limited_ticks = self.crud_primary.find_large_volume_ticks(
            min_volume=1000,
            limit=2
        )
        self.assertEqual(len(limited_ticks), 2)  # Limited to 2 results

    @database_test_required
    def test_TickCRUD_Get_Latest_Ticks_Real(self):
        """Test TickCRUD get latest ticks business helper method with real database"""
        # Create test ticks with different timestamps
        timestamps = [
            datetime(2023, 6, 15, 10, 0, 0),
            datetime(2023, 6, 15, 10, 1, 0),
            datetime(2023, 6, 15, 10, 2, 0),
            datetime(2023, 6, 15, 10, 3, 0),
            datetime(2023, 6, 15, 10, 4, 0),
        ]

        for i, timestamp in enumerate(timestamps):
            params = self.test_tick_params.copy()
            params["timestamp"] = timestamp
            params["price"] = to_decimal(10.00 + i * 0.01)
            self.crud_primary.create(**params)

        # Test get latest ticks (default limit)
        latest_ticks = self.crud_primary.get_latest_ticks()
        self.assertEqual(len(latest_ticks), 5)  # All ticks

        # Verify ordering (latest first)
        self.assertTrue(latest_ticks[0].timestamp >= latest_ticks[-1].timestamp)

        # Test with custom limit
        limited_latest = self.crud_primary.get_latest_ticks(limit=3)
        self.assertEqual(len(limited_latest), 3)

        # Verify these are the 3 most recent
        self.assertEqual(limited_latest[0].timestamp, datetime(2023, 6, 15, 10, 4, 0))
        self.assertEqual(limited_latest[1].timestamp, datetime(2023, 6, 15, 10, 3, 0))
        self.assertEqual(limited_latest[2].timestamp, datetime(2023, 6, 15, 10, 2, 0))

    @database_test_required
    def test_TickCRUD_Delete_By_Time_Range_Real(self):
        """Test TickCRUD delete by time range business helper method with real database"""
        # Create test ticks with different timestamps
        timestamps = [
            datetime(2023, 6, 15, 10, 0, 0),
            datetime(2023, 6, 16, 10, 0, 0),
            datetime(2023, 6, 17, 10, 0, 0),
            datetime(2023, 6, 18, 10, 0, 0),
        ]

        for i, timestamp in enumerate(timestamps):
            params = self.test_tick_params.copy()
            params["timestamp"] = timestamp
            params["price"] = to_decimal(10.00 + i * 0.10)
            self.crud_primary.create(**params)

        # Get initial count
        initial_count = len(self.crud_primary.find({}))
        self.assertEqual(initial_count, 4)

        # Delete by time range (June 16-17)
        self.crud_primary.delete_by_time_range(
            start_time=datetime(2023, 6, 16),
            end_time=datetime(2023, 6, 18)  # Next day to include full June 17
        )

        # Verify deletion
        remaining_ticks = self.crud_primary.find({})
        self.assertEqual(len(remaining_ticks), 2)  # June 15 and June 18 should remain

        # Verify remaining ticks are correct
        remaining_dates = [tick.timestamp.date() for tick in remaining_ticks]
        self.assertIn(datetime(2023, 6, 15).date(), remaining_dates)
        self.assertIn(datetime(2023, 6, 18).date(), remaining_dates)

        # Test deletion with only start_time
        self.crud_primary.delete_by_time_range(start_time=datetime(2023, 6, 18))

        final_ticks = self.crud_primary.find({})
        self.assertEqual(len(final_ticks), 1)  # Only June 15 should remain

        # Test safety check - must specify at least one time
        with self.assertRaises(ValueError):
            self.crud_primary.delete_by_time_range()

    @database_test_required
    def test_TickCRUD_Tick_Object_Conversion_Real(self):
        """Test TickCRUD Tick object conversion with real database"""
        # Create test tick
        created_tick = self.crud_primary.create(**self.test_tick_params)

        # Find with Tick output type
        tick_objects = self.crud_primary.find(
            filters={"code": self.test_code_primary},
            output_type="tick"
        )

        # Verify conversion
        self.assertEqual(len(tick_objects), 1)
        tick = tick_objects[0]
        self.assertIsInstance(tick, Tick)
        self.assertEqual(tick.code, self.test_code_primary)
        self.assertEqual(tick.price, Decimal("10.50"))
        self.assertEqual(tick.volume, 1000)
        self.assertEqual(tick.direction, TICKDIRECTION_TYPES.BUY)

    @database_test_required
    def test_TickCRUD_DataFrame_Output_Real(self):
        """Test TickCRUD DataFrame output with real database"""
        # Create test ticks
        test_data = [
            {"price": 10.10, "volume": 1000, "direction": TICKDIRECTION_TYPES.BUY},
            {"price": 10.20, "volume": 1500, "direction": TICKDIRECTION_TYPES.SELL},
            {"price": 10.15, "volume": 2000, "direction": TICKDIRECTION_TYPES.OTHER},
        ]

        for i, data in enumerate(test_data):
            params = self.test_tick_params.copy()
            params.update(data)
            params["timestamp"] = datetime(2023, 6, 15, 10, i, 0)
            self.crud_primary.create(**params)

        # Get as DataFrame using find_by_time_range
        df_result = self.crud_primary.find_by_time_range(
            start_time=datetime(2023, 6, 15),
            end_time=datetime(2023, 6, 16),
            as_dataframe=True
        )

        # Verify DataFrame
        import pandas as pd

        self.assertIsInstance(df_result, pd.DataFrame)
        self.assertEqual(len(df_result), 3)

        # Check columns and data
        self.assertIn("code", df_result.columns)
        self.assertIn("price", df_result.columns)
        self.assertIn("volume", df_result.columns)
        self.assertIn("direction", df_result.columns)

        # Verify data content (DataFrame may convert Decimal to float)
        prices = df_result["price"].tolist()
        # Convert to float for comparison since DataFrame may return float values
        expected_prices = [10.10, 10.20, 10.15]
        for expected_price in expected_prices:
            self.assertIn(expected_price, prices)

    @database_test_required
    def test_TickCRUD_Multiple_Stock_Tables_Real(self):
        """Test TickCRUD with multiple stock code tables with real database"""
        # Create ticks for primary stock
        params_primary = self.test_tick_params.copy()
        created_primary = self.crud_primary.create(**params_primary)

        # Create ticks for secondary stock
        params_secondary = {
            "code": self.test_code_secondary,
            "price": to_decimal(20.50),
            "volume": 2000,
            "direction": TICKDIRECTION_TYPES.SELL,
            "timestamp": self.test_timestamp,
            "source": SOURCE_TYPES.REALTIME,
        }
        created_secondary = self.crud_secondary.create(**params_secondary)

        # Verify both ticks exist in their respective tables
        primary_ticks = self.crud_primary.find({})
        secondary_ticks = self.crud_secondary.find({})

        self.assertEqual(len(primary_ticks), 1)
        self.assertEqual(len(secondary_ticks), 1)

        self.assertEqual(primary_ticks[0].code, self.test_code_primary)
        self.assertEqual(secondary_ticks[0].code, self.test_code_secondary)

        self.assertEqual(primary_ticks[0].price, to_decimal(10.50))
        self.assertEqual(secondary_ticks[0].price, to_decimal(20.50))

        # Verify tables are separate (no cross-contamination)
        # Primary CRUD should not see secondary data
        primary_by_secondary_code = self.crud_primary.find({"code": self.test_code_secondary})
        self.assertEqual(len(primary_by_secondary_code), 0)

    @database_test_required
    def test_TickCRUD_Complex_Filters_Real(self):
        """Test TickCRUD complex filters with real database"""
        # Create ticks with different attributes
        test_data = [
            {"price": 10.00, "volume": 1000, "direction": TICKDIRECTION_TYPES.BUY, "timestamp": datetime(2023, 6, 15, 10, 0)},
            {"price": 10.50, "volume": 2000, "direction": TICKDIRECTION_TYPES.SELL, "timestamp": datetime(2023, 6, 15, 11, 0)},
            {"price": 11.00, "volume": 1500, "direction": TICKDIRECTION_TYPES.BUY, "timestamp": datetime(2023, 6, 15, 12, 0)},
            {"price": 9.50, "volume": 3000, "direction": TICKDIRECTION_TYPES.OTHER, "timestamp": datetime(2023, 6, 15, 13, 0)},
        ]

        for data in test_data:
            params = self.test_tick_params.copy()
            params.update(data)
            self.crud_primary.create(**params)

        # Test combined filters
        buy_expensive_ticks = self.crud_primary.find(
            filters={
                "direction": TICKDIRECTION_TYPES.BUY,
                "price__gte": to_decimal(10.25),
                "volume__gte": 1200,
            }
        )

        # Should find 1 tick (price=11.00, volume=1500, direction=BUY)
        self.assertEqual(len(buy_expensive_ticks), 1)
        self.assertEqual(buy_expensive_ticks[0].price, to_decimal(11.00))

        # Test IN operator for directions
        buy_sell_ticks = self.crud_primary.find(
            filters={
                "direction__in": [TICKDIRECTION_TYPES.BUY, TICKDIRECTION_TYPES.SELL],
                "price__lte": to_decimal(10.75)
            }
        )

        # Should find 2 ticks (price=10.00 BUY and price=10.50 SELL)
        self.assertEqual(len(buy_sell_ticks), 2)
        directions = [tick.direction for tick in buy_sell_ticks]
        self.assertIn(TICKDIRECTION_TYPES.BUY, directions)
        self.assertIn(TICKDIRECTION_TYPES.SELL, directions)

    @database_test_required
    def test_TickCRUD_Exists_Real(self):
        """Test TickCRUD exists functionality with real database"""
        # Test non-existent tick
        exists_before = self.crud_primary.exists(filters={"price": to_decimal(99.99)})
        self.assertFalse(exists_before)

        # Create test tick
        created_tick = self.crud_primary.create(**self.test_tick_params)

        # Test existing tick
        exists_after = self.crud_primary.exists(filters={"price": to_decimal(10.50)})
        self.assertTrue(exists_after)

        # Test with more specific filters
        exists_specific = self.crud_primary.exists(
            filters={
                "price": to_decimal(10.50),
                "volume": 1000,
                "direction": TICKDIRECTION_TYPES.BUY,
            }
        )
        self.assertTrue(exists_specific)

        # Test with non-matching filters
        exists_false = self.crud_primary.exists(
            filters={
                "price": to_decimal(10.50),
                "direction": TICKDIRECTION_TYPES.SELL
            }
        )
        self.assertFalse(exists_false)

    @database_test_required
    def test_TickCRUD_Bulk_Operations_With_Size_Verification_Real(self):
        """Test TickCRUD bulk operations with table size verification"""
        # Get initial table size
        size0 = get_table_size(self.model_primary)

        # Create bulk test data
        bulk_ticks = []
        bulk_count = 5
        prices = [10.10, 10.20, 10.30, 10.40, 10.50]
        volumes = [1000, 1100, 1200, 1300, 1400]
        directions = [
            TICKDIRECTION_TYPES.BUY, TICKDIRECTION_TYPES.SELL, TICKDIRECTION_TYPES.OTHER,
            TICKDIRECTION_TYPES.BUY, TICKDIRECTION_TYPES.SELL
        ]

        for i in range(bulk_count):
            tick = Tick(
                code=self.test_code_primary,
                price=prices[i],
                volume=volumes[i],
                direction=directions[i],
                timestamp=datetime(2023, 6, 15, 10, i, 0),
                source=SOURCE_TYPES.TDX,
            )
            bulk_ticks.append(tick)

        # Perform bulk addition
        result = self.crud_primary.add_batch(bulk_ticks)

        # Get table size after bulk addition
        size1 = get_table_size(self.model_primary)

        # Verify table size increased by bulk_count
        self.assertEqual(bulk_count, size1 - size0)

        # Verify each tick was added correctly
        for i in range(bulk_count):
            found_ticks = self.crud_primary.find(filters={"price": to_decimal(prices[i])})
            self.assertEqual(len(found_ticks), 1)
            self.assertEqual(found_ticks[0].volume, volumes[i])
            self.assertEqual(found_ticks[0].direction, directions[i])

        # Bulk delete test ticks using time range
        self.crud_primary.delete_by_time_range(
            start_time=datetime(2023, 6, 15),
            end_time=datetime(2023, 6, 16)
        )

        # Get final table size
        size2 = get_table_size(self.model_primary)

        # Verify table size returned to original
        self.assertEqual(size2, size0)

    @database_test_required
    def test_TickCRUD_Decimal_Precision_Real(self):
        """Test TickCRUD decimal precision handling with real database"""
        # Test with high-precision decimal values
        precision_prices = [
            Decimal("10.12"),
            Decimal("0.01"),
            Decimal("999.99"),
            Decimal("0.00"),
            Decimal("123.456"),  # More than 2 decimal places (should be rounded)
        ]

        for i, price in enumerate(precision_prices):
            params = self.test_tick_params.copy()
            params["price"] = price
            params["volume"] = 1000 + i
            params["timestamp"] = datetime(2023, 6, 15, 10, i, 0)

            created_tick = self.crud_primary.create(**params)

            # Verify precision is maintained (or truncated for > 2 decimal places)
            if price == Decimal("123.456"):
                # Should be truncated to 2 decimal places by database DECIMAL(16,2) field
                self.assertEqual(created_tick.price, Decimal("123.45"))
            else:
                self.assertEqual(created_tick.price, price)

            # Verify in database
            found_ticks = self.crud_primary.find(filters={"volume": 1000 + i})
            self.assertEqual(len(found_ticks), 1)

    @database_test_required
    def test_TickCRUD_Timestamp_Handling_Real(self):
        """Test TickCRUD timestamp normalization with real database"""
        # Test with different timestamp formats (now supported by enhanced datetime_normalize)
        timestamps = [
            datetime(2023, 1, 1, 10, 0, 0),
            "2023-06-15 14:30:00",
            "2023-12-31T23:59:59",  # ISO format with T separator
        ]

        for i, timestamp in enumerate(timestamps):
            params = self.test_tick_params.copy()
            params["timestamp"] = timestamp
            params["price"] = to_decimal(10.00 + i * 0.10)

            created_tick = self.crud_primary.create(**params)

            # Verify timestamp is normalized to datetime
            self.assertIsInstance(created_tick.timestamp, datetime)

            # Verify in database
            found_ticks = self.crud_primary.find(filters={"price": to_decimal(10.00 + i * 0.10)})
            self.assertEqual(len(found_ticks), 1)
            self.assertIsInstance(found_ticks[0].timestamp, datetime)

    @database_test_required
    def test_TickCRUD_Exception_Handling_Real(self):
        """Test TickCRUD exception handling with real database"""
        # Test find with empty filters (should not cause issues)
        all_ticks = self.crud_primary.find(filters={})
        self.assertIsInstance(all_ticks, list)

        # Test remove with overly broad filters (should be safe)
        self.crud_primary.remove({})  # Should be safely handled

        # Test create with minimal data
        minimal_params = {
            "code": self.test_code_primary,
            "price": to_decimal(5.00),
            "volume": 100,
            "direction": TICKDIRECTION_TYPES.BUY,
            "timestamp": datetime(2023, 6, 15, 14, 30, 0),  # ClickHouse required field
        }

        try:
            minimal_tick = self.crud_primary.create(**minimal_params)
            self.assertIsNotNone(minimal_tick)
            # Should have default values
            self.assertEqual(minimal_tick.code, self.test_code_primary)  # From instance
            self.assertEqual(minimal_tick.direction, TICKDIRECTION_TYPES.BUY)  # As specified
            self.assertEqual(minimal_tick.volume, 100)  # As specified
        except Exception as e:
            self.fail(f"Creating tick with minimal parameters should not fail: {e}")

        # Test conversion with invalid object
        invalid_conversion = self.crud_primary._convert_input_item("invalid_object")
        self.assertIsNone(invalid_conversion)

    @database_test_required
    def test_TickCRUD_Business_Logic_Integration_Real(self):
        """Test TickCRUD business logic integration with real database"""
        # Create a realistic trading scenario throughout the day
        trading_scenario = [
            {"time": "09:30:00", "price": 10.00, "volume": 2000, "direction": TICKDIRECTION_TYPES.BUY},
            {"time": "10:15:30", "price": 10.05, "volume": 1500, "direction": TICKDIRECTION_TYPES.BUY},
            {"time": "11:30:45", "price": 10.10, "volume": 3000, "direction": TICKDIRECTION_TYPES.SELL},
            {"time": "13:00:15", "price": 10.02, "volume": 1000, "direction": TICKDIRECTION_TYPES.SELL},
            {"time": "14:30:00", "price": 10.08, "volume": 2500, "direction": TICKDIRECTION_TYPES.BUY},
            {"time": "15:00:00", "price": 10.12, "volume": 4000, "direction": TICKDIRECTION_TYPES.SELL},
        ]

        for scenario in trading_scenario:
            time_parts = scenario["time"].split(":")
            timestamp = datetime(2023, 6, 15, int(time_parts[0]), int(time_parts[1]), int(time_parts[2]))

            params = self.test_tick_params.copy()
            params["timestamp"] = timestamp
            params["price"] = to_decimal(scenario["price"])
            params["volume"] = scenario["volume"]
            params["direction"] = scenario["direction"]
            self.crud_primary.create(**params)

        # Test various business queries

        # 1. Get morning trading (9:30-12:00)
        morning_ticks = self.crud_primary.find_by_time_range(
            start_time=datetime(2023, 6, 15, 9, 30),
            end_time=datetime(2023, 6, 15, 12, 0)
        )
        self.assertEqual(len(morning_ticks), 3)  # First 3 transactions

        # 2. Find large volume transactions (>= 2500)
        large_volume = self.crud_primary.find_large_volume_ticks(min_volume=2500)
        self.assertEqual(len(large_volume), 3)  # 3000, 2500, 4000 volume ticks

        # 3. Find price breakout (price >= 10.10)
        breakout_ticks = self.crud_primary.find_by_price_range(min_price=10.10)
        self.assertEqual(len(breakout_ticks), 2)  # 10.10 and 10.12 price ticks

        # 4. Get latest 3 ticks
        latest_ticks = self.crud_primary.get_latest_ticks(limit=3)
        self.assertEqual(len(latest_ticks), 3)
        # Should be sorted by timestamp descending
        self.assertEqual(latest_ticks[0].timestamp, datetime(2023, 6, 15, 15, 0, 0))
        self.assertEqual(latest_ticks[1].timestamp, datetime(2023, 6, 15, 14, 30, 0))
        self.assertEqual(latest_ticks[2].timestamp, datetime(2023, 6, 15, 13, 0, 15))

        # 5. Analysis: count buy vs sell
        buy_ticks = self.crud_primary.find({"direction": TICKDIRECTION_TYPES.BUY})
        sell_ticks = self.crud_primary.find({"direction": TICKDIRECTION_TYPES.SELL})
        self.assertEqual(len(buy_ticks), 3)
        self.assertEqual(len(sell_ticks), 3)

        # 6. Calculate total volume
        all_ticks = self.crud_primary.find({})
        total_volume = sum(tick.volume for tick in all_ticks)
        expected_volume = sum(scenario["volume"] for scenario in trading_scenario)
        self.assertEqual(total_volume, expected_volume)  # 14000
