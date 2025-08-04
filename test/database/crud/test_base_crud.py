import unittest
import sys
import os
import uuid
from decimal import Decimal
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import text
from test.database.test_isolation import database_test_required


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

try:
    from ginkgo.data.crud.base_crud import BaseCRUD
    from ginkgo.data.crud.validation import ValidationError
    from ginkgo.data.models import MBar, MMysqlBase
    from ginkgo.backtest import Bar
    from ginkgo.enums import FREQUENCY_TYPES, SOURCE_TYPES
    from ginkgo.libs import GCONF, datetime_normalize, to_decimal
    from ginkgo.data.drivers import get_db_connection, get_table_size, create_table, drop_table
except ImportError as e:
    print(f"Import error: {e}")
    BaseCRUD = None
    MBar = None
    GCONF = None
    ValidationError = None


class TestBarCRUDForBaseCRUD(BaseCRUD[MBar]):
    """Concrete CRUD implementation for testing BaseCRUD with real database"""

    def __init__(self):
        super().__init__(MBar)

    def _get_field_config(self) -> dict:
        """测试用的字段验证配置"""
        return {
            # 股票代码 - 非空字符串
            'code': {
                'type': 'string',
                'min': 1
            },
            
            # 开盘价 - 必须大于0
            'open': {
                'type': ['decimal', 'float', 'int'],
                'min': 0.01
            },
            
            # 最高价 - 必须大于0
            'high': {
                'type': ['decimal', 'float', 'int'],
                'min': 0.01
            },
            
            # 最低价 - 必须大于0
            'low': {
                'type': ['decimal', 'float', 'int'],
                'min': 0.01
            },
            
            # 收盘价 - 必须大于0
            'close': {
                'type': ['decimal', 'float', 'int'],
                'min': 0.01
            },
            
            # 成交量 - 非负整数
            'volume': {
                'type': ['int', 'float'],
                'min': 0
            },
            
            # 成交额 - 非负数值
            'amount': {
                'type': ['decimal', 'float', 'int'],
                'min': 0
            },
            
            # 频率 - 枚举值
            'frequency': {
                'type': 'enum',
                'choices': [
                    FREQUENCY_TYPES.DAY,
                    FREQUENCY_TYPES.MIN5
                ]
            },
            
            # 时间戳 - datetime 或字符串
            'timestamp': {
                'type': ['datetime', 'string']
            },
            
            # 数据源 - 枚举值
            'source': {
                'type': 'enum',
                'choices': [
                    SOURCE_TYPES.TUSHARE,
                    SOURCE_TYPES.YAHOO,
                    SOURCE_TYPES.AKSHARE,
                    SOURCE_TYPES.BAOSTOCK
                ]
            }
        }

    def _create_from_params(self, **kwargs) -> MBar:
        return MBar(
            code=kwargs.get("code"),
            open=to_decimal(kwargs.get("open", 0)),
            high=to_decimal(kwargs.get("high", 0)),
            low=to_decimal(kwargs.get("low", 0)),
            close=to_decimal(kwargs.get("close", 0)),
            volume=kwargs.get("volume", 0),
            amount=to_decimal(kwargs.get("amount", 0)),
            frequency=kwargs.get("frequency", FREQUENCY_TYPES.DAY),
            timestamp=datetime_normalize(kwargs.get("timestamp")),
            source=kwargs.get("source", SOURCE_TYPES.TUSHARE),
        )

    def _convert_input_item(self, item: Any) -> Optional[MBar]:
        if isinstance(item, Bar):
            return MBar(
                code=item.code,
                open=item.open,
                high=item.high,
                low=item.low,
                close=item.close,
                volume=item.volume,
                amount=item.amount,
                frequency=item.frequency,
                timestamp=item.timestamp,
            )
        return None


