import unittest
import sys
import os
import uuid
from decimal import Decimal
from datetime import datetime
from sqlalchemy import text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

try:
    from ginkgo.data.crud.portfolio_crud import PortfolioCRUD
    from ginkgo.data.crud.validation import ValidationError
    from ginkgo.data.models import MPortfolio
    from ginkgo.enums import SOURCE_TYPES
    from ginkgo.libs import GCONF, datetime_normalize, to_decimal
    from ginkgo.data.drivers import get_db_connection, get_table_size, create_table, drop_table
except ImportError as e:
    print(f"Import error: {e}")
    PortfolioCRUD = None
    GCONF = None
    ValidationError = None


class PortfolioCRUDTest(unittest.TestCase):
    """
    PortfolioCRUD database integration tests.
    Tests Portfolio-specific CRUD operations with actual database.
    """

    @classmethod
    def setUpClass(cls):
        """Class-level setup: check database configuration and connection"""
        if PortfolioCRUD is None or GCONF is None:
            raise AssertionError("PortfolioCRUD or GCONF not available")

        # Set model for table size verification
        cls.model = MPortfolio

        # Recreate table for clean testing
        try:
            drop_table(cls.model, no_skip=True)
            create_table(cls.model, no_skip=True)
            print(":white_check_mark: Portfolio table recreated for testing")
        except Exception as e:
            print(f":warning: Portfolio table recreation failed: {e}")

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

        # Create PortfolioCRUD instance
        cls.crud = PortfolioCRUD()

        # Test database connection
        try:
            connection = get_db_connection(MPortfolio)
            with connection.get_session() as session:
                session.execute(text("SELECT 1"))
            print(":white_check_mark: Portfolio database connection successful")
        except Exception as e:
            raise AssertionError(f"Database connection failed: {e}")

    def setUp(self):
        """Setup for each test: prepare unique test data"""
        self.test_id = str(uuid.uuid4())[:8]
        self.test_start_date = datetime(2023, 1, 1, 9, 30)
        self.test_end_date = datetime(2023, 12, 31, 15, 0)

        # Test portfolio data - 匹配 MPortfolio 模型字段
        self.test_portfolio_params = {
            "name": f"TestPortfolio_{self.test_id}",
            "backtest_start_date": self.test_start_date,
            "backtest_end_date": self.test_end_date,
            "is_live": False,
            "source": SOURCE_TYPES.SIM,
        }

    def tearDown(self):
        """Cleanup after each test"""
        try:
            # Clean up by name pattern
            self.crud.remove({"name__like": f"TestPortfolio_{self.test_id}%"})

            print(f":broom: Cleaned up all test data for TestPortfolio_{self.test_id}")
        except Exception as e:
            print(f":warning: Cleanup failed: {e}")

    @classmethod
    def tearDownClass(cls):
        """Class-level cleanup: remove any remaining test data"""
        try:
            # Final cleanup of any remaining test records
            cls.crud.remove({"name__like": "TestPortfolio_%"})
            print(":broom: Final cleanup of all portfolio test records completed")
        except Exception as e:
            print(f":warning: Final cleanup failed: {e}")

    def test_PortfolioCRUD_Create_From_Params_Real(self):
        """Test PortfolioCRUD create from parameters with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create portfolio from parameters
        created_portfolio = self.crud.create(**self.test_portfolio_params)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify creation
        self.assertIsNotNone(created_portfolio)
        self.assertIsInstance(created_portfolio, MPortfolio)
        self.assertEqual(created_portfolio.name, f"TestPortfolio_{self.test_id}")
        self.assertEqual(created_portfolio.backtest_start_date, self.test_start_date)
        self.assertEqual(created_portfolio.backtest_end_date, self.test_end_date)
        self.assertEqual(created_portfolio.is_live, False)
        self.assertEqual(created_portfolio.source, SOURCE_TYPES.SIM)

        # Verify in database
        found_portfolios = self.crud.find(filters={"name": f"TestPortfolio_{self.test_id}"})
        self.assertEqual(len(found_portfolios), 1)
        self.assertEqual(found_portfolios[0].name, f"TestPortfolio_{self.test_id}")

    def test_PortfolioCRUD_Name_Length_Validation_Real(self):
        """Test PortfolioCRUD name field length validation (max 64 characters)"""
        if ValidationError is not None:
            # Test name too long (should be rejected)
            with self.assertRaises(ValidationError):
                invalid_params = self.test_portfolio_params.copy()
                invalid_params["name"] = "x" * 65  # Exceeds max length of 64
                self.crud.create(**invalid_params)

            # Test valid name length (should pass)
            valid_params = self.test_portfolio_params.copy()
            valid_params["name"] = "x" * 64  # Exactly max length
            created_portfolio = self.crud.create(**valid_params)
            self.assertEqual(len(created_portfolio.name), 64)

            # Test empty name (should be rejected due to min: 1)
            with self.assertRaises(ValidationError):
                invalid_params = self.test_portfolio_params.copy()
                invalid_params["name"] = ""  # Empty string
                self.crud.create(**invalid_params)

    def test_PortfolioCRUD_DateTime_Validation_Real(self):
        """Test PortfolioCRUD datetime field validation"""
        # Test with string datetime
        string_params = self.test_portfolio_params.copy()
        string_params["backtest_start_date"] = "2023-01-01 09:30:00"
        string_params["backtest_end_date"] = "2023-12-31 15:00:00"
        
        created_portfolio = self.crud.create(**string_params)
        self.assertIsNotNone(created_portfolio)
        
        # Test with datetime objects (should also work)
        datetime_params = self.test_portfolio_params.copy()
        datetime_params["name"] = f"TestPortfolio_datetime_{self.test_id}"
        datetime_params["backtest_start_date"] = datetime(2023, 6, 1, 10, 0)
        datetime_params["backtest_end_date"] = datetime(2023, 6, 30, 16, 0)
        
        created_portfolio2 = self.crud.create(**datetime_params)
        self.assertEqual(created_portfolio2.backtest_start_date, datetime(2023, 6, 1, 10, 0))

    def test_PortfolioCRUD_Boolean_Validation_Real(self):
        """Test PortfolioCRUD boolean field validation"""
        # Test with boolean True
        live_params = self.test_portfolio_params.copy()
        live_params["name"] = f"TestPortfolio_live_{self.test_id}"
        live_params["is_live"] = True
        
        created_live = self.crud.create(**live_params)
        self.assertTrue(created_live.is_live)
        
        # Test with boolean False
        sim_params = self.test_portfolio_params.copy()
        sim_params["name"] = f"TestPortfolio_sim_{self.test_id}"
        sim_params["is_live"] = False
        
        created_sim = self.crud.create(**sim_params)
        self.assertFalse(created_sim.is_live)

    def test_PortfolioCRUD_Add_Batch_Real(self):
        """Test PortfolioCRUD batch addition with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create multiple portfolios
        portfolios = []
        batch_count = 3
        for i in range(batch_count):
            params = self.test_portfolio_params.copy()
            params["name"] = f"TestPortfolio_batch_{self.test_id}_{i}"
            params["is_live"] = i % 2 == 0  # Alternate live/sim
            
            portfolio = self.crud._create_from_params(**params)
            portfolios.append(portfolio)

        # Add batch
        result = self.crud.add_batch(portfolios)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by batch count
        self.assertEqual(batch_count, size1 - size0)

        # Verify batch addition
        self.assertIsInstance(result, tuple)

        # Verify each portfolio in database
        for i in range(batch_count):
            found_portfolios = self.crud.find(filters={"name": f"TestPortfolio_batch_{self.test_id}_{i}"})
            self.assertEqual(len(found_portfolios), 1)
            self.assertEqual(found_portfolios[0].is_live, i % 2 == 0)

    def test_PortfolioCRUD_DataFrame_Output_Real(self):
        """Test PortfolioCRUD DataFrame output with real database"""
        # Create test portfolio
        created_portfolio = self.crud.create(**self.test_portfolio_params)

        # Get as DataFrame
        df_result = self.crud.find(filters={"name": f"TestPortfolio_{self.test_id}"}, as_dataframe=True)

        # Verify DataFrame
        import pandas as pd

        self.assertIsInstance(df_result, pd.DataFrame)
        self.assertEqual(len(df_result), 1)
        self.assertEqual(df_result.iloc[0]["name"], f"TestPortfolio_{self.test_id}")

    def test_PortfolioCRUD_Exception_Handling_Real(self):
        """Test PortfolioCRUD exception handling with real database"""
        # Test find with empty filters (should not cause issues)
        all_portfolios = self.crud.find(filters={})
        self.assertIsInstance(all_portfolios, list)

        # Test remove with overly broad filters (should be safe)
        self.crud.remove({})  # Should be safely handled without affecting other tests

        # Test create with invalid data types - should raise ValidationError
        if ValidationError is not None:
            # Test missing required name field
            with self.assertRaises(ValidationError):
                self.crud.create(
                    name="",  # Empty name should fail
                    backtest_start_date=datetime(2023, 1, 1),
                    backtest_end_date=datetime(2023, 12, 31),
                    is_live=False,
                    source=SOURCE_TYPES.SIM
                )
                
            # Test invalid source enum
            with self.assertRaises(ValidationError):
                self.crud.create(
                    name=f"TestPortfolio_{self.test_id}",
                    backtest_start_date=datetime(2023, 1, 1),
                    backtest_end_date=datetime(2023, 12, 31),
                    is_live=False,
                    source="INVALID_SOURCE"  # Invalid enum should fail
                )

            # Test invalid boolean type
            with self.assertRaises(ValidationError):
                self.crud.create(
                    name=f"TestPortfolio_{self.test_id}",
                    backtest_start_date=datetime(2023, 1, 1),
                    backtest_end_date=datetime(2023, 12, 31),
                    is_live="not_a_boolean",  # Invalid boolean should fail
                    source=SOURCE_TYPES.SIM
                )

            # Test invalid date type
            with self.assertRaises(ValidationError):
                self.crud.create(
                    name=f"TestPortfolio_{self.test_id}",
                    backtest_start_date={"invalid": "date"},  # Dict cannot be converted to datetime or string
                    backtest_end_date=datetime(2023, 12, 31),
                    is_live=False,
                    source=SOURCE_TYPES.SIM
                )

    def test_PortfolioCRUD_Exists_Real(self):
        """Test PortfolioCRUD exists functionality with real database"""
        # Test non-existent portfolio
        exists_before = self.crud.exists(filters={"name": f"TestPortfolio_{self.test_id}"})
        self.assertFalse(exists_before)

        # Create test portfolio
        created_portfolio = self.crud.create(**self.test_portfolio_params)

        # Test existing portfolio
        exists_after = self.crud.exists(filters={"name": f"TestPortfolio_{self.test_id}"})
        self.assertTrue(exists_after)

        # Test with more specific filters
        exists_specific = self.crud.exists(filters={
            "name": f"TestPortfolio_{self.test_id}",
            "is_live": False
        })
        self.assertTrue(exists_specific)

        # Test with non-matching filters
        exists_false = self.crud.exists(filters={
            "name": f"TestPortfolio_{self.test_id}",
            "is_live": True
        })
        self.assertFalse(exists_false)
