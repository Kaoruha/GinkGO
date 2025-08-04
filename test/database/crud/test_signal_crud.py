import unittest
import sys
import os
import uuid
from datetime import datetime
from sqlalchemy import text
from test.database.test_isolation import database_test_required


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

try:
    from ginkgo.data.crud.signal_crud import SignalCRUD
    from ginkgo.data.models import MSignal
    from ginkgo.backtest import Signal
    from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
    from ginkgo.libs import GCONF, datetime_normalize
    from ginkgo.data.drivers import get_db_connection, get_table_size, create_table, drop_table
except ImportError as e:
    print(f"Import error: {e}")
    SignalCRUD = None
    GCONF = None


class SignalCRUDTest(unittest.TestCase):
    """
    SignalCRUD database integration tests.
    Tests Signal-specific CRUD operations with actual database.
    """

    @classmethod
    def setUpClass(cls):
        """Class-level setup: check database configuration and connection"""
        if SignalCRUD is None or GCONF is None:
            raise AssertionError("SignalCRUD or GCONF not available")

        # Set model for table size verification
        cls.model = MSignal

        # Recreate table for clean testing
        try:
            drop_table(cls.model, no_skip=True)
            create_table(cls.model, no_skip=True)
            print(":white_check_mark: Signal table recreated for testing")
        except Exception as e:
            print(f":warning: Signal table recreation failed: {e}")

        # Verify database configuration (ClickHouse for MSignal)
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

        # Create SignalCRUD instance
        cls.crud = SignalCRUD()

        # Test database connection
        try:
            connection = get_db_connection(MSignal)
            with connection.get_session() as session:
                session.execute(text("SELECT 1"))
            print(":white_check_mark: Signal database connection successful")
        except Exception as e:
            raise AssertionError(f"Database connection failed: {e}")

    def setUp(self):
        """Setup for each test: prepare unique test data"""
        self.test_id = str(uuid.uuid4())[:8]
        self.test_portfolio_id = f"TestPortfolio{self.test_id}"
        self.test_engine_id = f"TestEngine{self.test_id}"

        # Test signal data based on actual MSignal fields
        self.test_signal_params = {
            "portfolio_id": self.test_portfolio_id,
            "engine_id": self.test_engine_id,
            "timestamp": datetime_normalize("2023-01-01 09:30:00"),
            "code": "000001.SZ",
            "direction": DIRECTION_TYPES.LONG,
            "reason": f"TestSignal{self.test_id}",
            "source": SOURCE_TYPES.SIM,
        }

    def tearDown(self):
        """Cleanup after each test"""
        try:
            # Single pattern cleanup for all test data
            self.crud.remove({"reason__like": f"TestSignal{self.test_id}%"})
        except Exception as e:
            print(f":warning: Cleanup failed: {e}")

    @classmethod
    def tearDownClass(cls):
        """Class-level cleanup: remove any remaining test data"""
        try:
            # Final cleanup of any remaining test records
            cls.crud.remove({"reason__like": "TestSignal%"})
            print(":broom: Final cleanup of all TestSignal records completed")
        except Exception as e:
            print(f":warning: Final cleanup failed: {e}")

    @database_test_required
    def test_SignalCRUD_Create_From_Params_Real(self):
        """Test SignalCRUD create from parameters with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create signal from parameters
        created_signal = self.crud.create(**self.test_signal_params)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify creation
        self.assertIsNotNone(created_signal)
        self.assertIsInstance(created_signal, MSignal)
        self.assertEqual(created_signal.portfolio_id, self.test_portfolio_id)
        self.assertEqual(created_signal.engine_id, self.test_engine_id)
        self.assertEqual(created_signal.code, "000001.SZ")
        self.assertEqual(created_signal.direction, DIRECTION_TYPES.LONG)
        self.assertTrue(created_signal.reason.startswith(f"TestSignal{self.test_id}"))

        # Verify in database
        found_signals = self.crud.find(filters={"reason": f"TestSignal{self.test_id}"})
        self.assertEqual(len(found_signals), 1)
        self.assertEqual(found_signals[0].portfolio_id, self.test_portfolio_id)

    @database_test_required
    def test_SignalCRUD_Add_Signal_Object_Real(self):
        """Test SignalCRUD add signal object with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create signal object (simple object with attributes)
        class SignalObj:
            def __init__(self, test_id):
                self.portfolio_id = f"TestPortfolio{test_id}_obj"
                self.engine_id = f"TestEngine{test_id}_obj"
                self.timestamp = datetime_normalize("2023-01-01 10:00:00")
                self.code = "000002.SZ"
                self.direction = DIRECTION_TYPES.SHORT
                self.reason = f"TestSignal{test_id}_obj"
                self.source = SOURCE_TYPES.REALTIME

        signal_obj = SignalObj(self.test_id)

        # Convert signal to MSignal and add
        msignal = self.crud._create_from_params(
            portfolio_id=signal_obj.portfolio_id,
            engine_id=signal_obj.engine_id,
            timestamp=signal_obj.timestamp,
            code=signal_obj.code,
            direction=signal_obj.direction,
            reason=signal_obj.reason,
            source=signal_obj.source
        )
        added_signal = self.crud.add(msignal)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify addition
        self.assertIsNotNone(added_signal)
        self.assertEqual(added_signal.portfolio_id, f"TestPortfolio{self.test_id}_obj")
        self.assertEqual(added_signal.engine_id, f"TestEngine{self.test_id}_obj")
        self.assertEqual(added_signal.code, "000002.SZ")
        self.assertEqual(added_signal.direction, DIRECTION_TYPES.SHORT)

        # Verify in database
        found_signals = self.crud.find(filters={"reason": f"TestSignal{self.test_id}_obj"})
        self.assertEqual(len(found_signals), 1)

    @database_test_required
    def test_SignalCRUD_Add_Batch_Real(self):
        """Test SignalCRUD batch addition with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create multiple signal objects
        signals = []
        batch_count = 3
        for i in range(batch_count):
            signal = self.crud._create_from_params(
                portfolio_id=f"TestPortfolio{self.test_id}_batch",
                engine_id=f"TestEngine{self.test_id}_batch",
                timestamp=datetime_normalize("2023-01-01 09:30:00"),
                code=f"00000{i}.SZ",
                direction=DIRECTION_TYPES.LONG if i % 2 == 0 else DIRECTION_TYPES.SHORT,
                reason=f"TestSignal{self.test_id}_batch_{i}",
                source=SOURCE_TYPES.SIM,
            )
            signals.append(signal)

        # Add batch
        result = self.crud.add_batch(signals)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by batch count
        self.assertEqual(batch_count, size1 - size0)

        # Verify batch addition
        self.assertIsInstance(result, tuple)

        # Verify each signal in database
        for i in range(batch_count):
            found_signals = self.crud.find(filters={"reason": f"TestSignal{self.test_id}_batch_{i}"})
            self.assertEqual(len(found_signals), 1)
            expected_direction = DIRECTION_TYPES.LONG if i % 2 == 0 else DIRECTION_TYPES.SHORT
            self.assertEqual(found_signals[0].direction, expected_direction)
            self.assertEqual(found_signals[0].code, f"00000{i}.SZ")

    @database_test_required
    def test_SignalCRUD_Find_By_Portfolio_Real(self):
        """Test SignalCRUD find by portfolio business helper method with real database"""
        # Create test signals
        for i in range(3):
            params = self.test_signal_params.copy()
            params["reason"] = f"TestSignal{self.test_id}_portfolio_{i}"
            params["code"] = f"00000{i}.SZ"
            self.crud.create(**params)

        # Test find by portfolio
        found_signals = self.crud.find_by_portfolio(self.test_portfolio_id)

        # Should find 3 signals
        self.assertEqual(len(found_signals), 3)
        for signal in found_signals:
            self.assertEqual(signal.portfolio_id, self.test_portfolio_id)

        # Test find by portfolio with date range
        found_signals_range = self.crud.find_by_portfolio(
            self.test_portfolio_id,
            start_date="2022-12-31",
            end_date="2023-12-31"
        )
        self.assertEqual(len(found_signals_range), 3)

    @database_test_required
    def test_SignalCRUD_Find_By_Engine_Real(self):
        """Test SignalCRUD find by engine business helper method with real database"""
        # Create test signals
        for i in range(2):
            params = self.test_signal_params.copy()
            params["reason"] = f"TestSignal{self.test_id}_engine_{i}"
            params["code"] = f"00000{i}.SZ"
            self.crud.create(**params)

        # Test find by engine
        found_signals = self.crud.find_by_engine(self.test_engine_id)

        # Should find 2 signals
        self.assertEqual(len(found_signals), 2)
        for signal in found_signals:
            self.assertEqual(signal.engine_id, self.test_engine_id)

        # Test find by engine with date range
        found_signals_range = self.crud.find_by_engine(
            self.test_engine_id,
            start_date="2022-12-31",
            end_date="2023-12-31"
        )
        self.assertEqual(len(found_signals_range), 2)

    @database_test_required
    def test_SignalCRUD_Find_By_Code_And_Direction_Real(self):
        """Test SignalCRUD find by code and direction business helper method with real database"""
        # Create test signals with different directions
        directions = [DIRECTION_TYPES.LONG, DIRECTION_TYPES.SHORT, DIRECTION_TYPES.LONG]

        for i, direction in enumerate(directions):
            params = self.test_signal_params.copy()
            params["reason"] = f"TestSignal{self.test_id}_codedir_{i}"
            params["direction"] = direction
            self.crud.create(**params)

        # Test find by code and direction
        long_signals = self.crud.find_by_code_and_direction("000001.SZ", DIRECTION_TYPES.LONG)
        self.assertEqual(len(long_signals), 2)
        for signal in long_signals:
            self.assertEqual(signal.direction, DIRECTION_TYPES.LONG)
            self.assertEqual(signal.code, "000001.SZ")

        short_signals = self.crud.find_by_code_and_direction("000001.SZ", DIRECTION_TYPES.SHORT)
        self.assertEqual(len(short_signals), 1)
        self.assertEqual(short_signals[0].direction, DIRECTION_TYPES.SHORT)

    @database_test_required
    def test_SignalCRUD_Get_Latest_Signals_Real(self):
        """Test SignalCRUD get latest signals business helper method with real database"""
        # Create test signals with different timestamps
        timestamps = ["2023-01-01 09:30:00", "2023-01-01 10:00:00", "2023-01-01 10:30:00"]

        for i, timestamp in enumerate(timestamps):
            params = self.test_signal_params.copy()
            params["reason"] = f"TestSignal{self.test_id}_latest_{i}"
            params["timestamp"] = datetime_normalize(timestamp)
            self.crud.create(**params)

        # Test get latest signals
        latest_signals = self.crud.get_latest_signals(self.test_portfolio_id, limit=2)

        # Should get 2 latest signals (most recent first)
        self.assertEqual(len(latest_signals), 2)
        # Latest should be the most recent timestamp
        self.assertTrue(latest_signals[0].timestamp >= latest_signals[1].timestamp)

    @database_test_required
    def test_SignalCRUD_Count_By_Portfolio_Real(self):
        """Test SignalCRUD count by portfolio business helper method with real database"""
        # Create test signals
        for i in range(4):
            params = self.test_signal_params.copy()
            params["reason"] = f"TestSignal{self.test_id}_count_{i}"
            self.crud.create(**params)

        # Test count by portfolio
        count = self.crud.count_by_portfolio(self.test_portfolio_id)
        self.assertEqual(count, 4)

        # Test count by non-existent portfolio
        count_empty = self.crud.count_by_portfolio("NON_EXISTENT_PORTFOLIO")
        self.assertEqual(count_empty, 0)

    @database_test_required
    def test_SignalCRUD_Count_By_Code_And_Direction_Real(self):
        """Test SignalCRUD count by code and direction business helper method with real database"""
        # Create test signals with different codes and directions
        test_data = [
            {"code": "000001.SZ", "direction": DIRECTION_TYPES.LONG},
            {"code": "000001.SZ", "direction": DIRECTION_TYPES.LONG},
            {"code": "000001.SZ", "direction": DIRECTION_TYPES.SHORT},
            {"code": "000002.SZ", "direction": DIRECTION_TYPES.LONG},
        ]

        for i, data in enumerate(test_data):
            params = self.test_signal_params.copy()
            params["reason"] = f"TestSignal{self.test_id}_codecount_{i}"
            params["code"] = data["code"]
            params["direction"] = data["direction"]
            self.crud.create(**params)

        # Test count by code and direction
        long_count = self.crud.count_by_code_and_direction("000001.SZ", DIRECTION_TYPES.LONG)
        self.assertEqual(long_count, 2)

        short_count = self.crud.count_by_code_and_direction("000001.SZ", DIRECTION_TYPES.SHORT)
        self.assertEqual(short_count, 1)

        other_long_count = self.crud.count_by_code_and_direction("000002.SZ", DIRECTION_TYPES.LONG)
        self.assertEqual(other_long_count, 1)

    @database_test_required
    def test_SignalCRUD_Get_All_Codes_Real(self):
        """Test SignalCRUD get all codes business helper method with real database"""
        # Create test signals with different codes
        codes = ["000001.SZ", "000002.SZ", "000003.SZ", "000001.SZ"]  # Duplicate to test uniqueness

        for i, code in enumerate(codes):
            params = self.test_signal_params.copy()
            params["reason"] = f"TestSignal{self.test_id}_codes_{i}"
            params["code"] = code
            self.crud.create(**params)

        # Test get all codes
        all_codes = self.crud.get_all_codes()

        # Verify our test codes are included (unique)
        unique_test_codes = list(set(codes))
        for test_code in unique_test_codes:
            self.assertIn(test_code, all_codes)

    @database_test_required
    def test_SignalCRUD_Get_Portfolio_Ids_Real(self):
        """Test SignalCRUD get portfolio IDs business helper method with real database"""
        # Create test signals with different portfolio IDs
        portfolio_ids = [f"Portfolio{self.test_id}_1", f"Portfolio{self.test_id}_2", f"Portfolio{self.test_id}_1"]

        for i, portfolio_id in enumerate(portfolio_ids):
            params = self.test_signal_params.copy()
            params["reason"] = f"TestSignal{self.test_id}_portfolios_{i}"
            params["portfolio_id"] = portfolio_id
            self.crud.create(**params)

        # Test get portfolio IDs
        all_portfolio_ids = self.crud.get_portfolio_ids()

        # Verify our test portfolio IDs are included (unique)
        unique_test_portfolio_ids = list(set(portfolio_ids))
        for test_portfolio_id in unique_test_portfolio_ids:
            self.assertIn(test_portfolio_id, all_portfolio_ids)

    @database_test_required
    def test_SignalCRUD_Delete_By_Portfolio_Real(self):
        """Test SignalCRUD delete by portfolio business helper method with real database"""
        # Create test signals
        for i in range(3):
            params = self.test_signal_params.copy()
            params["reason"] = f"TestSignal{self.test_id}_delete_{i}"
            self.crud.create(**params)

        # Verify signals exist
        found_signals = self.crud.find_by_portfolio(self.test_portfolio_id)
        self.assertEqual(len(found_signals), 3)

        # Get table size before deletion
        size0 = get_table_size(self.model)

        # Delete by portfolio
        self.crud.delete_by_portfolio(self.test_portfolio_id)

        # Get table size after deletion
        size1 = get_table_size(self.model)

        # Verify table size decreased by 3
        self.assertEqual(-3, size1 - size0)

        # Verify signals no longer exist
        found_signals_after = self.crud.find_by_portfolio(self.test_portfolio_id)
        self.assertEqual(len(found_signals_after), 0)

        # Test delete with empty portfolio_id (should raise ValueError)
        with self.assertRaises(ValueError):
            self.crud.delete_by_portfolio("")

    @database_test_required
    def test_SignalCRUD_DataFrame_Output_Real(self):
        """Test SignalCRUD DataFrame output with real database"""
        # Create test signal
        created_signal = self.crud.create(**self.test_signal_params)

        # Get as DataFrame
        df_result = self.crud.find_by_portfolio(self.test_portfolio_id, as_dataframe=True)

        # Verify DataFrame
        import pandas as pd

        self.assertIsInstance(df_result, pd.DataFrame)
        self.assertGreaterEqual(len(df_result), 1)

        # Find our test signal in the DataFrame
        test_signal_rows = df_result[df_result["reason"] == f"TestSignal{self.test_id}"]
        self.assertEqual(len(test_signal_rows), 1)
        self.assertEqual(test_signal_rows.iloc[0]["portfolio_id"], self.test_portfolio_id)

    @database_test_required
    def test_SignalCRUD_Complex_Filters_Real(self):
        """Test SignalCRUD complex filters with real database"""
        # Create signals with different attributes
        test_data = [
            {"code": "000001.SZ", "direction": DIRECTION_TYPES.LONG, "engine_id": f"Engine{self.test_id}_1"},
            {"code": "000002.SZ", "direction": DIRECTION_TYPES.SHORT, "engine_id": f"Engine{self.test_id}_2"},
            {"code": "000001.SZ", "direction": DIRECTION_TYPES.SHORT, "engine_id": f"Engine{self.test_id}_1"},
            {"code": "000003.SZ", "direction": DIRECTION_TYPES.LONG, "engine_id": f"Engine{self.test_id}_3"},
        ]

        for i, data in enumerate(test_data):
            params = self.test_signal_params.copy()
            params["reason"] = f"TestSignal{self.test_id}_complex_{i}"
            params["code"] = data["code"]
            params["direction"] = data["direction"]
            params["engine_id"] = data["engine_id"]
            self.crud.create(**params)

        # Test combined filters
        filtered_signals = self.crud.find(
            filters={
                "reason__like": f"TestSignal{self.test_id}_complex_%",
                "code": "000001.SZ",
                "direction": DIRECTION_TYPES.LONG,
            }
        )

        # Should find 1 signal (000001.SZ + LONG)
        self.assertEqual(len(filtered_signals), 1)
        self.assertEqual(filtered_signals[0].code, "000001.SZ")
        self.assertEqual(filtered_signals[0].direction, DIRECTION_TYPES.LONG)

        # Test IN operator for codes
        multi_code_signals = self.crud.find(
            filters={
                "reason__like": f"TestSignal{self.test_id}_complex_%",
                "code__in": ["000001.SZ", "000003.SZ"]
            }
        )

        # Should find 3 signals (2 for 000001.SZ + 1 for 000003.SZ)
        self.assertEqual(len(multi_code_signals), 3)
        codes = [s.code for s in multi_code_signals]
        self.assertIn("000001.SZ", codes)
        self.assertIn("000003.SZ", codes)

    @database_test_required
    def test_SignalCRUD_Exists_Real(self):
        """Test SignalCRUD exists functionality with real database"""
        # Test non-existent signal
        exists_before = self.crud.exists(filters={"reason": f"TestSignal{self.test_id}"})
        self.assertFalse(exists_before)

        # Create test signal
        created_signal = self.crud.create(**self.test_signal_params)

        # Test existing signal
        exists_after = self.crud.exists(filters={"reason": f"TestSignal{self.test_id}"})
        self.assertTrue(exists_after)

        # Test with more specific filters
        exists_specific = self.crud.exists(
            filters={
                "reason": f"TestSignal{self.test_id}",
                "code": "000001.SZ",
                "direction": DIRECTION_TYPES.LONG,
            }
        )
        self.assertTrue(exists_specific)

        # Test with non-matching filters
        exists_false = self.crud.exists(
            filters={
                "reason": f"TestSignal{self.test_id}",
                "code": "999999.SZ"
            }
        )
        self.assertFalse(exists_false)

    @database_test_required
    def test_SignalCRUD_Exception_Handling_Real(self):
        """Test SignalCRUD exception handling with real database"""
        # Test find with empty filters (should not cause issues)
        all_signals = self.crud.find(filters={})
        self.assertIsInstance(all_signals, list)

        # Test delete with empty portfolio_id (should raise ValueError)
        with self.assertRaises(ValueError):
            self.crud.delete_by_portfolio("")

        # Test remove with overly broad filters (should be safe)
        self.crud.remove({})  # Should be safely handled without affecting other tests