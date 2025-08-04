import unittest
import sys
import os
import uuid
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

try:
    from ginkgo.data.crud.handler_crud import HandlerCRUD
    from ginkgo.data.crud.validation import ValidationError
    from ginkgo.data.models import MHandler
    from ginkgo.enums import SOURCE_TYPES
    from ginkgo.libs import GCONF, datetime_normalize
    from ginkgo.data.drivers import get_db_connection, get_table_size, create_table, drop_table
    from sqlalchemy import text
except ImportError as e:
    print(f"Import error: {e}")
    HandlerCRUD = None
    GCONF = None
    ValidationError = None


class HandlerCRUDTest(unittest.TestCase):
    """
    HandlerCRUD database integration tests.
    Tests Handler-specific CRUD operations with actual database.
    """

    @classmethod
    def setUpClass(cls):
        """Class-level setup: check database configuration and connection"""
        if HandlerCRUD is None or GCONF is None:
            raise AssertionError("HandlerCRUD or GCONF not available")

        # Set model for table size verification
        cls.model = MHandler

        # Recreate table for clean testing
        try:
            drop_table(cls.model, no_skip=True)
            create_table(cls.model, no_skip=True)
            print(":white_check_mark: Handler table recreated for testing")
        except Exception as e:
            print(f":warning: Handler table recreation failed: {e}")

        # Verify database configuration (MHandler uses MySQL)
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

        # Create HandlerCRUD instance
        cls.crud = HandlerCRUD()

        # Test database connection
        try:
            connection = get_db_connection(MHandler)
            with connection.get_session() as session:
                session.execute(text("SELECT 1"))
            print(":white_check_mark: Handler database connection successful")
        except Exception as e:
            raise AssertionError(f"Database connection failed: {e}")

    def setUp(self):
        """Setup for each test: prepare unique test data"""
        self.test_id = str(uuid.uuid4())[:8]

        # Test handler data based on actual MHandler fields
        self.test_handler_params = {
            "name": f"TestHandler_{self.test_id}",
            "lib_path": f"/test/path/lib_{self.test_id}.py",
            "func_name": f"test_function_{self.test_id}",
            "source": SOURCE_TYPES.SIM,
        }

    def tearDown(self):
        """Cleanup after each test"""
        try:
            # Remove test records by name pattern (using actual field names)
            self.crud.remove({"name__like": f"TestHandler_{self.test_id}%"})
            self.crud.remove({"lib_path__like": f"/test/path/lib_{self.test_id}%"})
            print(f":broom: Cleaned up test data for handler {self.test_id}")
        except Exception as e:
            print(f":warning: Cleanup failed: {e}")
            # Fallback: try table recreation if remove fails
            try:
                drop_table(self.model, no_skip=True)
                create_table(self.model, no_skip=True)
                print(f":arrows_counterclockwise: Fallback cleanup: recreated handler table")
            except Exception as fallback_error:
                print(f":warning: Fallback cleanup also failed: {fallback_error}")

    @classmethod
    def tearDownClass(cls):
        """Class-level cleanup: remove any remaining test data"""
        try:
            # Final cleanup using actual field patterns
            cls.crud.remove({"name__like": "TestHandler_%"})
            cls.crud.remove({"lib_path__like": "/test/path/%"})
            print(":broom: Final cleanup of all handler test records completed")
        except Exception as e:
            print(f":warning: Final cleanup failed: {e}")
            # Fallback final cleanup
            try:
                drop_table(cls.model, no_skip=True)
                create_table(cls.model, no_skip=True)
                print(f":arrows_counterclockwise: Final fallback cleanup: recreated handler table")
            except Exception as fallback_error:
                print(f":warning: Final fallback cleanup also failed: {fallback_error}")

    def test_HandlerCRUD_Create_From_Params_Real(self):
        """Test HandlerCRUD create from parameters with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create handler from parameters
        created_handler = self.crud.create(**self.test_handler_params)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify creation
        self.assertIsNotNone(created_handler)
        self.assertIsInstance(created_handler, MHandler)
        self.assertEqual(created_handler.name, f"TestHandler_{self.test_id}")
        self.assertEqual(created_handler.lib_path, f"/test/path/lib_{self.test_id}.py")
        self.assertEqual(created_handler.func_name, f"test_function_{self.test_id}")
        self.assertEqual(created_handler.source, SOURCE_TYPES.SIM)

        # Verify in database
        found_handlers = self.crud.find(filters={"name": f"TestHandler_{self.test_id}"})
        self.assertEqual(len(found_handlers), 1)
        self.assertEqual(found_handlers[0].lib_path, f"/test/path/lib_{self.test_id}.py")

    def test_HandlerCRUD_Add_Handler_Object_Real(self):
        """Test HandlerCRUD add handler object with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create handler object (simple object with attributes)
        class HandlerObj:
            def __init__(self, test_id):
                self.name = f"TestHandlerObj_{test_id}"
                self.lib_path = f"/test/obj/lib_{test_id}.py"
                self.func_name = f"test_obj_function_{test_id}"
                self.source = SOURCE_TYPES.SIM

        handler_obj = HandlerObj(self.test_id)

        # Convert handler to MHandler and add
        mhandler = self.crud._convert_input_item(handler_obj)
        added_handler = self.crud.add(mhandler)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify addition
        self.assertIsNotNone(added_handler)
        self.assertEqual(added_handler.name, f"TestHandlerObj_{self.test_id}")
        self.assertEqual(added_handler.lib_path, f"/test/obj/lib_{self.test_id}.py")
        self.assertEqual(added_handler.source, SOURCE_TYPES.SIM)

        # Verify in database
        found_handlers = self.crud.find(filters={"name": f"TestHandlerObj_{self.test_id}"})
        self.assertEqual(len(found_handlers), 1)

    def test_HandlerCRUD_Add_Batch_Real(self):
        """Test HandlerCRUD batch addition with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create multiple handler objects
        handlers = []
        batch_count = 3
        for i in range(batch_count):
            handler = self.crud._create_from_params(
                name=f"BatchHandler_{self.test_id}_{i}",
                lib_path=f"/batch/lib_{self.test_id}_{i}.py",
                func_name=f"batch_function_{i}",
                source=SOURCE_TYPES.SIM,
            )
            handlers.append(handler)

        # Add batch
        result = self.crud.add_batch(handlers)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by batch count
        self.assertEqual(batch_count, size1 - size0)

        # Verify batch addition
        self.assertIsInstance(result, tuple)

        # Verify each handler in database
        for i in range(batch_count):
            found_handlers = self.crud.find(filters={"name": f"BatchHandler_{self.test_id}_{i}"})
            self.assertEqual(len(found_handlers), 1)
            self.assertEqual(found_handlers[0].lib_path, f"/batch/lib_{self.test_id}_{i}.py")

    def test_HandlerCRUD_Find_By_Name_Real(self):
        """Test HandlerCRUD find by name with real database"""
        # Create test handler
        created_handler = self.crud.create(**self.test_handler_params)

        # Test find by name
        found_handlers = self.crud.find(filters={"name": f"TestHandler_{self.test_id}"})
        self.assertEqual(len(found_handlers), 1)
        self.assertEqual(found_handlers[0].name, f"TestHandler_{self.test_id}")

        # Test find non-existent handler
        non_existent_handlers = self.crud.find(filters={"name": "NON_EXISTENT_HANDLER"})
        self.assertEqual(len(non_existent_handlers), 0)

    def test_HandlerCRUD_DataFrame_Output_Real(self):
        """Test HandlerCRUD DataFrame output with real database"""
        # Create test handler
        created_handler = self.crud.create(**self.test_handler_params)

        # Get as DataFrame
        df_result = self.crud.find(filters={"name": f"TestHandler_{self.test_id}"}, as_dataframe=True)

        # Verify DataFrame
        import pandas as pd

        self.assertIsInstance(df_result, pd.DataFrame)
        self.assertEqual(len(df_result), 1)
        self.assertEqual(df_result.iloc[0]["name"], f"TestHandler_{self.test_id}")

    def test_HandlerCRUD_Exception_Handling_Real(self):
        """Test HandlerCRUD exception handling with real database"""
        # Test find with empty filters (should not cause issues)
        all_handlers = self.crud.find(filters={})
        self.assertIsInstance(all_handlers, list)

        # Test create with minimal data
        minimal_params = {
            "name": f"MinimalHandler_{self.test_id}",
        }

        try:
            minimal_handler = self.crud.create(**minimal_params)
            self.assertIsNotNone(minimal_handler)
            # Should have default values
            self.assertEqual(minimal_handler.name, f"MinimalHandler_{self.test_id}")
            self.assertEqual(minimal_handler.lib_path, "")  # Default
            self.assertEqual(minimal_handler.func_name, "")  # Default
        except Exception as e:
            self.fail(f"Creating handler with minimal parameters should not fail: {e}")

        # Test conversion with invalid object
        invalid_conversion = self.crud._convert_input_item("invalid_object")
        self.assertIsNone(invalid_conversion)

    def test_HandlerCRUD_Name_Length_Validation_Real(self):
        """Test HandlerCRUD name field length validation (max 32 characters)"""
        if ValidationError is not None:
            # Test name too long (should be rejected)
            with self.assertRaises(ValidationError):
                invalid_params = self.test_handler_params.copy()
                invalid_params["name"] = "x" * 33  # Exceeds max length of 32
                self.crud.create(**invalid_params)

            # Test valid name length (should pass)
            valid_params = self.test_handler_params.copy()
            valid_params["name"] = "x" * 32  # Exactly max length
            created_handler = self.crud.create(**valid_params)
            self.assertEqual(len(created_handler.name), 32)

            # Test empty name (should be rejected due to min: 1)
            with self.assertRaises(ValidationError):
                invalid_params = self.test_handler_params.copy()
                invalid_params["name"] = ""  # Empty string
                self.crud.create(**invalid_params)

    def test_HandlerCRUD_Business_Helper_Methods_Real(self):
        """Test HandlerCRUD business helper methods with real database"""
        # Create test handlers
        handler1 = self.crud.create(**self.test_handler_params)
        
        params2 = self.test_handler_params.copy()
        params2["name"] = f"TestHandler2_{self.test_id}"
        params2["lib_path"] = f"/test/path2/lib_{self.test_id}.py"
        handler2 = self.crud.create(**params2)

        # Test find_by_uuid
        found_by_uuid = self.crud.find_by_uuid(handler1.uuid)
        self.assertEqual(len(found_by_uuid), 1)
        self.assertEqual(found_by_uuid[0].uuid, handler1.uuid)

        # Test find_by_name_pattern
        found_by_pattern = self.crud.find_by_name_pattern(f"TestHandler%{self.test_id}")
        self.assertGreaterEqual(len(found_by_pattern), 2)

        # Test find_by_lib_path
        found_by_lib_path = self.crud.find_by_lib_path(f"/test/path/lib_{self.test_id}.py")
        self.assertEqual(len(found_by_lib_path), 1)
        self.assertEqual(found_by_lib_path[0].lib_path, f"/test/path/lib_{self.test_id}.py")

        # Test get_all_uuids
        all_uuids = self.crud.get_all_uuids()
        self.assertIn(handler1.uuid, all_uuids)
        self.assertIn(handler2.uuid, all_uuids)

        # Test update_lib_path
        new_lib_path = f"/updated/path/lib_{self.test_id}.py"
        self.crud.update_lib_path(handler1.uuid, new_lib_path)
        updated_handler = self.crud.find_by_uuid(handler1.uuid)[0]
        self.assertEqual(updated_handler.lib_path, new_lib_path)

        # Test update_func_name
        new_func_name = f"updated_function_{self.test_id}"
        self.crud.update_func_name(handler1.uuid, new_func_name)
        updated_handler = self.crud.find_by_uuid(handler1.uuid)[0]
        self.assertEqual(updated_handler.func_name, new_func_name)

        # Test delete_by_uuid
        self.crud.delete_by_uuid(handler1.uuid)
        deleted_handler = self.crud.find_by_uuid(handler1.uuid)
        self.assertEqual(len(deleted_handler), 0)

        # Test delete with empty UUID (should raise ValueError)
        with self.assertRaises(ValueError):
            self.crud.delete_by_uuid("")
