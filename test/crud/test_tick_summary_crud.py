import unittest
import sys
import os
import uuid
from decimal import Decimal
from datetime import datetime
from sqlalchemy import text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

try:
    from ginkgo.data.crud.tick_summary_crud import TickSummaryCRUD
    from ginkgo.data.models import MTickSummary
    from ginkgo.enums import SOURCE_TYPES
    from ginkgo.libs import GCONF, datetime_normalize, to_decimal
    from ginkgo.data.drivers import get_db_connection, get_table_size, create_table, drop_table
    from ginkgo.data.crud.validation import ValidationError
except ImportError as e:
    print(f"Import error: {e}")
    TickSummaryCRUD = None
    GCONF = None


class TickSummaryCRUDTest(unittest.TestCase):
    """
    TickSummaryCRUD database integration tests.
    Tests TickSummary-specific CRUD operations with actual database.
    
    Note: ClickHouse is optimized for append-only operations and analytics.
    Update operations are not supported and will not modify data, which is
    the expected and tested behavior.
    """

    @classmethod
    def setUpClass(cls):
        """Class-level setup: check database configuration and connection"""
        if TickSummaryCRUD is None or GCONF is None:
            raise AssertionError("TickSummaryCRUD or GCONF not available")

        # Set model for table size verification
        cls.model = MTickSummary

        # Recreate table for clean testing
        try:
            drop_table(cls.model, no_skip=True)
            create_table(cls.model, no_skip=True)
            print(":white_check_mark: TickSummary table recreated for testing")
        except Exception as e:
            print(f":warning: TickSummary table recreation failed: {e}")

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

        # Create TickSummaryCRUD instance
        cls.crud = TickSummaryCRUD()

        # Test database connection
        try:
            connection = get_db_connection(MTickSummary)
            with connection.get_session() as session:
                session.execute(text("SELECT 1"))
            print(":white_check_mark: TickSummary database connection successful")
        except Exception as e:
            raise AssertionError(f"Database connection failed: {e}")

    def setUp(self):
        """Setup for each test: prepare unique test data"""
        self.test_id = str(uuid.uuid4())[:8]
        self.test_code = f"TEST{self.test_id}.SZ"
        self.test_timestamp = datetime(2023, 1, 1, 9, 30)

        # Test tick summary data based on MTickSummary model fields
        self.test_tick_summary_params = {
            "code": self.test_code,
            "price": 100.50,
            "volume": 1000,
            "timestamp": self.test_timestamp,
            "source": SOURCE_TYPES.TDX,
        }

    def tearDown(self):
        """Cleanup after each test"""
        try:
            # Remove all test records by test code pattern
            self.crud.remove({"code__like": f"TEST{self.test_id}%"})

            print(f":broom: Cleaned up all test data for {self.test_id}")
        except Exception as e:
            print(f":warning: Cleanup failed: {e}")

    @classmethod
    def tearDownClass(cls):
        """Class-level cleanup: remove any remaining test data"""
        try:
            # Final cleanup of any remaining test records
            cls.crud.remove({"code__like": "TEST%"})
            print(":broom: Final cleanup of all tick summary test records completed")
        except Exception as e:
            print(f":warning: Final cleanup failed: {e}")

    def test_TickSummaryCRUD_Create_From_Params_Real(self):
        """Test TickSummaryCRUD create from parameters with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create tick summary from parameters
        created_tick_summary = self.crud.create(**self.test_tick_summary_params)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify creation
        self.assertIsNotNone(created_tick_summary)
        self.assertIsInstance(created_tick_summary, MTickSummary)
        self.assertEqual(created_tick_summary.code, self.test_code)
        self.assertEqual(created_tick_summary.price, Decimal("100.50"))
        self.assertEqual(created_tick_summary.volume, 1000)
        self.assertEqual(created_tick_summary.timestamp, self.test_timestamp)
        self.assertEqual(created_tick_summary.source, SOURCE_TYPES.TDX)

        # Verify in database  
        found_tick_summaries = self.crud.find(filters={"code": self.test_code})
        self.assertEqual(len(found_tick_summaries), 1)
        self.assertEqual(found_tick_summaries[0].code, self.test_code)

    def test_TickSummaryCRUD_Field_Validation_Real(self):
        """Test TickSummaryCRUD field validation with real database"""
        # Test missing required fields
        with self.assertRaises(ValidationError):
            self.crud.create(code="", price=100.0)
            
        # Test invalid price values (negative)
        with self.assertRaises(ValidationError):
            self.crud.create(
                code=self.test_code,
                price=-100.0  # Negative price should fail
            )

        # Test invalid volume values (negative)
        with self.assertRaises(ValidationError):
            self.crud.create(
                code=self.test_code,
                price=100.0,
                volume=-1000  # Negative volume should fail
            )

        # Test invalid enum values
        with self.assertRaises(ValidationError):
            self.crud.create(
                code=self.test_code,
                price=100.0,
                volume=1000,
                source="INVALID_SOURCE"
            )

    def test_TickSummaryCRUD_Find_By_Code_Real(self):
        """Test TickSummaryCRUD find by code with real database"""
        # Create multiple tick summary records for different codes
        test_codes = [f"TEST{self.test_id}_A.SZ", f"TEST{self.test_id}_B.SZ", f"TEST{self.test_id}_C.SZ"]
        
        for i, code in enumerate(test_codes):
            params = self.test_tick_summary_params.copy()
            params["code"] = code
            params["price"] = 100.0 + i * 10.0
            params["volume"] = 1000 + i * 100
            params["timestamp"] = datetime(2023, 1, i + 1, 9, 30)
            self.crud.create(**params)

        # Test find by specific code
        code_a_summaries = self.crud.find(filters={"code": test_codes[0]})
        self.assertEqual(len(code_a_summaries), 1)
        self.assertEqual(code_a_summaries[0].code, test_codes[0])
        self.assertEqual(code_a_summaries[0].price, Decimal("100.0"))

        # Test find by code pattern
        all_test_summaries = self.crud.find(filters={"code__like": f"TEST{self.test_id}_%"})
        self.assertEqual(len(all_test_summaries), 3)

    def test_TickSummaryCRUD_Find_By_Date_Range_Real(self):
        """Test TickSummaryCRUD find by date range with real database"""
        # Create tick summary records with different dates
        test_dates = [
            datetime(2023, 1, 1, 9, 30),
            datetime(2023, 1, 15, 9, 30),
            datetime(2023, 2, 1, 9, 30),
        ]

        for i, test_date in enumerate(test_dates):
            params = self.test_tick_summary_params.copy()
            params["code"] = f"TEST{self.test_id}_{i}.SZ"
            params["timestamp"] = test_date
            params["price"] = 100.0 + i * 5.0
            self.crud.create(**params)

        # Test find by date range
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 31)
        
        filtered_summaries = self.crud.find(filters={
            "code__like": f"TEST{self.test_id}_%",
            "timestamp__gte": start_date,
            "timestamp__lte": end_date
        })

        # Should find 2 records (January dates)
        self.assertEqual(len(filtered_summaries), 2)
        for summary in filtered_summaries:
            self.assertGreaterEqual(summary.timestamp, start_date)
            self.assertLessEqual(summary.timestamp, end_date)

    def test_TickSummaryCRUD_Find_By_Source_Real(self):
        """Test TickSummaryCRUD find by source with real database"""
        # Create tick summary records with different sources
        sources = [SOURCE_TYPES.TDX, SOURCE_TYPES.TUSHARE, SOURCE_TYPES.AKSHARE]

        for i, source in enumerate(sources):
            params = self.test_tick_summary_params.copy()
            params["code"] = f"TEST{self.test_id}_{i}.SZ"
            params["source"] = source
            params["timestamp"] = datetime(2023, 1, i + 1, 9, 30)
            self.crud.create(**params)

        # Test find by specific source
        tdx_summaries = self.crud.find(filters={
            "code__like": f"TEST{self.test_id}_%",
            "source": SOURCE_TYPES.TDX
        })
        
        self.assertEqual(len(tdx_summaries), 1)
        self.assertEqual(tdx_summaries[0].source, SOURCE_TYPES.TDX)

        # Test find by multiple sources
        multiple_source_summaries = self.crud.find(filters={
            "code__like": f"TEST{self.test_id}_%",
            "source__in": [SOURCE_TYPES.TUSHARE, SOURCE_TYPES.AKSHARE]
        })
        
        self.assertEqual(len(multiple_source_summaries), 2)

    def test_TickSummaryCRUD_Complex_Filters_Real(self):
        """Test TickSummaryCRUD complex filters with real database"""
        # Create tick summary records with different attributes
        test_data = [
            {"code": f"TEST{self.test_id}_A.SZ", "price": 150.0, "volume": 2000, "source": SOURCE_TYPES.TDX},
            {"code": f"TEST{self.test_id}_B.SZ", "price": 80.0, "volume": 500, "source": SOURCE_TYPES.TUSHARE},
            {"code": f"TEST{self.test_id}_C.SZ", "price": 120.0, "volume": 1500, "source": SOURCE_TYPES.TDX},
        ]

        for i, data in enumerate(test_data):
            params = self.test_tick_summary_params.copy()
            params.update(data)
            params["timestamp"] = datetime(2023, 1, i + 1, 9, 30)
            self.crud.create(**params)

        # Test combined filters
        filtered_summaries = self.crud.find(filters={
            "code__like": f"TEST{self.test_id}_%",
            "source": SOURCE_TYPES.TDX,
            "price__gte": 130.0
        })

        # Should find 1 record (TDX source with price >= 130.0)
        self.assertEqual(len(filtered_summaries), 1)
        self.assertEqual(filtered_summaries[0].price, Decimal("150.0"))

    def test_TickSummaryCRUD_Update_Operations_Real(self):
        """Test TickSummaryCRUD modify functionality - ClickHouse limitation"""
        # Create test tick summary
        created_summary = self.crud.create(**self.test_tick_summary_params)
        original_price = created_summary.price
        original_volume = created_summary.volume

        # Attempt to modify (should not work in ClickHouse)
        new_values = {
            "price": 200.0,
            "volume": 2000
        }

        # ClickHouse doesn't support UPDATE operations, so this should not modify anything
        self.crud.modify({"code": self.test_code}, new_values)

        # Verify NO modification occurred (ClickHouse limitation)
        updated_summaries = self.crud.find(filters={"code": self.test_code})
        self.assertEqual(len(updated_summaries), 1)

        # Data should remain unchanged due to ClickHouse limitation
        self.assertEqual(updated_summaries[0].price, original_price)
        self.assertEqual(updated_summaries[0].volume, original_volume)
        self.assertEqual(updated_summaries[0].code, self.test_code)

    def test_TickSummaryCRUD_Bulk_Operations_Real(self):
        """Test TickSummaryCRUD bulk operations with table size verification"""
        # Get initial table size
        size0 = get_table_size(self.model)

        # Create bulk test data
        bulk_summaries = []
        bulk_count = 5

        for i in range(bulk_count):
            summary = self.crud._create_from_params(
                code=f"BULK{self.test_id}_{i}.SZ",
                price=100.0 + i * 10.0,
                volume=1000 + i * 100,
                timestamp=datetime(2023, 1, i + 1, 9, 30),
                source=SOURCE_TYPES.TDX,
            )
            bulk_summaries.append(summary)

        # Perform bulk addition
        result = self.crud.add_batch(bulk_summaries)

        # Get table size after bulk addition
        size1 = get_table_size(self.model)

        # Verify table size increased by bulk_count
        self.assertEqual(bulk_count, size1 - size0)

        # Verify each summary was added correctly
        for i in range(bulk_count):
            found_summaries = self.crud.find(filters={"code": f"BULK{self.test_id}_{i}.SZ"})
            self.assertEqual(len(found_summaries), 1)
            self.assertEqual(found_summaries[0].price, Decimal(f"{100.0 + i * 10.0}"))

        # Cleanup bulk data
        self.crud.remove({"code__like": f"BULK{self.test_id}_%"})

    def test_TickSummaryCRUD_DataFrame_Output_Real(self):
        """Test TickSummaryCRUD DataFrame output with real database"""
        # Create test tick summary
        created_summary = self.crud.create(**self.test_tick_summary_params)

        # Get as DataFrame
        df_result = self.crud.find(filters={"code": self.test_code}, as_dataframe=True)

        # Verify DataFrame
        import pandas as pd

        self.assertIsInstance(df_result, pd.DataFrame)
        self.assertEqual(len(df_result), 1)

        # Verify DataFrame content
        self.assertEqual(df_result.iloc[0]["code"], self.test_code)
        self.assertEqual(float(df_result.iloc[0]["price"]), 100.50)
        self.assertEqual(int(df_result.iloc[0]["volume"]), 1000)

    def test_TickSummaryCRUD_Count_Operations_Real(self):
        """Test TickSummaryCRUD count operations with real database"""
        # Create multiple test summaries
        test_codes = [f"COUNT{self.test_id}_{i}.SZ" for i in range(3)]
        
        for code in test_codes:
            params = self.test_tick_summary_params.copy()
            params["code"] = code
            self.crud.create(**params)

        # Test count with filters
        count = self.crud.count({"code__like": f"COUNT{self.test_id}_%"})
        self.assertEqual(count, 3)

        # Test count with specific filter
        specific_count = self.crud.count({"code": test_codes[0]})
        self.assertEqual(specific_count, 1)

        # Cleanup
        self.crud.remove({"code__like": f"COUNT{self.test_id}_%"})

    def test_TickSummaryCRUD_Exception_Handling_Real(self):
        """Test TickSummaryCRUD exception handling with real database"""
        # Test find with empty filters (should not cause issues)
        all_summaries = self.crud.find(filters={})
        self.assertIsInstance(all_summaries, list)

        # Test with invalid decimal values
        try:
            invalid_params = self.test_tick_summary_params.copy()
            invalid_params["price"] = "invalid_price"
            result = self.crud.create(**invalid_params)
        except Exception as e:
            # Exception handling is working
            pass

        # Test exists functionality
        exists_before = self.crud.exists(filters={"code": "NONEXISTENT_CODE"})
        self.assertFalse(exists_before)

        # Create and test exists
        created_summary = self.crud.create(**self.test_tick_summary_params)
        exists_after = self.crud.exists(filters={"code": self.test_code})
        self.assertTrue(exists_after)