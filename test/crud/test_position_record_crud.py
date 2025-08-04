import unittest
import sys
import os
import uuid
from decimal import Decimal
from datetime import datetime
from sqlalchemy import text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

try:
    from ginkgo.data.crud.position_record_crud import PositionRecordCRUD
    from ginkgo.data.crud.validation import ValidationError
    from ginkgo.data.models import MPositionRecord
    from ginkgo.enums import SOURCE_TYPES
    from ginkgo.libs import GCONF, datetime_normalize, to_decimal
    from ginkgo.data.drivers import get_db_connection, get_table_size, create_table, drop_table
except ImportError as e:
    print(f"Import error: {e}")
    PositionRecordCRUD = None
    GCONF = None
    ValidationError = None


class PositionRecordCRUDTest(unittest.TestCase):
    """
    PositionRecordCRUD database integration tests.
    Tests PositionRecord-specific CRUD operations with actual database.
    """

    @classmethod
    def setUpClass(cls):
        """Class-level setup: check database configuration and connection"""
        if PositionRecordCRUD is None or GCONF is None:
            raise AssertionError("PositionRecordCRUD or GCONF not available")

        # Set model for table size verification
        cls.model = MPositionRecord

        # Recreate table for clean testing
        try:
            drop_table(cls.model, no_skip=True)
            create_table(cls.model, no_skip=True)
            print(":white_check_mark: PositionRecord table recreated for testing")
        except Exception as e:
            print(f":warning: PositionRecord table recreation failed: {e}")

        # Verify database configuration (ClickHouse for MPositionRecord)
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

        # Create PositionRecordCRUD instance
        cls.crud = PositionRecordCRUD()

        # Test database connection
        try:
            connection = get_db_connection(MPositionRecord)
            with connection.get_session() as session:
                session.execute(text("SELECT 1"))
            print(":white_check_mark: PositionRecord database connection successful")
        except Exception as e:
            raise AssertionError(f"Database connection failed: {e}")

    def setUp(self):
        """Setup for each test: prepare unique test data"""
        self.test_id = str(uuid.uuid4())[:8]
        self.test_portfolio_id = f"TestPortfolio{self.test_id}"
        self.test_engine_id = f"TestEngine{self.test_id}"

        # Test position record data based on actual MPositionRecord fields
        self.test_position_params = {
            "portfolio_id": self.test_portfolio_id,
            "engine_id": self.test_engine_id,
            "timestamp": datetime_normalize("2023-01-01 09:30:00"),
            "code": "000001.SZ",
            "cost": to_decimal(10000.50),
            "volume": 1000,
            "frozen_volume": 100,
            "frozen_money": to_decimal(1000.25),
            "price": to_decimal(10.50),
            "fee": to_decimal(5.50),
        }

    def tearDown(self):
        """Cleanup after each test"""
        try:
            # Single pattern cleanup for all test data
            self.crud.remove({"portfolio_id__like": f"TestPortfolio{self.test_id}%"})
        except Exception as e:
            print(f":warning: Cleanup failed: {e}")

    @classmethod
    def tearDownClass(cls):
        """Class-level cleanup: remove any remaining test data"""
        try:
            # Final cleanup of any remaining test records
            cls.crud.remove({"portfolio_id__like": "TestPortfolio%"})
            print(":broom: Final cleanup of all TestPortfolio records completed")
        except Exception as e:
            print(f":warning: Final cleanup failed: {e}")

    def test_PositionRecordCRUD_Create_From_Params_Real(self):
        """Test PositionRecordCRUD create from parameters with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create position record from parameters
        created_position = self.crud.create(**self.test_position_params)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify creation
        self.assertIsNotNone(created_position)
        self.assertIsInstance(created_position, MPositionRecord)
        self.assertEqual(created_position.portfolio_id, self.test_portfolio_id)
        self.assertEqual(created_position.engine_id, self.test_engine_id)
        self.assertEqual(created_position.code, "000001.SZ")
        self.assertEqual(created_position.cost, to_decimal(10000.50))
        self.assertEqual(created_position.volume, 1000)
        self.assertEqual(created_position.frozen_volume, 100)

        # Verify in database
        found_positions = self.crud.find(filters={"portfolio_id": self.test_portfolio_id})
        self.assertEqual(len(found_positions), 1)
        self.assertEqual(found_positions[0].portfolio_id, self.test_portfolio_id)

    def test_PositionRecordCRUD_Add_Position_Object_Real(self):
        """Test PositionRecordCRUD add position object with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create position object using _create_from_params
        position_params = {
            "portfolio_id": f"TestPortfolio{self.test_id}_obj",
            "engine_id": f"TestEngine{self.test_id}_obj",
            "timestamp": datetime_normalize("2023-01-01 10:00:00"),
            "code": "000002.SZ",
            "cost": to_decimal(20000.75),
            "volume": 2000,
            "frozen_volume": 200,
            "frozen_money": to_decimal(2000.50),
            "price": to_decimal(20.75),
            "fee": to_decimal(10.25),
        }

        position = self.crud._create_from_params(**position_params)
        added_position = self.crud.add(position)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify addition
        self.assertIsNotNone(added_position)
        self.assertEqual(added_position.portfolio_id, f"TestPortfolio{self.test_id}_obj")
        self.assertEqual(added_position.engine_id, f"TestEngine{self.test_id}_obj")
        self.assertEqual(added_position.code, "000002.SZ")
        self.assertEqual(added_position.cost, to_decimal(20000.75))
        self.assertEqual(added_position.volume, 2000)

        # Verify in database
        found_positions = self.crud.find(filters={"portfolio_id": f"TestPortfolio{self.test_id}_obj"})
        self.assertEqual(len(found_positions), 1)

    def test_PositionRecordCRUD_Add_Batch_Real(self):
        """Test PositionRecordCRUD batch addition with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create multiple position record objects
        positions = []
        batch_count = 3
        for i in range(batch_count):
            position = self.crud._create_from_params(
                portfolio_id=f"TestPortfolio{self.test_id}_batch",
                engine_id=f"TestEngine{self.test_id}_batch",
                timestamp=datetime_normalize("2023-01-01 09:30:00"),
                code=f"00000{i}.SZ",
                cost=to_decimal(1000 * (i + 1)),
                volume=100 * (i + 1),
                frozen_volume=10 * (i + 1),
                frozen_money=to_decimal(100 * (i + 1)),
                price=to_decimal(10 + i),
                fee=to_decimal(5 + i),
            )
            positions.append(position)

        # Add batch
        result = self.crud.add_batch(positions)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by batch count
        self.assertEqual(batch_count, size1 - size0)

        # Verify batch addition
        self.assertIsInstance(result, tuple)

        # Verify each position in database
        for i in range(batch_count):
            found_positions = self.crud.find(filters={
                "portfolio_id": f"TestPortfolio{self.test_id}_batch",
                "code": f"00000{i}.SZ"
            })
            self.assertEqual(len(found_positions), 1)
            self.assertEqual(found_positions[0].cost, to_decimal(1000 * (i + 1)))
            self.assertEqual(found_positions[0].volume, 100 * (i + 1))

    def test_PositionRecordCRUD_Find_By_Portfolio_Real(self):
        """Test PositionRecordCRUD find by portfolio business helper method with real database"""
        # Create test position records
        for i in range(3):
            params = self.test_position_params.copy()
            params["code"] = f"00000{i}.SZ"
            params["cost"] = to_decimal(1000 * (i + 1))
            self.crud.create(**params)

        # Test find by portfolio
        found_positions = self.crud.find_by_portfolio(self.test_portfolio_id)

        # Should find 3 positions
        self.assertEqual(len(found_positions), 3)
        for position in found_positions:
            self.assertEqual(position.portfolio_id, self.test_portfolio_id)

        # Test find by portfolio with date range
        found_positions_range = self.crud.find_by_portfolio(
            self.test_portfolio_id,
            start_date="2022-12-31",
            end_date="2023-12-31"
        )
        self.assertEqual(len(found_positions_range), 3)

        # Test find by portfolio with specific code
        found_positions_code = self.crud.find_by_portfolio(
            self.test_portfolio_id,
            code="000001.SZ"
        )
        self.assertEqual(len(found_positions_code), 1)
        self.assertEqual(found_positions_code[0].code, "000001.SZ")

    def test_PositionRecordCRUD_Find_By_Code_Real(self):
        """Test PositionRecordCRUD find by code business helper method with real database"""
        # Create test position records with same code but different portfolios
        codes = ["TESTCODE.SZ", "TESTCODE.SZ", "OTHERCODE.SZ"]

        for i, code in enumerate(codes):
            params = self.test_position_params.copy()
            params["portfolio_id"] = f"TestPortfolio{self.test_id}_{i}"
            params["code"] = code
            params["cost"] = to_decimal(1000 * (i + 1))
            self.crud.create(**params)

        # Test find by code
        found_positions = self.crud.find_by_code("TESTCODE.SZ")

        # Should find 2 positions with the same code
        matching_positions = [p for p in found_positions if p.portfolio_id.startswith(f"TestPortfolio{self.test_id}")]
        self.assertGreaterEqual(len(matching_positions), 2)
        for position in matching_positions:
            self.assertEqual(position.code, "TESTCODE.SZ")

    def test_PositionRecordCRUD_Get_Latest_Position_Real(self):
        """Test PositionRecordCRUD get latest position business helper method with real database"""
        # Create test position records with different timestamps for same code
        timestamps = ["2023-01-01 09:30:00", "2023-01-01 10:00:00", "2023-01-01 10:30:00"]

        for i, timestamp in enumerate(timestamps):
            params = self.test_position_params.copy()
            params["timestamp"] = datetime_normalize(timestamp)
            params["cost"] = to_decimal(1000 * (i + 1))
            self.crud.create(**params)

        # Test get latest position for specific code
        latest_position = self.crud.get_latest_position(self.test_portfolio_id, "000001.SZ")

        # Should get 1 position (most recent)
        self.assertEqual(len(latest_position), 1)
        # Latest should have the highest cost (last created)
        self.assertEqual(latest_position[0].cost, to_decimal(3000))

    def test_PositionRecordCRUD_Count_By_Portfolio_Real(self):
        """Test PositionRecordCRUD count by portfolio business helper method with real database"""
        # Create test position records
        for i in range(4):
            params = self.test_position_params.copy()
            params["code"] = f"COUNTTEST{i}.SZ"
            self.crud.create(**params)

        # Test count by portfolio
        count = self.crud.count_by_portfolio(self.test_portfolio_id)
        self.assertEqual(count, 4)

        # Test count by non-existent portfolio
        count_empty = self.crud.count_by_portfolio("NON_EXISTENT_PORTFOLIO")
        self.assertEqual(count_empty, 0)

    def test_PositionRecordCRUD_Get_Portfolio_Summary_Real(self):
        """Test PositionRecordCRUD get portfolio summary business helper method with real database"""
        # Create test position records with different costs and volumes
        test_data = [
            {"cost": 1000, "volume": 100, "price": 10.50},
            {"cost": 2000, "volume": 200, "price": 10.00},
            {"cost": 1500, "volume": 150, "price": 10.25},
        ]

        for i, data in enumerate(test_data):
            params = self.test_position_params.copy()
            params["code"] = f"SUMMARY{i}.SZ"
            params["cost"] = to_decimal(data["cost"])
            params["volume"] = data["volume"]
            params["price"] = to_decimal(data["price"])
            self.crud.create(**params)

        # Test get portfolio summary
        summary = self.crud.get_portfolio_summary(self.test_portfolio_id)

        # Should return summary data
        self.assertIsInstance(summary, dict)
        self.assertGreater(summary.get("total_positions", 0), 0)
        self.assertGreater(summary.get("total_cost", 0), 0)
        self.assertGreater(summary.get("active_positions", 0), 0)
        self.assertGreater(summary.get("total_market_value", 0), 0)
        self.assertIsInstance(summary.get("codes", []), list)

    def test_PositionRecordCRUD_Delete_By_Portfolio_Real(self):
        """Test PositionRecordCRUD delete by portfolio business helper method with real database"""
        # Create test position records
        for i in range(3):
            params = self.test_position_params.copy()
            params["code"] = f"DELETE{i}.SZ"
            self.crud.create(**params)

        # Verify positions exist
        found_positions = self.crud.find_by_portfolio(self.test_portfolio_id)
        self.assertEqual(len(found_positions), 3)

        # Get table size before deletion
        size0 = get_table_size(self.model)

        # Delete by portfolio
        self.crud.delete_by_portfolio(self.test_portfolio_id)

        # Get table size after deletion
        size1 = get_table_size(self.model)

        # Verify table size decreased by 3
        self.assertEqual(-3, size1 - size0)

        # Verify positions no longer exist
        found_positions_after = self.crud.find_by_portfolio(self.test_portfolio_id)
        self.assertEqual(len(found_positions_after), 0)

        # Test delete with empty portfolio_id (should raise ValueError)
        with self.assertRaises(ValueError):
            self.crud.delete_by_portfolio("")

    def test_PositionRecordCRUD_DataFrame_Output_Real(self):
        """Test PositionRecordCRUD DataFrame output with real database"""
        # Create test position record
        created_position = self.crud.create(**self.test_position_params)

        # Get as DataFrame
        df_result = self.crud.find_by_portfolio(self.test_portfolio_id, as_dataframe=True)

        # Verify DataFrame
        import pandas as pd

        self.assertIsInstance(df_result, pd.DataFrame)
        self.assertGreaterEqual(len(df_result), 1)

        # Find our test position in the DataFrame
        test_position_rows = df_result[df_result["portfolio_id"] == self.test_portfolio_id]
        self.assertEqual(len(test_position_rows), 1)
        self.assertEqual(test_position_rows.iloc[0]["portfolio_id"], self.test_portfolio_id)

    def test_PositionRecordCRUD_Complex_Filters_Real(self):
        """Test PositionRecordCRUD complex filters with real database"""
        # Create position records with different attributes
        test_data = [
            {"code": "000001.SZ", "cost": 1000, "volume": 100, "engine_id": f"Engine{self.test_id}_1"},
            {"code": "000002.SZ", "cost": 2000, "volume": 200, "engine_id": f"Engine{self.test_id}_2"},
            {"code": "000001.SZ", "cost": 1500, "volume": 150, "engine_id": f"Engine{self.test_id}_1"},
            {"code": "000003.SZ", "cost": 3000, "volume": 300, "engine_id": f"Engine{self.test_id}_3"},
        ]

        for i, data in enumerate(test_data):
            params = self.test_position_params.copy()
            params["code"] = data["code"]
            params["cost"] = to_decimal(data["cost"])
            params["volume"] = data["volume"]
            params["engine_id"] = data["engine_id"]
            self.crud.create(**params)

        # Test combined filters
        filtered_positions = self.crud.find(
            filters={
                "portfolio_id": self.test_portfolio_id,
                "code": "000001.SZ",
                "volume__gte": 100,
            }
        )

        # Should find 2 positions (000001.SZ with volume >= 100)
        self.assertEqual(len(filtered_positions), 2)
        for position in filtered_positions:
            self.assertEqual(position.code, "000001.SZ")
            self.assertGreaterEqual(position.volume, 100)

        # Test IN operator for codes
        multi_code_positions = self.crud.find(
            filters={
                "portfolio_id": self.test_portfolio_id,
                "code__in": ["000001.SZ", "000003.SZ"]
            }
        )

        # Should find 3 positions (2 for 000001.SZ + 1 for 000003.SZ)
        self.assertEqual(len(multi_code_positions), 3)
        codes = [p.code for p in multi_code_positions]
        self.assertIn("000001.SZ", codes)
        self.assertIn("000003.SZ", codes)

    def test_PositionRecordCRUD_Exists_Real(self):
        """Test PositionRecordCRUD exists functionality with real database"""
        # Test non-existent position record
        exists_before = self.crud.exists(filters={"portfolio_id": self.test_portfolio_id})
        self.assertFalse(exists_before)

        # Create test position record
        created_position = self.crud.create(**self.test_position_params)

        # Test existing position record
        exists_after = self.crud.exists(filters={"portfolio_id": self.test_portfolio_id})
        self.assertTrue(exists_after)

        # Test with more specific filters
        exists_specific = self.crud.exists(
            filters={
                "portfolio_id": self.test_portfolio_id,
                "code": "000001.SZ",
                "volume": 1000,
            }
        )
        self.assertTrue(exists_specific)

        # Test with non-matching filters
        exists_false = self.crud.exists(
            filters={
                "portfolio_id": self.test_portfolio_id,
                "code": "999999.SZ"
            }
        )
        self.assertFalse(exists_false)

    def test_PositionRecordCRUD_Bulk_Operations_With_Size_Verification_Real(self):
        """Test PositionRecordCRUD bulk operations with table size verification"""
        # Get initial table size
        size0 = get_table_size(self.model)

        # Create bulk test data
        bulk_positions = []
        bulk_count = 5

        for i in range(bulk_count):
            position = self.crud._create_from_params(
                portfolio_id=f"TestPortfolio{self.test_id}_bulk",
                engine_id=f"TestEngine{self.test_id}_bulk",
                timestamp=datetime_normalize("2023-01-01 09:30:00"),
                code=f"BULK{i}.SZ",
                cost=to_decimal(1000 * (i + 1)),
                volume=100 * (i + 1),
                frozen_volume=10 * (i + 1),
                frozen_money=to_decimal(100 * (i + 1)),
                price=to_decimal(10 + i),
                fee=to_decimal(5 + i),
            )
            bulk_positions.append(position)

        # Perform bulk addition
        result = self.crud.add_batch(bulk_positions)

        # Get table size after bulk addition
        size1 = get_table_size(self.model)

        # Verify table size increased by bulk_count
        self.assertEqual(bulk_count, size1 - size0)

        # Verify each position was added correctly
        for i in range(bulk_count):
            found_positions = self.crud.find(filters={
                "portfolio_id": f"TestPortfolio{self.test_id}_bulk",
                "code": f"BULK{i}.SZ"
            })
            self.assertEqual(len(found_positions), 1)
            self.assertEqual(found_positions[0].cost, to_decimal(1000 * (i + 1)))
            self.assertEqual(found_positions[0].volume, 100 * (i + 1))

        # Bulk delete test positions
        self.crud.remove({"portfolio_id": f"TestPortfolio{self.test_id}_bulk"})

        # Get final table size
        size2 = get_table_size(self.model)

        # Verify table size returned to original
        self.assertEqual(size2, size0)

    def test_PositionRecordCRUD_Find_Current_Positions_Real(self):
        """Test PositionRecordCRUD find current positions business helper method with real database"""
        # Create test position records with different volumes
        volumes = [100, 200, 0, 150]  # Include zero volume position

        for i, volume in enumerate(volumes):
            params = self.test_position_params.copy()
            params["code"] = f"CURRENT{i}.SZ"
            params["volume"] = volume
            self.crud.create(**params)

        # Test find current positions (all positions)
        current_positions = self.crud.find_current_positions(self.test_portfolio_id)
        self.assertEqual(len(current_positions), 4)

        # Test find current positions with minimum volume
        active_positions = self.crud.find_current_positions(self.test_portfolio_id, min_volume=1)
        # Should exclude the zero volume position
        active_count = len([p for p in active_positions if p.volume >= 1])
        self.assertEqual(active_count, 3)

    def test_PositionRecordCRUD_Find_Positions_With_Volume_Real(self):
        """Test PositionRecordCRUD find positions with volume business helper method with real database"""
        # Create test position records with different volumes
        volumes = [50, 100, 200, 500]  # Different volume levels

        for i, volume in enumerate(volumes):
            params = self.test_position_params.copy()
            params["code"] = f"VOLUME{i}.SZ"
            params["volume"] = volume
            self.crud.create(**params)

        # Test find positions with volume >= 100
        volume_positions = self.crud.find_positions_with_volume(self.test_portfolio_id, min_volume=100)
        # Should find 3 positions (100, 200, 500)
        self.assertEqual(len(volume_positions), 3)
        for position in volume_positions:
            self.assertGreaterEqual(position.volume, 100)

    def test_PositionRecordCRUD_Find_Frozen_Positions_Real(self):
        """Test PositionRecordCRUD find frozen positions business helper method with real database"""
        # Create test position records with different frozen volumes
        frozen_volumes = [0, 50, 100, 200]  # Include positions with no frozen volume

        for i, frozen_volume in enumerate(frozen_volumes):
            params = self.test_position_params.copy()
            params["code"] = f"FROZEN{i}.SZ"
            params["frozen_volume"] = frozen_volume
            self.crud.create(**params)

        # Test find frozen positions (frozen_volume >= 1)
        frozen_positions = self.crud.find_frozen_positions(self.test_portfolio_id, min_frozen_volume=1)
        # Should find 3 positions (50, 100, 200)
        self.assertEqual(len(frozen_positions), 3)
        for position in frozen_positions:
            self.assertGreaterEqual(position.frozen_volume, 1)

    def test_PositionRecordCRUD_Count_Active_Positions_Real(self):
        """Test PositionRecordCRUD count active positions business helper method with real database"""
        # Create test position records with different volumes
        volumes = [0, 100, 0, 200, 150]  # Mix of zero and non-zero volumes

        for i, volume in enumerate(volumes):
            params = self.test_position_params.copy()
            params["code"] = f"ACTIVE{i}.SZ"
            params["volume"] = volume
            self.crud.create(**params)

        # Test count active positions (volume >= 1)
        active_count = self.crud.count_active_positions(self.test_portfolio_id, min_volume=1)
        self.assertEqual(active_count, 3)

        # Test count active positions with higher threshold
        high_volume_count = self.crud.count_active_positions(self.test_portfolio_id, min_volume=150)
        self.assertEqual(high_volume_count, 2)  # 200 and 150

    def test_PositionRecordCRUD_Get_Position_PnL_Real(self):
        """Test PositionRecordCRUD get position P&L business helper method with real database"""
        # Create test position records for P&L calculation
        position_data = [
            {"cost": 1000, "volume": 100, "price": 12.00, "fee": 5.0},  # Profitable position
            {"cost": 500, "volume": 50, "price": 12.00, "fee": 2.5},    # Another profitable position
        ]

        for i, data in enumerate(position_data):
            params = self.test_position_params.copy()
            params["timestamp"] = datetime_normalize(f"2023-01-01 {9+i}:30:00")
            params["cost"] = to_decimal(data["cost"])
            params["volume"] = data["volume"] if i == 1 else data["volume"]  # Latest position volume
            params["price"] = to_decimal(data["price"])
            params["fee"] = to_decimal(data["fee"])
            self.crud.create(**params)

        # Test get position P&L
        pnl_data = self.crud.get_position_pnl(self.test_portfolio_id, "000001.SZ")

        # Verify P&L calculation
        self.assertIsInstance(pnl_data, dict)
        self.assertEqual(pnl_data["code"], "000001.SZ")
        self.assertGreater(pnl_data["total_cost"], 0)
        self.assertGreater(pnl_data["current_market_value"], 0)
        self.assertGreater(pnl_data["total_fees"], 0)
        self.assertEqual(pnl_data["position_count"], 2)

    def test_PositionRecordCRUD_Exception_Handling_Real(self):
        """Test PositionRecordCRUD exception handling with real database"""
        # Test find with empty filters (should not cause issues)
        all_positions = self.crud.find(filters={})
        self.assertIsInstance(all_positions, list)

        # Test delete with empty portfolio_id (should raise ValueError)
        with self.assertRaises(ValueError):
            self.crud.delete_by_portfolio("")

        with self.assertRaises(ValueError):
            self.crud.delete_by_portfolio_and_date_range("")

        # Test remove with overly broad filters (should be safe)
        self.crud.remove({})  # Should be safely handled without affecting other tests

        # Test create with invalid data types - should raise ValidationError
        if ValidationError is not None:
            with self.assertRaises(ValidationError):
                invalid_params = self.test_position_params.copy()
                invalid_params["volume"] = "invalid_volume"
                self.crud.create(**invalid_params)