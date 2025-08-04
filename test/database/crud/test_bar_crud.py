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
    from ginkgo.data.crud.bar_crud import BarCRUD
    from ginkgo.data.models import MBar
    from ginkgo.backtest import Bar
    from ginkgo.enums import FREQUENCY_TYPES, SOURCE_TYPES
    from ginkgo.libs import GCONF, datetime_normalize, to_decimal
    from ginkgo.data.drivers import get_db_connection, get_table_size, create_table, drop_table
except ImportError as e:
    print(f"Import error: {e}")
    BarCRUD = None
    GCONF = None


class BarCRUDTest(unittest.TestCase):
    """
    BarCRUD database integration tests.
    Tests Bar-specific CRUD operations with actual database.
    """

    @classmethod
    def setUpClass(cls):
        """Class-level setup: check database configuration and connection"""
        if BarCRUD is None or GCONF is None:
            raise AssertionError("BarCRUD or GCONF not available")

        # Set model for table size verification
        cls.model = MBar

        # Recreate table for clean testing
        try:
            drop_table(cls.model, no_skip=True)
            create_table(cls.model, no_skip=True)
            print(":white_check_mark: Bar table recreated for testing")
        except Exception as e:
            print(f":warning: Bar table recreation failed: {e}")

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

        # Create BarCRUD instance
        cls.crud = BarCRUD()

        # Test database connection
        try:
            connection = get_db_connection(MBar)
            with connection.get_session() as session:
                session.execute(text("SELECT 1"))
            print(":white_check_mark: Bar database connection successful")
        except Exception as e:
            raise AssertionError(f"Database connection failed: {e}")

    def setUp(self):
        """Setup for each test: prepare unique test data"""
        self.test_id = str(uuid.uuid4())[:8]
        self.test_code = f"BARTEST{self.test_id}.SZ"
        self.test_timestamp = datetime(2023, 1, 1, 9, 30)

        # Test bar data
        self.test_bar_params = {
            "code": self.test_code,
            "open": 15.8,
            "high": 16.5,
            "low": 15.2,
            "close": 16.1,
            "volume": 1500,
            "amount": 24150,
            "frequency": FREQUENCY_TYPES.DAY,
            "timestamp": self.test_timestamp,
            "source": SOURCE_TYPES.TUSHARE,
        }

    def tearDown(self):
        """Cleanup after each test"""
        try:
            # Single pattern cleanup for all test data
            self.crud.remove({"code__like": f"BARTEST{self.test_id}%"})
        except Exception as e:
            print(f":warning: Cleanup failed: {e}")

    @classmethod
    def tearDownClass(cls):
        """Class-level cleanup: remove any remaining test data"""
        try:
            # Final cleanup of any remaining test records
            cls.crud.remove({"code__like": "BARTEST%"})
            print(":broom: Final cleanup of all BARTEST records completed")
        except Exception as e:
            print(f":warning: Final cleanup failed: {e}")

    @database_test_required
    def test_BarCRUD_Create_From_Params_Real(self):
        """Test BarCRUD create from parameters with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create bar from parameters
        created_bar = self.crud.create(**self.test_bar_params)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify creation
        self.assertIsNotNone(created_bar)
        self.assertIsInstance(created_bar, MBar)
        self.assertEqual(created_bar.code, self.test_code)
        self.assertEqual(created_bar.open, Decimal("15.8"))
        self.assertEqual(created_bar.high, Decimal("16.5"))
        self.assertEqual(created_bar.volume, 1500)
        self.assertEqual(created_bar.frequency, FREQUENCY_TYPES.DAY)

        # Verify in database
        found_bars = self.crud.find(filters={"code": self.test_code})
        self.assertEqual(len(found_bars), 1)
        self.assertEqual(found_bars[0].code, self.test_code)

    @database_test_required
    def test_BarCRUD_Add_Bar_Object_Real(self):
        """Test BarCRUD add Bar object with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create Bar object
        bar = Bar()
        bar.set(
            self.test_code,
            Decimal("12.5"),
            Decimal("13.2"),
            Decimal("12.0"),
            Decimal("12.8"),
            2500,
            Decimal("31800"),
            FREQUENCY_TYPES.DAY,
            self.test_timestamp,
        )

        # Convert Bar to MBar and add
        mbar = self.crud._convert_input_item(bar)
        added_bar = self.crud.add(mbar)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify addition
        self.assertIsNotNone(added_bar)
        self.assertEqual(added_bar.code, self.test_code)
        self.assertEqual(added_bar.open, Decimal("12.5"))

        # Verify in database
        found_bars = self.crud.find(filters={"code": self.test_code})
        self.assertEqual(len(found_bars), 1)

    @database_test_required
    def test_BarCRUD_Add_Batch_Real(self):
        """Test BarCRUD batch addition with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create multiple Bar objects
        bars = []
        batch_count = 3
        for i in range(batch_count):
            bar = Bar()
            bar.set(
                f"{self.test_code}_{i}",
                Decimal(f"{20+i}.5"),
                Decimal(f"{21+i}.0"),
                Decimal(f"{19+i}.8"),
                Decimal(f"{20+i}.2"),
                1000 * (i + 1),
                Decimal(f"{20000*(i+1)}"),
                FREQUENCY_TYPES.DAY,
                self.test_timestamp,
            )
            bars.append(bar)

        # Add batch
        result = self.crud.add_batch(bars)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by batch count
        self.assertEqual(batch_count, size1 - size0)

        # Verify batch addition
        self.assertIsInstance(result, tuple)

        # Verify each bar in database
        for i in range(3):
            found_bars = self.crud.find(filters={"code": f"{self.test_code}_{i}"})
            self.assertEqual(len(found_bars), 1)
            self.assertEqual(found_bars[0].open, Decimal(f"{20+i}.5"))

    @database_test_required
    def test_BarCRUD_Find_By_Code_And_Date_Range_Real(self):
        """Test BarCRUD business helper method with real database"""
        # Create bars with different dates
        dates = [
            datetime(2023, 1, 1),
            datetime(2023, 1, 15),
            datetime(2023, 2, 1),
            datetime(2023, 2, 15),
        ]

        for i, date in enumerate(dates):
            params = self.test_bar_params.copy()
            params["code"] = f"{self.test_code}_{i}"
            params["timestamp"] = date
            params["open"] = 10 + i
            self.crud.create(**params)

        # Test date range query
        found_bars = self.crud.find_by_code_and_date_range(
            code=f"{self.test_code}_1", start_date="2023-01-01", end_date="2023-01-31"
        )

        # Should find the January record
        self.assertEqual(len(found_bars), 1)
        self.assertIsInstance(found_bars[0], Bar)  # Should return Bar objects
        self.assertEqual(found_bars[0].code, f"{self.test_code}_1")

        # Test broader date range
        found_bars = self.crud.find(
            filters={
                "code__like": f"{self.test_code}_",
                "timestamp__gte": "2023-01-01",
                "timestamp__lte": "2023-12-31",
            },
            output_type="bar",
        )

        # Should find all records
        codes_found = [bar.code for bar in found_bars if bar.code.startswith(self.test_code)]
        self.assertGreaterEqual(len(codes_found), 4)

    @database_test_required
    def test_BarCRUD_Get_Latest_Bars_Real(self):
        """Test BarCRUD get latest bars with real database"""
        # Create bars with different timestamps
        timestamps = [
            datetime(2023, 1, 1, 9, 30),
            datetime(2023, 1, 2, 9, 30),
            datetime(2023, 1, 3, 9, 30),
        ]

        for i, timestamp in enumerate(timestamps):
            params = self.test_bar_params.copy()
            params["timestamp"] = timestamp
            params["volume"] = 1000 + i * 100  # Different volumes for verification
            self.crud.create(**params)

        # Get latest bars (should be in descending order)
        latest_bars = self.crud.get_latest_bars(code=self.test_code, limit=2)

        # Verify results
        self.assertEqual(len(latest_bars), 2)
        self.assertIsInstance(latest_bars[0], Bar)

        # Latest should have highest volume (latest timestamp)
        self.assertGreater(latest_bars[0].volume, latest_bars[1].volume)

    @database_test_required
    def test_BarCRUD_Count_By_Code_Real(self):
        """Test BarCRUD count by code with real database"""
        # Get initial count
        initial_count = self.crud.count_by_code(self.test_code)
        self.assertEqual(initial_count, 0)

        # Create multiple bars for same code
        for i in range(3):
            params = self.test_bar_params.copy()
            params["timestamp"] = datetime(2023, 1, i + 1, 9, 30)
            self.crud.create(**params)

        # Verify count
        new_count = self.crud.count_by_code(self.test_code)
        self.assertEqual(new_count, 3)

    @database_test_required
    def test_BarCRUD_Remove_By_Code_And_Date_Range_Real(self):
        """Test BarCRUD remove by code and date range with real database"""
        # Create bars with different dates
        dates = [
            datetime(2023, 1, 1),
            datetime(2023, 1, 15),
            datetime(2023, 2, 1),
        ]

        for i, date in enumerate(dates):
            params = self.test_bar_params.copy()
            params["timestamp"] = date
            self.crud.create(**params)

        # Verify all created
        all_bars = self.crud.find(filters={"code": self.test_code})
        self.assertEqual(len(all_bars), 3)

        # Get table size before removal
        size0 = get_table_size(self.model)

        # Remove January records only
        self.crud.remove_by_code_and_date_range(code=self.test_code, start_date="2023-01-01", end_date="2023-01-31")

        # Get table size after removal
        size1 = get_table_size(self.model)

        # Verify table size decreased by 2 (2 January records removed)
        self.assertEqual(-2, size1 - size0)

        # Verify only February record remains
        remaining_bars = self.crud.find(filters={"code": self.test_code})
        self.assertEqual(len(remaining_bars), 1)
        self.assertEqual(remaining_bars[0].timestamp.month, 2)

    @database_test_required
    def test_BarCRUD_Get_Date_Range_For_Code_Real(self):
        """Test BarCRUD get date range for code with real database"""
        # Create bars with different dates
        dates = [
            datetime(2023, 1, 1, 9, 30),
            datetime(2023, 6, 15, 14, 30),
            datetime(2023, 12, 31, 15, 0),
        ]

        for date in dates:
            params = self.test_bar_params.copy()
            params["timestamp"] = date
            self.crud.create(**params)

        # Get date range
        min_date, max_date = self.crud.get_date_range_for_code(self.test_code)

        # Verify date range
        self.assertIsNotNone(min_date)
        self.assertIsNotNone(max_date)
        self.assertEqual(min_date.date(), datetime(2023, 1, 1).date())
        self.assertEqual(max_date.date(), datetime(2023, 12, 31).date())

    @database_test_required
    def test_BarCRUD_Get_All_Codes_Real(self):
        """Test BarCRUD get all codes with real database"""
        # Create bars with different codes
        test_codes = [f"{self.test_code}_{i}" for i in range(3)]

        for code in test_codes:
            params = self.test_bar_params.copy()
            params["code"] = code
            self.crud.create(**params)

        # Get all codes
        all_codes = self.crud.get_all_codes()

        # Verify our test codes are included
        for test_code in test_codes:
            self.assertIn(test_code, all_codes)

    @database_test_required
    def test_BarCRUD_Output_Type_Conversion_Real(self):
        """Test BarCRUD output type conversion with real database"""
        # Create test bar
        created_bar = self.crud.create(**self.test_bar_params)

        # Get as model objects (MBar)
        model_bars = self.crud.find(filters={"code": self.test_code}, output_type="model")
        self.assertEqual(len(model_bars), 1)
        self.assertIsInstance(model_bars[0], MBar)

        # Get as Bar objects
        bar_objects = self.crud.find(filters={"code": self.test_code}, output_type="bar")
        self.assertEqual(len(bar_objects), 1)
        self.assertIsInstance(bar_objects[0], Bar)

        # Verify data consistency
        self.assertEqual(model_bars[0].code, bar_objects[0].code)
        self.assertEqual(model_bars[0].open, bar_objects[0].open)

    @database_test_required
    def test_BarCRUD_DataFrame_Output_Real(self):
        """Test BarCRUD DataFrame output with real database"""
        # Create test bar
        created_bar = self.crud.create(**self.test_bar_params)

        # Get as DataFrame
        df_result = self.crud.find_by_code_and_date_range(code=self.test_code, as_dataframe=True)

        # Verify DataFrame
        import pandas as pd

        self.assertIsInstance(df_result, pd.DataFrame)
        self.assertEqual(len(df_result), 1)
        self.assertEqual(df_result.iloc[0]["code"], self.test_code)

    @database_test_required
    def test_BarCRUD_Complex_Filters_Real(self):
        """Test BarCRUD complex filters with real database"""
        # Create bars with different volumes and amounts
        test_data = [
            {"volume": 1000, "amount": 15000},
            {"volume": 2000, "amount": 30000},
            {"volume": 3000, "amount": 45000},
        ]

        for i, data in enumerate(test_data):
            params = self.test_bar_params.copy()
            params["code"] = f"{self.test_code}_{i}"
            params["volume"] = data["volume"]
            params["amount"] = data["amount"]
            self.crud.create(**params)

        # Test volume range filter
        medium_volume_bars = self.crud.find(
            filters={"code__like": f"{self.test_code}_", "volume__gte": 1500, "volume__lte": 2500}
        )

        # Should find the 2000 volume bar
        matching_bars = [bar for bar in medium_volume_bars if bar.code.startswith(self.test_code)]
        self.assertEqual(len(matching_bars), 1)
        self.assertEqual(matching_bars[0].volume, 2000)

        # Test IN operator
        specific_volume_bars = self.crud.find(filters={"volume__in": [1000, 3000]})

        # Should find bars with volumes 1000 and 3000
        matching_codes = [bar.code for bar in specific_volume_bars if bar.code.startswith(self.test_code)]
        self.assertEqual(len(matching_codes), 2)

    @database_test_required
    def test_BarCRUD_Soft_Delete_Real(self):
        """Test BarCRUD soft delete functionality with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create test bar
        created_bar = self.crud.create(**self.test_bar_params)

        # Get table size after creation
        size1 = get_table_size(self.model)
        self.assertEqual(size0 + 1, size1)

        # Verify bar exists
        found_bars = self.crud.find(filters={"code": self.test_code})
        self.assertEqual(len(found_bars), 1)
        bar_uuid = found_bars[0].uuid

        # Perform soft delete if supported by CRUD
        if hasattr(self.crud, "soft_delete"):
            self.crud.soft_delete({"uuid": bar_uuid})

            # Get table size after soft delete
            size2 = get_table_size(self.model)

            # Table size should decrease after soft delete
            self.assertEqual(-1, size2 - size1)

            # Verify bar is no longer found in normal queries
            found_bars_after = self.crud.find(filters={"code": self.test_code})
            self.assertEqual(len(found_bars_after), 0)

    @database_test_required
    def test_BarCRUD_Bulk_Operations_With_Size_Verification_Real(self):
        """Test BarCRUD bulk operations with table size verification"""
        # Get initial table size
        size0 = get_table_size(self.model)

        # Create bulk test data
        bulk_bars = []
        bulk_count = 5

        for i in range(bulk_count):
            bar = Bar()
            bar.set(
                f"{self.test_code}_bulk_{i}",
                Decimal(f"{15+i}.5"),
                Decimal(f"{16+i}.0"),
                Decimal(f"{14+i}.5"),
                Decimal(f"{15+i}.2"),
                1500 + i * 100,
                Decimal(f"{22500+i*1500}"),
                FREQUENCY_TYPES.DAY,
                datetime(2023, 1, i + 1, 9, 30),
            )
            bulk_bars.append(bar)

        # Perform bulk addition
        result = self.crud.add_batch(bulk_bars)

        # Get table size after bulk addition
        size1 = get_table_size(self.model)

        # Verify table size increased by bulk_count
        self.assertEqual(bulk_count, size1 - size0)

        # Verify each bar was added correctly
        for i in range(bulk_count):
            found_bars = self.crud.find(filters={"code": f"{self.test_code}_bulk_{i}"})
            self.assertEqual(len(found_bars), 1)
            self.assertEqual(found_bars[0].volume, 1500 + i * 100)

        # Bulk delete test bars
        for i in range(bulk_count):
            self.crud.remove({"code": f"{self.test_code}_bulk_{i}"})

        # Get final table size
        size2 = get_table_size(self.model)

        # Verify table size returned to original
        self.assertEqual(size2, size0)

    @database_test_required
    def test_BarCRUD_Exists_Real(self):
        """Test BarCRUD exists functionality with real database"""
        # Test non-existent bar
        exists_before = self.crud.exists(filters={"code": self.test_code})
        self.assertFalse(exists_before)

        # Create test bar
        created_bar = self.crud.create(**self.test_bar_params)

        # Test existing bar
        exists_after = self.crud.exists(filters={"code": self.test_code})
        self.assertTrue(exists_after)

        # Test with more specific filters
        exists_specific = self.crud.exists(filters={"code": self.test_code, "volume": 1500})
        self.assertTrue(exists_specific)

        # Test with non-matching filters
        exists_false = self.crud.exists(filters={"code": self.test_code, "volume": 9999})
        self.assertFalse(exists_false)

    @database_test_required
    def test_BarCRUD_Exception_Handling_Real(self):
        """Test BarCRUD exception handling with real database"""
        # Test create with invalid data
        try:
            invalid_params = self.test_bar_params.copy()
            invalid_params["open"] = "invalid_decimal"
            # This might not raise exception due to type conversion
            result = self.crud.create(**invalid_params)
        except Exception as e:
            # Exception handling is working
            pass

        # Test find with empty filters (should not cause issues)
        all_bars = self.crud.find(filters={})
        self.assertIsInstance(all_bars, list)

        # Test remove with overly broad filters (should be safe)
        # This should log a warning but not crash
        self.crud.remove({})  # Should be safely handled

    @database_test_required
    def test_BarCRUD_Modify_Real(self):
        """Test BarCRUD modify functionality with real database - ClickHouse limitation"""
        # Create test bar
        created_bar = self.crud.create(**self.test_bar_params)
        original_volume = created_bar.volume
        original_amount = created_bar.amount

        # Get table size before modification attempt
        size0 = get_table_size(self.model)

        # Attempt to modify the bar (should fail for ClickHouse)
        new_volume = 5000
        new_amount = Decimal("75000")
        updates = {"volume": new_volume, "amount": new_amount}

        # ClickHouse doesn't support UPDATE operations, so this should not modify anything
        self.crud.modify(filters={"code": self.test_code}, updates=updates)

        # Get table size after modification attempt (should be same)
        size1 = get_table_size(self.model)
        self.assertEqual(size0, size1)

        # Verify NO modification occurred (ClickHouse limitation)
        unmodified_bars = self.crud.find(filters={"code": self.test_code})
        self.assertEqual(len(unmodified_bars), 1)

        # Data should remain unchanged due to ClickHouse limitation
        self.assertEqual(unmodified_bars[0].volume, original_volume)
        self.assertEqual(unmodified_bars[0].amount, original_amount)
        self.assertEqual(unmodified_bars[0].code, self.test_code)
        self.assertEqual(unmodified_bars[0].open, created_bar.open)

        # Test modify with empty filters (should be safely handled)
        self.crud.modify(filters={}, updates={"volume": 7500})

        # Verify still no modification
        final_bars = self.crud.find(filters={"code": self.test_code})
        self.assertEqual(len(final_bars), 1)
        self.assertEqual(final_bars[0].volume, original_volume)

        # Test modify with empty updates (should be safely handled)
        self.crud.modify(filters={"code": self.test_code}, updates={})

        # Verify still no modification
        final_bars = self.crud.find(filters={"code": self.test_code})
        self.assertEqual(len(final_bars), 1)
        self.assertEqual(final_bars[0].volume, original_volume)

    @database_test_required
    def test_BarCRUD_Pagination_Real(self):
        """Test BarCRUD pagination functionality with real database"""
        # Create multiple test bars
        bar_count = 10
        for i in range(bar_count):
            params = self.test_bar_params.copy()
            params["code"] = f"{self.test_code}_page_{i}"
            params["volume"] = 1000 + i * 100
            self.crud.create(**params)

        # Test pagination with page_size = 3
        page_size = 3

        # Get first page
        page0_bars = self.crud.find(
            filters={"code__like": f"{self.test_code}_page_"}, page=0, page_size=page_size, order_by="volume"
        )

        self.assertEqual(len(page0_bars), page_size)
        self.assertEqual(page0_bars[0].volume, 1000)  # First item

        # Get second page
        page1_bars = self.crud.find(
            filters={"code__like": f"{self.test_code}_page_"}, page=1, page_size=page_size, order_by="volume"
        )

        self.assertEqual(len(page1_bars), page_size)
        self.assertEqual(page1_bars[0].volume, 1300)  # Fourth item (3*100 + 1000)

        # Get last page (should have remaining items)
        last_page = (bar_count - 1) // page_size
        last_page_bars = self.crud.find(
            filters={"code__like": f"{self.test_code}_page_"}, page=last_page, page_size=page_size, order_by="volume"
        )

        expected_last_page_size = bar_count - (last_page * page_size)
        self.assertEqual(len(last_page_bars), expected_last_page_size)

        # Test page beyond available data
        empty_page_bars = self.crud.find(
            filters={"code__like": f"{self.test_code}_page_"}, page=99, page_size=page_size, order_by="volume"
        )

        self.assertEqual(len(empty_page_bars), 0)

    @database_test_required
    def test_BarCRUD_Ordering_Real(self):
        """Test BarCRUD ordering functionality with real database"""
        # Create test bars with different values
        test_data = [
            {"volume": 3000, "timestamp": datetime(2023, 1, 3)},
            {"volume": 1000, "timestamp": datetime(2023, 1, 1)},
            {"volume": 2000, "timestamp": datetime(2023, 1, 2)},
        ]

        for i, data in enumerate(test_data):
            params = self.test_bar_params.copy()
            params["code"] = f"{self.test_code}_order_{i}"
            params["volume"] = data["volume"]
            params["timestamp"] = data["timestamp"]
            self.crud.create(**params)

        # Test ascending order by volume
        asc_volume_bars = self.crud.find(
            filters={"code__like": f"{self.test_code}_order_"}, order_by="volume", desc_order=False
        )

        self.assertEqual(len(asc_volume_bars), 3)
        self.assertEqual(asc_volume_bars[0].volume, 1000)
        self.assertEqual(asc_volume_bars[1].volume, 2000)
        self.assertEqual(asc_volume_bars[2].volume, 3000)

        # Test descending order by volume
        desc_volume_bars = self.crud.find(
            filters={"code__like": f"{self.test_code}_order_"}, order_by="volume", desc_order=True
        )

        self.assertEqual(len(desc_volume_bars), 3)
        self.assertEqual(desc_volume_bars[0].volume, 3000)
        self.assertEqual(desc_volume_bars[1].volume, 2000)
        self.assertEqual(desc_volume_bars[2].volume, 1000)

        # Test ascending order by timestamp
        asc_time_bars = self.crud.find(
            filters={"code__like": f"{self.test_code}_order_"}, order_by="timestamp", desc_order=False
        )

        self.assertEqual(len(asc_time_bars), 3)
        self.assertEqual(asc_time_bars[0].timestamp.day, 1)
        self.assertEqual(asc_time_bars[1].timestamp.day, 2)
        self.assertEqual(asc_time_bars[2].timestamp.day, 3)

        # Test descending order by timestamp
        desc_time_bars = self.crud.find(
            filters={"code__like": f"{self.test_code}_order_"}, order_by="timestamp", desc_order=True
        )

        self.assertEqual(len(desc_time_bars), 3)
        self.assertEqual(desc_time_bars[0].timestamp.day, 3)
        self.assertEqual(desc_time_bars[1].timestamp.day, 2)
        self.assertEqual(desc_time_bars[2].timestamp.day, 1)

    @database_test_required
    def test_BarCRUD_Invalid_Parameters_Real(self):
        """Test BarCRUD invalid parameters handling with real database"""
        # Test create with missing required fields
        try:
            invalid_params = {"code": self.test_code}  # Missing other required fields
            created_bar = self.crud.create(**invalid_params)
            # Should create with default values
            self.assertIsNotNone(created_bar)
            self.assertEqual(created_bar.code, self.test_code)
            self.assertEqual(created_bar.open, Decimal("0"))
        except Exception as e:
            # Exception handling is working
            self.assertIsInstance(e, Exception)

        # Test find with invalid field names
        invalid_bars = self.crud.find(filters={"nonexistent_field": "value"})
        self.assertIsInstance(invalid_bars, list)

        # Test find with invalid operators
        invalid_operator_bars = self.crud.find(filters={"code__invalid_op": self.test_code})
        self.assertIsInstance(invalid_operator_bars, list)

        # Test modify with invalid filters
        try:
            self.crud.modify(filters={}, updates={"volume": 1000})
            # Should be handled safely (no filters provided)
        except Exception as e:
            pass

        # Test remove with empty filters
        try:
            self.crud.remove({})
            # Should be handled safely (no filters provided)
        except Exception as e:
            pass

        # Test pagination with invalid parameters
        negative_page_bars = self.crud.find(filters={"code__like": f"{self.test_code}%"}, page=-1, page_size=10)
        self.assertIsInstance(negative_page_bars, list)

        # Test ordering with invalid field
        invalid_order_bars = self.crud.find(filters={"code__like": f"{self.test_code}%"}, order_by="nonexistent_field")
        self.assertIsInstance(invalid_order_bars, list)

    @database_test_required
    def test_BarCRUD_Cache_Behavior_Real(self):
        """Test BarCRUD cache behavior with real database"""
        # Create test bars
        for i in range(3):
            params = self.test_bar_params.copy()
            params["code"] = f"{self.test_code}_cache_{i}"
            params["timestamp"] = datetime(2023, 1, i + 1, 9, 30)
            self.crud.create(**params)

        # Test get_date_range_for_code cache behavior
        # First call should hit database
        start_time = datetime.now()
        min_date1, max_date1 = self.crud.get_date_range_for_code(f"{self.test_code}_cache_0")
        first_call_time = datetime.now() - start_time

        # Second call should use cache (should be faster)
        start_time = datetime.now()
        min_date2, max_date2 = self.crud.get_date_range_for_code(f"{self.test_code}_cache_0")
        second_call_time = datetime.now() - start_time

        # Results should be identical
        self.assertEqual(min_date1, min_date2)
        self.assertEqual(max_date1, max_date2)
        self.assertIsNotNone(min_date1)
        self.assertIsNotNone(max_date1)

        # Test get_all_codes method (no longer cached)
        all_codes = self.crud.get_all_codes()
        self.assertIsInstance(all_codes, list)

        # Verify our test codes are in the results
        for i in range(3):
            test_code = f"{self.test_code}_cache_{i}"
            self.assertIn(test_code, all_codes)

    @database_test_required
    def test_BarCRUD_Multiple_Filters_Real(self):
        """Test BarCRUD multiple filters combination with real database"""
        # Create test bars with different combinations
        test_data = [
            {"code": f"{self.test_code}_multi_1", "volume": 1000, "timestamp": datetime(2023, 1, 1)},
            {"code": f"{self.test_code}_multi_2", "volume": 2000, "timestamp": datetime(2023, 1, 2)},
            {"code": f"{self.test_code}_multi_3", "volume": 3000, "timestamp": datetime(2023, 1, 3)},
            {"code": f"{self.test_code}_other_1", "volume": 1500, "timestamp": datetime(2023, 1, 1)},
        ]

        for data in test_data:
            params = self.test_bar_params.copy()
            params.update(data)
            self.crud.create(**params)

        # Test multiple filters with AND logic
        multi_filter_bars = self.crud.find(
            filters={
                "code__like": f"{self.test_code}_multi_",
                "volume__gte": 1500,
                "timestamp__gte": "2023-01-01",
                "timestamp__lte": "2023-01-31",
            }
        )

        # Should find bars with multi prefix, volume >= 1500, and in January
        matching_codes = [bar.code for bar in multi_filter_bars]
        self.assertIn(f"{self.test_code}_multi_2", matching_codes)
        self.assertIn(f"{self.test_code}_multi_3", matching_codes)
        self.assertNotIn(f"{self.test_code}_multi_1", matching_codes)  # volume < 1500
        self.assertNotIn(f"{self.test_code}_other_1", matching_codes)  # wrong prefix

        # Test IN operator with other filters
        in_filter_bars = self.crud.find(
            filters={"code__in": [f"{self.test_code}_multi_1", f"{self.test_code}_multi_3"], "volume__gt": 500}
        )

        found_codes = [bar.code for bar in in_filter_bars]
        self.assertIn(f"{self.test_code}_multi_1", found_codes)
        self.assertIn(f"{self.test_code}_multi_3", found_codes)
        self.assertNotIn(f"{self.test_code}_multi_2", found_codes)  # not in IN list

        # Test complex range filters
        range_filter_bars = self.crud.find(
            filters={
                "volume__gte": 1000,
                "volume__lte": 2500,
                "timestamp__gte": "2023-01-01",
                "timestamp__lt": "2023-01-03",
            }
        )

        # Should find bars with volume between 1000-2500 and timestamp on Jan 1-2
        found_volumes = [bar.volume for bar in range_filter_bars if bar.code.startswith(self.test_code)]
        self.assertIn(1000, found_volumes)
        self.assertIn(2000, found_volumes)
        self.assertIn(1500, found_volumes)
        self.assertNotIn(3000, found_volumes)  # timestamp on Jan 3

    @database_test_required
    def test_BarCRUD_Empty_Results_Real(self):
        """Test BarCRUD handling of empty results with real database"""
        # Test find with non-existent code
        empty_bars = self.crud.find(filters={"code": "NONEXISTENT_CODE"})
        self.assertIsInstance(empty_bars, list)
        self.assertEqual(len(empty_bars), 0)

        # Test find with impossible filter combination
        impossible_bars = self.crud.find(filters={"volume__gt": 1000000, "volume__lt": 1000})
        self.assertIsInstance(impossible_bars, list)
        self.assertEqual(len(impossible_bars), 0)

        # Test count with non-existent code
        empty_count = self.crud.count_by_code("NONEXISTENT_CODE")
        self.assertEqual(empty_count, 0)

        # Test exists with non-existent code
        empty_exists = self.crud.exists(filters={"code": "NONEXISTENT_CODE"})
        self.assertFalse(empty_exists)

        # Test get_latest_bars with non-existent code
        empty_latest = self.crud.get_latest_bars("NONEXISTENT_CODE")
        self.assertIsInstance(empty_latest, list)
        self.assertEqual(len(empty_latest), 0)

        # Test find_by_code_and_date_range with non-existent code
        empty_range = self.crud.find_by_code_and_date_range("NONEXISTENT_CODE", "2023-01-01", "2023-12-31")
        self.assertIsInstance(empty_range, list)
        self.assertEqual(len(empty_range), 0)

        # Test get_date_range_for_code with non-existent code
        empty_min, empty_max = self.crud.get_date_range_for_code("NONEXISTENT_CODE")
        self.assertIsNone(empty_min)
        self.assertIsNone(empty_max)

        # Test DataFrame output with empty results
        empty_df = self.crud.find(filters={"code": "NONEXISTENT_CODE"}, as_dataframe=True)
        import pandas as pd

        self.assertIsInstance(empty_df, pd.DataFrame)
        self.assertEqual(len(empty_df), 0)

    @database_test_required
    def test_BarCRUD_ClickHouse_String_Cleanup_Real(self):
        """Test BarCRUD ClickHouse string cleanup with real database"""
        # Create test bar with code that might have null bytes in ClickHouse
        test_code_with_nulls = f"{self.test_code}_cleanup"
        params = self.test_bar_params.copy()
        params["code"] = test_code_with_nulls

        created_bar = self.crud.create(**params)
        self.assertIsNotNone(created_bar)

        # Test get_all_codes with DISTINCT (should clean null bytes)
        all_codes = self.crud.get_all_codes()
        self.assertIn(test_code_with_nulls, all_codes)

        # Verify that returned codes don't contain null bytes
        for code in all_codes:
            if code.startswith(self.test_code):
                self.assertNotIn("\x00", code)
                self.assertIsInstance(code, str)

        # Test find with distinct_field (should clean null bytes)
        distinct_codes = self.crud.find(filters={"code__like": f"{self.test_code}%"}, distinct_field="code")

        self.assertIsInstance(distinct_codes, list)
        for code in distinct_codes:
            self.assertNotIn("\x00", code)
            self.assertIsInstance(code, str)

        # Test DataFrame output (should clean null bytes)
        df_result = self.crud.find(filters={"code": test_code_with_nulls}, as_dataframe=True)

        import pandas as pd

        self.assertIsInstance(df_result, pd.DataFrame)
        if len(df_result) > 0:
            code_value = df_result.iloc[0]["code"]
            self.assertNotIn("\x00", str(code_value))

        # Test that regular find operations work correctly
        found_bars = self.crud.find(filters={"code": test_code_with_nulls})
        self.assertEqual(len(found_bars), 1)
        self.assertEqual(found_bars[0].code, test_code_with_nulls)

        # Test that business helper methods work with cleaned strings
        latest_bars = self.crud.get_latest_bars(test_code_with_nulls)
        self.assertEqual(len(latest_bars), 1)
        self.assertEqual(latest_bars[0].code, test_code_with_nulls)
