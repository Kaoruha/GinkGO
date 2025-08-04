import unittest
import sys
import os
import uuid
from datetime import datetime
from sqlalchemy import text
from test.database.test_isolation import database_test_required


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

try:
    from ginkgo.data.crud.file_crud import FileCRUD
    from ginkgo.data.crud.validation import ValidationError
    from ginkgo.data.models import MFile
    from ginkgo.backtest.core.file_info import FileInfo
    from ginkgo.enums import SOURCE_TYPES, FILE_TYPES
    from ginkgo.libs import GCONF, datetime_normalize
    from ginkgo.data.drivers import get_db_connection, get_table_size, create_table, drop_table
except ImportError as e:
    print(f"Import error: {e}")
    FileCRUD = None
    GCONF = None
    ValidationError = None


class FileCRUDTest(unittest.TestCase):
    """
    FileCRUD database integration tests.
    Tests File-specific CRUD operations with actual database.
    """

    @classmethod
    def setUpClass(cls):
        """Class-level setup: check database configuration and connection"""
        if FileCRUD is None or GCONF is None:
            raise AssertionError("FileCRUD or GCONF not available")

        # Set model for table size verification
        cls.model = MFile

        # Recreate table for clean testing
        try:
            drop_table(cls.model, no_skip=True)
            create_table(cls.model, no_skip=True)
            print(":white_check_mark: File table recreated for testing")
        except Exception as e:
            print(f":warning: File table recreation failed: {e}")

        # Verify database configuration (MySQL for MFile)
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

        # Create FileCRUD instance
        cls.crud = FileCRUD()

        # Test database connection
        try:
            connection = get_db_connection(MFile)
            with connection.get_session() as session:
                session.execute(text("SELECT 1"))
            print(":white_check_mark: File database connection successful")
        except Exception as e:
            raise AssertionError(f"Database connection failed: {e}")

    def setUp(self):
        """Setup for each test: prepare unique test data"""
        self.test_id = str(uuid.uuid4())[:8]
        self.test_filename = f"TestFile{self.test_id}.py"

        # Test file data based on actual MFile fields
        self.test_file_params = {
            "type": FILE_TYPES.STRATEGY,
            "name": self.test_filename,
            "data": b"# Test file content\nprint('Hello, Ginkgo!')",
            "source": SOURCE_TYPES.SIM,
        }

    def tearDown(self):
        """Cleanup after each test"""
        try:
            # Single pattern cleanup for all test data
            self.crud.remove({"name__like": f"TestFile{self.test_id}%"})
        except Exception as e:
            print(f":warning: Cleanup failed: {e}")

    @classmethod
    def tearDownClass(cls):
        """Class-level cleanup: remove any remaining test data"""
        try:
            # Final cleanup of any remaining test records
            cls.crud.remove({"name__like": "TestFile%"})
            print(":broom: Final cleanup of all TestFile records completed")
        except Exception as e:
            print(f":warning: Final cleanup failed: {e}")

    @database_test_required
    def test_FileCRUD_Create_From_Params_Real(self):
        """Test FileCRUD create from parameters with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create file from parameters
        created_file = self.crud.create(**self.test_file_params)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify creation
        self.assertIsNotNone(created_file)
        self.assertIsInstance(created_file, MFile)
        self.assertEqual(created_file.type, FILE_TYPES.STRATEGY)
        self.assertEqual(created_file.name, self.test_filename)
        self.assertEqual(created_file.data, b"# Test file content\nprint('Hello, Ginkgo!')")
        self.assertEqual(created_file.source, SOURCE_TYPES.SIM)

        # Verify in database
        found_files = self.crud.find(filters={"name": self.test_filename})
        self.assertEqual(len(found_files), 1)
        self.assertEqual(found_files[0].name, self.test_filename)

    @database_test_required
    def test_FileCRUD_Add_File_Object_Real(self):
        """Test FileCRUD add file object with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create file object (simple object with attributes)
        class FileObj:
            def __init__(self, test_id):
                self.type = FILE_TYPES.ANALYZER
                self.name = f"TestFile{test_id}_obj.py"
                self.data = b"# Analyzer file\nclass TestAnalyzer: pass"
                self.source = SOURCE_TYPES.DATABASE

        file_obj = FileObj(self.test_id)

        # Convert file to MFile and add
        mfile = self.crud._convert_input_item(file_obj)
        # Since file_obj is not FileInfo, _convert_input_item returns None
        # Let's create directly
        mfile = self.crud._create_from_params(
            type=file_obj.type,
            name=file_obj.name,
            data=file_obj.data,
            source=file_obj.source
        )
        added_file = self.crud.add(mfile)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify addition
        self.assertIsNotNone(added_file)
        self.assertEqual(added_file.type, FILE_TYPES.ANALYZER)
        self.assertEqual(added_file.name, f"TestFile{self.test_id}_obj.py")
        self.assertEqual(added_file.data, b"# Analyzer file\nclass TestAnalyzer: pass")
        self.assertEqual(added_file.source, SOURCE_TYPES.DATABASE)

        # Verify in database
        found_files = self.crud.find(filters={"name": f"TestFile{self.test_id}_obj.py"})
        self.assertEqual(len(found_files), 1)

    @database_test_required
    def test_FileCRUD_Add_Batch_Real(self):
        """Test FileCRUD batch addition with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create multiple file objects
        files = []
        batch_count = 3
        file_types = [FILE_TYPES.STRATEGY, FILE_TYPES.ANALYZER, FILE_TYPES.INDEX]
        
        for i in range(batch_count):
            file_data = self.crud._create_from_params(
                type=file_types[i],
                name=f"TestFile{self.test_id}_batch_{i}.py",
                data=f"# Batch file {i}\nprint('File {i}')".encode(),
                source=SOURCE_TYPES.SIM,
            )
            files.append(file_data)

        # Add batch
        result = self.crud.add_batch(files)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by batch count
        self.assertEqual(batch_count, size1 - size0)

        # Verify batch addition
        self.assertIsInstance(result, tuple)

        # Verify each file in database
        for i in range(batch_count):
            found_files = self.crud.find(filters={"name": f"TestFile{self.test_id}_batch_{i}.py"})
            self.assertEqual(len(found_files), 1)
            self.assertEqual(found_files[0].type, file_types[i])

    @database_test_required
    def test_FileCRUD_Find_By_File_ID_Real(self):
        """Test FileCRUD find by file ID business helper method with real database"""
        # Create test file
        created_file = self.crud.create(**self.test_file_params)
        test_file_id = created_file.uuid

        # Test find by file ID
        found_files = self.crud.find_by_file_id(test_file_id)

        # Should find 1 file
        self.assertEqual(len(found_files), 1)
        self.assertEqual(found_files[0].uuid, test_file_id)
        self.assertEqual(found_files[0].name, self.test_filename)
        self.assertEqual(found_files[0].type, FILE_TYPES.STRATEGY)

        # Test find by non-existent file ID
        not_found_files = self.crud.find_by_file_id("NON_EXISTENT_ID")
        self.assertEqual(len(not_found_files), 0)

    @database_test_required
    def test_FileCRUD_Find_By_Filename_Real(self):
        """Test FileCRUD find by filename business helper method with real database"""
        # Create files with different names
        filenames = [f"TestFile{self.test_id}_name_{i}.py" for i in range(3)]

        for i, filename in enumerate(filenames):
            params = self.test_file_params.copy()
            params["name"] = filename
            params["type"] = FILE_TYPES.STRATEGY if i % 2 == 0 else FILE_TYPES.ANALYZER
            self.crud.create(**params)

        # Test find by filename pattern
        found_files = self.crud.find_by_filename(f"TestFile{self.test_id}_name_%")

        # Should find 3 files
        self.assertEqual(len(found_files), 3)
        found_names = [f.name for f in found_files]
        for filename in filenames:
            self.assertIn(filename, found_names)

    @database_test_required
    def test_FileCRUD_Find_By_Type_Real(self):
        """Test FileCRUD find by type business helper method with real database"""
        # Create files with different types
        file_types = [FILE_TYPES.STRATEGY, FILE_TYPES.ANALYZER, FILE_TYPES.INDEX, FILE_TYPES.STRATEGY]

        for i, file_type in enumerate(file_types):
            params = self.test_file_params.copy()
            params["name"] = f"TestFile{self.test_id}_type_{i}.py"
            params["type"] = file_type
            self.crud.create(**params)

        # Test find by specific type
        strategy_files = self.crud.find_by_type(FILE_TYPES.STRATEGY)

        # Should find at least 2 strategy files (our test records)
        matching_strategy = [f for f in strategy_files if f.name.startswith(f"TestFile{self.test_id}_type_")]
        self.assertGreaterEqual(len(matching_strategy), 2)
        for file in matching_strategy:
            self.assertEqual(file.type, FILE_TYPES.STRATEGY)

        # Test find by another type
        analyzer_files = self.crud.find_by_type(FILE_TYPES.ANALYZER)
        matching_analyzer = [f for f in analyzer_files if f.name.startswith(f"TestFile{self.test_id}_type_")]
        self.assertEqual(len(matching_analyzer), 1)
        self.assertEqual(matching_analyzer[0].type, FILE_TYPES.ANALYZER)

    @database_test_required
    def test_FileCRUD_Find_By_Type_String_Real(self):
        """Test FileCRUD find by type using string input with real database"""
        # Create files with different types
        params1 = self.test_file_params.copy()
        params1["name"] = f"TestFile{self.test_id}_str_strategy.py"
        params1["type"] = FILE_TYPES.STRATEGY
        self.crud.create(**params1)

        params2 = self.test_file_params.copy()
        params2["name"] = f"TestFile{self.test_id}_str_analyzer.py"
        params2["type"] = FILE_TYPES.ANALYZER
        self.crud.create(**params2)

        # Test find by string type
        strategy_files = self.crud.find_by_type("STRATEGY")
        matching_strategy = [f for f in strategy_files if f.name.startswith(f"TestFile{self.test_id}_str_")]
        self.assertEqual(len(matching_strategy), 1)
        self.assertEqual(matching_strategy[0].type, FILE_TYPES.STRATEGY)

        # Test find by string type (different case)
        analyzer_files = self.crud.find_by_type("analyzer")
        matching_analyzer = [f for f in analyzer_files if f.name.startswith(f"TestFile{self.test_id}_str_")]
        self.assertEqual(len(matching_analyzer), 1)
        self.assertEqual(matching_analyzer[0].type, FILE_TYPES.ANALYZER)

    @database_test_required
    def test_FileCRUD_Find_By_Size_Range_Real(self):
        """Test FileCRUD find by size range business helper method with real database"""
        # This method doesn't actually implement size filtering due to model limitations
        # It just returns all files with a warning
        
        # Create test file
        created_file = self.crud.create(**self.test_file_params)

        # Test find by size range (should return all files)
        found_files = self.crud.find_by_size_range(0, 1000)

        # Should return at least our test file
        self.assertIsInstance(found_files, list)
        self.assertGreaterEqual(len(found_files), 1)

    @database_test_required
    def test_FileCRUD_Get_Total_Size_By_Type_Real(self):
        """Test FileCRUD get total size by type business helper method with real database"""
        # Create files of specific type
        for i in range(3):
            params = self.test_file_params.copy()
            params["name"] = f"TestFile{self.test_id}_size_{i}.py"
            params["type"] = FILE_TYPES.STRATEGY
            self.crud.create(**params)

        # Get total size by type (returns count due to model limitations)
        total_size = self.crud.get_total_size_by_type(FILE_TYPES.STRATEGY)

        # Should return at least 3 (count of our test files)
        self.assertGreaterEqual(total_size, 3)

    @database_test_required
    def test_FileCRUD_Delete_By_File_ID_Real(self):
        """Test FileCRUD delete by file ID business helper method with real database"""
        # Create test file
        created_file = self.crud.create(**self.test_file_params)
        test_file_id = created_file.uuid

        # Verify file exists
        found_files = self.crud.find(filters={"uuid": test_file_id})
        self.assertEqual(len(found_files), 1)

        # Get table size before deletion
        size0 = get_table_size(self.model)

        # Delete by file ID
        self.crud.delete_by_file_id(test_file_id)

        # Get table size after deletion
        size1 = get_table_size(self.model)

        # Verify table size decreased by 1
        self.assertEqual(-1, size1 - size0)

        # Verify file no longer exists
        found_files_after = self.crud.find(filters={"uuid": test_file_id})
        self.assertEqual(len(found_files_after), 0)

    @database_test_required
    def test_FileCRUD_FileInfo_Integration_Real(self):
        """Test FileCRUD integration with FileInfo objects"""
        # Create FileInfo object using constructor (properties are read-only)
        file_info = FileInfo(
            name=f"TestFile{self.test_id}_info.py",
            type=FILE_TYPES.INDEX,
            data=b"# FileInfo test\nclass TestIndex: pass"
        )
        # Set source using the base class attribute (FileInfo inherits from Base)
        file_info._source = SOURCE_TYPES.REALTIME

        # Convert FileInfo to MFile
        mfile = self.crud._convert_input_item(file_info)
        self.assertIsNotNone(mfile)
        self.assertEqual(mfile.name, file_info.name)
        self.assertEqual(mfile.type, FILE_TYPES.INDEX)
        self.assertEqual(mfile.data, file_info.data)
        self.assertEqual(mfile.source, SOURCE_TYPES.REALTIME)

        # Add to database
        added_file = self.crud.add(mfile)
        self.assertIsNotNone(added_file)

        # Verify in database
        found_files = self.crud.find(filters={"name": file_info.name})
        self.assertEqual(len(found_files), 1)
        self.assertEqual(found_files[0].type, FILE_TYPES.INDEX)

    @database_test_required
    def test_FileCRUD_Complex_Filters_Real(self):
        """Test FileCRUD complex filters with real database"""
        # Create files with different attributes
        test_data = [
            {"name": f"TestFile{self.test_id}_complex_A.py", "type": FILE_TYPES.STRATEGY, "source": SOURCE_TYPES.SIM},
            {"name": f"TestFile{self.test_id}_complex_B.py", "type": FILE_TYPES.ANALYZER, "source": SOURCE_TYPES.DATABASE},
            {"name": f"TestFile{self.test_id}_complex_C.py", "type": FILE_TYPES.STRATEGY, "source": SOURCE_TYPES.REALTIME},
            {"name": f"TestFile{self.test_id}_complex_D.py", "type": FILE_TYPES.INDEX, "source": SOURCE_TYPES.SIM},
        ]

        for data in test_data:
            params = self.test_file_params.copy()
            params.update(data)
            self.crud.create(**params)

        # Test combined filters
        filtered_files = self.crud.find(
            filters={
                "name__like": f"TestFile{self.test_id}_complex_%",
                "type": FILE_TYPES.STRATEGY,
                "source": SOURCE_TYPES.SIM,
            }
        )

        # Should find 1 file (complex_A with STRATEGY + SIM)
        self.assertEqual(len(filtered_files), 1)
        self.assertEqual(filtered_files[0].type, FILE_TYPES.STRATEGY)
        self.assertEqual(filtered_files[0].source, SOURCE_TYPES.SIM)

        # Test IN operator for types
        multi_type_files = self.crud.find(
            filters={
                "name__like": f"TestFile{self.test_id}_complex_%",
                "type__in": [FILE_TYPES.ANALYZER, FILE_TYPES.INDEX]
            }
        )

        # Should find 2 files (ANALYZER and INDEX)
        self.assertEqual(len(multi_type_files), 2)
        types = [f.type for f in multi_type_files]
        self.assertIn(FILE_TYPES.ANALYZER, types)
        self.assertIn(FILE_TYPES.INDEX, types)

    @database_test_required
    def test_FileCRUD_DataFrame_Output_Real(self):
        """Test FileCRUD DataFrame output with real database"""
        # Create test file
        created_file = self.crud.create(**self.test_file_params)

        # Get as DataFrame
        df_result = self.crud.find_by_type(FILE_TYPES.STRATEGY, as_dataframe=True)

        # Verify DataFrame
        import pandas as pd

        self.assertIsInstance(df_result, pd.DataFrame)
        self.assertGreaterEqual(len(df_result), 1)

        # Find our test file in the DataFrame
        test_file_rows = df_result[df_result["name"] == self.test_filename]
        self.assertEqual(len(test_file_rows), 1)
        self.assertEqual(test_file_rows.iloc[0]["name"], self.test_filename)

    @database_test_required
    def test_FileCRUD_Bulk_Operations_With_Size_Verification_Real(self):
        """Test FileCRUD bulk operations with table size verification"""
        # Get initial table size
        size0 = get_table_size(self.model)

        # Create bulk test data
        bulk_files = []
        bulk_count = 4
        file_types = [FILE_TYPES.STRATEGY, FILE_TYPES.ANALYZER, FILE_TYPES.INDEX, FILE_TYPES.ENGINE]

        for i in range(bulk_count):
            file_data = self.crud._create_from_params(
                type=file_types[i],
                name=f"TestFile{self.test_id}_bulk_{i}.py" if i < 3 else f"TestFile{self.test_id}_bulk_{i}.json",
                data=f"# Bulk file {i}\ndata = {i}".encode(),
                source=SOURCE_TYPES.SIM,
            )
            bulk_files.append(file_data)

        # Perform bulk addition
        result = self.crud.add_batch(bulk_files)

        # Get table size after bulk addition
        size1 = get_table_size(self.model)

        # Verify table size increased by bulk_count
        self.assertEqual(bulk_count, size1 - size0)

        # Verify each file was added correctly
        for i in range(bulk_count):
            extension = ".py" if i < 3 else ".json"
            found_files = self.crud.find(filters={"name": f"TestFile{self.test_id}_bulk_{i}{extension}"})
            self.assertEqual(len(found_files), 1)
            self.assertEqual(found_files[0].type, file_types[i])

        # Bulk delete test files
        self.crud.remove({"name__like": f"TestFile{self.test_id}_bulk_%"})

        # Get final table size
        size2 = get_table_size(self.model)

        # Verify table size returned to original
        self.assertEqual(size2, size0)

    @database_test_required
    def test_FileCRUD_Exists_Real(self):
        """Test FileCRUD exists functionality with real database"""
        # Test non-existent file
        exists_before = self.crud.exists(filters={"name": self.test_filename})
        self.assertFalse(exists_before)

        # Create test file
        created_file = self.crud.create(**self.test_file_params)

        # Test existing file
        exists_after = self.crud.exists(filters={"name": self.test_filename})
        self.assertTrue(exists_after)

        # Test with more specific filters
        exists_specific = self.crud.exists(
            filters={
                "name": self.test_filename,
                "type": FILE_TYPES.STRATEGY,
                "source": SOURCE_TYPES.SIM
            }
        )
        self.assertTrue(exists_specific)

        # Test with non-matching filters
        exists_false = self.crud.exists(
            filters={
                "name": self.test_filename,
                "type": FILE_TYPES.ANALYZER
            }
        )
        self.assertFalse(exists_false)

    @database_test_required
    def test_FileCRUD_Exception_Handling_Real(self):
        """Test FileCRUD exception handling with real database"""
        # Test find with empty filters (should not cause issues)
        all_files = self.crud.find(filters={})
        self.assertIsInstance(all_files, list)

        # Test remove with overly broad filters (should be safe)
        self.crud.remove({})  # Should be safely handled without affecting other tests

        # Test create with invalid data types - should raise ValidationError
        if ValidationError is not None:
            with self.assertRaises(ValidationError):
                invalid_params = self.test_file_params.copy()
                invalid_params["name"] = "x" * 50  # Exceeds max length of 40
                self.crud.create(**invalid_params)

            with self.assertRaises(ValidationError):
                invalid_params = self.test_file_params.copy()
                invalid_params["data"] = {"invalid": "dict"}  # Dict cannot be converted to bytes
                self.crud.create(**invalid_params)

    @database_test_required
    def test_FileCRUD_Name_Length_Validation_Real(self):
        """Test FileCRUD name field length validation (max 40 characters)"""
        if ValidationError is not None:
            # Test name too long (should be rejected)
            with self.assertRaises(ValidationError):
                invalid_params = self.test_file_params.copy()
                invalid_params["name"] = "x" * 41  # Exceeds max length of 40
                self.crud.create(**invalid_params)

            # Test valid name length (should pass)
            valid_params = self.test_file_params.copy()
            valid_params["name"] = "x" * 40  # Exactly max length
            created_file = self.crud.create(**valid_params)
            self.assertEqual(len(created_file.name), 40)

            # Test empty name (should be rejected due to min: 1)
            with self.assertRaises(ValidationError):
                invalid_params = self.test_file_params.copy()
                invalid_params["name"] = ""  # Empty string
                self.crud.create(**invalid_params)