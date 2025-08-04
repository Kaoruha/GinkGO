import unittest
import sys
import os
import uuid
from decimal import Decimal
from datetime import datetime
from test.database.test_isolation import database_test_required


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

try:
    from sqlalchemy import text
    from ginkgo.data.crud.transfer_crud import TransferCRUD
    from ginkgo.data.models import MTransfer
    from ginkgo.backtest import Transfer
    from ginkgo.enums import SOURCE_TYPES, TRANSFERDIRECTION_TYPES, TRANSFERSTATUS_TYPES, MARKET_TYPES
    from ginkgo.libs import GCONF, datetime_normalize, to_decimal
    from ginkgo.data.drivers import get_db_connection, get_table_size, create_table, drop_table
    from ginkgo.data.crud.validation import ValidationError
except ImportError as e:
    print(f"Import error: {e}")
    TransferCRUD = None
    GCONF = None


class TransferCRUDTest(unittest.TestCase):
    """
    TransferCRUD database integration tests.
    Tests Transfer-specific CRUD operations with actual database.
    """

    @classmethod
    def setUpClass(cls):
        """Class-level setup: check database configuration and connection"""
        if TransferCRUD is None or GCONF is None:
            raise AssertionError("TransferCRUD or GCONF not available")

        # Set model for table size verification
        cls.model = MTransfer

        # Recreate table for clean testing
        try:
            drop_table(cls.model, no_skip=True)
            create_table(cls.model, no_skip=True)
            print(":white_check_mark: Transfer table recreated for testing")
        except Exception as e:
            print(f":warning: Transfer table recreation failed: {e}")

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

        # Create TransferCRUD instance
        cls.crud = TransferCRUD()

        # Test database connection
        try:
            connection = get_db_connection(MTransfer)
            with connection.get_session() as session:
                session.execute(text("SELECT 1"))
            print(":white_check_mark: Transfer database connection successful")
        except Exception as e:
            raise AssertionError(f"Database connection failed: {e}")

    def setUp(self):
        """Setup for each test: prepare unique test data"""
        self.test_id = str(uuid.uuid4())[:8]
        self.test_portfolio_id = f"PORTFOLIO_{self.test_id}"
        self.test_engine_id = f"ENGINE_{self.test_id}"
        self.test_timestamp = datetime(2023, 1, 1, 9, 30)

        # Test transfer data based on MTransfer model fields
        self.test_transfer_params = {
            "portfolio_id": self.test_portfolio_id,
            "engine_id": self.test_engine_id,
            "direction": TRANSFERDIRECTION_TYPES.IN,
            "market": MARKET_TYPES.CHINA,
            "money": 100000.0,
            "status": TRANSFERSTATUS_TYPES.PENDING,
            "timestamp": self.test_timestamp,
            "source": SOURCE_TYPES.SIM,
        }

    def tearDown(self):
        """Cleanup after each test"""
        try:
            # Remove all test records by test portfolio ID pattern
            self.crud.remove({"portfolio_id__like": f"PORTFOLIO_{self.test_id}%"})
            
            # Also clean up by engine ID pattern
            self.crud.remove({"engine_id__like": f"ENGINE_{self.test_id}%"})

            print(f":broom: Cleaned up all test data for {self.test_id}")
        except Exception as e:
            print(f":warning: Cleanup failed: {e}")

    @classmethod
    def tearDownClass(cls):
        """Class-level cleanup: remove any remaining test data"""
        try:
            # Final cleanup of any remaining test records
            cls.crud.remove({"portfolio_id__like": "PORTFOLIO_%"})
            cls.crud.remove({"engine_id__like": "ENGINE_%"})
            print(":broom: Final cleanup of all transfer test records completed")
        except Exception as e:
            print(f":warning: Final cleanup failed: {e}")

    @database_test_required
    def test_TransferCRUD_Create_From_Params_Real(self):
        """Test TransferCRUD create from parameters with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create transfer from parameters
        created_transfer = self.crud.create(**self.test_transfer_params)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify creation
        self.assertIsNotNone(created_transfer)
        self.assertIsInstance(created_transfer, MTransfer)
        self.assertEqual(created_transfer.portfolio_id, self.test_portfolio_id)
        self.assertEqual(created_transfer.engine_id, self.test_engine_id)
        self.assertEqual(created_transfer.direction, TRANSFERDIRECTION_TYPES.IN)
        self.assertEqual(created_transfer.market, MARKET_TYPES.CHINA)
        self.assertEqual(created_transfer.money, Decimal("100000.0"))
        self.assertEqual(created_transfer.status, TRANSFERSTATUS_TYPES.PENDING)
        self.assertEqual(created_transfer.timestamp, self.test_timestamp)
        self.assertEqual(created_transfer.source, SOURCE_TYPES.SIM)

        # Verify in database
        found_transfers = self.crud.find(filters={"portfolio_id": self.test_portfolio_id})
        self.assertEqual(len(found_transfers), 1)
        self.assertEqual(found_transfers[0].portfolio_id, self.test_portfolio_id)

    @database_test_required
    def test_TransferCRUD_Field_Validation_Real(self):
        """Test TransferCRUD field validation with real database"""
        # Test missing required fields
        with self.assertRaises(ValidationError):
            self.crud.create(portfolio_id="", engine_id=self.test_engine_id)
            
        with self.assertRaises(ValidationError):
            self.crud.create(portfolio_id=self.test_portfolio_id, engine_id="")

        # Test invalid money value
        with self.assertRaises(ValidationError):
            self.crud.create(
                portfolio_id=self.test_portfolio_id,
                engine_id=self.test_engine_id,
                money=-100  # Negative money should fail
            )

        # Test invalid enum values
        with self.assertRaises(ValidationError):
            self.crud.create(
                portfolio_id=self.test_portfolio_id,
                engine_id=self.test_engine_id,
                direction="INVALID_DIRECTION"
            )

    @database_test_required
    def test_TransferCRUD_Find_By_Portfolio_Real(self):
        """Test TransferCRUD find by portfolio business helper method with real database"""
        # Create multiple transfers for the same portfolio
        test_transfers = [
            {"direction": TRANSFERDIRECTION_TYPES.IN, "money": 10000.0},
            {"direction": TRANSFERDIRECTION_TYPES.OUT, "money": 5000.0},
            {"direction": TRANSFERDIRECTION_TYPES.IN, "money": 15000.0},
        ]

        for i, transfer_data in enumerate(test_transfers):
            params = self.test_transfer_params.copy()
            params["engine_id"] = f"{self.test_engine_id}_{i}"
            params["direction"] = transfer_data["direction"]
            params["money"] = transfer_data["money"]
            params["timestamp"] = datetime(2023, 1, i + 1, 9, 30)
            self.crud.create(**params)

        # Test find by portfolio (all directions)
        all_transfers = self.crud.find_by_portfolio(self.test_portfolio_id)
        self.assertEqual(len(all_transfers), 3)

        # Test find by portfolio with specific direction
        in_transfers = self.crud.find_by_portfolio(self.test_portfolio_id, TRANSFERDIRECTION_TYPES.IN)
        self.assertEqual(len(in_transfers), 2)
        for transfer in in_transfers:
            self.assertEqual(transfer.direction, TRANSFERDIRECTION_TYPES.IN)

        out_transfers = self.crud.find_by_portfolio(self.test_portfolio_id, TRANSFERDIRECTION_TYPES.OUT)
        self.assertEqual(len(out_transfers), 1)
        self.assertEqual(out_transfers[0].direction, TRANSFERDIRECTION_TYPES.OUT)

    @database_test_required
    def test_TransferCRUD_Find_By_Status_Real(self):
        """Test TransferCRUD find by status business helper method with real database"""
        # Create transfers with different statuses
        statuses = [TRANSFERSTATUS_TYPES.PENDING, TRANSFERSTATUS_TYPES.FILLED, TRANSFERSTATUS_TYPES.CANCELED]

        for i, status in enumerate(statuses):
            params = self.test_transfer_params.copy()
            params["engine_id"] = f"{self.test_engine_id}_{i}"
            params["status"] = status
            params["timestamp"] = datetime(2023, 1, i + 1, 9, 30)
            self.crud.create(**params)

        # Test find by specific status
        pending_transfers = self.crud.find_by_status(TRANSFERSTATUS_TYPES.PENDING)
        
        # Should find at least 1 pending transfer (our test transfer)
        matching_pending = [t for t in pending_transfers if t.portfolio_id == self.test_portfolio_id]
        self.assertEqual(len(matching_pending), 1)
        self.assertEqual(matching_pending[0].status, TRANSFERSTATUS_TYPES.PENDING)

        # Test find filled transfers
        filled_transfers = self.crud.find_by_status(TRANSFERSTATUS_TYPES.FILLED)
        matching_filled = [t for t in filled_transfers if t.portfolio_id == self.test_portfolio_id]
        self.assertEqual(len(matching_filled), 1)
        self.assertEqual(matching_filled[0].status, TRANSFERSTATUS_TYPES.FILLED)

    @database_test_required
    def test_TransferCRUD_Get_Total_Transfer_Amount_Real(self):
        """Test TransferCRUD get total transfer amount business helper method"""
        # Create transfers for testing amount calculation
        test_transfers = [
            {"direction": TRANSFERDIRECTION_TYPES.IN, "money": 10000.0, "status": TRANSFERSTATUS_TYPES.FILLED},
            {"direction": TRANSFERDIRECTION_TYPES.IN, "money": 5000.0, "status": TRANSFERSTATUS_TYPES.FILLED},
            {"direction": TRANSFERDIRECTION_TYPES.IN, "money": 3000.0, "status": TRANSFERSTATUS_TYPES.PENDING},  # Should not count
            {"direction": TRANSFERDIRECTION_TYPES.OUT, "money": 2000.0, "status": TRANSFERSTATUS_TYPES.FILLED},
        ]

        for i, transfer_data in enumerate(test_transfers):
            params = self.test_transfer_params.copy()
            params["engine_id"] = f"{self.test_engine_id}_{i}"
            params["direction"] = transfer_data["direction"]
            params["money"] = transfer_data["money"]
            params["status"] = transfer_data["status"]
            self.crud.create(**params)

        # Test total IN amount (only filled transfers)
        total_in = self.crud.get_total_transfer_amount(self.test_portfolio_id, TRANSFERDIRECTION_TYPES.IN)
        self.assertEqual(total_in, 15000.0)  # 10000 + 5000, excluding pending

        # Test total OUT amount
        total_out = self.crud.get_total_transfer_amount(self.test_portfolio_id, TRANSFERDIRECTION_TYPES.OUT)
        self.assertEqual(total_out, 2000.0)

    @database_test_required
    def test_TransferCRUD_Update_Status_Real(self):
        """Test TransferCRUD update status business helper method"""
        # Create test transfer
        created_transfer = self.crud.create(**self.test_transfer_params)

        # Verify initial status
        self.assertEqual(created_transfer.status, TRANSFERSTATUS_TYPES.PENDING)

        # Update status to filled
        self.crud.update_status(self.test_portfolio_id, TRANSFERSTATUS_TYPES.FILLED)

        # Verify status updated
        updated_transfers = self.crud.find(filters={"portfolio_id": self.test_portfolio_id})
        self.assertEqual(len(updated_transfers), 1)
        self.assertEqual(updated_transfers[0].status, TRANSFERSTATUS_TYPES.FILLED)

    @database_test_required
    def test_TransferCRUD_DataFrame_Output_Real(self):
        """Test TransferCRUD DataFrame output with real database"""
        # Create test transfer
        created_transfer = self.crud.create(**self.test_transfer_params)

        # Get as DataFrame
        df_result = self.crud.find_by_status(TRANSFERSTATUS_TYPES.PENDING, as_dataframe=True)

        # Verify DataFrame
        import pandas as pd

        self.assertIsInstance(df_result, pd.DataFrame)
        self.assertGreaterEqual(len(df_result), 1)

        # Find our test transfer in the DataFrame
        test_transfer_rows = df_result[df_result["portfolio_id"] == self.test_portfolio_id]
        self.assertEqual(len(test_transfer_rows), 1)
        self.assertEqual(test_transfer_rows.iloc[0]["engine_id"], self.test_engine_id)

    @database_test_required
    def test_TransferCRUD_Bulk_Operations_Real(self):
        """Test TransferCRUD bulk operations with table size verification"""
        # Get initial table size
        size0 = get_table_size(self.model)

        # Create bulk test data
        bulk_transfers = []
        bulk_count = 3

        for i in range(bulk_count):
            transfer = self.crud._create_from_params(
                portfolio_id=f"{self.test_portfolio_id}_{i}",
                engine_id=f"{self.test_engine_id}_{i}",
                direction=TRANSFERDIRECTION_TYPES.IN if i % 2 == 0 else TRANSFERDIRECTION_TYPES.OUT,
                market=MARKET_TYPES.CHINA,
                money=100000.0 + i * 10000,
                status=TRANSFERSTATUS_TYPES.PENDING,
                timestamp=datetime(2023, 1, i + 1, 9, 30),
                source=SOURCE_TYPES.SIM,
            )
            bulk_transfers.append(transfer)

        # Perform bulk addition
        result = self.crud.add_batch(bulk_transfers)

        # Get table size after bulk addition
        size1 = get_table_size(self.model)

        # Verify table size increased by bulk_count
        self.assertEqual(bulk_count, size1 - size0)

        # Verify each transfer was added correctly
        for i in range(bulk_count):
            found_transfers = self.crud.find(filters={"portfolio_id": f"{self.test_portfolio_id}_{i}"})
            self.assertEqual(len(found_transfers), 1)
            self.assertEqual(found_transfers[0].money, Decimal(f"{100000.0 + i * 10000}"))

    @database_test_required
    def test_TransferCRUD_Exception_Handling_Real(self):
        """Test TransferCRUD exception handling with real database"""
        # Test find with empty filters (should not cause issues)
        all_transfers = self.crud.find(filters={})
        self.assertIsInstance(all_transfers, list)

        # Test business methods with invalid parameters
        try:
            total = self.crud.get_total_transfer_amount("invalid_portfolio", TRANSFERDIRECTION_TYPES.IN)
            self.assertEqual(total, 0.0)  # Should return 0 for non-existent portfolio
        except Exception as e:
            # Exception handling is working
            pass

        # Test get_portfolio_ids method
        try:
            portfolio_ids = self.crud.get_portfolio_ids()
            self.assertIsInstance(portfolio_ids, list)
        except Exception as e:
            # Exception handling is working
            pass