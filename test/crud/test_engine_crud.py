import unittest
import sys
import os
import uuid
from datetime import datetime
from sqlalchemy import text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

try:
    from ginkgo.data.crud.engine_crud import EngineCRUD
    from ginkgo.data.crud.validation import ValidationError
    from ginkgo.data.models import MEngine
    from ginkgo.enums import SOURCE_TYPES, ENGINESTATUS_TYPES
    from ginkgo.libs import GCONF
    from ginkgo.data.drivers import get_db_connection, get_table_size, create_table, drop_table
except ImportError as e:
    print(f"Import error: {e}")
    EngineCRUD = None
    GCONF = None
    ValidationError = None


class EngineCRUDTest(unittest.TestCase):
    """
    EngineCRUD database integration tests.
    Tests Engine-specific CRUD operations with actual database.
    """

    @classmethod
    def setUpClass(cls):
        """Class-level setup: check database configuration and connection"""
        if EngineCRUD is None or GCONF is None:
            raise AssertionError("EngineCRUD or GCONF not available")

        # Set model for table size verification
        cls.model = MEngine

        # Recreate table for clean testing
        try:
            drop_table(cls.model, no_skip=True)
            create_table(cls.model, no_skip=True)
            print(":white_check_mark: Engine table recreated for testing")
        except Exception as e:
            print(f":warning: Engine table recreation failed: {e}")

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

        # Create EngineCRUD instance
        cls.crud = EngineCRUD()

        # Test database connection
        try:
            connection = get_db_connection(MEngine)
            with connection.get_session() as session:
                session.execute(text("SELECT 1"))
            print(":white_check_mark: Engine database connection successful")
        except Exception as e:
            raise AssertionError(f"Database connection failed: {e}")

    def setUp(self):
        """Setup for each test: prepare unique test data"""
        self.test_id = str(uuid.uuid4())[:8]
        self.test_engine_name = f"TestEngine{self.test_id}"

        # Test engine data based on actual MEngine fields
        self.test_engine_params = {
            "name": self.test_engine_name,
            "status": ENGINESTATUS_TYPES.IDLE,
            "is_live": False,
            "source": SOURCE_TYPES.SIM,
        }

    def tearDown(self):
        """Cleanup after each test"""
        try:
            # Single pattern cleanup for all test data
            self.crud.remove({"name__like": f"TestEngine{self.test_id}%"})
        except Exception as e:
            print(f":warning: Cleanup failed: {e}")

    @classmethod
    def tearDownClass(cls):
        """Class-level cleanup: remove any remaining test data"""
        try:
            # Final cleanup of any remaining test records
            cls.crud.remove({"name__like": "TestEngine%"})
            print(":broom: Final cleanup of all TestEngine records completed")
        except Exception as e:
            print(f":warning: Final cleanup failed: {e}")

    def test_EngineCRUD_Create_From_Params_Real(self):
        """Test EngineCRUD create from parameters with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create engine from parameters
        created_engine = self.crud.create(**self.test_engine_params)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify creation
        self.assertIsNotNone(created_engine)
        self.assertIsInstance(created_engine, MEngine)
        self.assertEqual(created_engine.name, self.test_engine_name)
        self.assertEqual(created_engine.status, ENGINESTATUS_TYPES.IDLE)
        self.assertEqual(created_engine.is_live, False)
        self.assertEqual(created_engine.source, SOURCE_TYPES.SIM)

        # Verify in database
        found_engines = self.crud.find(filters={"name": self.test_engine_name})
        self.assertEqual(len(found_engines), 1)
        self.assertEqual(found_engines[0].name, self.test_engine_name)

    def test_EngineCRUD_Add_Engine_Object_Real(self):
        """Test EngineCRUD add engine object with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create engine object (simple object with attributes)
        class EngineObj:
            def __init__(self, test_id):
                self.name = f"TestEngine{test_id}_obj"
                self.status = ENGINESTATUS_TYPES.RUNNING
                self.is_live = True
                self.source = SOURCE_TYPES.REALTIME

        engine_obj = EngineObj(self.test_id)

        # Convert engine to MEngine and add
        mengine = self.crud._convert_input_item(engine_obj)
        added_engine = self.crud.add(mengine)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify addition
        self.assertIsNotNone(added_engine)
        self.assertEqual(added_engine.name, f"TestEngine{self.test_id}_obj")
        self.assertEqual(added_engine.status, ENGINESTATUS_TYPES.RUNNING)
        self.assertEqual(added_engine.is_live, True)
        self.assertEqual(added_engine.source, SOURCE_TYPES.REALTIME)

        # Verify in database
        found_engines = self.crud.find(filters={"name": f"TestEngine{self.test_id}_obj"})
        self.assertEqual(len(found_engines), 1)

    def test_EngineCRUD_Add_Batch_Real(self):
        """Test EngineCRUD batch addition with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create multiple engine objects
        engines = []
        batch_count = 3
        for i in range(batch_count):
            engine = self.crud._create_from_params(
                name=f"TestEngine{self.test_id}_batch_{i}",
                status=ENGINESTATUS_TYPES.IDLE if i % 2 == 0 else ENGINESTATUS_TYPES.RUNNING,
                is_live=i % 2 == 1,
                source=SOURCE_TYPES.SIM,
            )
            engines.append(engine)

        # Add batch
        result = self.crud.add_batch(engines)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by batch count
        self.assertEqual(batch_count, size1 - size0)

        # Verify batch addition
        self.assertIsInstance(result, tuple)

        # Verify each engine in database
        for i in range(batch_count):
            found_engines = self.crud.find(filters={"name": f"TestEngine{self.test_id}_batch_{i}"})
            self.assertEqual(len(found_engines), 1)
            expected_status = ENGINESTATUS_TYPES.IDLE if i % 2 == 0 else ENGINESTATUS_TYPES.RUNNING
            self.assertEqual(found_engines[0].status, expected_status)
            self.assertEqual(found_engines[0].is_live, i % 2 == 1)

    def test_EngineCRUD_Find_By_UUID_Real(self):
        """Test EngineCRUD find by UUID business helper method with real database"""
        # Create test engine
        created_engine = self.crud.create(**self.test_engine_params)
        test_uuid = created_engine.uuid

        # Test find by UUID
        found_engines = self.crud.find_by_uuid(test_uuid)

        # Should find 1 engine
        self.assertEqual(len(found_engines), 1)
        self.assertEqual(found_engines[0].uuid, test_uuid)
        self.assertEqual(found_engines[0].name, self.test_engine_name)
        self.assertEqual(found_engines[0].status, ENGINESTATUS_TYPES.IDLE)

        # Test find by non-existent UUID
        not_found_engines = self.crud.find_by_uuid("NON_EXISTENT_UUID")
        self.assertEqual(len(not_found_engines), 0)

    def test_EngineCRUD_Find_By_Status_Real(self):
        """Test EngineCRUD find by status business helper method with real database"""
        # Create engines with different statuses
        engine_statuses = [ENGINESTATUS_TYPES.IDLE, ENGINESTATUS_TYPES.RUNNING, ENGINESTATUS_TYPES.STOPPED, ENGINESTATUS_TYPES.IDLE]

        for i, status in enumerate(engine_statuses):
            params = self.test_engine_params.copy()
            params["name"] = f"TestEngine{self.test_id}_status_{i}"
            params["status"] = status
            self.crud.create(**params)

        # Test find by specific status
        idle_engines = self.crud.find_by_status(ENGINESTATUS_TYPES.IDLE)

        # Should find at least 2 idle engines (our test records)
        matching_idle = [e for e in idle_engines if e.name.startswith(f"TestEngine{self.test_id}_status_")]
        self.assertGreaterEqual(len(matching_idle), 2)
        for engine in matching_idle:
            self.assertEqual(engine.status, ENGINESTATUS_TYPES.IDLE)

        # Test find by another status
        running_engines = self.crud.find_by_status(ENGINESTATUS_TYPES.RUNNING)
        matching_running = [e for e in running_engines if e.name.startswith(f"TestEngine{self.test_id}_status_")]
        self.assertEqual(len(matching_running), 1)
        self.assertEqual(matching_running[0].status, ENGINESTATUS_TYPES.RUNNING)

    def test_EngineCRUD_Find_By_Name_Pattern_Real(self):
        """Test EngineCRUD find by name pattern business helper method with real database"""
        # Create engines with different names
        names = ["HistoricEngine", "LiveEngine", "TestingEngine"]

        for i, name in enumerate(names):
            params = self.test_engine_params.copy()
            params["name"] = f"{name}{self.test_id}"
            params["status"] = ENGINESTATUS_TYPES.IDLE if i % 2 == 0 else ENGINESTATUS_TYPES.RUNNING
            self.crud.create(**params)

        # Test find by name pattern
        historic_engines = self.crud.find_by_name_pattern(f"Historic%{self.test_id}")

        # Should find 1 historic engine
        self.assertEqual(len(historic_engines), 1)
        self.assertTrue(historic_engines[0].name.startswith("Historic"))

        # Test find by broader pattern
        all_test_engines = self.crud.find_by_name_pattern(f"%Engine{self.test_id}")

        # Should find 3 engines
        self.assertEqual(len(all_test_engines), 3)

    def test_EngineCRUD_Get_All_UUIDs_Real(self):
        """Test EngineCRUD get all UUIDs business helper method with real database"""
        # Create engines with different names
        created_uuids = []
        for i in range(3):
            params = self.test_engine_params.copy()
            params["name"] = f"TestEngine{self.test_id}_uuid_{i}"
            created_engine = self.crud.create(**params)
            created_uuids.append(created_engine.uuid)

        # Get all engine UUIDs
        all_uuids = self.crud.get_all_uuids()

        # Verify our test engine UUIDs are included
        for test_uuid in created_uuids:
            self.assertIn(test_uuid, all_uuids)

    def test_EngineCRUD_Get_Engine_Statuses_Real(self):
        """Test EngineCRUD get engine statuses business helper method with real database"""
        # Create engines with different statuses
        engine_statuses = [ENGINESTATUS_TYPES.IDLE, ENGINESTATUS_TYPES.RUNNING, ENGINESTATUS_TYPES.COMPLETED, ENGINESTATUS_TYPES.IDLE]  # Duplicate to test uniqueness

        for i, status in enumerate(engine_statuses):
            params = self.test_engine_params.copy()
            params["name"] = f"TestEngine{self.test_id}_getstatus_{i}"
            params["status"] = status
            self.crud.create(**params)

        # Get all engine statuses
        all_statuses = self.crud.get_engine_statuses()

        # Verify our test engine statuses are included (unique)
        unique_test_statuses = list(set(engine_statuses))
        for test_status in unique_test_statuses:
            self.assertIn(test_status, all_statuses)

    def test_EngineCRUD_Delete_By_UUID_Real(self):
        """Test EngineCRUD delete by UUID business helper method with real database"""
        # Create test engine
        created_engine = self.crud.create(**self.test_engine_params)
        test_uuid = created_engine.uuid

        # Verify engine exists
        found_engines = self.crud.find(filters={"uuid": test_uuid})
        self.assertEqual(len(found_engines), 1)

        # Get table size before deletion
        size0 = get_table_size(self.model)

        # Delete by UUID
        self.crud.delete_by_uuid(test_uuid)

        # Get table size after deletion
        size1 = get_table_size(self.model)

        # Verify table size decreased by 1
        self.assertEqual(-1, size1 - size0)

        # Verify engine no longer exists
        found_engines_after = self.crud.find(filters={"uuid": test_uuid})
        self.assertEqual(len(found_engines_after), 0)

        # Test delete with empty UUID (should raise ValueError)
        with self.assertRaises(ValueError):
            self.crud.delete_by_uuid("")

    def test_EngineCRUD_Update_Status_Real(self):
        """Test EngineCRUD update status business helper method with real database"""
        # Create test engine
        created_engine = self.crud.create(**self.test_engine_params)
        test_uuid = created_engine.uuid

        # Verify initial status
        self.assertEqual(created_engine.status, ENGINESTATUS_TYPES.IDLE)

        # Update status
        new_status = ENGINESTATUS_TYPES.RUNNING
        self.crud.update_status(test_uuid, new_status)

        # Verify status updated
        updated_engines = self.crud.find(filters={"uuid": test_uuid})
        self.assertEqual(len(updated_engines), 1)
        self.assertEqual(updated_engines[0].status, new_status)

    def test_EngineCRUD_Count_By_Status_Real(self):
        """Test EngineCRUD count by status with real database"""
        # Create engines with different statuses
        engine_statuses = [ENGINESTATUS_TYPES.IDLE, ENGINESTATUS_TYPES.RUNNING, ENGINESTATUS_TYPES.IDLE, ENGINESTATUS_TYPES.COMPLETED]
        created_engines = []

        for i, status in enumerate(engine_statuses):
            params = self.test_engine_params.copy()
            params["name"] = f"TestEngine{self.test_id}_count_{i}"
            params["status"] = status
            created_engine = self.crud.create(**params)
            created_engines.append(created_engine)

        # Verify engines were created
        self.assertEqual(len(created_engines), 4)

        # Count using individual engine names to verify they exist and have correct status
        idle_engines = []
        running_engines = []
        completed_engines = []

        for i, engine in enumerate(created_engines):
            if engine.status == ENGINESTATUS_TYPES.IDLE:
                idle_engines.append(engine)
            elif engine.status == ENGINESTATUS_TYPES.RUNNING:
                running_engines.append(engine)
            elif engine.status == ENGINESTATUS_TYPES.COMPLETED:
                completed_engines.append(engine)

        # Verify counts
        self.assertEqual(len(idle_engines), 2)
        self.assertEqual(len(running_engines), 1)
        self.assertEqual(len(completed_engines), 1)

        # Also test database count queries
        total_test_engines = self.crud.count({"name__like": f"TestEngine{self.test_id}_count_%"})
        self.assertEqual(total_test_engines, 4)

    def test_EngineCRUD_Complex_Filters_Real(self):
        """Test EngineCRUD complex filters with real database"""
        # Create engines with different attributes
        test_data = [
            {"status": ENGINESTATUS_TYPES.IDLE, "is_live": False, "source": SOURCE_TYPES.SIM},
            {"status": ENGINESTATUS_TYPES.RUNNING, "is_live": True, "source": SOURCE_TYPES.REALTIME},
            {"status": ENGINESTATUS_TYPES.IDLE, "is_live": True, "source": SOURCE_TYPES.REALTIME},
            {"status": ENGINESTATUS_TYPES.COMPLETED, "is_live": False, "source": SOURCE_TYPES.SIM},
        ]

        for i, data in enumerate(test_data):
            params = self.test_engine_params.copy()
            params["name"] = f"TestEngine{self.test_id}_complex_{i}"
            params["status"] = data["status"]
            params["is_live"] = data["is_live"]
            params["source"] = data["source"]
            self.crud.create(**params)

        # Test combined filters
        filtered_engines = self.crud.find(
            filters={
                "name__like": f"TestEngine{self.test_id}_complex_%",
                "status": ENGINESTATUS_TYPES.IDLE,
                "is_live": True,
            }
        )

        # Should find 1 engine (IDLE + is_live=True)
        self.assertEqual(len(filtered_engines), 1)
        self.assertEqual(filtered_engines[0].status, ENGINESTATUS_TYPES.IDLE)
        self.assertEqual(filtered_engines[0].is_live, True)

        # Test IN operator for statuses
        multi_status_engines = self.crud.find(
            filters={
                "name__like": f"TestEngine{self.test_id}_complex_%",
                "status__in": [ENGINESTATUS_TYPES.RUNNING, ENGINESTATUS_TYPES.COMPLETED]
            }
        )

        # Should find 2 engines (RUNNING and COMPLETED)
        self.assertEqual(len(multi_status_engines), 2)
        statuses = [e.status for e in multi_status_engines]
        self.assertIn(ENGINESTATUS_TYPES.RUNNING, statuses)
        self.assertIn(ENGINESTATUS_TYPES.COMPLETED, statuses)

    def test_EngineCRUD_DataFrame_Output_Real(self):
        """Test EngineCRUD DataFrame output with real database"""
        # Create test engine
        created_engine = self.crud.create(**self.test_engine_params)

        # Get as DataFrame
        df_result = self.crud.find_by_status(ENGINESTATUS_TYPES.IDLE, as_dataframe=True)

        # Verify DataFrame
        import pandas as pd

        self.assertIsInstance(df_result, pd.DataFrame)
        self.assertGreaterEqual(len(df_result), 1)

        # Find our test engine in the DataFrame
        test_engine_rows = df_result[df_result["name"] == self.test_engine_name]
        self.assertEqual(len(test_engine_rows), 1)
        self.assertEqual(test_engine_rows.iloc[0]["name"], self.test_engine_name)

    def test_EngineCRUD_Bulk_Operations_With_Size_Verification_Real(self):
        """Test EngineCRUD bulk operations with table size verification"""
        # Get initial table size
        size0 = get_table_size(self.model)

        # Create bulk test data
        bulk_engines = []
        bulk_count = 5

        for i in range(bulk_count):
            engine = self.crud._create_from_params(
                name=f"TestEngine{self.test_id}_bulk_{i}",
                status=ENGINESTATUS_TYPES.IDLE if i % 2 == 0 else ENGINESTATUS_TYPES.RUNNING,
                is_live=i % 3 == 0,
                source=SOURCE_TYPES.SIM,
            )
            bulk_engines.append(engine)

        # Perform bulk addition
        result = self.crud.add_batch(bulk_engines)

        # Get table size after bulk addition
        size1 = get_table_size(self.model)

        # Verify table size increased by bulk_count
        self.assertEqual(bulk_count, size1 - size0)

        # Verify each engine was added correctly
        for i in range(bulk_count):
            found_engines = self.crud.find(filters={"name": f"TestEngine{self.test_id}_bulk_{i}"})
            self.assertEqual(len(found_engines), 1)
            expected_status = ENGINESTATUS_TYPES.IDLE if i % 2 == 0 else ENGINESTATUS_TYPES.RUNNING
            self.assertEqual(found_engines[0].status, expected_status)
            self.assertEqual(found_engines[0].is_live, i % 3 == 0)

        # Bulk delete test engines
        self.crud.remove({"name__like": f"TestEngine{self.test_id}_bulk_%"})

        # Get final table size
        size2 = get_table_size(self.model)

        # Verify table size returned to original
        self.assertEqual(size2, size0)

    def test_EngineCRUD_Exists_Real(self):
        """Test EngineCRUD exists functionality with real database"""
        # Test non-existent engine
        exists_before = self.crud.exists(filters={"name": self.test_engine_name})
        self.assertFalse(exists_before)

        # Create test engine
        created_engine = self.crud.create(**self.test_engine_params)

        # Test existing engine
        exists_after = self.crud.exists(filters={"name": self.test_engine_name})
        self.assertTrue(exists_after)

        # Test with more specific filters
        exists_specific = self.crud.exists(
            filters={
                "name": self.test_engine_name,
                "status": ENGINESTATUS_TYPES.IDLE,
                "is_live": False
            }
        )
        self.assertTrue(exists_specific)

        # Test with non-matching filters
        exists_false = self.crud.exists(
            filters={
                "name": self.test_engine_name,
                "status": ENGINESTATUS_TYPES.ERROR
            }
        )
        self.assertFalse(exists_false)

    def test_EngineCRUD_Exception_Handling_Real(self):
        """Test EngineCRUD exception handling with real database"""
        # Test find with empty filters (should not cause issues)
        all_engines = self.crud.find(filters={})
        self.assertIsInstance(all_engines, list)

        # Test delete with empty UUID (should raise ValueError)
        with self.assertRaises(ValueError):
            self.crud.delete_by_uuid("")

        # Test remove with overly broad filters (should be safe)
        self.crud.remove({})  # Should be safely handled without affecting other tests

        # Test create with invalid data types - should raise ValidationError
        if ValidationError is not None:
            # Test missing required name field
            with self.assertRaises(ValidationError):
                self.crud.create(
                    name="",  # Empty name should fail
                    status=ENGINESTATUS_TYPES.IDLE,
                    is_live=False,
                    source=SOURCE_TYPES.SIM
                )
                
            # Test invalid status enum
            with self.assertRaises(ValidationError):
                self.crud.create(
                    name=self.test_engine_name,
                    status="INVALID_STATUS",  # Invalid enum should fail
                    is_live=False,
                    source=SOURCE_TYPES.SIM
                )

            # Test invalid source enum
            with self.assertRaises(ValidationError):
                self.crud.create(
                    name=self.test_engine_name,
                    status=ENGINESTATUS_TYPES.IDLE,
                    is_live=False,
                    source="INVALID_SOURCE"  # Invalid enum should fail
                )

            # Test invalid boolean type
            with self.assertRaises(ValidationError):
                self.crud.create(
                    name=self.test_engine_name,
                    status=ENGINESTATUS_TYPES.IDLE,
                    is_live="not_a_boolean",  # Invalid boolean should fail
                    source=SOURCE_TYPES.SIM
                )