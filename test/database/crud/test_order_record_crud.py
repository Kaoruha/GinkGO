import unittest
import sys
import os
import uuid
from decimal import Decimal
from datetime import datetime
from sqlalchemy import text
from test.database.test_isolation import database_test_required


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

try:
    from ginkgo.data.crud.order_record_crud import OrderRecordCRUD
    from ginkgo.data.crud.validation import ValidationError
    from ginkgo.data.models import MOrderRecord
    from ginkgo.backtest import Order
    from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES
    from ginkgo.libs import GCONF, datetime_normalize, to_decimal
    from ginkgo.data.drivers import get_db_connection, get_table_size, create_table, drop_table
except ImportError as e:
    print(f"Import error: {e}")
    OrderRecordCRUD = None
    GCONF = None
    ValidationError = None


class OrderRecordCRUDTest(unittest.TestCase):
    """
    OrderRecordCRUD database integration tests.
    Tests OrderRecord-specific CRUD operations with actual database.
    """

    @classmethod
    def setUpClass(cls):
        """Class-level setup: check database configuration and connection"""
        if OrderRecordCRUD is None or GCONF is None:
            raise AssertionError("OrderRecordCRUD or GCONF not available")

        # Set model for table size verification
        cls.model = MOrderRecord

        # Recreate table for clean testing
        try:
            drop_table(cls.model, no_skip=True)
            create_table(cls.model, no_skip=True)
            print(":white_check_mark: OrderRecord table recreated for testing")
        except Exception as e:
            print(f":warning: OrderRecord table recreation failed: {e}")

        # Verify database configuration (ClickHouse for MOrderRecord)
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

        # Create OrderRecordCRUD instance
        cls.crud = OrderRecordCRUD()

        # Test database connection
        try:
            connection = get_db_connection(MOrderRecord)
            with connection.get_session() as session:
                session.execute(text("SELECT 1"))
            print(":white_check_mark: OrderRecord database connection successful")
        except Exception as e:
            raise AssertionError(f"Database connection failed: {e}")

    def setUp(self):
        """Setup for each test: prepare unique test data"""
        self.test_id = str(uuid.uuid4())[:8]
        self.test_portfolio_id = f"TestPortfolio{self.test_id}"
        self.test_engine_id = f"TestEngine{self.test_id}"
        self.test_order_id = f"TestOrder{self.test_id}"

        # Test order record data based on actual MOrderRecord fields
        self.test_order_params = {
            "order_id": self.test_order_id,
            "portfolio_id": self.test_portfolio_id,
            "engine_id": self.test_engine_id,
            "timestamp": datetime_normalize("2023-01-01 09:30:00"),
            "code": "000001.SZ",
            "direction": DIRECTION_TYPES.LONG,
            "order_type": ORDER_TYPES.MARKETORDER,
            "status": ORDERSTATUS_TYPES.SUBMITTED.value,
            "volume": 1000,
            "limit_price": to_decimal(10.50),
            "frozen": to_decimal(10500.00),
            "transaction_price": to_decimal(0),
            "remain": to_decimal(10500.00),
            "fee": to_decimal(0),
        }

    def tearDown(self):
        """Cleanup after each test"""
        try:
            # Single pattern cleanup for all test data
            self.crud.remove({"order_id__like": f"TestOrder{self.test_id}%"})
        except Exception as e:
            print(f":warning: Cleanup failed: {e}")

    @classmethod
    def tearDownClass(cls):
        """Class-level cleanup: remove any remaining test data"""
        try:
            # Final cleanup of any remaining test records
            cls.crud.remove({"order_id__like": "TestOrder%"})
            print(":broom: Final cleanup of all TestOrder records completed")
        except Exception as e:
            print(f":warning: Final cleanup failed: {e}")

    @database_test_required
    def test_OrderRecordCRUD_Create_From_Params_Real(self):
        """Test OrderRecordCRUD create from parameters with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create order record from parameters
        created_order = self.crud.create(**self.test_order_params)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify creation - 数据库存储的是整数值
        self.assertIsNotNone(created_order)
        self.assertIsInstance(created_order, MOrderRecord)
        self.assertEqual(created_order.order_id, self.test_order_id)
        self.assertEqual(created_order.portfolio_id, self.test_portfolio_id)
        self.assertEqual(created_order.engine_id, self.test_engine_id)
        self.assertEqual(created_order.code, "000001.SZ")
        self.assertEqual(created_order.direction, DIRECTION_TYPES.LONG.value)
        self.assertEqual(created_order.order_type, ORDER_TYPES.MARKETORDER.value)
        self.assertEqual(created_order.status, ORDERSTATUS_TYPES.SUBMITTED.value.value)
        self.assertEqual(created_order.volume, 1000)
        self.assertEqual(created_order.limit_price, to_decimal(10.50))

        # Verify in database
        found_orders = self.crud.find(filters={"order_id": self.test_order_id})
        self.assertEqual(len(found_orders), 1)
        self.assertEqual(found_orders[0].order_id, self.test_order_id)

    @database_test_required
    def test_OrderRecordCRUD_Add_Order_Object_Real(self):
        """Test OrderRecordCRUD add order object with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create order object using _create_from_params
        order_params = {
            "order_id": f"TestOrder{self.test_id}_obj",
            "portfolio_id": f"TestPortfolio{self.test_id}_obj",
            "engine_id": f"TestEngine{self.test_id}_obj",
            "timestamp": datetime_normalize("2023-01-01 10:00:00"),
            "code": "000002.SZ",
            "direction": DIRECTION_TYPES.SHORT,
            "order_type": ORDER_TYPES.LIMITORDER,
            "status": ORDERSTATUS_TYPES.FILLED.value,
            "volume": 2000,
            "limit_price": to_decimal(20.75),
            "frozen": to_decimal(0),
            "transaction_price": to_decimal(20.50),
            "remain": to_decimal(0),
            "fee": to_decimal(10.25),
        }

        order = self.crud._create_from_params(**order_params)
        added_order = self.crud.add(order)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify addition
        self.assertIsNotNone(added_order)
        self.assertEqual(added_order.order_id, f"TestOrder{self.test_id}_obj")
        self.assertEqual(added_order.portfolio_id, f"TestPortfolio{self.test_id}_obj")
        self.assertEqual(added_order.code, "000002.SZ")
        self.assertEqual(added_order.direction, DIRECTION_TYPES.SHORT.value)
        self.assertEqual(added_order.status, ORDERSTATUS_TYPES.FILLED.value)
        self.assertEqual(added_order.transaction_price, to_decimal(20.50))

        # Verify in database
        found_orders = self.crud.find(filters={"order_id": f"TestOrder{self.test_id}_obj"})
        self.assertEqual(len(found_orders), 1)

    @database_test_required
    def test_OrderRecordCRUD_Add_Batch_Real(self):
        """Test OrderRecordCRUD batch addition with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create multiple order record objects
        orders = []
        batch_count = 3
        for i in range(batch_count):
            order = self.crud._create_from_params(
                order_id=f"TestOrder{self.test_id}_batch_{i}",
                portfolio_id=f"TestPortfolio{self.test_id}_batch",
                engine_id=f"TestEngine{self.test_id}_batch",
                timestamp=datetime_normalize("2023-01-01 09:30:00"),
                code=f"00000{i}.SZ",
                direction=DIRECTION_TYPES.LONG if i % 2 == 0 else DIRECTION_TYPES.SHORT,
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.SUBMITTED.value,
                volume=100 * (i + 1),
                limit_price=to_decimal(10 + i),
                frozen=to_decimal(1000 * (i + 1)),
                transaction_price=to_decimal(0),
                remain=to_decimal(1000 * (i + 1)),
                fee=to_decimal(0),
            )
            orders.append(order)

        # Add batch
        result = self.crud.add_batch(orders)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by batch count
        self.assertEqual(batch_count, size1 - size0)

        # Verify batch addition
        self.assertIsInstance(result, tuple)

        # Verify each order in database
        for i in range(batch_count):
            found_orders = self.crud.find(filters={"order_id": f"TestOrder{self.test_id}_batch_{i}"})
            self.assertEqual(len(found_orders), 1)
            expected_direction = DIRECTION_TYPES.LONG if i % 2 == 0 else DIRECTION_TYPES.SHORT
            self.assertEqual(found_orders[0].direction, expected_direction)
            self.assertEqual(found_orders[0].volume, 100 * (i + 1))

    @database_test_required
    def test_OrderRecordCRUD_Find_By_Portfolio_Real(self):
        """Test OrderRecordCRUD find by portfolio business helper method with real database"""
        # Create test order records
        for i in range(3):
            params = self.test_order_params.copy()
            params["order_id"] = f"TestOrder{self.test_id}_portfolio_{i}"
            params["code"] = f"00000{i}.SZ"
            params["status"] = ORDERSTATUS_TYPES.SUBMITTED.value if i == 0 else ORDERSTATUS_TYPES.FILLED.value
            self.crud.create(**params)

        # Test find by portfolio
        found_orders = self.crud.find_by_portfolio(self.test_portfolio_id)

        # Should find 3 orders
        self.assertEqual(len(found_orders), 3)
        for order in found_orders:
            self.assertEqual(order.portfolio_id, self.test_portfolio_id)

        # Test find by portfolio with date range
        found_orders_range = self.crud.find_by_portfolio(
            self.test_portfolio_id,
            start_date="2022-12-31",
            end_date="2023-12-31"
        )
        self.assertEqual(len(found_orders_range), 3)

        # Test find by portfolio with status filter
        found_orders_status = self.crud.find_by_portfolio(
            self.test_portfolio_id,
            status=ORDERSTATUS_TYPES.FILLED.value
        )
        self.assertEqual(len(found_orders_status), 2)  # 2 filled orders

    @database_test_required
    def test_OrderRecordCRUD_Find_By_Order_Id_Real(self):
        """Test OrderRecordCRUD find by order ID business helper method with real database"""
        # Create test order record
        created_order = self.crud.create(**self.test_order_params)

        # Test find by order ID
        found_orders = self.crud.find_by_order_id(self.test_order_id)

        # Should find 1 order
        self.assertEqual(len(found_orders), 1)
        self.assertEqual(found_orders[0].order_id, self.test_order_id)
        self.assertEqual(found_orders[0].portfolio_id, self.test_portfolio_id)

        # Test find non-existent order ID
        non_existent_orders = self.crud.find_by_order_id("NON_EXISTENT_ORDER")
        self.assertEqual(len(non_existent_orders), 0)

    @database_test_required
    def test_OrderRecordCRUD_Find_By_Code_And_Status_Real(self):
        """Test OrderRecordCRUD find by code and status business helper method with real database"""
        # Create test order records with different codes and statuses
        test_data = [
            {"code": "TESTCODE.SZ", "status": ORDERSTATUS_TYPES.SUBMITTED.value},
            {"code": "TESTCODE.SZ", "status": ORDERSTATUS_TYPES.FILLED.value},
            {"code": "OTHERCODE.SZ", "status": ORDERSTATUS_TYPES.SUBMITTED.value},
        ]

        for i, data in enumerate(test_data):
            params = self.test_order_params.copy()
            params["order_id"] = f"TestOrder{self.test_id}_codestatus_{i}"
            params["code"] = data["code"]
            params["status"] = data["status"]
            self.crud.create(**params)

        # Test find by code and status
        submitted_testcode_orders = self.crud.find_by_code_and_status("TESTCODE.SZ", ORDERSTATUS_TYPES.SUBMITTED.value)
        self.assertEqual(len(submitted_testcode_orders), 1)
        self.assertEqual(submitted_testcode_orders[0].code, "TESTCODE.SZ")
        self.assertEqual(submitted_testcode_orders[0].status, ORDERSTATUS_TYPES.SUBMITTED.value)

        filled_testcode_orders = self.crud.find_by_code_and_status("TESTCODE.SZ", ORDERSTATUS_TYPES.FILLED.value)
        self.assertEqual(len(filled_testcode_orders), 1)
        self.assertEqual(filled_testcode_orders[0].status, ORDERSTATUS_TYPES.FILLED.value)

    @database_test_required
    def test_OrderRecordCRUD_Find_Pending_Orders_Real(self):
        """Test OrderRecordCRUD find pending orders business helper method with real database"""
        # Create test order records with different statuses
        statuses = [ORDERSTATUS_TYPES.SUBMITTED.value, ORDERSTATUS_TYPES.FILLED.value, ORDERSTATUS_TYPES.SUBMITTED.value, ORDERSTATUS_TYPES.CANCELED]

        for i, status in enumerate(statuses):
            params = self.test_order_params.copy()
            params["order_id"] = f"TestOrder{self.test_id}_pending_{i}"
            params["status"] = status
            params["code"] = f"SUBMITTED{i}.SZ"
            self.crud.create(**params)

        # Test find pending orders (now mapped to SUBMITTED status)
        pending_orders = self.crud.find_pending_orders(portfolio_id=self.test_portfolio_id)

        # Should find 2 submitted orders (SUBMITTED is the equivalent of pending)
        self.assertEqual(len(pending_orders), 2)
        for order in pending_orders:
            self.assertEqual(order.status, ORDERSTATUS_TYPES.SUBMITTED.value)
            self.assertEqual(order.portfolio_id, self.test_portfolio_id)

        # Test find pending orders for specific code
        pending_orders_code = self.crud.find_pending_orders(code="SUBMITTED0.SZ")
        self.assertEqual(len(pending_orders_code), 1)
        self.assertEqual(pending_orders_code[0].code, "SUBMITTED0.SZ")

    @database_test_required
    def test_OrderRecordCRUD_Find_Filled_Orders_Real(self):
        """Test OrderRecordCRUD find filled orders business helper method with real database"""
        # Create test order records with different statuses and timestamps
        test_data = [
            {"status": ORDERSTATUS_TYPES.FILLED.value, "timestamp": "2023-01-01 09:30:00"},
            {"status": ORDERSTATUS_TYPES.FILLED.value, "timestamp": "2023-01-01 10:00:00"},
            {"status": ORDERSTATUS_TYPES.SUBMITTED.value, "timestamp": "2023-01-01 10:30:00"},
        ]

        for i, data in enumerate(test_data):
            params = self.test_order_params.copy()
            params["order_id"] = f"TestOrder{self.test_id}_filled_{i}"
            params["status"] = data["status"]
            params["timestamp"] = datetime_normalize(data["timestamp"])
            self.crud.create(**params)

        # Test find filled orders
        filled_orders = self.crud.find_filled_orders(portfolio_id=self.test_portfolio_id)

        # Should find 2 filled orders
        self.assertEqual(len(filled_orders), 2)
        for order in filled_orders:
            self.assertEqual(order.status, ORDERSTATUS_TYPES.FILLED.value)

        # Test find filled orders with date range
        filled_orders_range = self.crud.find_filled_orders(
            portfolio_id=self.test_portfolio_id,
            start_date="2023-01-01 09:45:00",
            end_date="2023-01-01 10:15:00"
        )
        self.assertEqual(len(filled_orders_range), 1)  # Only the 10:00:00 order

    @database_test_required
    def test_OrderRecordCRUD_Count_By_Portfolio_Real(self):
        """Test OrderRecordCRUD count by portfolio business helper method with real database"""
        # Create test order records
        for i in range(4):
            params = self.test_order_params.copy()
            params["order_id"] = f"TestOrder{self.test_id}_count_{i}"
            self.crud.create(**params)

        # Test count by portfolio
        count = self.crud.count_by_portfolio(self.test_portfolio_id)
        self.assertEqual(count, 4)

        # Test count by non-existent portfolio
        count_empty = self.crud.count_by_portfolio("NON_EXISTENT_PORTFOLIO")
        self.assertEqual(count_empty, 0)

    @database_test_required
    def test_OrderRecordCRUD_Count_By_Status_Real(self):
        """Test OrderRecordCRUD count by status business helper method with real database"""
        # Create test order records with different statuses
        statuses = [
            ORDERSTATUS_TYPES.SUBMITTED.value,
            ORDERSTATUS_TYPES.SUBMITTED.value,
            ORDERSTATUS_TYPES.FILLED.value,
            ORDERSTATUS_TYPES.CANCELED,
        ]

        for i, status in enumerate(statuses):
            params = self.test_order_params.copy()
            params["order_id"] = f"TestOrder{self.test_id}_statuscount_{i}"
            params["status"] = status
            self.crud.create(**params)

        # Test count by status
        submitted_count = self.crud.count_by_status(ORDERSTATUS_TYPES.SUBMITTED.value, portfolio_id=self.test_portfolio_id)
        self.assertEqual(submitted_count, 2)

        filled_count = self.crud.count_by_status(ORDERSTATUS_TYPES.FILLED.value, portfolio_id=self.test_portfolio_id)
        self.assertEqual(filled_count, 1)

        cancelled_count = self.crud.count_by_status(ORDERSTATUS_TYPES.CANCELED, portfolio_id=self.test_portfolio_id)
        self.assertEqual(cancelled_count, 1)

    @database_test_required
    def test_OrderRecordCRUD_Get_Total_Transaction_Amount_Real(self):
        """Test OrderRecordCRUD get total transaction amount business helper method with real database"""
        # Create test filled order records with transaction data
        transaction_data = [
            {"transaction_price": 10.50, "volume": 100, "fee": 5.0},    # 1050 + 5 = 1055
            {"transaction_price": 20.00, "volume": 200, "fee": 10.0},   # 4000 + 10 = 4010
            {"transaction_price": 15.75, "volume": 150, "fee": 7.5},    # 2362.5 + 7.5 = 2370
        ]

        for i, data in enumerate(transaction_data):
            params = self.test_order_params.copy()
            params["order_id"] = f"TestOrder{self.test_id}_amount_{i}"
            params["status"] = ORDERSTATUS_TYPES.FILLED.value
            params["transaction_price"] = to_decimal(data["transaction_price"])
            params["volume"] = data["volume"]
            params["fee"] = to_decimal(data["fee"])
            self.crud.create(**params)

        # Test get total transaction amount
        total_amount = self.crud.get_total_transaction_amount(self.test_portfolio_id)

        # Expected: (10.50*100 + 5) + (20.00*200 + 10) + (15.75*150 + 7.5) = 1055 + 4010 + 2370 = 7435
        expected_amount = 1055.0 + 4010.0 + 2370.0
        self.assertEqual(total_amount, expected_amount)

        # Test with date range
        amount_with_range = self.crud.get_total_transaction_amount(
            self.test_portfolio_id,
            start_date="2022-12-31",
            end_date="2023-12-31"
        )
        self.assertEqual(amount_with_range, expected_amount)

    @database_test_required
    def test_OrderRecordCRUD_Delete_By_Portfolio_Real(self):
        """Test OrderRecordCRUD delete by portfolio business helper method with real database"""
        # Create test order records
        for i in range(3):
            params = self.test_order_params.copy()
            params["order_id"] = f"TestOrder{self.test_id}_delete_{i}"
            self.crud.create(**params)

        # Verify orders exist
        found_orders = self.crud.find_by_portfolio(self.test_portfolio_id)
        self.assertEqual(len(found_orders), 3)

        # Get table size before deletion
        size0 = get_table_size(self.model)

        # Delete by portfolio
        self.crud.delete_by_portfolio(self.test_portfolio_id)

        # Get table size after deletion
        size1 = get_table_size(self.model)

        # Verify table size decreased by 3
        self.assertEqual(-3, size1 - size0)

        # Verify orders no longer exist
        found_orders_after = self.crud.find_by_portfolio(self.test_portfolio_id)
        self.assertEqual(len(found_orders_after), 0)

        # Test delete with empty portfolio_id (should raise ValueError)
        with self.assertRaises(ValueError):
            self.crud.delete_by_portfolio("")

    @database_test_required
    def test_OrderRecordCRUD_Delete_By_Order_Id_Real(self):
        """Test OrderRecordCRUD delete by order ID business helper method with real database"""
        # Create test order record
        created_order = self.crud.create(**self.test_order_params)

        # Verify order exists
        found_orders = self.crud.find_by_order_id(self.test_order_id)
        self.assertEqual(len(found_orders), 1)

        # Delete by order ID
        self.crud.delete_by_order_id(self.test_order_id)

        # Verify order no longer exists
        found_orders_after = self.crud.find_by_order_id(self.test_order_id)
        self.assertEqual(len(found_orders_after), 0)

        # Test delete with empty order_id (should raise ValueError)
        with self.assertRaises(ValueError):
            self.crud.delete_by_order_id("")

    @database_test_required
    def test_OrderRecordCRUD_Delete_By_Status_Real(self):
        """Test OrderRecordCRUD delete by status business helper method with real database"""
        # Create test order records with different statuses
        statuses = [ORDERSTATUS_TYPES.SUBMITTED.value, ORDERSTATUS_TYPES.FILLED.value, ORDERSTATUS_TYPES.SUBMITTED.value, ORDERSTATUS_TYPES.CANCELED]

        for i, status in enumerate(statuses):
            params = self.test_order_params.copy()
            params["order_id"] = f"TestOrder{self.test_id}_delstatus_{i}"
            params["status"] = status
            self.crud.create(**params)

        # Verify all orders exist
        all_orders = self.crud.find_by_portfolio(self.test_portfolio_id)
        self.assertEqual(len(all_orders), 4)

        # Delete submitted orders (pending equivalent)
        self.crud.delete_by_status(ORDERSTATUS_TYPES.SUBMITTED.value, portfolio_id=self.test_portfolio_id)

        # Verify only 2 orders remain (filled and canceled)
        remaining_orders = self.crud.find_by_portfolio(self.test_portfolio_id)
        self.assertEqual(len(remaining_orders), 2)
        statuses_remaining = [order.status for order in remaining_orders]
        self.assertIn(ORDERSTATUS_TYPES.FILLED.value, statuses_remaining)
        self.assertIn(ORDERSTATUS_TYPES.CANCELED, statuses_remaining)
        self.assertNotIn(ORDERSTATUS_TYPES.SUBMITTED.value, statuses_remaining)

    @database_test_required
    def test_OrderRecordCRUD_DataFrame_Output_Real(self):
        """Test OrderRecordCRUD DataFrame output with real database"""
        # Create test order record
        created_order = self.crud.create(**self.test_order_params)

        # Get as DataFrame
        df_result = self.crud.find_by_portfolio(self.test_portfolio_id, as_dataframe=True)

        # Verify DataFrame
        import pandas as pd

        self.assertIsInstance(df_result, pd.DataFrame)
        self.assertGreaterEqual(len(df_result), 1)

        # Find our test order in the DataFrame
        if len(df_result) > 0:
            test_order_rows = df_result[df_result["order_id"] == self.test_order_id]
            if len(test_order_rows) == 0:
                # If no exact match, check if our portfolio exists
                portfolio_rows = df_result[df_result["portfolio_id"] == self.test_portfolio_id]
                self.assertEqual(len(portfolio_rows), 1)
                self.assertEqual(portfolio_rows.iloc[0]["portfolio_id"], self.test_portfolio_id)
            else:
                self.assertEqual(len(test_order_rows), 1)
                self.assertEqual(test_order_rows.iloc[0]["portfolio_id"], self.test_portfolio_id)

    @database_test_required
    def test_OrderRecordCRUD_Complex_Filters_Real(self):
        """Test OrderRecordCRUD complex filters with real database"""
        # Create order records with different attributes
        test_data = [
            {"code": "000001.SZ", "status": ORDERSTATUS_TYPES.FILLED.value, "volume": 100},
            {"code": "000002.SZ", "status": ORDERSTATUS_TYPES.SUBMITTED.value, "volume": 200},
            {"code": "000001.SZ", "status": ORDERSTATUS_TYPES.SUBMITTED.value, "volume": 150},
            {"code": "000003.SZ", "status": ORDERSTATUS_TYPES.FILLED.value, "volume": 300},
        ]

        for i, data in enumerate(test_data):
            params = self.test_order_params.copy()
            params["order_id"] = f"TestOrder{self.test_id}_complex_{i}"
            params["code"] = data["code"]
            params["status"] = data["status"]
            params["volume"] = data["volume"]
            self.crud.create(**params)

        # Test combined filters
        filtered_orders = self.crud.find(
            filters={
                "portfolio_id": self.test_portfolio_id,
                "code": "000001.SZ",
                "status": ORDERSTATUS_TYPES.SUBMITTED.value,
            }
        )

        # Should find 1 order (000001.SZ + PENDING)
        self.assertEqual(len(filtered_orders), 1)
        self.assertEqual(filtered_orders[0].code, "000001.SZ")
        self.assertEqual(filtered_orders[0].status, ORDERSTATUS_TYPES.SUBMITTED.value)

        # Test IN operator for codes
        multi_code_orders = self.crud.find(
            filters={
                "portfolio_id": self.test_portfolio_id,
                "code__in": ["000001.SZ", "000003.SZ"]
            }
        )

        # Should find 3 orders (2 for 000001.SZ + 1 for 000003.SZ)
        self.assertEqual(len(multi_code_orders), 3)
        codes = [o.code for o in multi_code_orders]
        self.assertIn("000001.SZ", codes)
        self.assertIn("000003.SZ", codes)

    @database_test_required
    def test_OrderRecordCRUD_Exists_Real(self):
        """Test OrderRecordCRUD exists functionality with real database"""
        # Test non-existent order record
        exists_before = self.crud.exists(filters={"order_id": self.test_order_id})
        self.assertFalse(exists_before)

        # Create test order record
        created_order = self.crud.create(**self.test_order_params)

        # Test existing order record
        exists_after = self.crud.exists(filters={"order_id": self.test_order_id})
        self.assertTrue(exists_after)

        # Test with more specific filters
        exists_specific = self.crud.exists(
            filters={
                "order_id": self.test_order_id,
                "code": "000001.SZ",
                "status": ORDERSTATUS_TYPES.SUBMITTED.value,
            }
        )
        self.assertTrue(exists_specific)

        # Test with non-matching filters
        exists_false = self.crud.exists(
            filters={
                "order_id": self.test_order_id,
                "code": "999999.SZ"
            }
        )
        self.assertFalse(exists_false)

    @database_test_required
    def test_OrderRecordCRUD_Bulk_Operations_With_Size_Verification_Real(self):
        """Test OrderRecordCRUD bulk operations with table size verification"""
        # Get initial table size
        size0 = get_table_size(self.model)

        # Create bulk test data
        bulk_orders = []
        bulk_count = 5

        for i in range(bulk_count):
            order = self.crud._create_from_params(
                order_id=f"TestOrder{self.test_id}_bulk_{i}",
                portfolio_id=f"TestPortfolio{self.test_id}_bulk",
                engine_id=f"TestEngine{self.test_id}_bulk",
                timestamp=datetime_normalize("2023-01-01 09:30:00"),
                code=f"BULK{i}.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.SUBMITTED.value,
                volume=100 * (i + 1),
                limit_price=to_decimal(10 + i),
                frozen=to_decimal(1000 * (i + 1)),
                transaction_price=to_decimal(0),
                remain=to_decimal(1000 * (i + 1)),
                fee=to_decimal(0),
            )
            bulk_orders.append(order)

        # Perform bulk addition
        result = self.crud.add_batch(bulk_orders)

        # Get table size after bulk addition
        size1 = get_table_size(self.model)

        # Verify table size increased by bulk_count
        self.assertEqual(bulk_count, size1 - size0)

        # Verify each order was added correctly
        for i in range(bulk_count):
            found_orders = self.crud.find(filters={"order_id": f"TestOrder{self.test_id}_bulk_{i}"})
            self.assertEqual(len(found_orders), 1)
            self.assertEqual(found_orders[0].volume, 100 * (i + 1))
            self.assertEqual(found_orders[0].limit_price, to_decimal(10 + i))

        # Bulk delete test orders
        self.crud.remove({"portfolio_id": f"TestPortfolio{self.test_id}_bulk"})

        # Get final table size
        size2 = get_table_size(self.model)

        # Verify table size returned to original
        self.assertEqual(size2, size0)

    @database_test_required
    def test_OrderRecordCRUD_Exception_Handling_Real(self):
        """Test OrderRecordCRUD exception handling with application-layer validation"""
        # Test find with empty filters (should not cause issues)
        all_orders = self.crud.find(filters={})
        self.assertIsInstance(all_orders, list)

        # Test delete with empty portfolio_id (should raise ValueError)
        with self.assertRaises(ValueError):
            self.crud.delete_by_portfolio("")

        with self.assertRaises(ValueError):
            self.crud.delete_by_order_id("")

        # Test remove with overly broad filters (should be safe)
        self.crud.remove({})  # Should be safely handled without affecting other tests

    # ============================================================================
    # Data Validation System Tests for OrderRecord
    # ============================================================================

    @database_test_required
    def test_OrderRecordCRUD_Data_Validation_Invalid_Volume(self):
        """Test OrderRecordCRUD data validation - invalid volume"""
        if ValidationError is None:
            self.skipTest("ValidationError not available")

        print(":test_tube: Testing OrderRecord data validation - invalid volume...")

        # Test application-layer data validation - invalid volume
        with self.assertRaises(ValidationError) as context:
            invalid_params = self.test_order_params.copy()
            invalid_params["volume"] = "invalid_volume"  # Should trigger ValidationError
            self.crud.create(**invalid_params)

        print(":white_check_mark: Invalid volume correctly rejected with ValidationError")


    @database_test_required
    def test_OrderRecordCRUD_Data_Validation_Order_Status(self):
        """Test OrderRecordCRUD data validation - order status"""
        if ValidationError is None:
            self.skipTest("ValidationError not available")

        print(":test_tube: Testing OrderRecord data validation - order status...")

        # Test order status validation
        with self.assertRaises(ValidationError) as context:
            invalid_params = self.test_order_params.copy()
            invalid_params["order_id"] = f"{self.test_order_id}_status_test"
            invalid_params["status"] = "INVALID_STATUS"
            self.crud.create(**invalid_params)

        print(":white_check_mark: Invalid order status correctly rejected with ValidationError")

    @database_test_required
    def test_OrderRecordCRUD_Data_Validation_Direction_Type(self):
        """Test OrderRecordCRUD data validation - direction type"""
        if ValidationError is None:
            self.skipTest("ValidationError not available")

        print(":test_tube: Testing OrderRecord data validation - direction type...")

        # Test direction validation
        with self.assertRaises(ValidationError) as context:
            invalid_params = self.test_order_params.copy()
            invalid_params["order_id"] = f"{self.test_order_id}_direction_test"
            invalid_params["direction"] = "INVALID_DIRECTION"
            self.crud.create(**invalid_params)

        print(":white_check_mark: Invalid direction correctly rejected with ValidationError")

    @database_test_required
    def test_OrderRecordCRUD_Data_Validation_Order_Type(self):
        """Test OrderRecordCRUD data validation - order type"""
        if ValidationError is None:
            self.skipTest("ValidationError not available")

        print(":test_tube: Testing OrderRecord data validation - order type...")

        # Test order type validation
        with self.assertRaises(ValidationError) as context:
            invalid_params = self.test_order_params.copy()
            invalid_params["order_id"] = f"{self.test_order_id}_type_test"
            invalid_params["order_type"] = "INVALID_ORDER_TYPE"
            self.crud.create(**invalid_params)

        print(":white_check_mark: Invalid order type correctly rejected with ValidationError")


    @database_test_required
    def test_OrderRecordCRUD_Data_Validation_Positive_Values(self):
        """Test OrderRecordCRUD data validation - positive values"""
        if ValidationError is None:
            self.skipTest("ValidationError not available")

        print(":test_tube: Testing OrderRecord data validation - positive values...")

        # Test negative volume validation
        with self.assertRaises(ValidationError) as context:
            invalid_params = self.test_order_params.copy()
            invalid_params["order_id"] = f"{self.test_order_id}_negative_test"
            invalid_params["volume"] = -100  # Negative volume should be rejected
            self.crud.create(**invalid_params)

        print(":white_check_mark: Negative volume correctly rejected with ValidationError")


    @database_test_required
    def test_OrderRecordCRUD_Data_Validation_Valid_Data_Passes(self):
        """Test OrderRecordCRUD data validation - valid data passes"""
        if ValidationError is None:
            self.skipTest("ValidationError not available")

        print(":test_tube: Testing OrderRecord data validation - valid data passes...")

        # Test that valid data passes validation and creates successfully
        valid_params = self.test_order_params.copy()
        valid_params["order_id"] = f"{self.test_order_id}_valid_test"

        try:
            created_order = self.crud.create(**valid_params)
            self.assertIsNotNone(created_order)
            self.assertEqual(created_order.order_id, f"{self.test_order_id}_valid_test")
            self.assertEqual(created_order.code, "000001.SZ")
            self.assertEqual(created_order.volume, 1000)
            print(":white_check_mark: Valid OrderRecord data passed validation and created successfully")

            # Cleanup
            self.crud.remove({"order_id": f"{self.test_order_id}_valid_test"})
        except Exception as e:
            self.fail(f"Valid OrderRecord data validation failed: {e}")

    @database_test_required
    def test_OrderRecordCRUD_Data_Validation_Type_Conversion(self):
        """Test OrderRecordCRUD data validation - automatic type conversion"""
        if ValidationError is None:
            self.skipTest("ValidationError not available")

        print(":test_tube: Testing OrderRecord data validation - type conversion...")

        # Test valid data type conversion - string to int
        valid_params = self.test_order_params.copy()
        valid_params["order_id"] = f"{self.test_order_id}_conv"
        valid_params["volume"] = "1000"  # String that can be converted to int
        valid_params["limit_price"] = "10.50"  # String that can be converted to decimal

        try:
            created_order = self.crud.create(**valid_params)
            self.assertIsNotNone(created_order)
            self.assertEqual(created_order.volume, 1000)  # Should be converted to int
            self.assertEqual(created_order.limit_price, to_decimal(10.50))  # Should be converted to decimal
            print(":white_check_mark: Type conversion validation works correctly")

            # Cleanup
            self.crud.remove({"order_id": f"{self.test_order_id}_conv"})
        except Exception as e:
            self.fail(f"Type conversion validation failed: {e}")


    @database_test_required
    def test_OrderRecordCRUD_Data_Validation_Comprehensive(self):
        """Test OrderRecordCRUD comprehensive data validation scenarios"""
        if ValidationError is None:
            self.skipTest("ValidationError not available")

        print(":test_tube: Testing OrderRecord comprehensive data validation...")

        # Test 1: Multiple validation errors (should catch first one)
        print("\n:memo: Testing multiple validation errors:")
        with self.assertRaises(ValidationError) as context:
            invalid_params = {
                # 基础必填字段
                "order_id": f"{self.test_order_id}_multi_test",
                "portfolio_id": self.test_portfolio_id,
                "engine_id": self.test_engine_id,
                "timestamp": "2023-01-01 09:30:00",
                "code": "000001.SZ",  # 有效代码
                
                # 添加缺少的必填字段（使用有效值）
                "direction": DIRECTION_TYPES.LONG,
                "order_type": ORDER_TYPES.MARKETORDER,
                "status": ORDERSTATUS_TYPES.SUBMITTED.value,
                "limit_price": 10.5,
                
                # 故意设置无效值来测试验证
                "volume": "invalid_volume",  # Invalid type
            }
            self.crud.create(**invalid_params)

        print(":white_check_mark: Multiple validation errors handled correctly")

        # Test 2: Edge case - empty string validation
        print("\n:memo: Testing empty string validation:")
        with self.assertRaises(ValidationError) as context:
            invalid_params = self.test_order_params.copy()
            invalid_params["order_id"] = ""  # Empty string
            self.crud.create(**invalid_params)

        print(":white_check_mark: Empty string validation handled correctly")
