import unittest
import sys
import os
import uuid
from test.database.test_isolation import database_test_required


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

try:
    from ginkgo.data.crud.param_crud import ParamCRUD
    from ginkgo.data.crud.validation import ValidationError
    from ginkgo.data.models import MParam
    from ginkgo.enums import SOURCE_TYPES
    from ginkgo.libs import GCONF
    from ginkgo.data.drivers import get_db_connection, get_table_size, create_table, drop_table
    from sqlalchemy import text
except ImportError as e:
    print(f"Import error: {e}")
    ParamCRUD = None
    GCONF = None
    ValidationError = None


class ParamCRUDTest(unittest.TestCase):
    """
    ParamCRUD database integration tests.
    Tests Param-specific CRUD operations with actual database.
    """

    @classmethod
    def setUpClass(cls):
        """Class-level setup: check database configuration and connection"""
        if ParamCRUD is None or GCONF is None:
            raise AssertionError("ParamCRUD or GCONF not available")

        # Set model for table size verification
        cls.model = MParam

        # Recreate table for clean testing
        try:
            drop_table(cls.model, no_skip=True)
            create_table(cls.model, no_skip=True)
            print(":white_check_mark: Param table recreated for testing")
        except Exception as e:
            print(f":warning: Param table recreation failed: {e}")

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

        # Create ParamCRUD instance
        cls.crud = ParamCRUD()

        # Test database connection
        try:
            connection = get_db_connection(MParam)
            with connection.get_session() as session:
                session.execute(text("SELECT 1"))
            print(":white_check_mark: Param database connection successful")
        except Exception as e:
            raise AssertionError(f"Database connection failed: {e}")

    def setUp(self):
        """Setup for each test: prepare unique test data"""
        self.test_id = str(uuid.uuid4())[:8]
        self.test_mapping_id = f"TestMapping{self.test_id}"

        # Test param data based on actual MParam fields
        self.test_param_params = {
            "mapping_id": self.test_mapping_id,
            "index": 0,
            "value": "test_value_0",
            "source": SOURCE_TYPES.SIM,
        }

    def tearDown(self):
        """Cleanup after each test"""
        try:
            # Single pattern cleanup for all test data
            self.crud.remove({"mapping_id__like": f"TestMapping{self.test_id}%"})
        except Exception as e:
            print(f":warning: Cleanup failed: {e}")

    @classmethod
    def tearDownClass(cls):
        """Class-level cleanup: remove any remaining test data"""
        try:
            # Final cleanup of any remaining test records
            cls.crud.remove({"mapping_id__like": "TestMapping%"})
            print(":broom: Final cleanup of all TestMapping records completed")
        except Exception as e:
            print(f":warning: Final cleanup failed: {e}")

    @database_test_required
    def test_ParamCRUD_Create_From_Params_Real(self):
        """Test ParamCRUD create from parameters with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create param from parameters
        created_param = self.crud.create(**self.test_param_params)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify creation
        self.assertIsNotNone(created_param)
        self.assertIsInstance(created_param, MParam)
        self.assertEqual(created_param.mapping_id, self.test_mapping_id)
        self.assertEqual(created_param.index, 0)
        self.assertEqual(created_param.value, "test_value_0")
        self.assertEqual(created_param.source, SOURCE_TYPES.SIM)

        # Verify in database
        found_params = self.crud.find(filters={"mapping_id": self.test_mapping_id})
        self.assertEqual(len(found_params), 1)
        self.assertEqual(found_params[0].mapping_id, self.test_mapping_id)

    @database_test_required
    def test_ParamCRUD_Add_Param_Object_Real(self):
        """Test ParamCRUD add param object with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create param object (simple object with attributes)
        class ParamObj:
            def __init__(self, test_id):
                self.mapping_id = f"TestMapping{test_id}_obj"
                self.index = 1
                self.value = "test_value_obj"
                self.source = SOURCE_TYPES.DATABASE

        param_obj = ParamObj(self.test_id)

        # Convert param to MParam and add
        mparam = self.crud._convert_input_item(param_obj)
        added_param = self.crud.add(mparam)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify addition
        self.assertIsNotNone(added_param)
        self.assertEqual(added_param.mapping_id, f"TestMapping{self.test_id}_obj")
        self.assertEqual(added_param.index, 1)
        self.assertEqual(added_param.value, "test_value_obj")
        self.assertEqual(added_param.source, SOURCE_TYPES.DATABASE)

        # Verify in database
        found_params = self.crud.find(filters={"mapping_id": f"TestMapping{self.test_id}_obj"})
        self.assertEqual(len(found_params), 1)

    @database_test_required
    def test_ParamCRUD_Add_Batch_Real(self):
        """Test ParamCRUD batch addition with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create multiple param objects
        params = []
        batch_count = 3
        for i in range(batch_count):
            param = self.crud._create_from_params(
                mapping_id=f"TestMapping{self.test_id}_batch",
                index=i,
                value=f"batch_value_{i}",
                source=SOURCE_TYPES.SIM,
            )
            params.append(param)

        # Add batch
        result = self.crud.add_batch(params)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by batch count
        self.assertEqual(batch_count, size1 - size0)

        # Verify batch addition
        self.assertIsInstance(result, tuple)

        # Verify each param in database
        for i in range(batch_count):
            found_params = self.crud.find(filters={
                "mapping_id": f"TestMapping{self.test_id}_batch",
                "index": i
            })
            self.assertEqual(len(found_params), 1)
            self.assertEqual(found_params[0].value, f"batch_value_{i}")

    @database_test_required
    def test_ParamCRUD_Find_By_Mapping_ID_Real(self):
        """Test ParamCRUD find by mapping ID business helper method with real database"""
        # Create test params with same mapping_id but different indices
        for i in range(3):
            params = self.test_param_params.copy()
            params["index"] = i
            params["value"] = f"test_value_{i}"
            self.crud.create(**params)

        # Test find by mapping ID
        found_params = self.crud.find_by_mapping_id(self.test_mapping_id)

        # Should find 3 params ordered by index
        self.assertEqual(len(found_params), 3)
        for i, param in enumerate(found_params):
            self.assertEqual(param.mapping_id, self.test_mapping_id)
            self.assertEqual(param.index, i)
            self.assertEqual(param.value, f"test_value_{i}")

    @database_test_required
    def test_ParamCRUD_Find_By_Index_Range_Real(self):
        """Test ParamCRUD find by index range business helper method with real database"""
        # Create test params with different indices
        indices = [0, 1, 2, 3, 4, 5]
        for index in indices:
            params = self.test_param_params.copy()
            params["index"] = index
            params["value"] = f"range_value_{index}"
            self.crud.create(**params)

        # Test find by index range
        found_params = self.crud.find_by_index_range(self.test_mapping_id, 2, 4)

        # Should find 3 params (indices 2, 3, 4)
        self.assertEqual(len(found_params), 3)
        for i, param in enumerate(found_params):
            expected_index = i + 2
            self.assertEqual(param.index, expected_index)
            self.assertEqual(param.value, f"range_value_{expected_index}")

    @database_test_required
    def test_ParamCRUD_Find_By_Value_Pattern_Real(self):
        """Test ParamCRUD find by value pattern business helper method with real database"""
        # Create test params with different values
        values = ["pattern_test_1", "pattern_test_2", "other_value", "pattern_test_3"]
        for i, value in enumerate(values):
            params = self.test_param_params.copy()
            params["mapping_id"] = f"TestMapping{self.test_id}_pattern_{i}"
            params["index"] = i
            params["value"] = value
            self.crud.create(**params)

        # Test find by value pattern
        found_params = self.crud.find_by_value_pattern("pattern_test_%")

        # Should find 3 params with pattern_test_ values
        self.assertEqual(len(found_params), 3)
        for param in found_params:
            self.assertTrue(param.value.startswith("pattern_test_"))

    @database_test_required
    def test_ParamCRUD_Get_Set_Param_Value_Real(self):
        """Test ParamCRUD get and set param value business helper methods with real database"""
        # Test getting non-existent parameter (should return default)
        value = self.crud.get_param_value(self.test_mapping_id, 0, "default_value")
        self.assertEqual(value, "default_value")

        # Set a parameter value
        self.crud.set_param_value(self.test_mapping_id, 0, "initial_value")

        # Get the parameter value
        value = self.crud.get_param_value(self.test_mapping_id, 0)
        self.assertEqual(value, "initial_value")

        # Update the parameter value
        self.crud.set_param_value(self.test_mapping_id, 0, "updated_value")

        # Get the updated value
        value = self.crud.get_param_value(self.test_mapping_id, 0)
        self.assertEqual(value, "updated_value")

        # Verify in database
        found_params = self.crud.find(filters={"mapping_id": self.test_mapping_id, "index": 0})
        self.assertEqual(len(found_params), 1)
        self.assertEqual(found_params[0].value, "updated_value")

    @database_test_required
    def test_ParamCRUD_Get_All_Mapping_IDs_Real(self):
        """Test ParamCRUD get all mapping IDs business helper method with real database"""
        # Create params with different mapping IDs
        mapping_ids = [f"TestMapping{self.test_id}_id_{i}" for i in range(3)]
        for mapping_id in mapping_ids:
            params = self.test_param_params.copy()
            params["mapping_id"] = mapping_id
            self.crud.create(**params)

        # Get all mapping IDs
        all_mapping_ids = self.crud.get_all_mapping_ids()

        # Verify our test mapping IDs are included
        for test_mapping_id in mapping_ids:
            self.assertIn(test_mapping_id, all_mapping_ids)

    @database_test_required
    def test_ParamCRUD_Delete_By_UUID_Real(self):
        """Test ParamCRUD delete by UUID business helper method with real database"""
        # Create test param
        created_param = self.crud.create(**self.test_param_params)
        test_uuid = created_param.uuid

        # Verify param exists
        found_params = self.crud.find(filters={"uuid": test_uuid})
        self.assertEqual(len(found_params), 1)

        # Get table size before deletion
        size0 = get_table_size(self.model)

        # Delete by UUID
        self.crud.delete_by_uuid(test_uuid)

        # Get table size after deletion
        size1 = get_table_size(self.model)

        # Verify table size decreased by 1
        self.assertEqual(-1, size1 - size0)

        # Verify param no longer exists
        found_params_after = self.crud.find(filters={"uuid": test_uuid})
        self.assertEqual(len(found_params_after), 0)

        # Test delete with empty UUID (should raise ValueError)
        with self.assertRaises(ValueError):
            self.crud.delete_by_uuid("")

    @database_test_required
    def test_ParamCRUD_Update_Value_Real(self):
        """Test ParamCRUD update value business helper method with real database"""
        # Create test param
        created_param = self.crud.create(**self.test_param_params)
        test_uuid = created_param.uuid

        # Verify initial value
        self.assertEqual(created_param.value, "test_value_0")

        # Update value
        new_value = "updated_test_value"
        self.crud.update_value(test_uuid, new_value)

        # Verify value updated
        updated_params = self.crud.find(filters={"uuid": test_uuid})
        self.assertEqual(len(updated_params), 1)
        self.assertEqual(updated_params[0].value, new_value)

    @database_test_required
    def test_ParamCRUD_Complex_Filters_Real(self):
        """Test ParamCRUD complex filters with real database"""
        # Create params with different attributes
        test_data = [
            {"mapping_id": f"TestMapping{self.test_id}_complex_A", "index": 0, "value": "value_A_0", "source": SOURCE_TYPES.SIM},
            {"mapping_id": f"TestMapping{self.test_id}_complex_A", "index": 1, "value": "value_A_1", "source": SOURCE_TYPES.DATABASE},
            {"mapping_id": f"TestMapping{self.test_id}_complex_B", "index": 0, "value": "value_B_0", "source": SOURCE_TYPES.SIM},
            {"mapping_id": f"TestMapping{self.test_id}_complex_B", "index": 1, "value": "value_B_1", "source": SOURCE_TYPES.REALTIME},
        ]

        for data in test_data:
            self.crud.create(**data)

        # Test combined filters
        filtered_params = self.crud.find(
            filters={
                "mapping_id__like": f"TestMapping{self.test_id}_complex_%",
                "index": 0,
                "source": SOURCE_TYPES.SIM,
            }
        )

        # Should find 2 params (A_0 and B_0 with SIM source)
        self.assertEqual(len(filtered_params), 2)
        for param in filtered_params:
            self.assertEqual(param.index, 0)
            self.assertEqual(param.source, SOURCE_TYPES.SIM)

        # Test IN operator for mapping IDs
        multi_mapping_params = self.crud.find(
            filters={
                "mapping_id__in": [f"TestMapping{self.test_id}_complex_A", f"TestMapping{self.test_id}_complex_B"],
                "index": 1
            }
        )

        # Should find 2 params (A_1 and B_1)
        self.assertEqual(len(multi_mapping_params), 2)
        for param in multi_mapping_params:
            self.assertEqual(param.index, 1)

    @database_test_required
    def test_ParamCRUD_DataFrame_Output_Real(self):
        """Test ParamCRUD DataFrame output with real database"""
        # Create test param
        created_param = self.crud.create(**self.test_param_params)

        # Get as DataFrame
        df_result = self.crud.find_by_mapping_id(self.test_mapping_id, as_dataframe=True)

        # Verify DataFrame
        import pandas as pd

        self.assertIsInstance(df_result, pd.DataFrame)
        self.assertGreaterEqual(len(df_result), 1)

        # Find our test param in the DataFrame
        test_param_rows = df_result[df_result["mapping_id"] == self.test_mapping_id]
        self.assertEqual(len(test_param_rows), 1)
        self.assertEqual(test_param_rows.iloc[0]["mapping_id"], self.test_mapping_id)

    @database_test_required
    def test_ParamCRUD_Bulk_Operations_With_Size_Verification_Real(self):
        """Test ParamCRUD bulk operations with table size verification"""
        # Get initial table size
        size0 = get_table_size(self.model)

        # Create bulk test data
        bulk_params = []
        bulk_count = 5

        for i in range(bulk_count):
            param = self.crud._create_from_params(
                mapping_id=f"TestMapping{self.test_id}_bulk",
                index=i,
                value=f"bulk_value_{i}",
                source=SOURCE_TYPES.SIM,
            )
            bulk_params.append(param)

        # Perform bulk addition
        result = self.crud.add_batch(bulk_params)

        # Get table size after bulk addition
        size1 = get_table_size(self.model)

        # Verify table size increased by bulk_count
        self.assertEqual(bulk_count, size1 - size0)

        # Verify each param was added correctly
        for i in range(bulk_count):
            found_params = self.crud.find(filters={
                "mapping_id": f"TestMapping{self.test_id}_bulk",
                "index": i
            })
            self.assertEqual(len(found_params), 1)
            self.assertEqual(found_params[0].value, f"bulk_value_{i}")

        # Bulk delete test params
        self.crud.remove({"mapping_id": f"TestMapping{self.test_id}_bulk"})

        # Get final table size
        size2 = get_table_size(self.model)

        # Verify table size returned to original
        self.assertEqual(size2, size0)

    @database_test_required
    def test_ParamCRUD_Exists_Real(self):
        """Test ParamCRUD exists functionality with real database"""
        # Test non-existent param
        exists_before = self.crud.exists(filters={"mapping_id": self.test_mapping_id})
        self.assertFalse(exists_before)

        # Create test param
        created_param = self.crud.create(**self.test_param_params)

        # Test existing param
        exists_after = self.crud.exists(filters={"mapping_id": self.test_mapping_id})
        self.assertTrue(exists_after)

        # Test with more specific filters
        exists_specific = self.crud.exists(
            filters={
                "mapping_id": self.test_mapping_id,
                "index": 0,
                "value": "test_value_0"
            }
        )
        self.assertTrue(exists_specific)

        # Test with non-matching filters
        exists_false = self.crud.exists(
            filters={
                "mapping_id": self.test_mapping_id,
                "index": 999
            }
        )
        self.assertFalse(exists_false)

    @database_test_required
    def test_ParamCRUD_Range_Queries_Real(self):
        """Test ParamCRUD range queries with real database"""
        # Create params with sequential indices
        for i in range(10):
            params = self.test_param_params.copy()
            params["index"] = i
            params["value"] = f"range_test_{i}"
            self.crud.create(**params)

        # Test various range queries
        # Range query: index >= 3
        gte_params = self.crud.find(filters={
            "mapping_id": self.test_mapping_id,
            "index__gte": 3
        })
        self.assertEqual(len(gte_params), 7)  # indices 3-9

        # Range query: index <= 5
        lte_params = self.crud.find(filters={
            "mapping_id": self.test_mapping_id,
            "index__lte": 5
        })
        self.assertEqual(len(lte_params), 6)  # indices 0-5

        # Range query: 2 <= index <= 7
        range_params = self.crud.find(filters={
            "mapping_id": self.test_mapping_id,
            "index__gte": 2,
            "index__lte": 7
        })
        self.assertEqual(len(range_params), 6)  # indices 2-7
        for param in range_params:
            self.assertGreaterEqual(param.index, 2)
            self.assertLessEqual(param.index, 7)

    @database_test_required
    def test_ParamCRUD_Ordering_Real(self):
        """Test ParamCRUD ordering functionality with real database"""
        # Create params with different indices
        indices = [5, 1, 8, 3, 0, 7, 2]
        for index in indices:
            params = self.test_param_params.copy()
            params["index"] = index
            params["value"] = f"order_test_{index}"
            self.crud.create(**params)

        # Test default ordering (by index ascending)
        ordered_params = self.crud.find_by_mapping_id(self.test_mapping_id)
        self.assertEqual(len(ordered_params), len(indices))
        
        previous_index = -1
        for param in ordered_params:
            self.assertGreater(param.index, previous_index)
            previous_index = param.index

        # Test descending order
        desc_params = self.crud.find(
            filters={"mapping_id": self.test_mapping_id},
            order_by="index",
            desc_order=True
        )
        
        previous_index = float('inf')
        for param in desc_params:
            self.assertLess(param.index, previous_index)
            previous_index = param.index

    @database_test_required
    def test_ParamCRUD_Count_Operations_Real(self):
        """Test ParamCRUD count operations with real database"""
        # Create params with different mapping IDs
        mapping_counts = {
            f"TestMapping{self.test_id}_count_A": 3,
            f"TestMapping{self.test_id}_count_B": 5,
            f"TestMapping{self.test_id}_count_C": 2,
        }

        for mapping_id, count in mapping_counts.items():
            for i in range(count):
                params = self.test_param_params.copy()
                params["mapping_id"] = mapping_id
                params["index"] = i
                params["value"] = f"count_test_{i}"
                self.crud.create(**params)

        # Test count for specific mapping IDs
        for mapping_id, expected_count in mapping_counts.items():
            actual_count = self.crud.count({"mapping_id": mapping_id})
            self.assertEqual(actual_count, expected_count)

        # Test total count for all test mappings
        total_count = self.crud.count({"mapping_id__like": f"TestMapping{self.test_id}_count_%"})
        expected_total = sum(mapping_counts.values())
        self.assertEqual(total_count, expected_total)

    @database_test_required
    def test_ParamCRUD_Exception_Handling_Real(self):
        """Test ParamCRUD exception handling with real database"""
        # Test find with empty filters (should not cause issues)
        all_params = self.crud.find(filters={})
        self.assertIsInstance(all_params, list)

        # Test delete with empty UUID (should raise ValueError)
        with self.assertRaises(ValueError):
            self.crud.delete_by_uuid("")

        # Test remove with overly broad filters (should be safe)
        self.crud.remove({})  # Should be safely handled without affecting other tests

        # Test create with invalid data types - should raise ValidationError
        if ValidationError is not None:
            with self.assertRaises(ValidationError):
                invalid_params = self.test_param_params.copy()
                invalid_params["index"] = "invalid_index"  # String instead of int
                self.crud.create(**invalid_params)

            with self.assertRaises(ValidationError):
                invalid_params = self.test_param_params.copy()
                invalid_params["mapping_id"] = ""  # Empty string (min length 1)
                self.crud.create(**invalid_params)

    @database_test_required
    def test_ParamCRUD_Index_Validation_Real(self):
        """Test ParamCRUD index field validation (only int allowed)"""
        if ValidationError is not None:
            # Test float index (should be rejected)
            with self.assertRaises(ValidationError):
                invalid_params = self.test_param_params.copy()
                invalid_params["index"] = 1.5  # Float should be rejected
                self.crud.create(**invalid_params)

            # Test negative index (should be rejected due to min: 0)
            with self.assertRaises(ValidationError):
                invalid_params = self.test_param_params.copy()
                invalid_params["index"] = -1  # Negative should be rejected
                self.crud.create(**invalid_params)

            # Test valid int index (should pass)
            valid_params = self.test_param_params.copy()
            valid_params["index"] = 5  # Valid int
            created_param = self.crud.create(**valid_params)
            self.assertEqual(created_param.index, 5)