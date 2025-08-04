import unittest
import sys
import os
import uuid
from decimal import Decimal
from datetime import datetime
from sqlalchemy import text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

try:
    from ginkgo.data.crud.adjustfactor_crud import AdjustfactorCRUD
    from ginkgo.data.models import MAdjustfactor
    from ginkgo.enums import SOURCE_TYPES
    from ginkgo.libs import GCONF, datetime_normalize, to_decimal
    from ginkgo.data.drivers import get_db_connection, get_table_size, create_table, drop_table
    from ginkgo.data.crud.validation import ValidationError
except ImportError as e:
    print(f"Import error: {e}")
    AdjustfactorCRUD = None
    GCONF = None


class AdjustfactorCRUDTest(unittest.TestCase):
    """
    AdjustfactorCRUD database integration tests.
    Tests Adjustfactor-specific CRUD operations with actual database.
    
    Note: ClickHouse is optimized for append-only operations and analytics.
    Update operations are not supported and will not modify data, which is
    the expected and tested behavior.
    """

    @classmethod
    def setUpClass(cls):
        """Class-level setup: check database configuration and connection"""
        if AdjustfactorCRUD is None or GCONF is None:
            raise AssertionError("AdjustfactorCRUD or GCONF not available")

        # Set model for table size verification
        cls.model = MAdjustfactor

        # Recreate table for clean testing
        try:
            drop_table(cls.model, no_skip=True)
            create_table(cls.model, no_skip=True)
            print(":white_check_mark: Adjustfactor table recreated for testing")
        except Exception as e:
            print(f":warning: Adjustfactor table recreation failed: {e}")

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

        # Create AdjustfactorCRUD instance
        cls.crud = AdjustfactorCRUD()

        # Test database connection
        try:
            connection = get_db_connection(MAdjustfactor)
            with connection.get_session() as session:
                session.execute(text("SELECT 1"))
            print(":white_check_mark: Adjustfactor database connection successful")
        except Exception as e:
            raise AssertionError(f"Database connection failed: {e}")

    def setUp(self):
        """Setup for each test: prepare unique test data"""
        self.test_id = str(uuid.uuid4())[:8]
        self.test_code = f"TEST{self.test_id}.SZ"
        self.test_timestamp = datetime(2023, 1, 1, 9, 30)

        # Test adjustfactor data based on MAdjustfactor model fields
        self.test_adjustfactor_params = {
            "code": self.test_code,
            "foreadjustfactor": 1.0,
            "backadjustfactor": 1.0,
            "adjustfactor": 1.0,
            "timestamp": self.test_timestamp,
            "source": SOURCE_TYPES.TUSHARE,
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
            print(":broom: Final cleanup of all adjustfactor test records completed")
        except Exception as e:
            print(f":warning: Final cleanup failed: {e}")

    def test_AdjustfactorCRUD_Create_From_Params_Real(self):
        """Test AdjustfactorCRUD create from parameters with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create adjustfactor from parameters
        created_adjustfactor = self.crud.create(**self.test_adjustfactor_params)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify creation
        self.assertIsNotNone(created_adjustfactor)
        self.assertIsInstance(created_adjustfactor, MAdjustfactor)
        self.assertEqual(created_adjustfactor.code, self.test_code)
        self.assertEqual(created_adjustfactor.foreadjustfactor, Decimal("1.0"))
        self.assertEqual(created_adjustfactor.backadjustfactor, Decimal("1.0"))
        self.assertEqual(created_adjustfactor.adjustfactor, Decimal("1.0"))
        self.assertEqual(created_adjustfactor.timestamp, self.test_timestamp)
        self.assertEqual(created_adjustfactor.source, SOURCE_TYPES.TUSHARE)

        # Verify in database
        found_adjustfactors = self.crud.find(filters={"code": self.test_code})
        self.assertEqual(len(found_adjustfactors), 1)
        self.assertEqual(found_adjustfactors[0].code, self.test_code)

    def test_AdjustfactorCRUD_Field_Validation_Real(self):
        """Test AdjustfactorCRUD field validation with real database"""
        # Test missing required fields
        with self.assertRaises(ValidationError):
            self.crud.create(code="", foreadjustfactor=1.0)
            
        # Test invalid factor values (too small)
        with self.assertRaises(ValidationError):
            self.crud.create(
                code=self.test_code,
                foreadjustfactor=0.0001  # Below minimum 0.001
            )

        with self.assertRaises(ValidationError):
            self.crud.create(
                code=self.test_code,
                foreadjustfactor=1.0,
                backadjustfactor=-1.0  # Negative value
            )

        # Test invalid enum values
        with self.assertRaises(ValidationError):
            self.crud.create(
                code=self.test_code,
                foreadjustfactor=1.0,
                backadjustfactor=1.0,
                adjustfactor=1.0,
                source="INVALID_SOURCE"
            )

    def test_AdjustfactorCRUD_Find_By_Code_Real(self):
        """Test AdjustfactorCRUD find by code with real database"""
        # Create multiple adjustfactor records for different codes
        test_codes = [f"TEST{self.test_id}_A.SZ", f"TEST{self.test_id}_B.SZ", f"TEST{self.test_id}_C.SZ"]
        
        for i, code in enumerate(test_codes):
            params = self.test_adjustfactor_params.copy()
            params["code"] = code
            params["foreadjustfactor"] = 1.0 + i * 0.1
            params["backadjustfactor"] = 1.0 + i * 0.05
            params["adjustfactor"] = 1.0 + i * 0.02
            params["timestamp"] = datetime(2023, 1, i + 1, 9, 30)
            self.crud.create(**params)

        # Test find by specific code
        code_a_factors = self.crud.find(filters={"code": test_codes[0]})
        self.assertEqual(len(code_a_factors), 1)
        self.assertEqual(code_a_factors[0].code, test_codes[0])
        self.assertEqual(code_a_factors[0].foreadjustfactor, Decimal("1.0"))

        # Test find by code pattern
        all_test_factors = self.crud.find(filters={"code__like": f"TEST{self.test_id}_%"})
        self.assertEqual(len(all_test_factors), 3)

    def test_AdjustfactorCRUD_Find_By_Date_Range_Real(self):
        """Test AdjustfactorCRUD find by date range with real database"""
        # Create adjustfactor records with different dates
        test_dates = [
            datetime(2023, 1, 1, 9, 30),
            datetime(2023, 1, 15, 9, 30),
            datetime(2023, 2, 1, 9, 30),
        ]

        for i, test_date in enumerate(test_dates):
            params = self.test_adjustfactor_params.copy()
            params["code"] = f"TEST{self.test_id}_{i}.SZ"
            params["timestamp"] = test_date
            params["foreadjustfactor"] = 1.0 + i * 0.1
            self.crud.create(**params)

        # Test find by date range
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 31)
        
        filtered_factors = self.crud.find(filters={
            "code__like": f"TEST{self.test_id}_%",
            "timestamp__gte": start_date,
            "timestamp__lte": end_date
        })

        # Should find 2 records (January dates)
        self.assertEqual(len(filtered_factors), 2)
        for factor in filtered_factors:
            self.assertGreaterEqual(factor.timestamp, start_date)
            self.assertLessEqual(factor.timestamp, end_date)

    def test_AdjustfactorCRUD_Find_By_Source_Real(self):
        """Test AdjustfactorCRUD find by source with real database"""
        # Create adjustfactor records with different sources
        sources = [SOURCE_TYPES.TUSHARE, SOURCE_TYPES.YAHOO, SOURCE_TYPES.AKSHARE]

        for i, source in enumerate(sources):
            params = self.test_adjustfactor_params.copy()
            params["code"] = f"TEST{self.test_id}_{i}.SZ"
            params["source"] = source
            params["timestamp"] = datetime(2023, 1, i + 1, 9, 30)
            self.crud.create(**params)

        # Test find by specific source
        tushare_factors = self.crud.find(filters={
            "code__like": f"TEST{self.test_id}_%",
            "source": SOURCE_TYPES.TUSHARE
        })
        
        self.assertEqual(len(tushare_factors), 1)
        self.assertEqual(tushare_factors[0].source, SOURCE_TYPES.TUSHARE)

        # Test find by multiple sources
        multiple_source_factors = self.crud.find(filters={
            "code__like": f"TEST{self.test_id}_%",
            "source__in": [SOURCE_TYPES.YAHOO, SOURCE_TYPES.AKSHARE]
        })
        
        self.assertEqual(len(multiple_source_factors), 2)

    def test_AdjustfactorCRUD_Complex_Filters_Real(self):
        """Test AdjustfactorCRUD complex filters with real database"""
        # Create adjustfactor records with different attributes
        test_data = [
            {"code": f"TEST{self.test_id}_A.SZ", "foreadjustfactor": 1.5, "source": SOURCE_TYPES.TUSHARE},
            {"code": f"TEST{self.test_id}_B.SZ", "foreadjustfactor": 0.8, "source": SOURCE_TYPES.YAHOO},
            {"code": f"TEST{self.test_id}_C.SZ", "foreadjustfactor": 1.2, "source": SOURCE_TYPES.TUSHARE},
        ]

        for i, data in enumerate(test_data):
            params = self.test_adjustfactor_params.copy()
            params.update(data)
            params["timestamp"] = datetime(2023, 1, i + 1, 9, 30)
            self.crud.create(**params)

        # Test combined filters
        filtered_factors = self.crud.find(filters={
            "code__like": f"TEST{self.test_id}_%",
            "source": SOURCE_TYPES.TUSHARE,
            "foreadjustfactor__gte": 1.3
        })

        # Should find 1 record (TUSHARE source with factor >= 1.3)
        self.assertEqual(len(filtered_factors), 1)
        self.assertEqual(filtered_factors[0].foreadjustfactor, Decimal("1.5"))

    def test_AdjustfactorCRUD_Bulk_Operations_Real(self):
        """Test AdjustfactorCRUD bulk operations with table size verification"""
        # Get initial table size
        size0 = get_table_size(self.model)

        # Create bulk test data
        bulk_factors = []
        bulk_count = 5

        for i in range(bulk_count):
            factor = self.crud._create_from_params(
                code=f"BULK{self.test_id}_{i}.SZ",
                foreadjustfactor=1.0 + i * 0.1,
                backadjustfactor=1.0 + i * 0.05,
                adjustfactor=1.0 + i * 0.02,
                timestamp=datetime(2023, 1, i + 1, 9, 30),
                source=SOURCE_TYPES.TUSHARE,
            )
            bulk_factors.append(factor)

        # Perform bulk addition
        result = self.crud.add_batch(bulk_factors)

        # Get table size after bulk addition
        size1 = get_table_size(self.model)

        # Verify table size increased by bulk_count
        self.assertEqual(bulk_count, size1 - size0)

        # Verify each factor was added correctly
        for i in range(bulk_count):
            found_factors = self.crud.find(filters={"code": f"BULK{self.test_id}_{i}.SZ"})
            self.assertEqual(len(found_factors), 1)
            self.assertEqual(found_factors[0].foreadjustfactor, Decimal(f"{1.0 + i * 0.1:.1f}"))

        # Cleanup bulk data
        self.crud.remove({"code__like": f"BULK{self.test_id}_%"})

    def test_AdjustfactorCRUD_DataFrame_Output_Real(self):
        """Test AdjustfactorCRUD DataFrame output with real database"""
        # Create test adjustfactor
        created_factor = self.crud.create(**self.test_adjustfactor_params)

        # Get as DataFrame
        df_result = self.crud.find(filters={"code": self.test_code}, as_dataframe=True)

        # Verify DataFrame
        import pandas as pd

        self.assertIsInstance(df_result, pd.DataFrame)
        self.assertEqual(len(df_result), 1)

        # Verify DataFrame content
        self.assertEqual(df_result.iloc[0]["code"], self.test_code)
        self.assertEqual(float(df_result.iloc[0]["foreadjustfactor"]), 1.0)

    def test_AdjustfactorCRUD_Update_Operations_Real(self):
        """Test AdjustfactorCRUD modify functionality - ClickHouse limitation"""
        # Create test adjustfactor
        created_factor = self.crud.create(**self.test_adjustfactor_params)
        original_fore = created_factor.foreadjustfactor
        original_back = created_factor.backadjustfactor
        original_adj = created_factor.adjustfactor

        # Attempt to modify (should not work in ClickHouse)
        new_values = {
            "foreadjustfactor": 1.5,
            "backadjustfactor": 0.8,
            "adjustfactor": 1.2
        }

        # ClickHouse doesn't support UPDATE operations, so this should not modify anything
        self.crud.modify({"code": self.test_code}, new_values)

        # Verify NO modification occurred (ClickHouse limitation)
        updated_factors = self.crud.find(filters={"code": self.test_code})
        self.assertEqual(len(updated_factors), 1)

        # Data should remain unchanged due to ClickHouse limitation
        self.assertEqual(updated_factors[0].foreadjustfactor, original_fore)
        self.assertEqual(updated_factors[0].backadjustfactor, original_back)
        self.assertEqual(updated_factors[0].adjustfactor, original_adj)
        self.assertEqual(updated_factors[0].code, self.test_code)

    def test_AdjustfactorCRUD_Count_Operations_Real(self):
        """Test AdjustfactorCRUD count operations with real database"""
        # Create multiple test factors
        test_codes = [f"COUNT{self.test_id}_{i}.SZ" for i in range(3)]
        
        for code in test_codes:
            params = self.test_adjustfactor_params.copy()
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

    def test_AdjustfactorCRUD_Exception_Handling_Real(self):
        """Test AdjustfactorCRUD exception handling with real database"""
        # Test find with empty filters (should not cause issues)
        all_factors = self.crud.find(filters={})
        self.assertIsInstance(all_factors, list)

        # Test with invalid decimal values
        try:
            invalid_params = self.test_adjustfactor_params.copy()
            invalid_params["foreadjustfactor"] = "invalid_decimal"
            result = self.crud.create(**invalid_params)
        except Exception as e:
            # Exception handling is working
            pass

        # Test exists functionality
        exists_before = self.crud.exists(filters={"code": "NONEXISTENT_CODE"})
        self.assertFalse(exists_before)

        # Create and test exists
        created_factor = self.crud.create(**self.test_adjustfactor_params)
        exists_after = self.crud.exists(filters={"code": self.test_code})
        self.assertTrue(exists_after)