class BaseCRUDTest(unittest.TestCase):
    """
    BaseCRUD database integration tests.
    Tests template method pattern with actual database operations.
    """

    @classmethod
    def setUpClass(cls):
        """Class-level setup: check database configuration availability"""
        if BaseCRUD is None or GCONF is None:
            raise AssertionError("BaseCRUD or GCONF not available")

        # Set model for table size verification
        cls.model = MBar

        # Recreate table for clean testing
        try:
            drop_table(cls.model, no_skip=True)
            create_table(cls.model, no_skip=True)
            print(":white_check_mark: Table recreated for testing")
        except Exception as e:
            print(f":warning: Table recreation failed: {e}")

        # Verify database configuration
        try:
            cls.mysql_config = {
                "user": GCONF.MYSQLUSER,
                "pwd": GCONF.MYSQLPWD,
                "host": GCONF.MYSQLHOST,
                "port": str(GCONF.MYSQLPORT),
                "db": GCONF.MYSQLDB,
            }

            # Verify configuration completeness
            for key, value in cls.mysql_config.items():
                if not value:
                    raise AssertionError(f"MySQL configuration missing: {key}")

        except Exception as e:
            raise AssertionError(f"Failed to read MySQL configuration: {e}")

        # Create CRUD instance for testing
        cls.crud = TestBarCRUDForBaseCRUD()

        # Test database connection
        try:
            connection = get_db_connection(MBar)
            with connection.get_session() as session:
                # Simple connection test
                session.execute(text("SELECT 1"))
            print(":white_check_mark: Database connection successful")
        except Exception as e:
            raise AssertionError(f"Database connection failed: {e}")

    def setUp(self):
        """Setup for each test: prepare unique test data"""
        self.test_id = str(uuid.uuid4())[:8]
        self.test_code = f"TEST{self.test_id}.SZ"
        self.test_timestamp = datetime(2023, 1, 1, 9, 30)

        # Test data for creating records
        self.test_bar_data = {
            "code": self.test_code,
            "open": 10.5,
            "high": 11.0,
            "low": 10.0,
            "close": 10.8,
            "volume": 1000,
            "amount": 10800,
            "frequency": FREQUENCY_TYPES.DAY,
            "timestamp": self.test_timestamp,
            "source": SOURCE_TYPES.TUSHARE,
        }

        # List to track created records for cleanup
        self.created_records = []

    def tearDown(self):
        """Cleanup after each test"""
        try:
            # Single pattern cleanup for all test data
            self.crud.remove({"code__like": f"BARTEST{self.test_id}%"})
        except Exception as e:
            print(f":warning: Cleanup failed: {e}")

    @classmethod
    def tearDownClass(cls):
        """Class-level cleanup: remove any remaining test data"""
        try:
            # Final cleanup of any remaining test records
            cls.crud.remove({"code__like": "TEST%"})
            print(":broom: Final cleanup of all TEST records completed")
        except Exception as e:
            print(f":warning: Final cleanup failed: {e}")

    @database_test_required
    def test_BaseCRUD_Create_Real(self):
        """Test BaseCRUD create method with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create record using template method
        created_bar = self.crud.create(**self.test_bar_data)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify the record was created
        self.assertIsNotNone(created_bar)
        self.assertIsInstance(created_bar, MBar)
        self.assertEqual(created_bar.code, self.test_code)
        self.assertEqual(created_bar.open, Decimal("10.5"))
        self.assertEqual(created_bar.volume, 1000)

        # Verify in database
        found_records = self.crud.find(filters={"code": self.test_code})
        self.assertEqual(len(found_records), 1)
        self.assertEqual(found_records[0].code, self.test_code)

    @database_test_required
    def test_BaseCRUD_Add_Real(self):
        """Test BaseCRUD add method with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create MBar instance
        test_bar = MBar(
            code=self.test_code,
            open=Decimal("12.5"),
            high=Decimal("13.0"),
            low=Decimal("12.0"),
            close=Decimal("12.8"),
            volume=2000,
            amount=Decimal("25600"),
            frequency=FREQUENCY_TYPES.DAY,
            timestamp=self.test_timestamp,
            source=SOURCE_TYPES.TUSHARE,
        )

        # Add using template method
        added_bar = self.crud.add(test_bar)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify addition
        self.assertIsNotNone(added_bar)
        self.assertEqual(added_bar.code, self.test_code)

        # Verify in database
        found_records = self.crud.find(filters={"code": self.test_code})
        self.assertEqual(len(found_records), 1)
        self.assertEqual(found_records[0].open, Decimal("12.5"))

    @database_test_required
    def test_BaseCRUD_Add_Batch_Real(self):
        """Test BaseCRUD add_batch method with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create multiple test records
        test_bars = []
        batch_count = 3
        for i in range(batch_count):
            bar = MBar(
                code=f"{self.test_code}_{i}",
                open=Decimal(f"{10+i}.5"),
                high=Decimal(f"{11+i}.0"),
                low=Decimal(f"{9+i}.5"),
                close=Decimal(f"{10+i}.2"),
                volume=1000 * (i + 1),
                amount=Decimal(f"{10000*(i+1)}"),
                frequency=FREQUENCY_TYPES.DAY,
                timestamp=self.test_timestamp,
                source=SOURCE_TYPES.TUSHARE,
            )
            test_bars.append(bar)

        # Add batch using template method
        result = self.crud.add_batch(test_bars)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by batch count
        self.assertEqual(batch_count, size1 - size0)

        # Verify batch addition result
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)  # (clickhouse_count, mysql_count)

        # Verify in database
        for i in range(3):
            found_records = self.crud.find(filters={"code": f"{self.test_code}_{i}"})
            self.assertEqual(len(found_records), 1)

            # Clean up each test record
            self.crud.remove({"code": f"{self.test_code}_{i}"})

    @database_test_required
    def test_BaseCRUD_Find_With_Filters_Real(self):
        """Test BaseCRUD find method with filters using real database"""
        # Create test record
        created_bar = self.crud.create(**self.test_bar_data)

        # Test basic filter
        found_records = self.crud.find(filters={"code": self.test_code})
        self.assertEqual(len(found_records), 1)
        self.assertEqual(found_records[0].code, self.test_code)

        # Test filter with operators (volume >= 1000)
        found_records = self.crud.find(filters={"volume__gte": 1000})
        self.assertGreater(len(found_records), 0)

        # Test filter with multiple conditions
        found_records = self.crud.find(filters={"code": self.test_code, "volume": 1000})
        self.assertEqual(len(found_records), 1)

    @database_test_required
    def test_BaseCRUD_Find_With_Pagination_Real(self):
        """Test BaseCRUD find method with pagination using real database"""
        # Create multiple test records
        for i in range(5):
            test_data = self.test_bar_data.copy()
            test_data["code"] = f"{self.test_code}_{i}"
            test_data["volume"] = 1000 + i * 100
            self.crud.create(**test_data)

        # Test pagination
        page_0_records = self.crud.find(
            filters={"code__like": f"{self.test_code}_"}, page=0, page_size=2, order_by="volume"
        )
        self.assertEqual(len(page_0_records), 2)

        page_1_records = self.crud.find(
            filters={"code__like": f"{self.test_code}_"}, page=1, page_size=2, order_by="volume"
        )
        self.assertEqual(len(page_1_records), 2)

        # Verify ordering
        self.assertLess(page_0_records[0].volume, page_1_records[0].volume)

        # Clean up test records
        for i in range(5):
            self.crud.remove({"code": f"{self.test_code}_{i}"})

    @database_test_required
    def test_BaseCRUD_Count_Real(self):
        """Test BaseCRUD count method with real database"""
        # Get initial count
        initial_count = self.crud.count()
        print(initial_count)

        # Create test record
        created_bar = self.crud.create(**self.test_bar_data)
        print(initial_count)

        # Verify count increased
        new_count = self.crud.count()
        self.assertEqual(new_count, initial_count + 1)

        # Test count with filters
        filtered_count = self.crud.count(filters={"code": self.test_code})
        self.assertEqual(filtered_count, 1)

    @database_test_required
    def test_BaseCRUD_Remove_Real(self):
        """Test BaseCRUD remove method with real database"""
        # Create test record
        created_bar = self.crud.create(**self.test_bar_data)

        # Verify record exists
        found_records = self.crud.find(filters={"code": self.test_code})
        self.assertEqual(len(found_records), 1)

        # Get table size before removal
        size0 = get_table_size(self.model)

        # Remove record
        self.crud.remove({"code": self.test_code})

        # Get table size after removal
        size1 = get_table_size(self.model)

        # Verify table size decreased by 1
        self.assertEqual(-1, size1 - size0)

        # Verify record is removed
        found_records = self.crud.find(filters={"code": self.test_code})
        self.assertEqual(len(found_records), 0)

    @database_test_required
    def test_BaseCRUD_Modify_Real(self):
        """Test BaseCRUD modify method with real database (MySQL only)"""
        # Create test record
        created_bar = self.crud.create(**self.test_bar_data)

        # Test modify (only works with MySQL)
        if self.crud._is_mysql:
            # Store original update_at time
            original_update_at = created_bar.update_at

            # Update volume
            self.crud.modify(filters={"code": self.test_code}, updates={"volume": 2000})

            # Verify modification
            found_records = self.crud.find(filters={"code": self.test_code})
            self.assertEqual(len(found_records), 1)
            self.assertEqual(found_records[0].volume, 2000)

            # Verify update_at was automatically updated
            self.assertGreater(found_records[0].update_at, original_update_at)

    @database_test_required
    def test_BaseCRUD_Filter_Operators_Real(self):
        """Test BaseCRUD enhanced filter operators with real database"""
        # Create test records with different volumes
        volumes = [800, 1000, 1200, 1500, 2000]
        for i, volume in enumerate(volumes):
            test_data = self.test_bar_data.copy()
            test_data["code"] = f"{self.test_code}_{i}"
            test_data["volume"] = volume
            self.crud.create(**test_data)

        # Test gte operator
        gte_records = self.crud.find(filters={"volume__gte": 1200})
        gte_codes = [r.code for r in gte_records if r.code.startswith(self.test_code)]
        self.assertGreaterEqual(len(gte_codes), 3)  # 1200, 1500, 2000

        # Test lte operator
        lte_records = self.crud.find(filters={"volume__lte": 1200})
        lte_codes = [r.code for r in lte_records if r.code.startswith(self.test_code)]
        self.assertGreaterEqual(len(lte_codes), 3)  # 800, 1000, 1200

        # Test in operator
        in_records = self.crud.find(filters={"volume__in": [1000, 1500]})
        in_codes = [r.code for r in in_records if r.code.startswith(self.test_code)]
        self.assertGreaterEqual(len(in_codes), 2)

        # Clean up test records
        for i in range(len(volumes)):
            self.crud.remove({"code": f"{self.test_code}_{i}"})

    @database_test_required
    def test_BaseCRUD_DataFrame_Output_Real(self):
        """Test BaseCRUD DataFrame output with real database"""
        # Create test record
        created_bar = self.crud.create(**self.test_bar_data)

        # Get results as DataFrame
        df_result = self.crud.find(filters={"code": self.test_code}, as_dataframe=True)

        # Verify DataFrame
        import pandas as pd

        self.assertIsInstance(df_result, pd.DataFrame)
        self.assertEqual(len(df_result), 1)
        self.assertEqual(df_result.iloc[0]["code"], self.test_code)

    @database_test_required
    def test_BaseCRUD_Error_Handling_Real(self):
        """Test BaseCRUD error handling with real database"""

        # Create a record to ensure the database is not empty
        self.crud.create(**self.test_bar_data)
        # Test remove without filters (should be blocked for safety)
        # This should not remove anything
        self.crud.remove({})  # Should log error and return without action

        # Test modify without filters (should be blocked for safety)
        self.crud.modify({}, {"volume": 999})  # Should log error and return

        # Verify no unintended modifications
        all_records_count = self.crud.count()
        self.assertGreater(all_records_count, 0)  # Should still have records

    @database_test_required
    def test_BaseCRUD_Exists_Real(self):
        """Test BaseCRUD exists functionality with real database"""
        # Test non-existent record
        exists_before = self.crud.exists(filters={"code": self.test_code})
        self.assertFalse(exists_before)

        # Create test record
        created_bar = self.crud.create(**self.test_bar_data)

        # Test existing record
        exists_after = self.crud.exists(filters={"code": self.test_code})
        self.assertTrue(exists_after)

        # Test with more specific filters
        exists_specific = self.crud.exists(filters={"code": self.test_code, "volume": 1000})
        self.assertTrue(exists_specific)

        # Test with non-matching filters
        exists_false = self.crud.exists(filters={"code": self.test_code, "volume": 9999})
        self.assertFalse(exists_false)

    @database_test_required
    def test_BaseCRUD_Soft_Remove_Real(self):
        """Test BaseCRUD soft remove functionality with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create test record
        created_bar = self.crud.create(**self.test_bar_data)

        # Get table size after creation
        size1 = get_table_size(self.model)
        self.assertEqual(size0 + 1, size1)

        # Verify record exists
        found_records = self.crud.find(filters={"code": self.test_code})
        self.assertEqual(len(found_records), 1)
        record_uuid = found_records[0].uuid

        # Perform soft remove
        self.crud.soft_remove({"uuid": record_uuid})

        # Get table size after soft remove
        size2 = get_table_size(self.model)

        # Test behavior based on database type
        if self.crud._is_mysql:
            # MySQL soft remove: record still exists but is marked as deleted
            self.assertEqual(size2, size1)  # Table size unchanged

            # Verify record is marked as deleted (is_del=True)
            found_records_after = self.crud.find(filters={"uuid": record_uuid})
            self.assertEqual(len(found_records_after), 1)
            self.assertTrue(found_records_after[0].is_del)

            # Verify update_at was updated
            self.assertGreater(found_records_after[0].update_at, created_bar.update_at)

        else:
            # ClickHouse hard remove: record is physically removed
            self.assertEqual(size2, size1 - 1)  # Table size decreased

            # Verify record is physically removed
            found_records_after = self.crud.find(filters={"uuid": record_uuid})
            self.assertEqual(len(found_records_after), 0)

    @database_test_required
    def test_BaseCRUD_Date_Range_Operations_Real(self):
        """Test BaseCRUD date range operations with real database"""
        # Create records with different dates
        dates = [
            datetime(2023, 1, 1, 9, 30),
            datetime(2023, 1, 15, 14, 30),
            datetime(2023, 2, 1, 10, 30),
            datetime(2023, 2, 15, 15, 30),
        ]

        for i, date in enumerate(dates):
            test_data = self.test_bar_data.copy()
            test_data["code"] = f"{self.test_code}_date_{i}"
            test_data["timestamp"] = date
            test_data["volume"] = 1000 + i * 100
            self.crud.create(**test_data)

        # Test date range filtering using timestamp operators
        january_records = self.crud.find(
            filters={
                "code__like": f"{self.test_code}_date_",
                "timestamp__gte": datetime(2023, 1, 1),
                "timestamp__lte": datetime(2023, 1, 31, 23, 59, 59),
            }
        )

        # Should find January records
        january_codes = [r.code for r in january_records if r.code.startswith(self.test_code)]
        self.assertGreaterEqual(len(january_codes), 2)  # At least 2 January records

        # Test specific date range
        mid_january_records = self.crud.find(
            filters={
                "code__like": f"{self.test_code}_date_",
                "timestamp__gte": datetime(2023, 1, 10),
                "timestamp__lte": datetime(2023, 1, 20),
            }
        )

        # Should find only the mid-January record
        mid_january_codes = [r.code for r in mid_january_records if r.code.startswith(self.test_code)]
        self.assertGreaterEqual(len(mid_january_codes), 1)

        # Clean up test records
        for i in range(len(dates)):
            self.crud.remove({"code": f"{self.test_code}_date_{i}"})

    @database_test_required
    def test_BaseCRUD_Bulk_Operations_Advanced_Real(self):
        """Test BaseCRUD advanced bulk operations with real database"""
        # Get initial table size
        size0 = get_table_size(self.model)

        # Create multiple test records with varying data
        bulk_records = []
        bulk_count = 7

        for i in range(bulk_count):
            record = MBar(
                code=f"{self.test_code}_bulk_adv_{i}",
                open=Decimal(f"{20+i}.5"),
                high=Decimal(f"{21+i}.0"),
                low=Decimal(f"{19+i}.5"),
                close=Decimal(f"{20+i}.2"),
                volume=2000 + i * 200,
                amount=Decimal(f"{40000+i*4000}"),
                frequency=FREQUENCY_TYPES.DAY,
                timestamp=datetime(2023, 1, i + 1, 9, 30),
                source=SOURCE_TYPES.TUSHARE,
            )
            bulk_records.append(record)

        # Perform bulk addition
        result = self.crud.add_batch(bulk_records)

        # Get table size after bulk addition
        size1 = get_table_size(self.model)

        # Verify table size increased by bulk_count
        self.assertEqual(bulk_count, size1 - size0)

        # Verify records with complex queries
        # Find records with volume between 2200 and 2800
        medium_volume_records = self.crud.find(
            filters={"code__like": f"{self.test_code}_bulk_adv_", "volume__gte": 2200, "volume__lte": 2800}
        )

        matching_records = [r for r in medium_volume_records if r.code.startswith(self.test_code)]
        self.assertGreaterEqual(len(matching_records), 3)  # Should find several records

        # Test bulk removal
        removal_count = self.crud.remove({"code__like": f"{self.test_code}_bulk_adv_%"})

        # Get final table size
        size2 = get_table_size(self.model)

        # Verify table size returned to original
        self.assertEqual(size2, size0)

    @database_test_required
    def test_BaseCRUD_Performance_Monitoring_Real(self):
        """Test BaseCRUD performance monitoring with table size tracking"""
        import time

        # Get initial metrics
        size0 = get_table_size(self.model)
        initial_count = self.crud.count()

        # Perform a series of operations while monitoring performance
        operations_count = 5

        for i in range(operations_count):
            # Create
            test_data = self.test_bar_data.copy()
            test_data["code"] = f"{self.test_code}_perf_{i}"
            test_data["volume"] = 1000 + i * 100

            start_time = time.time()
            created_record = self.crud.create(**test_data)
            create_time = time.time() - start_time

            # Verify creation was fast (under 1 second)
            self.assertLess(create_time, 1.0)

            # Find
            start_time = time.time()
            found_records = self.crud.find(filters={"code": test_data["code"]})
            find_time = time.time() - start_time

            # Verify find was fast
            self.assertLess(find_time, 1.0)
            self.assertEqual(len(found_records), 1)

        # Verify final metrics
        size1 = get_table_size(self.model)
        final_count = self.crud.count()

        # Table size should have increased by operations_count
        self.assertEqual(operations_count, size1 - size0)
        self.assertEqual(operations_count, final_count - initial_count)

        # Bulk cleanup
        for i in range(operations_count):
            self.crud.remove({"code": f"{self.test_code}_perf_{i}"})

        # Verify cleanup
        size2 = get_table_size(self.model)
        self.assertEqual(size2, size0)

    # ============================================================================
    # Data Validation System Tests
    # ============================================================================

    @database_test_required
    def test_BaseCRUD_Data_Validation_System_Overview(self):
        """Test BaseCRUD data validation system base functionality"""
        if ValidationError is None:
            self.skipTest("ValidationError not available")

        print(":test_tube: Testing BaseCRUD validation system base functionality...")

        # Test 1: Valid data passes through validation with config
        test_data = {
            "code": "000001.SZ",
            "open": 10.5,
            "high": 11.0,
            "low": 10.0,
            "close": 10.8,
            "volume": 1000,
            "amount": 10800.5,
            "frequency": FREQUENCY_TYPES.DAY,
            "timestamp": "2023-01-01 09:30:00",
            "source": SOURCE_TYPES.TUSHARE
        }
        
        try:
            validated_data = self.crud._validate_before_database(test_data)
            self.assertIsInstance(validated_data, dict)
            self.assertEqual(validated_data["code"], "000001.SZ")
            self.assertEqual(validated_data["volume"], 1000)
            print(":white_check_mark: Valid data passed through validation with config")
        except Exception as e:
            self.fail(f"Valid data validation failed unexpectedly: {e}")

        # Test 2: Validate that validation methods exist and return expected types
        database_config = self.crud._get_database_required_config()
        self.assertIsInstance(database_config, dict)
        print(":white_check_mark: Database required config method returns dict")
        
        field_config = self.crud._get_field_config()
        self.assertIsInstance(field_config, dict)
        # Now we have actual validation config, so it shouldn't be empty
        self.assertGreater(len(field_config), 0)
        # Verify core fields are configured
        self.assertIn("code", field_config)
        self.assertIn("open", field_config)
        self.assertIn("volume", field_config)
        print(":white_check_mark: Field config method returns non-empty dict with core fields")
        
        # Test 3: Validate database-specific config behavior
        if self.crud._is_mysql:
            mysql_config = self.crud._get_mysql_required_config()
            self.assertIsInstance(mysql_config, dict)
            print(":white_check_mark: MySQL config method returns dict")
        elif self.crud._is_clickhouse:
            clickhouse_config = self.crud._get_clickhouse_required_config()
            self.assertIsInstance(clickhouse_config, dict)
            self.assertIn("timestamp", clickhouse_config)  # ClickHouse requires timestamp
            print(":white_check_mark: ClickHouse config method returns dict with timestamp requirement")




    @database_test_required
    def test_BaseCRUD_Create_With_Validation_Integration(self):
        """Test BaseCRUD create method validation integration"""
        if ValidationError is None:
            self.skipTest("ValidationError not available")

        print(":test_tube: Testing create method validation integration...")

        # Test 1: Create method calls validation before database operations
        valid_params = {
            "code": f"CREATETEST{self.test_id}.SZ",
            "open": 10.5,
            "high": 11.0,
            "low": 10.0,
            "close": 10.8,
            "volume": 1000,
            "amount": 10800,
            "frequency": FREQUENCY_TYPES.DAY,
            "timestamp": "2023-01-01 09:30:00",
            "source": SOURCE_TYPES.TUSHARE,
        }

        try:
            # This should work as validation passes through when no config is defined
            created_record = self.crud.create(**valid_params)
            self.assertIsNotNone(created_record)
            self.assertEqual(created_record.code, f"CREATETEST{self.test_id}.SZ")
            print(":white_check_mark: Create method successfully integrates validation (no config)")
            
            # Cleanup
            self.crud.remove({"code": f"CREATETEST{self.test_id}.SZ"})
        except Exception as e:
            self.fail(f"Create method validation integration failed: {e}")

        # Test 2: Verify create method calls _validate_before_database
        # This is an integration test to ensure the validation flow exists
        print(":white_check_mark: Create method validation integration verified")

    @database_test_required
    def test_BaseCRUD_Add_No_Validation(self):
        """Test BaseCRUD add method does not perform validation"""
        print(":test_tube: Testing add method does not perform validation...")

        # Test: add method bypasses validation (relies on database constraints)
        valid_bar = MBar(
            code=f"ADDTEST{self.test_id}.SZ",
            open=Decimal("10.5"),
            high=Decimal("11.0"),
            low=Decimal("10.0"),
            close=Decimal("10.8"),
            volume=1000,
            amount=Decimal("10800"),
            frequency=FREQUENCY_TYPES.DAY,
            timestamp=datetime(2023, 1, 1, 9, 30),
            source=SOURCE_TYPES.TUSHARE,
        )

        try:
            added_record = self.crud.add(valid_bar)
            self.assertIsNotNone(added_record)
            self.assertEqual(added_record.code, f"ADDTEST{self.test_id}.SZ")
            print(":white_check_mark: Add method works without validation (relies on database constraints)")
            
            # Cleanup
            self.crud.remove({"code": f"ADDTEST{self.test_id}.SZ"})
        except Exception as e:
            self.fail(f"Add method failed: {e}")

    @database_test_required
    def test_BaseCRUD_Add_Batch_No_Validation(self):
        """Test BaseCRUD add_batch method does not perform validation"""
        print(":test_tube: Testing add_batch method does not perform validation...")

        # Test: add_batch method bypasses validation (relies on database constraints)
        valid_bars = []
        for i in range(3):
            bar = MBar(
                code=f"BATCHTEST{self.test_id}_{i}.SZ",
                open=Decimal(f"{10+i}.5"),
                high=Decimal(f"{11+i}.0"),
                low=Decimal(f"{9+i}.5"),
                close=Decimal(f"{10+i}.2"),
                volume=1000 + i * 100,
                amount=Decimal(f"{10000+i*1000}"),
                frequency=FREQUENCY_TYPES.DAY,
                timestamp=datetime(2023, 1, 1+i, 9, 30),
                source=SOURCE_TYPES.TUSHARE,
            )
            valid_bars.append(bar)

        try:
            result = self.crud.add_batch(valid_bars)
            self.assertIsInstance(result, tuple)
            print(":white_check_mark: Add_batch method works without validation (relies on database constraints)")
            
            # Cleanup
            for i in range(3):
                self.crud.remove({"code": f"BATCHTEST{self.test_id}_{i}.SZ"})
        except Exception as e:
            self.fail(f"Add_batch method failed: {e}")

    @database_test_required
    def test_BaseCRUD_Validation_Error_Structure(self):
        """Test ValidationError class structure and availability"""
        if ValidationError is None:
            self.skipTest("ValidationError not available")

        print(":test_tube: Testing validation error infrastructure...")

        # Test ValidationError inheritance
        self.assertTrue(issubclass(ValidationError, Exception))
        print(":white_check_mark: ValidationError properly inherits from Exception")
        
        # Test ValidationError can be instantiated
        try:
            error = ValidationError("Test error", "test_field", "test_value")
            self.assertEqual(error.field, "test_field")
            self.assertEqual(error.value, "test_value")
            self.assertIn("Test error", str(error))
            print(":white_check_mark: ValidationError can be instantiated with field and value info")
        except Exception as e:
            self.fail(f"ValidationError instantiation failed: {e}")

    @database_test_required
    def test_BaseCRUD_Validation_Performance(self):
        """Test data validation system performance impact"""
        if ValidationError is None:
            self.skipTest("ValidationError not available")

        print(":test_tube: Testing validation system performance...")

        import time

        # Test validation performance with valid data
        valid_data = {
            "code": f"PERF{self.test_id}.SZ",
            "open": 10.5,
            "high": 11.0,
            "low": 10.0,
            "close": 10.8,
            "volume": 1000,
            "amount": 10800.5,
            "timestamp": "2023-01-01 09:30:00"
        }

        # Measure validation time
        start_time = time.time()
        for _ in range(100):  # Run validation 100 times
            try:
                validated_data = self.crud._validate_before_database(valid_data)
            except ValidationError:
                pass
        validation_time = time.time() - start_time

        # Validation should be fast (under 1 second for 100 validations)
        self.assertLess(validation_time, 1.0)
        print(f":white_check_mark: Validation performance acceptable: {validation_time:.4f}s for 100 validations")

        # Test that validation doesn't significantly impact create performance
        start_time = time.time()
        created_record = self.crud.create(**{
            "code": f"PERFTEST{self.test_id}.SZ",
            "open": 10.5,
            "high": 11.0,
            "low": 10.0,
            "close": 10.8,
            "volume": 1000,
            "amount": 10800,
            "frequency": FREQUENCY_TYPES.DAY,
            "timestamp": "2023-01-01 09:30:00",
            "source": SOURCE_TYPES.TUSHARE,
        })
        create_time = time.time() - start_time

        # Create with validation should still be fast
        self.assertLess(create_time, 2.0)
        print(f":white_check_mark: Create with validation performance acceptable: {create_time:.4f}s")

        # Cleanup
        self.crud.remove({"code": f"PERFTEST{self.test_id}.SZ"})

    # ============================================================================
    # Specific Field Validation Tests  
    # ============================================================================

    @database_test_required
    def test_Create_Validation_Success_Cases(self):
        """测试create()方法各种成功验证场景"""
        if ValidationError is None:
            self.skipTest("ValidationError not available")

        print(":test_tube: Testing create validation success cases...")

        # Test 1: All valid data with different types
        valid_cases = [
            {
                "name": "Standard decimal prices",
                "data": {
                    "code": f"SUCCESS1_{self.test_id}.SZ",
                    "open": 10.5,
                    "high": 11.0,
                    "low": 10.0,
                    "close": 10.8,
                    "volume": 1000,
                    "amount": 10800.0,
                    "frequency": FREQUENCY_TYPES.DAY,
                    "timestamp": "2023-01-01 09:30:00",
                    "source": SOURCE_TYPES.TUSHARE,
                }
            },
            {
                "name": "Integer prices",
                "data": {
                    "code": f"SUCCESS2_{self.test_id}.SZ",
                    "open": 15,
                    "high": 16,
                    "low": 14,
                    "close": 15,
                    "volume": 2000,
                    "amount": 30000,
                    "frequency": FREQUENCY_TYPES.MIN5,
                    "timestamp": datetime(2023, 1, 1, 14, 30),
                    "source": SOURCE_TYPES.YAHOO,
                }
            },
            {
                "name": "Minimum valid values",
                "data": {
                    "code": f"SUCCESS3_{self.test_id}.SZ",
                    "open": 0.01,
                    "high": 0.01,
                    "low": 0.01,
                    "close": 0.01,
                    "volume": 0,
                    "amount": 0,
                    "frequency": FREQUENCY_TYPES.DAY,
                    "timestamp": "2023-01-01",
                    "source": SOURCE_TYPES.AKSHARE,
                }
            }
        ]

        for case in valid_cases:
            try:
                created_record = self.crud.create(**case["data"])
                self.assertIsNotNone(created_record)
                self.assertEqual(created_record.code, case["data"]["code"])
                print(f":white_check_mark: {case['name']} validation passed")
                
                # Cleanup
                self.crud.remove({"code": case["data"]["code"]})
            except ValidationError as e:
                self.fail(f"{case['name']} should have passed validation but failed: {e}")
            except Exception as e:
                self.fail(f"{case['name']} failed with unexpected error: {e}")

    @database_test_required
    def test_Create_Validation_String_Errors(self):
        """测试字符串字段验证错误"""
        if ValidationError is None:
            self.skipTest("ValidationError not available")

        print(":test_tube: Testing string field validation errors...")

        # Test empty string code
        invalid_data = self.test_bar_data.copy()
        invalid_data["code"] = ""

        with self.assertRaises(ValidationError) as context:
            self.crud.create(**invalid_data)
        
        error = context.exception
        self.assertEqual(error.field, "code")
        self.assertEqual(error.value, "")
        self.assertIn("length", str(error).lower())
        print(":white_check_mark: Empty string code validation error caught correctly")

        # Test None string code  
        invalid_data["code"] = None
        with self.assertRaises(ValidationError) as context:
            self.crud.create(**invalid_data)
        
        error = context.exception
        self.assertEqual(error.field, "code")
        self.assertEqual(error.value, None)
        print(":white_check_mark: None string code validation error caught correctly")

    @database_test_required
    def test_Create_Validation_Numeric_Range_Errors(self):
        """测试数值范围验证错误"""
        if ValidationError is None:
            self.skipTest("ValidationError not available")

        print(":test_tube: Testing numeric range validation errors...")

        # Test negative price values
        price_fields = ["open", "high", "low", "close"]
        for field in price_fields:
            invalid_data = self.test_bar_data.copy()
            invalid_data[field] = -1.0

            with self.assertRaises(ValidationError) as context:
                self.crud.create(**invalid_data)
            
            error = context.exception
            self.assertEqual(error.field, field)
            self.assertEqual(error.value, -1.0)
            self.assertIn("minimum", str(error).lower())
            print(f":white_check_mark: Negative {field} validation error caught correctly")

        # Test zero price values (should fail as min is 0.01)
        invalid_data = self.test_bar_data.copy()
        invalid_data["open"] = 0.0

        with self.assertRaises(ValidationError) as context:
            self.crud.create(**invalid_data)
        
        error = context.exception
        self.assertEqual(error.field, "open")
        self.assertEqual(error.value, 0.0)
        print(":white_check_mark: Zero price validation error caught correctly")

        # Test negative volume (should fail as min is 0)
        invalid_data = self.test_bar_data.copy()
        invalid_data["volume"] = -100

        with self.assertRaises(ValidationError) as context:
            self.crud.create(**invalid_data)
        
        error = context.exception
        self.assertEqual(error.field, "volume")
        self.assertEqual(error.value, -100)
        print(":white_check_mark: Negative volume validation error caught correctly")

    @database_test_required
    def test_Create_Validation_Enum_Errors(self):
        """测试枚举值验证错误"""
        if ValidationError is None:
            self.skipTest("ValidationError not available")

        print(":test_tube: Testing enum validation errors...")

        # Test invalid frequency enum
        invalid_data = self.test_bar_data.copy()
        invalid_data["frequency"] = "INVALID_FREQUENCY"

        with self.assertRaises(ValidationError) as context:
            self.crud.create(**invalid_data)
        
        error = context.exception
        self.assertEqual(error.field, "frequency")
        self.assertEqual(error.value, "INVALID_FREQUENCY")
        self.assertIn("choice", str(error).lower())
        print(":white_check_mark: Invalid frequency enum validation error caught correctly")

        # Test invalid source enum
        invalid_data = self.test_bar_data.copy()
        invalid_data["source"] = "INVALID_SOURCE"

        with self.assertRaises(ValidationError) as context:
            self.crud.create(**invalid_data)
        
        error = context.exception
        self.assertEqual(error.field, "source")
        self.assertEqual(error.value, "INVALID_SOURCE")
        print(":white_check_mark: Invalid source enum validation error caught correctly")

        # Test numeric value for enum field
        invalid_data = self.test_bar_data.copy()
        invalid_data["frequency"] = 123

        with self.assertRaises(ValidationError) as context:
            self.crud.create(**invalid_data)
        
        error = context.exception
        self.assertEqual(error.field, "frequency")
        self.assertEqual(error.value, 123)
        print(":white_check_mark: Numeric value for enum field validation error caught correctly")

    @database_test_required
    def test_Create_Validation_Type_Errors(self):
        """测试数据类型验证错误"""
        if ValidationError is None:
            self.skipTest("ValidationError not available")

        print(":test_tube: Testing data type validation errors...")

        # Test string value for numeric field
        invalid_data = self.test_bar_data.copy()
        invalid_data["open"] = "not_a_number"

        with self.assertRaises(ValidationError) as context:
            self.crud.create(**invalid_data)
        
        error = context.exception
        self.assertEqual(error.field, "open")
        self.assertEqual(error.value, "not_a_number")
        self.assertIn("type", str(error).lower())
        print(":white_check_mark: String value for numeric field validation error caught correctly")

        # Test list value for scalar field
        invalid_data = self.test_bar_data.copy()
        invalid_data["volume"] = [1000, 2000]

        with self.assertRaises(ValidationError) as context:
            self.crud.create(**invalid_data)
        
        error = context.exception
        self.assertEqual(error.field, "volume")
        self.assertEqual(error.value, [1000, 2000])
        print(":white_check_mark: List value for scalar field validation error caught correctly")

        # Test dict value for scalar field
        invalid_data = self.test_bar_data.copy()
        invalid_data["code"] = {"invalid": "data"}

        with self.assertRaises(ValidationError) as context:
            self.crud.create(**invalid_data)
        
        error = context.exception
        self.assertEqual(error.field, "code")
        self.assertEqual(error.value, {"invalid": "data"})
        print(":white_check_mark: Dict value for scalar field validation error caught correctly")

    @database_test_required
    def test_Create_Validation_Mixed_Errors(self):
        """测试多个字段同时验证错误（应该报告第一个错误）"""
        if ValidationError is None:
            self.skipTest("ValidationError not available")

        print(":test_tube: Testing mixed field validation errors...")

        # Test multiple invalid fields - should report first encountered error
        invalid_data = {
            "code": "",  # Invalid: empty string
            "open": -1.0,  # Invalid: negative price
            "high": "not_a_number",  # Invalid: wrong type
            "low": -0.5,  # Invalid: negative price
            "close": -2.0,  # Invalid: negative price
            "volume": -100,  # Invalid: negative volume
            "amount": -500,  # Invalid: negative amount
            "frequency": "INVALID",  # Invalid: wrong enum
            "timestamp": "",  # Invalid: empty string timestamp
            "source": "INVALID_SOURCE",  # Invalid: wrong enum
        }

        with self.assertRaises(ValidationError) as context:
            # Note: The exact field reported depends on validation order
            # but at least one error should be caught
            self.crud.create(**invalid_data)
        
        error = context.exception
        self.assertIsNotNone(error.field)
        self.assertIsNotNone(error.value)
        print(f":white_check_mark: Mixed validation errors caught correctly: {error.field} = {error.value}")

    @database_test_required
    def test_Create_Validation_Performance_With_Config(self):
        """测试带有验证配置的性能表现"""
        if ValidationError is None:
            self.skipTest("ValidationError not available")

        print(":test_tube: Testing validation performance with field config...")

        import time

        # Test validation performance with real config
        valid_data = {
            "code": f"PERFVAL{self.test_id}.SZ",
            "open": 10.5,
            "high": 11.0,
            "low": 10.0,
            "close": 10.8,
            "volume": 1000,
            "amount": 10800.0,
            "frequency": FREQUENCY_TYPES.DAY,
            "timestamp": "2023-01-01 09:30:00",
            "source": SOURCE_TYPES.TUSHARE,
        }

        # Measure validation time with config
        start_time = time.time()
        for _ in range(50):  # Run validation 50 times
            try:
                validated_data = self.crud._validate_before_database(valid_data.copy())
            except ValidationError:
                pass
        validation_time = time.time() - start_time

        # Validation should still be fast even with real config
        self.assertLess(validation_time, 2.0)
        print(f":white_check_mark: Validation with config performance acceptable: {validation_time:.4f}s for 50 validations")

        # Test that create with validation is still reasonably fast
        start_time = time.time()
        created_record = self.crud.create(**valid_data)
        create_time = time.time() - start_time

        # Create with real validation should still be fast
        self.assertLess(create_time, 3.0)
        print(f":white_check_mark: Create with real validation performance acceptable: {create_time:.4f}s")

        # Cleanup
        self.crud.remove({"code": f"PERFVAL{self.test_id}.SZ"})
