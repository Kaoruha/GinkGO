import unittest
import sys
import os
import uuid
from decimal import Decimal
from datetime import datetime
from sqlalchemy import text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

try:
    from ginkgo.data.crud.transfer_record_crud import TransferRecordCRUD
    from ginkgo.data.models import MTransferRecord
    from ginkgo.backtest import Transfer
    from ginkgo.enums import (
        MARKET_TYPES,
        SOURCE_TYPES,
        TRANSFERDIRECTION_TYPES,
        TRANSFERSTATUS_TYPES,
    )
    from ginkgo.libs import GCONF, datetime_normalize, to_decimal
    from ginkgo.data.drivers import get_db_connection, get_table_size, create_table, drop_table
    from ginkgo.data.crud.validation import ValidationError
except ImportError as e:
    print(f"Import error: {e}")
    TransferRecordCRUD = None
    GCONF = None


class TransferRecordCRUDTest(unittest.TestCase):
    """
    TransferRecordCRUD database integration tests.
    Tests TransferRecord-specific CRUD operations with actual database.
    """

    @classmethod
    def setUpClass(cls):
        """Class-level setup: check database configuration and connection"""
        if TransferRecordCRUD is None or GCONF is None:
            raise AssertionError("TransferRecordCRUD or GCONF not available")

        # Set model for table size verification
        cls.model = MTransferRecord

        # Recreate table for clean testing
        try:
            drop_table(cls.model, no_skip=True)
            create_table(cls.model, no_skip=True)
            print(":white_check_mark: TransferRecord table recreated for testing")
        except Exception as e:
            print(f":warning: TransferRecord table recreation failed: {e}")

        # Verify ClickHouse database configuration (MTransferRecord uses ClickHouse)
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

        # Create TransferRecordCRUD instance
        cls.crud = TransferRecordCRUD()

        # Test database connection
        try:
            connection = get_db_connection(MTransferRecord)
            with connection.get_session() as session:
                session.execute(text("SELECT 1"))
            print(":white_check_mark: TransferRecord database connection successful")
        except Exception as e:
            raise AssertionError(f"Database connection failed: {e}")

    def setUp(self):
        """Setup for each test: prepare unique test data"""
        self.test_id = str(uuid.uuid4())[:8]
        self.test_portfolio_id = f"PORTFOLIO{self.test_id}"
        self.test_engine_id = f"ENGINE{self.test_id}"
        self.test_timestamp = datetime(2023, 6, 15, 14, 30, 0)

        # Test transfer record data based on actual MTransferRecord fields
        self.test_transfer_record_params = {
            "portfolio_id": self.test_portfolio_id,
            "direction": TRANSFERDIRECTION_TYPES.IN,
            "market": MARKET_TYPES.CHINA,
            "money": to_decimal(1000.50),
            "status": TRANSFERSTATUS_TYPES.FILLED,
            "timestamp": self.test_timestamp,
            "source": SOURCE_TYPES.SIM,
        }

    def tearDown(self):
        """Cleanup after each test"""
        try:
            # Single pattern cleanup for all test data
            self.crud.remove({"portfolio_id__like": f"PORTFOLIO{self.test_id}%"})
        except Exception as e:
            print(f":warning: Cleanup failed: {e}")

    @classmethod
    def tearDownClass(cls):
        """Class-level cleanup: remove any remaining test data"""
        try:
            # Final cleanup of any remaining test records
            cls.crud.remove({"portfolio_id__like": "PORTFOLIO%"})
            print(":broom: Final cleanup of all PORTFOLIO records completed")
        except Exception as e:
            print(f":warning: Final cleanup failed: {e}")

    def test_TransferRecordCRUD_Create_From_Params_Real(self):
        """Test TransferRecordCRUD create from parameters with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create transfer record from parameters
        created_transfer_record = self.crud.create(**self.test_transfer_record_params)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify creation
        self.assertIsNotNone(created_transfer_record)
        self.assertIsInstance(created_transfer_record, MTransferRecord)
        self.assertEqual(created_transfer_record.portfolio_id, self.test_portfolio_id)
        self.assertEqual(created_transfer_record.direction, TRANSFERDIRECTION_TYPES.IN)
        self.assertEqual(created_transfer_record.market, MARKET_TYPES.CHINA)
        self.assertEqual(created_transfer_record.money, to_decimal(1000.50))
        self.assertEqual(created_transfer_record.status, TRANSFERSTATUS_TYPES.FILLED)
        self.assertEqual(created_transfer_record.source, SOURCE_TYPES.SIM)

        # Verify in database
        found_records = self.crud.find(filters={"portfolio_id": self.test_portfolio_id})
        self.assertEqual(len(found_records), 1)
        self.assertEqual(found_records[0].portfolio_id, self.test_portfolio_id)

    def test_TransferRecordCRUD_Add_Transfer_Object_Real(self):
        """Test TransferRecordCRUD add Transfer object with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create Transfer object
        transfer = Transfer(
            portfolio_id=f"{self.test_portfolio_id}_obj",
            engine_id=self.test_engine_id,
            direction=TRANSFERDIRECTION_TYPES.OUT,
            market=MARKET_TYPES.NASDAQ,
            money=500.25,
            status=TRANSFERSTATUS_TYPES.CANCELED,
            timestamp=self.test_timestamp,
        )

        # Convert Transfer to MTransferRecord and add
        mtransfer_record = self.crud._convert_input_item(transfer)
        added_record = self.crud.add(mtransfer_record)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify addition
        self.assertIsNotNone(added_record)
        self.assertEqual(added_record.portfolio_id, f"{self.test_portfolio_id}_obj")
        self.assertEqual(added_record.direction, TRANSFERDIRECTION_TYPES.OUT)
        self.assertEqual(added_record.market, MARKET_TYPES.NASDAQ)
        self.assertEqual(added_record.money, to_decimal(500.25))
        self.assertEqual(added_record.status, TRANSFERSTATUS_TYPES.CANCELED)

        # Verify in database
        found_records = self.crud.find(filters={"portfolio_id": f"{self.test_portfolio_id}_obj"})
        self.assertEqual(len(found_records), 1)

    def test_TransferRecordCRUD_Add_Batch_Real(self):
        """Test TransferRecordCRUD batch addition with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create multiple transfer record objects
        records = []
        batch_count = 3
        directions = [TRANSFERDIRECTION_TYPES.IN, TRANSFERDIRECTION_TYPES.OUT, TRANSFERDIRECTION_TYPES.IN]
        amounts = [1000, 500, 1500]

        for i in range(batch_count):
            record = self.crud._create_from_params(
                portfolio_id=f"{self.test_portfolio_id}_batch_{i}",
                direction=directions[i],
                market=MARKET_TYPES.CHINA,
                money=to_decimal(amounts[i]),
                status=TRANSFERSTATUS_TYPES.FILLED,
                timestamp=datetime(2023, 6, 15 + i, 10, 0, 0),
                source=SOURCE_TYPES.SIM,
            )
            records.append(record)

        # Add batch
        result = self.crud.add_batch(records)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by batch count
        self.assertEqual(batch_count, size1 - size0)

        # Verify batch addition
        self.assertIsInstance(result, tuple)

        # Verify each record in database
        for i in range(batch_count):
            found_records = self.crud.find(filters={"portfolio_id": f"{self.test_portfolio_id}_batch_{i}"})
            self.assertEqual(len(found_records), 1)
            self.assertEqual(found_records[0].direction, directions[i])
            self.assertEqual(found_records[0].money, to_decimal(amounts[i]))

    def test_TransferRecordCRUD_Find_By_Portfolio_Real(self):
        """Test TransferRecordCRUD find by portfolio business helper method with real database"""
        # Create test records with different directions and statuses
        test_records = [
            {"direction": TRANSFERDIRECTION_TYPES.IN, "status": TRANSFERSTATUS_TYPES.FILLED, "money": 1000},
            {"direction": TRANSFERDIRECTION_TYPES.OUT, "status": TRANSFERSTATUS_TYPES.FILLED, "money": 500},
            {"direction": TRANSFERDIRECTION_TYPES.IN, "status": TRANSFERSTATUS_TYPES.CANCELED, "money": 300},
        ]

        for i, record_data in enumerate(test_records):
            params = self.test_transfer_record_params.copy()
            params["portfolio_id"] = self.test_portfolio_id  # Same portfolio for all
            params["direction"] = record_data["direction"]
            params["status"] = record_data["status"]
            params["money"] = to_decimal(record_data["money"])
            params["timestamp"] = datetime(2023, 6, 15 + i, 10, 0, 0)
            self.crud.create(**params)

        # Test find by portfolio (all records)
        all_records = self.crud.find_by_portfolio(self.test_portfolio_id)
        self.assertEqual(len(all_records), 3)

        # Test find by portfolio and direction
        in_records = self.crud.find_by_portfolio(self.test_portfolio_id, direction=TRANSFERDIRECTION_TYPES.IN)
        self.assertEqual(len(in_records), 2)  # 2 IN records

        # Test find by portfolio and status
        filled_records = self.crud.find_by_portfolio(self.test_portfolio_id, status=TRANSFERSTATUS_TYPES.FILLED)
        self.assertEqual(len(filled_records), 2)  # 2 FILLED records

        # Test find with date range
        date_records = self.crud.find_by_portfolio(
            self.test_portfolio_id,
            start_date=datetime(2023, 6, 16),
            end_date=datetime(2023, 6, 18)  # Next day to include full June 17
        )
        self.assertEqual(len(date_records), 2)  # Records from June 16-17

    def test_TransferRecordCRUD_Get_Total_Transfer_Amount_Real(self):
        """Test TransferRecordCRUD get total transfer amount business helper method with real database"""
        # Create test records with different directions and statuses
        test_records = [
            {"direction": TRANSFERDIRECTION_TYPES.IN, "status": TRANSFERSTATUS_TYPES.FILLED, "money": 1000},
            {"direction": TRANSFERDIRECTION_TYPES.IN, "status": TRANSFERSTATUS_TYPES.FILLED, "money": 500},
            {"direction": TRANSFERDIRECTION_TYPES.IN, "status": TRANSFERSTATUS_TYPES.CANCELED, "money": 300},  # Should be ignored
            {"direction": TRANSFERDIRECTION_TYPES.OUT, "status": TRANSFERSTATUS_TYPES.FILLED, "money": 200},
        ]

        for i, record_data in enumerate(test_records):
            params = self.test_transfer_record_params.copy()
            params["portfolio_id"] = self.test_portfolio_id
            params["direction"] = record_data["direction"]
            params["status"] = record_data["status"]
            params["money"] = to_decimal(record_data["money"])
            params["timestamp"] = datetime(2023, 6, 15 + i, 10, 0, 0)
            self.crud.create(**params)

        # Test get total IN amount (should be 1000 + 500 = 1500, excluding canceled)
        total_in = self.crud.get_total_transfer_amount(self.test_portfolio_id, TRANSFERDIRECTION_TYPES.IN)
        self.assertEqual(total_in, 1500.0)

        # Test get total OUT amount
        total_out = self.crud.get_total_transfer_amount(self.test_portfolio_id, TRANSFERDIRECTION_TYPES.OUT)
        self.assertEqual(total_out, 200.0)

        # Test get total with date range
        total_range = self.crud.get_total_transfer_amount(
            self.test_portfolio_id,
            TRANSFERDIRECTION_TYPES.IN,
            start_date=datetime(2023, 6, 16),
            end_date=datetime(2023, 6, 17)  # Only include June 16 (Record 1: 500)
        )
        self.assertEqual(total_range, 500.0)  # Only the 500 record from June 16

    def test_TransferRecordCRUD_Get_Portfolio_Ids_Real(self):
        """Test TransferRecordCRUD get portfolio IDs business helper method with real database"""
        # Create test records with different portfolio IDs
        portfolio_ids = [f"{self.test_portfolio_id}_1", f"{self.test_portfolio_id}_2", f"{self.test_portfolio_id}_3"]

        for portfolio_id in portfolio_ids:
            params = self.test_transfer_record_params.copy()
            params["portfolio_id"] = portfolio_id
            self.crud.create(**params)

        # Get all portfolio IDs
        all_portfolio_ids = self.crud.get_portfolio_ids()

        # Verify our test portfolio IDs are included
        for test_portfolio_id in portfolio_ids:
            self.assertIn(test_portfolio_id, all_portfolio_ids)

        # Should be at least 3 (our test records)
        test_portfolio_count = len([pid for pid in all_portfolio_ids if pid.startswith(f"{self.test_portfolio_id}_")])
        self.assertGreaterEqual(test_portfolio_count, 3)

    def test_TransferRecordCRUD_Transfer_Object_Conversion_Real(self):
        """Test TransferRecordCRUD Transfer object conversion with real database"""
        # Create test record
        created_record = self.crud.create(**self.test_transfer_record_params)

        # Find with Transfer output type
        transfer_objects = self.crud.find(
            filters={"portfolio_id": self.test_portfolio_id},
            output_type="transfer"
        )

        # Verify conversion
        self.assertEqual(len(transfer_objects), 1)
        transfer = transfer_objects[0]
        self.assertIsInstance(transfer, Transfer)
        self.assertEqual(transfer.portfolio_id, self.test_portfolio_id)
        self.assertEqual(transfer.direction, TRANSFERDIRECTION_TYPES.IN)
        self.assertEqual(transfer.market, MARKET_TYPES.CHINA)
        self.assertEqual(transfer.money, Decimal("1000.50"))
        self.assertEqual(transfer.status, TRANSFERSTATUS_TYPES.FILLED)

    def test_TransferRecordCRUD_DataFrame_Output_Real(self):
        """Test TransferRecordCRUD DataFrame output with real database"""
        # Create test record
        created_record = self.crud.create(**self.test_transfer_record_params)

        # Get as DataFrame
        df_result = self.crud.find_by_portfolio(self.test_portfolio_id, as_dataframe=True)

        # Verify DataFrame
        import pandas as pd

        self.assertIsInstance(df_result, pd.DataFrame)
        self.assertEqual(len(df_result), 1)
        self.assertEqual(df_result.iloc[0]["portfolio_id"], self.test_portfolio_id)
        self.assertEqual(df_result.iloc[0]["direction"], TRANSFERDIRECTION_TYPES.IN)
        self.assertEqual(float(df_result.iloc[0]["money"]), 1000.50)

    def test_TransferRecordCRUD_Complex_Filters_Real(self):
        """Test TransferRecordCRUD complex filters with real database"""
        # Create records with different attributes
        test_data = [
            {"market": MARKET_TYPES.CHINA, "direction": TRANSFERDIRECTION_TYPES.IN, "status": TRANSFERSTATUS_TYPES.FILLED},
            {"market": MARKET_TYPES.NASDAQ, "direction": TRANSFERDIRECTION_TYPES.OUT, "status": TRANSFERSTATUS_TYPES.FILLED},
            {"market": MARKET_TYPES.CHINA, "direction": TRANSFERDIRECTION_TYPES.IN, "status": TRANSFERSTATUS_TYPES.CANCELED},
            {"market": MARKET_TYPES.OTHER, "direction": TRANSFERDIRECTION_TYPES.OUT, "status": TRANSFERSTATUS_TYPES.FILLED},
        ]

        for i, data in enumerate(test_data):
            params = self.test_transfer_record_params.copy()
            params["portfolio_id"] = f"{self.test_portfolio_id}_complex_{i}"
            params["market"] = data["market"]
            params["direction"] = data["direction"]
            params["status"] = data["status"]
            self.crud.create(**params)

        # Test combined filters
        china_in_records = self.crud.find(
            filters={
                "portfolio_id__like": f"{self.test_portfolio_id}_complex_%",
                "market": MARKET_TYPES.CHINA,
                "direction": TRANSFERDIRECTION_TYPES.IN
            }
        )

        # Should find 2 records (both CHINA IN, regardless of status)
        self.assertEqual(len(china_in_records), 2)
        for record in china_in_records:
            self.assertEqual(record.market, MARKET_TYPES.CHINA)
            self.assertEqual(record.direction, TRANSFERDIRECTION_TYPES.IN)

        # Test IN operator for markets
        multi_market_records = self.crud.find(
            filters={
                "portfolio_id__like": f"{self.test_portfolio_id}_complex_%",
                "market__in": [MARKET_TYPES.NASDAQ, MARKET_TYPES.OTHER]
            }
        )

        # Should find 2 records (NASDAQ and OTHER)
        self.assertEqual(len(multi_market_records), 2)
        markets = [r.market for r in multi_market_records]
        self.assertIn(MARKET_TYPES.NASDAQ, markets)
        self.assertIn(MARKET_TYPES.OTHER, markets)

    def test_TransferRecordCRUD_Exists_Real(self):
        """Test TransferRecordCRUD exists functionality with real database"""
        # Test non-existent record
        exists_before = self.crud.exists(filters={"portfolio_id": self.test_portfolio_id})
        self.assertFalse(exists_before)

        # Create test record
        created_record = self.crud.create(**self.test_transfer_record_params)

        # Test existing record
        exists_after = self.crud.exists(filters={"portfolio_id": self.test_portfolio_id})
        self.assertTrue(exists_after)

        # Test with more specific filters
        exists_specific = self.crud.exists(
            filters={
                "portfolio_id": self.test_portfolio_id,
                "direction": TRANSFERDIRECTION_TYPES.IN,
                "status": TRANSFERSTATUS_TYPES.FILLED,
            }
        )
        self.assertTrue(exists_specific)

        # Test with non-matching filters
        exists_false = self.crud.exists(
            filters={
                "portfolio_id": self.test_portfolio_id,
                "direction": TRANSFERDIRECTION_TYPES.OUT
            }
        )
        self.assertFalse(exists_false)

    def test_TransferRecordCRUD_Bulk_Operations_With_Size_Verification_Real(self):
        """Test TransferRecordCRUD bulk operations with table size verification"""
        # Get initial table size
        size0 = get_table_size(self.model)

        # Create bulk test data
        bulk_records = []
        bulk_count = 4
        directions = [TRANSFERDIRECTION_TYPES.IN, TRANSFERDIRECTION_TYPES.OUT,
                     TRANSFERDIRECTION_TYPES.IN, TRANSFERDIRECTION_TYPES.OUT]
        amounts = [1000, 500, 1500, 750]

        for i in range(bulk_count):
            record = self.crud._create_from_params(
                portfolio_id=f"{self.test_portfolio_id}_bulk_{i}",
                direction=directions[i],
                market=MARKET_TYPES.CHINA,
                money=to_decimal(amounts[i]),
                status=TRANSFERSTATUS_TYPES.FILLED,
                timestamp=datetime(2023, 6, 15 + i, 10, 0, 0),
                source=SOURCE_TYPES.SIM,
            )
            bulk_records.append(record)

        # Perform bulk addition
        result = self.crud.add_batch(bulk_records)

        # Get table size after bulk addition
        size1 = get_table_size(self.model)

        # Verify table size increased by bulk_count
        self.assertEqual(bulk_count, size1 - size0)

        # Verify each record was added correctly
        for i in range(bulk_count):
            found_records = self.crud.find(filters={"portfolio_id": f"{self.test_portfolio_id}_bulk_{i}"})
            self.assertEqual(len(found_records), 1)
            self.assertEqual(found_records[0].direction, directions[i])
            self.assertEqual(found_records[0].money, to_decimal(amounts[i]))

        # Bulk delete test records
        self.crud.remove({"portfolio_id__like": f"{self.test_portfolio_id}_bulk_%"})

        # Get final table size
        size2 = get_table_size(self.model)

        # Verify table size returned to original
        self.assertEqual(size2, size0)

    def test_TransferRecordCRUD_Decimal_Precision_Real(self):
        """Test TransferRecordCRUD decimal precision handling with real database"""
        # Test with high-precision decimal values (all must be >= 0.01)
        precision_amounts = [
            Decimal("1000.12"),    # Standard amount
            Decimal("0.01"),       # Minimum valid amount
            Decimal("999999.99"),  # Large amount
            Decimal("0.12"),       # Small valid amount
        ]

        for i, amount in enumerate(precision_amounts):
            params = self.test_transfer_record_params.copy()
            params["portfolio_id"] = f"{self.test_portfolio_id}_precision_{i}"
            params["money"] = amount

            created_record = self.crud.create(**params)

            # Verify precision is maintained
            self.assertEqual(created_record.money, amount)

            # Verify in database
            found_records = self.crud.find(filters={"portfolio_id": f"{self.test_portfolio_id}_precision_{i}"})
            self.assertEqual(len(found_records), 1)
            self.assertEqual(found_records[0].money, amount)

    def test_TransferRecordCRUD_Timestamp_Handling_Real(self):
        """Test TransferRecordCRUD timestamp normalization with real database"""
        # Test with different timestamp formats
        timestamps = [
            datetime(2023, 1, 1, 10, 0, 0),
            "2023-06-15 14:30:00",
            "2023-12-31T23:59:59",
        ]

        for i, timestamp in enumerate(timestamps):
            params = self.test_transfer_record_params.copy()
            params["portfolio_id"] = f"{self.test_portfolio_id}_timestamp_{i}"
            params["timestamp"] = timestamp

            created_record = self.crud.create(**params)

            # Verify timestamp is normalized to datetime
            self.assertIsInstance(created_record.timestamp, datetime)

            # Verify in database
            found_records = self.crud.find(filters={"portfolio_id": f"{self.test_portfolio_id}_timestamp_{i}"})
            self.assertEqual(len(found_records), 1)
            self.assertIsInstance(found_records[0].timestamp, datetime)

    def test_TransferRecordCRUD_Exception_Handling_Real(self):
        """Test TransferRecordCRUD exception handling with real database"""
        # Test find with empty filters (should not cause issues)
        all_records = self.crud.find(filters={})
        self.assertIsInstance(all_records, list)

        # Test remove with overly broad filters (should be safe)
        self.crud.remove({})  # Should be safely handled without affecting other tests

        # Test create with required parameters only
        required_params = {
            "portfolio_id": f"{self.test_portfolio_id}_minimal",
            "direction": TRANSFERDIRECTION_TYPES.IN,  # Required field
            "market": MARKET_TYPES.CHINA,  # Required field
            "money": 100.0,  # Required field (must be >= 0.01)
            "status": TRANSFERSTATUS_TYPES.PENDING,  # Required field
            "timestamp": self.test_timestamp,  # Required field
            "source": SOURCE_TYPES.SIM
        }

        try:
            minimal_record = self.crud.create(**required_params)
            self.assertIsNotNone(minimal_record)
            self.assertEqual(minimal_record.portfolio_id, f"{self.test_portfolio_id}_minimal")
            # Verify required fields are set correctly
            self.assertEqual(minimal_record.direction, TRANSFERDIRECTION_TYPES.IN)
            self.assertEqual(minimal_record.market, MARKET_TYPES.CHINA)
            self.assertEqual(minimal_record.status, TRANSFERSTATUS_TYPES.PENDING)
            self.assertEqual(minimal_record.money, Decimal("100.0"))
            self.assertEqual(minimal_record.source, SOURCE_TYPES.SIM)
        except Exception as e:
            self.fail(f"Creating record with required parameters should not fail: {e}")

    def test_TransferRecordCRUD_Business_Logic_Integration_Real(self):
        """Test TransferRecordCRUD business logic integration with real database"""
        # Create a realistic transfer scenario: deposit, withdraw, failed deposit
        scenarios = [
            {"direction": TRANSFERDIRECTION_TYPES.IN, "status": TRANSFERSTATUS_TYPES.FILLED, "money": 5000, "desc": "Initial deposit"},
            {"direction": TRANSFERDIRECTION_TYPES.OUT, "status": TRANSFERSTATUS_TYPES.FILLED, "money": 1500, "desc": "Withdrawal"},
            {"direction": TRANSFERDIRECTION_TYPES.IN, "status": TRANSFERSTATUS_TYPES.CANCELED, "money": 2000, "desc": "Failed deposit"},
            {"direction": TRANSFERDIRECTION_TYPES.OUT, "status": TRANSFERSTATUS_TYPES.FILLED, "money": 500, "desc": "Small withdrawal"},
        ]

        for i, scenario in enumerate(scenarios):
            params = self.test_transfer_record_params.copy()
            params["portfolio_id"] = self.test_portfolio_id  # Same portfolio for all
            params["direction"] = scenario["direction"]
            params["status"] = scenario["status"]
            params["money"] = to_decimal(scenario["money"])
            params["timestamp"] = datetime(2023, 6, 15 + i, 10, 0, 0)
            self.crud.create(**params)

        # Test business calculations
        total_deposits = self.crud.get_total_transfer_amount(
            self.test_portfolio_id, TRANSFERDIRECTION_TYPES.IN
        )
        self.assertEqual(total_deposits, 5000.0)  # Only successful deposits

        total_withdrawals = self.crud.get_total_transfer_amount(
            self.test_portfolio_id, TRANSFERDIRECTION_TYPES.OUT
        )
        self.assertEqual(total_withdrawals, 2000.0)  # 1500 + 500

        # Net flow should be 3000 (5000 in - 2000 out)
        net_flow = total_deposits - total_withdrawals
        self.assertEqual(net_flow, 3000.0)

        # Test finding all successful transfers
        successful_transfers = self.crud.find_by_portfolio(
            self.test_portfolio_id, status=TRANSFERSTATUS_TYPES.FILLED
        )
        self.assertEqual(len(successful_transfers), 3)  # Excluding the canceled one

        # Test finding transfers in date range
        recent_transfers = self.crud.find_by_portfolio(
            self.test_portfolio_id,
            start_date=datetime(2023, 6, 16),
            end_date=datetime(2023, 6, 19)  # Include full June 16-18
        )
        self.assertEqual(len(recent_transfers), 3)  # 3 transfers in this range

    def test_TransferRecordCRUD_ValidationError_Tests(self):
        """Test TransferRecordCRUD field validation functionality"""
        # Test empty portfolio_id
        with self.assertRaises(ValidationError):
            self.crud.create(
                portfolio_id="",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=100.0,
                status=TRANSFERSTATUS_TYPES.PENDING,
                timestamp=self.test_timestamp,
                source=SOURCE_TYPES.SIM
            )

        # Test invalid direction enum
        with self.assertRaises(ValidationError):
            self.crud.create(
                portfolio_id=self.test_portfolio_id,
                direction="INVALID_DIRECTION",
                market=MARKET_TYPES.CHINA,
                money=100.0,
                status=TRANSFERSTATUS_TYPES.PENDING,
                timestamp=self.test_timestamp,
                source=SOURCE_TYPES.SIM
            )

        # Test invalid market enum
        with self.assertRaises(ValidationError):
            self.crud.create(
                portfolio_id=self.test_portfolio_id,
                direction=TRANSFERDIRECTION_TYPES.IN,
                market="INVALID_MARKET",
                money=100.0,
                status=TRANSFERSTATUS_TYPES.PENDING,
                timestamp=self.test_timestamp,
                source=SOURCE_TYPES.SIM
            )

        # Test invalid money amount (too small)
        with self.assertRaises(ValidationError):
            self.crud.create(
                portfolio_id=self.test_portfolio_id,
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=0.005,  # Invalid: must be >= 0.01
                status=TRANSFERSTATUS_TYPES.PENDING,
                timestamp=self.test_timestamp,
                source=SOURCE_TYPES.SIM
            )

        # Test zero money amount
        with self.assertRaises(ValidationError):
            self.crud.create(
                portfolio_id=self.test_portfolio_id,
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=0,  # Invalid: must be >= 0.01
                status=TRANSFERSTATUS_TYPES.PENDING,
                timestamp=self.test_timestamp,
                source=SOURCE_TYPES.SIM
            )

        # Test invalid status enum
        with self.assertRaises(ValidationError):
            self.crud.create(
                portfolio_id=self.test_portfolio_id,
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=100.0,
                status="INVALID_STATUS",
                timestamp=self.test_timestamp,
                source=SOURCE_TYPES.SIM
            )

        # Test invalid source enum
        with self.assertRaises(ValidationError):
            self.crud.create(
                portfolio_id=self.test_portfolio_id,
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=100.0,
                status=TRANSFERSTATUS_TYPES.PENDING,
                timestamp=self.test_timestamp,
                source="INVALID_SOURCE"
            )
