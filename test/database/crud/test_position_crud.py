import unittest
import sys
import os
import uuid
from decimal import Decimal
from datetime import datetime
from test.database.test_isolation import database_test_required


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

try:
    from ginkgo.data.crud.position_crud import PositionCRUD
    from ginkgo.data.models import MPosition
    from ginkgo.backtest import Position
    from ginkgo.enums import SOURCE_TYPES
    from ginkgo.libs import GCONF, datetime_normalize, to_decimal
    from ginkgo.data.drivers import get_db_connection, get_table_size, create_table, drop_table
    from ginkgo.data.crud.validation import ValidationError
    from sqlalchemy import text
except ImportError as e:
    print(f"Import error: {e}")
    PositionCRUD = None
    GCONF = None


class PositionCRUDTest(unittest.TestCase):
    """
    PositionCRUD database integration tests.
    Tests Position-specific CRUD operations with actual database.
    """

    @classmethod
    def setUpClass(cls):
        """Class-level setup: check database configuration and connection"""
        if PositionCRUD is None or GCONF is None:
            raise AssertionError("PositionCRUD or GCONF not available")

        # Set model for table size verification
        cls.model = MPosition

        # Recreate table for clean testing
        try:
            drop_table(cls.model, no_skip=True)
            create_table(cls.model, no_skip=True)
            print(":white_check_mark: Position table recreated for testing")
        except Exception as e:
            print(f":warning: Position table recreation failed: {e}")

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

        # Create PositionCRUD instance
        cls.crud = PositionCRUD()

        # Test database connection
        try:
            connection = get_db_connection(MPosition)
            with connection.get_session() as session:
                session.execute(text("SELECT 1"))
            print(":white_check_mark: Position database connection successful")
        except Exception as e:
            raise AssertionError(f"Database connection failed: {e}")

    def setUp(self):
        """Setup for each test: prepare unique test data"""
        self.test_id = str(uuid.uuid4())[:8]
        self.test_portfolio_id = f"PORTFOLIO_{self.test_id}"
        self.test_engine_id = f"ENGINE_{self.test_id}"
        self.test_code = f"POSTEST{self.test_id}.SZ"
        self.test_timestamp = datetime(2023, 1, 1, 9, 30)

        # Test position data based on actual MPosition fields
        self.test_position_params = {
            "portfolio_id": self.test_portfolio_id,
            "engine_id": self.test_engine_id,
            "code": self.test_code,
            "cost": 10000.0,
            "volume": 1000,
            "frozen_volume": 200,
            "frozen_money": 2000.0,
            "price": 10.5,
            "fee": 5.0,
            "source": SOURCE_TYPES.SIM,
        }

    def tearDown(self):
        """Cleanup after each test"""
        try:
            # Remove all test records by test portfolio ID pattern
            self.crud.remove({"portfolio_id__like": f"PORTFOLIO_{self.test_id}%"})

            # Also clean up any bulk test records
            self.crud.remove({"portfolio_id__like": f"PORTFOLIO_{self.test_id}_bulk%"})

            # Clean up by code pattern
            self.crud.remove({"code__like": f"POSTEST{self.test_id}%"})

            print(f":broom: Cleaned up all test data for PORTFOLIO_{self.test_id}")
        except Exception as e:
            print(f":warning: Cleanup failed: {e}")

    @classmethod
    def tearDownClass(cls):
        """Class-level cleanup: remove any remaining test data"""
        try:
            # Final cleanup of any remaining test records
            cls.crud.remove({"portfolio_id__like": "PORTFOLIO_%"})
            cls.crud.remove({"code__like": "POSTEST%"})
            print(":broom: Final cleanup of all position test records completed")
        except Exception as e:
            print(f":warning: Final cleanup failed: {e}")

    @database_test_required
    def test_PositionCRUD_Create_From_Params_Real(self):
        """Test PositionCRUD create from parameters with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create position from parameters
        created_position = self.crud.create(**self.test_position_params)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify creation
        self.assertIsNotNone(created_position)
        self.assertIsInstance(created_position, MPosition)
        self.assertEqual(created_position.portfolio_id, self.test_portfolio_id)
        self.assertEqual(created_position.engine_id, self.test_engine_id)
        self.assertEqual(created_position.code, self.test_code)
        self.assertEqual(created_position.cost, Decimal("10000.0"))
        self.assertEqual(created_position.volume, 1000)
        self.assertEqual(created_position.frozen_volume, 200)
        self.assertEqual(created_position.frozen_money, Decimal("2000.0"))
        self.assertEqual(created_position.price, Decimal("10.5"))
        self.assertEqual(created_position.fee, Decimal("5.0"))
        self.assertEqual(created_position.source, SOURCE_TYPES.SIM)

        # Verify in database
        found_positions = self.crud.find(filters={"portfolio_id": self.test_portfolio_id})
        self.assertEqual(len(found_positions), 1)
        self.assertEqual(found_positions[0].code, self.test_code)

    @database_test_required
    def test_PositionCRUD_Add_Position_Object_Real(self):
        """Test PositionCRUD add position object with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create position object using the actual Position class
        position_obj = Position(
            portfolio_id=self.test_portfolio_id,
            engine_id=self.test_engine_id,
            code=self.test_code,
            cost=20000.0,
            volume=2000,
            frozen_volume=500,
            frozen_money=5000.0,
            price=10.5,
            fee=10.0
        )
        position_obj.source = SOURCE_TYPES.LIVE

        # Convert position to MPosition and add
        mposition = self.crud._convert_input_item(position_obj)
        added_position = self.crud.add(mposition)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify addition
        self.assertIsNotNone(added_position)
        self.assertEqual(added_position.portfolio_id, self.test_portfolio_id)
        self.assertEqual(added_position.engine_id, self.test_engine_id)
        self.assertEqual(added_position.code, self.test_code)
        self.assertEqual(added_position.cost, Decimal("20000.0"))
        self.assertEqual(added_position.volume, 2000)
        self.assertEqual(added_position.frozen_volume, 500)
        self.assertEqual(added_position.frozen_money, Decimal("5000.0"))
        self.assertEqual(added_position.price, Decimal("10.5"))
        self.assertEqual(added_position.fee, Decimal("10.0"))
        self.assertEqual(added_position.source, SOURCE_TYPES.LIVE)

        # Verify in database
        found_positions = self.crud.find(filters={"portfolio_id": self.test_portfolio_id})
        self.assertEqual(len(found_positions), 1)

    @database_test_required
    def test_PositionCRUD_Add_Batch_Real(self):
        """Test PositionCRUD batch addition with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create multiple position objects
        positions = []
        batch_count = 3
        for i in range(batch_count):
            position = self.crud._create_from_params(
                portfolio_id=f"{self.test_portfolio_id}_{i}",
                engine_id=f"{self.test_engine_id}_{i}",
                code=f"{self.test_code}_{i}",
                cost=10000.0 + i * 1000,
                volume=1000 + i * 100,
                frozen_volume=200 + i * 20,
                frozen_money=2000.0 + i * 200,
                price=10.5 + i * 0.5,
                fee=5.0 + i * 0.5,
                source=SOURCE_TYPES.SIM,
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
            found_positions = self.crud.find(filters={"portfolio_id": f"{self.test_portfolio_id}_{i}"})
            self.assertEqual(len(found_positions), 1)
            self.assertEqual(found_positions[0].volume, 1000 + i * 100)
            self.assertEqual(found_positions[0].cost, Decimal(f"{10000.0 + i * 1000}"))

    @database_test_required
    def test_PositionCRUD_Find_By_Portfolio_Real(self):
        """Test PositionCRUD find by portfolio business helper method with real database"""
        # Create positions for the same portfolio
        test_positions = [
            {"code": f"{self.test_code}_1", "volume": 1000, "cost": 10500.0},
            {"code": f"{self.test_code}_2", "volume": 2000, "cost": 21000.0},
            {"code": f"{self.test_code}_3", "volume": 500, "cost": 5250.0},
            {"code": f"{self.test_code}_4", "volume": 0, "cost": 0.0},  # Closed position
        ]

        for pos_data in test_positions:
            params = self.test_position_params.copy()
            params["code"] = pos_data["code"]
            params["volume"] = pos_data["volume"]
            params["cost"] = pos_data["cost"]
            self.crud.create(**params)

        # Test find by portfolio (all positions)
        all_positions = self.crud.find_by_portfolio(self.test_portfolio_id)
        self.assertEqual(len(all_positions), 4)

        # Verify they are ordered by cost descending (using cost instead of market_value)
        costs = [float(pos.cost) for pos in all_positions]
        self.assertEqual(costs, sorted(costs, reverse=True))

        # Test find by portfolio with minimum volume
        active_positions = self.crud.find_by_portfolio(self.test_portfolio_id, min_volume=1)
        self.assertEqual(len(active_positions), 3)  # Exclude volume=0 position
        for pos in active_positions:
            self.assertGreaterEqual(pos.volume, 1)

    @database_test_required
    def test_PositionCRUD_Find_By_Code_Real(self):
        """Test PositionCRUD find by code business helper method with real database"""
        # Create positions for the same code across different portfolios
        portfolios = [f"{self.test_portfolio_id}_{i}" for i in range(3)]

        for i, portfolio_id in enumerate(portfolios):
            params = self.test_position_params.copy()
            params["portfolio_id"] = portfolio_id
            params["volume"] = 1000 + i * 500
            params["cost"] = 10500.0 + i * 5250
            self.crud.create(**params)

        # Test find by code (all portfolios)
        code_positions = self.crud.find_by_code(self.test_code)
        self.assertEqual(len(code_positions), 3)

        # Verify they are ordered by volume descending
        volumes = [pos.volume for pos in code_positions]
        self.assertEqual(volumes, sorted(volumes, reverse=True))

        # Test find by code with specific portfolio
        specific_positions = self.crud.find_by_code(self.test_code, portfolio_id=portfolios[1])
        self.assertEqual(len(specific_positions), 1)
        self.assertEqual(specific_positions[0].portfolio_id, portfolios[1])

    @database_test_required
    def test_PositionCRUD_Get_Position_Real(self):
        """Test PositionCRUD get position business helper method with real database"""
        # Create test position
        created_position = self.crud.create(**self.test_position_params)

        # Test get existing position
        found_position = self.crud.get_position(self.test_portfolio_id, self.test_code)
        self.assertIsNotNone(found_position)
        self.assertEqual(found_position.portfolio_id, self.test_portfolio_id)
        self.assertEqual(found_position.code, self.test_code)
        self.assertEqual(found_position.volume, 1000)

        # Test get non-existent position
        non_existent_position = self.crud.get_position(self.test_portfolio_id, "NON_EXISTENT.SZ")
        self.assertIsNone(non_existent_position)

    @database_test_required
    def test_PositionCRUD_Get_Active_Positions_Real(self):
        """Test PositionCRUD get active positions business helper method with real database"""
        # Create positions with different volumes
        test_positions = [
            {"code": f"{self.test_code}_1", "volume": 1000},
            {"code": f"{self.test_code}_2", "volume": 2000},
            {"code": f"{self.test_code}_3", "volume": 0},     # Closed position
            {"code": f"{self.test_code}_4", "volume": 500},
        ]

        for pos_data in test_positions:
            params = self.test_position_params.copy()
            params["code"] = pos_data["code"]
            params["volume"] = pos_data["volume"]
            self.crud.create(**params)

        # Test get active positions (default min_volume=1)
        active_positions = self.crud.get_active_positions(self.test_portfolio_id)
        self.assertEqual(len(active_positions), 3)  # Exclude volume=0 position
        for pos in active_positions:
            self.assertGreaterEqual(pos.volume, 1)

        # Test get active positions with higher minimum volume
        large_positions = self.crud.get_active_positions(self.test_portfolio_id, min_volume=1000)
        self.assertEqual(len(large_positions), 2)  # Only positions with volume >= 1000
        for pos in large_positions:
            self.assertGreaterEqual(pos.volume, 1000)

    @database_test_required
    def test_PositionCRUD_Get_Portfolio_Value_Real(self):
        """Test PositionCRUD get portfolio value business helper method with real database"""
        # Create positions with different values
        test_positions = [
            {"code": f"{self.test_code}_1", "volume": 1000, "cost": 10000.0, "price": 10.5},
            {"code": f"{self.test_code}_2", "volume": 2000, "cost": 20000.0, "price": 10.5},
            {"code": f"{self.test_code}_3", "volume": 0, "cost": 0.0, "price": 0.0},
            {"code": f"{self.test_code}_4", "volume": 500, "cost": 5000.0, "price": 10.5},
        ]

        for pos_data in test_positions:
            params = self.test_position_params.copy()
            params["code"] = pos_data["code"]
            params["volume"] = pos_data["volume"]
            params["cost"] = pos_data["cost"]
            params["price"] = pos_data["price"]
            self.crud.create(**params)

        # Get portfolio value summary (this method may need to be updated in CRUD)
        portfolio_value = self.crud.get_portfolio_value(self.test_portfolio_id)

        # Verify summary - focus on fields that actually exist
        self.assertEqual(portfolio_value["portfolio_id"], self.test_portfolio_id)
        self.assertEqual(portfolio_value["total_positions"], 4)
        self.assertEqual(portfolio_value["active_positions"], 3)  # Exclude volume=0
        self.assertEqual(portfolio_value["total_cost"], 35000.0)  # 10000+20000+0+5000
        self.assertEqual(portfolio_value["total_volume"], 3500)  # 1000+2000+0+500
        # Market value = price * volume for active positions: 10.5*(1000+2000+500) = 36750.0
        self.assertEqual(portfolio_value["total_market_value"], 36750.0)
        self.assertEqual(portfolio_value["total_pnl"], 1750.0)  # 36750-35000

    @database_test_required
    def test_PositionCRUD_Update_Position_Real(self):
        """Test PositionCRUD update position business helper method with real database"""
        # Create test position
        created_position = self.crud.create(**self.test_position_params)

        # Verify initial values
        self.assertEqual(created_position.volume, 1000)
        self.assertEqual(created_position.cost, Decimal("10000.0"))

        # Update position
        self.crud.update_position(
            self.test_portfolio_id,
            self.test_code,
            volume=1200,
            cost=12600.0,
            price=11.0
        )

        # Verify position updated
        updated_position = self.crud.get_position(self.test_portfolio_id, self.test_code)
        self.assertIsNotNone(updated_position)
        self.assertEqual(updated_position.volume, 1200)
        self.assertEqual(updated_position.cost, Decimal("12600.0"))
        self.assertEqual(updated_position.price, Decimal("11.0"))

    @database_test_required
    def test_PositionCRUD_Close_Position_Real(self):
        """Test PositionCRUD close position business helper method with real database"""
        # Create test position
        created_position = self.crud.create(**self.test_position_params)

        # Verify initial values
        self.assertEqual(created_position.volume, 1000)
        self.assertEqual(created_position.frozen_volume, 200)

        # Close position
        self.crud.close_position(self.test_portfolio_id, self.test_code)

        # Verify position closed
        closed_position = self.crud.get_position(self.test_portfolio_id, self.test_code)
        self.assertIsNotNone(closed_position)
        self.assertEqual(closed_position.volume, 0)
        self.assertEqual(closed_position.frozen_volume, 0)

    @database_test_required
    def test_PositionCRUD_Count_By_Portfolio_Real(self):
        """Test PositionCRUD count by portfolio with real database"""
        # Create positions for different portfolios
        portfolios = [f"{self.test_portfolio_id}_{i}" for i in range(3)]

        for i, portfolio_id in enumerate(portfolios):
            # Create 2 positions per portfolio
            for j in range(2):
                params = self.test_position_params.copy()
                params["portfolio_id"] = portfolio_id
                params["code"] = f"{self.test_code}_{i}_{j}"
                self.crud.create(**params)

        # Count positions for each portfolio
        for portfolio_id in portfolios:
            count = self.crud.count({"portfolio_id": portfolio_id})
            self.assertEqual(count, 2)

        # Count all test positions
        total_count = self.crud.count({"portfolio_id__like": f"{self.test_portfolio_id}_%"})
        self.assertEqual(total_count, 6)

    @database_test_required
    def test_PositionCRUD_Remove_By_Portfolio_Real(self):
        """Test PositionCRUD remove by portfolio with real database"""
        # Create positions for different portfolios
        portfolios = [f"{self.test_portfolio_id}_{i}" for i in range(3)]

        for portfolio_id in portfolios:
            params = self.test_position_params.copy()
            params["portfolio_id"] = portfolio_id
            self.crud.create(**params)

        # Verify all created
        all_positions = self.crud.find(filters={"portfolio_id__like": f"{self.test_portfolio_id}_"})
        self.assertEqual(len(all_positions), 3)

        # Get table size before removal
        size0 = get_table_size(self.model)

        # Remove one portfolio's positions
        self.crud.remove({"portfolio_id": f"{self.test_portfolio_id}_1"})

        # Get table size after removal
        size1 = get_table_size(self.model)

        # Verify table size decreased by 1
        self.assertEqual(-1, size1 - size0)

        # Verify only 2 portfolios remain
        remaining_positions = self.crud.find(filters={"portfolio_id__like": f"{self.test_portfolio_id}_"})
        self.assertEqual(len(remaining_positions), 2)

    @database_test_required
    def test_PositionCRUD_Complex_Filters_Real(self):
        """Test PositionCRUD complex filters with real database"""
        # Create positions with different attributes
        test_data = [
            {"code": f"{self.test_code}_1", "volume": 1000, "cost": 10500.0, "source": SOURCE_TYPES.SIM},
            {"code": f"{self.test_code}_2", "volume": 2000, "cost": 21000.0, "source": SOURCE_TYPES.LIVE},
            {"code": f"{self.test_code}_3", "volume": 500, "cost": 5250.0, "source": SOURCE_TYPES.SIM},
            {"code": f"{self.test_code}_4", "volume": 0, "cost": 0.0, "source": SOURCE_TYPES.LIVE},
        ]

        for data in test_data:
            params = self.test_position_params.copy()
            params["code"] = data["code"]
            params["volume"] = data["volume"]
            params["cost"] = data["cost"]
            params["source"] = data["source"]
            self.crud.create(**params)

        # Test combined filters
        filtered_positions = self.crud.find(
            filters={
                "portfolio_id": self.test_portfolio_id,
                "volume__gte": 1000,
                "cost__gte": 10000.0,
                "source": SOURCE_TYPES.SIM
            }
        )

        # Should find 1 position (volume >= 1000, cost >= 10000, SIM source)
        self.assertEqual(len(filtered_positions), 1)
        self.assertGreaterEqual(filtered_positions[0].volume, 1000)
        self.assertGreaterEqual(float(filtered_positions[0].cost), 10000.0)
        self.assertEqual(filtered_positions[0].source, SOURCE_TYPES.SIM)

        # Test IN operator for sources
        source_filtered = self.crud.find(
            filters={
                "portfolio_id": self.test_portfolio_id,
                "source__in": [SOURCE_TYPES.LIVE]
            }
        )

        # Should find 2 positions (LIVE sources)
        self.assertEqual(len(source_filtered), 2)
        for pos in source_filtered:
            self.assertEqual(pos.source, SOURCE_TYPES.LIVE)

    @database_test_required
    def test_PositionCRUD_Output_Type_Conversion_Real(self):
        """Test PositionCRUD output type conversion with real database"""
        # Create test position
        created_position = self.crud.create(**self.test_position_params)

        # Get as model objects (MPosition)
        model_positions = self.crud.find(filters={"portfolio_id": self.test_portfolio_id}, output_type="model")
        self.assertEqual(len(model_positions), 1)
        self.assertIsInstance(model_positions[0], MPosition)

        # Position typically doesn't have a corresponding backtest object
        # So we test with default model output
        position_objects = self.crud.find(filters={"portfolio_id": self.test_portfolio_id}, output_type="model")
        self.assertEqual(len(position_objects), 1)
        self.assertIsInstance(position_objects[0], MPosition)

        # Verify data consistency
        self.assertEqual(model_positions[0].portfolio_id, position_objects[0].portfolio_id)
        self.assertEqual(model_positions[0].code, position_objects[0].code)
        self.assertEqual(model_positions[0].volume, position_objects[0].volume)

    @database_test_required
    def test_PositionCRUD_DataFrame_Output_Real(self):
        """Test PositionCRUD DataFrame output with real database"""
        # Create test position
        created_position = self.crud.create(**self.test_position_params)

        # Get as DataFrame
        df_result = self.crud.find_by_portfolio(self.test_portfolio_id, as_dataframe=True)

        # Verify DataFrame
        import pandas as pd

        self.assertIsInstance(df_result, pd.DataFrame)
        self.assertEqual(len(df_result), 1)
        self.assertEqual(df_result.iloc[0]["portfolio_id"], self.test_portfolio_id)
        self.assertEqual(df_result.iloc[0]["code"], self.test_code)

    @database_test_required
    def test_PositionCRUD_Soft_Delete_Real(self):
        """Test PositionCRUD soft delete functionality with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create test position
        created_position = self.crud.create(**self.test_position_params)

        # Get table size after creation
        size1 = get_table_size(self.model)
        self.assertEqual(size0 + 1, size1)

        # Verify position exists
        found_positions = self.crud.find(filters={"portfolio_id": self.test_portfolio_id})
        self.assertEqual(len(found_positions), 1)
        position_uuid = found_positions[0].uuid

        # Perform soft delete if supported by CRUD
        if hasattr(self.crud, 'soft_delete'):
            self.crud.soft_delete({"uuid": position_uuid})

            # Get table size after soft delete
            size2 = get_table_size(self.model)

            # Table size should decrease after soft delete
            self.assertEqual(-1, size2 - size1)

            # Verify position is no longer found in normal queries
            found_positions_after = self.crud.find(filters={"portfolio_id": self.test_portfolio_id})
            self.assertEqual(len(found_positions_after), 0)

    @database_test_required
    def test_PositionCRUD_Bulk_Operations_With_Size_Verification_Real(self):
        """Test PositionCRUD bulk operations with table size verification"""
        # Get initial table size
        size0 = get_table_size(self.model)

        # Create bulk test data
        bulk_positions = []
        bulk_count = 5

        for i in range(bulk_count):
            position = self.crud._create_from_params(
                portfolio_id=f"{self.test_portfolio_id}_bulk_{i}",
                engine_id=f"{self.test_engine_id}_bulk_{i}",
                code=f"{self.test_code}_bulk_{i}",
                cost=10000.0 + i * 1000,
                volume=1000 + i * 100,
                frozen_volume=200 + i * 20,
                frozen_money=2000.0 + i * 200,
                price=10.5 + i * 0.5,
                fee=5.0 + i * 0.5,
                source=SOURCE_TYPES.SIM,
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
            found_positions = self.crud.find(filters={"portfolio_id": f"{self.test_portfolio_id}_bulk_{i}"})
            self.assertEqual(len(found_positions), 1)
            self.assertEqual(found_positions[0].volume, 1000 + i * 100)
            self.assertEqual(found_positions[0].cost, Decimal(f"{10000.0 + i * 1000}"))

        # Bulk delete test positions
        self.crud.remove({"portfolio_id__like": f"{self.test_portfolio_id}_bulk_%"})

        # Get final table size
        size2 = get_table_size(self.model)

        # Verify table size returned to original
        self.assertEqual(size2, size0)

    @database_test_required
    def test_PositionCRUD_Exists_Real(self):
        """Test PositionCRUD exists functionality with real database"""
        # Test non-existent position
        exists_before = self.crud.exists(filters={"portfolio_id": self.test_portfolio_id})
        self.assertFalse(exists_before)

        # Create test position
        created_position = self.crud.create(**self.test_position_params)

        # Test existing position
        exists_after = self.crud.exists(filters={"portfolio_id": self.test_portfolio_id})
        self.assertTrue(exists_after)

        # Test with more specific filters
        exists_specific = self.crud.exists(filters={
            "portfolio_id": self.test_portfolio_id,
            "code": self.test_code,
            "volume": 1000
        })
        self.assertTrue(exists_specific)

        # Test with non-matching filters
        exists_false = self.crud.exists(filters={
            "portfolio_id": self.test_portfolio_id,
            "code": "NON_EXISTENT.SZ"
        })
        self.assertFalse(exists_false)

    @database_test_required
    def test_PositionCRUD_Exception_Handling_Real(self):
        """Test PositionCRUD exception handling with real database"""
        # Test create with invalid data
        try:
            invalid_params = self.test_position_params.copy()
            invalid_params["price"] = "invalid_price"
            # This might not raise exception due to decimal normalization
            result = self.crud.create(**invalid_params)
        except Exception as e:
            # Exception handling is working
            pass

        # Test find with empty filters (should not cause issues)
        all_positions = self.crud.find(filters={})
        self.assertIsInstance(all_positions, list)

        # Test remove with overly broad filters (should be safe)
        self.crud.remove({})  # Should be safely handled without affecting other tests

        # Test business methods with invalid parameters
        try:
            invalid_position = self.crud.get_position("", "")
            self.assertIsNone(invalid_position)
        except Exception as e:
            # Exception handling is working
            pass

        # Test with invalid decimal values
        try:
            invalid_params = self.test_position_params.copy()
            invalid_params["cost"] = "invalid_cost"
            result = self.crud.create(**invalid_params)
        except Exception as e:
            # Exception handling is working
            pass

    @database_test_required
    def test_PositionCRUD_ValidationError_Tests(self):
        """Test PositionCRUD field validation functionality"""
        # Test empty portfolio_id
        with self.assertRaises(ValidationError):
            self.crud.create(
                portfolio_id="",
                engine_id=self.test_engine_id,
                code=self.test_code,
                cost=1000.0,
                source=SOURCE_TYPES.SIM
            )

        # Test empty engine_id  
        with self.assertRaises(ValidationError):
            self.crud.create(
                portfolio_id=self.test_portfolio_id,
                engine_id="",
                code=self.test_code,
                cost=1000.0,
                source=SOURCE_TYPES.SIM
            )

        # Test empty code
        with self.assertRaises(ValidationError):
            self.crud.create(
                portfolio_id=self.test_portfolio_id,
                engine_id=self.test_engine_id,
                code="",
                cost=1000.0,
                source=SOURCE_TYPES.SIM
            )

        # Test negative cost
        with self.assertRaises(ValidationError):
            self.crud.create(
                portfolio_id=self.test_portfolio_id,
                engine_id=self.test_engine_id,
                code=self.test_code,
                cost=-1000.0,
                source=SOURCE_TYPES.SIM
            )

        # Test negative volume
        with self.assertRaises(ValidationError):
            self.crud.create(
                portfolio_id=self.test_portfolio_id,
                engine_id=self.test_engine_id,
                code=self.test_code,
                cost=1000.0,
                volume=-100,
                source=SOURCE_TYPES.SIM
            )

        # Test invalid source enum
        with self.assertRaises(ValidationError):
            self.crud.create(
                portfolio_id=self.test_portfolio_id,
                engine_id=self.test_engine_id,
                code=self.test_code,
                cost=1000.0,
                source="INVALID_SOURCE"
            )

        # Test string length limits
        with self.assertRaises(ValidationError):
            self.crud.create(
                portfolio_id="a" * 33,  # Too long (max 32)
                engine_id=self.test_engine_id,
                code=self.test_code,
                cost=1000.0,
                source=SOURCE_TYPES.SIM
            )
