import unittest
import sys
import os
import uuid
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

try:
    from ginkgo.data.crud.order_crud import OrderCRUD
    from ginkgo.data.models import MOrder
    from ginkgo.backtest import Order
    from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES
    from ginkgo.libs import GCONF, datetime_normalize, to_decimal
    from ginkgo.data.drivers import get_db_connection, get_table_size, create_table, drop_table
    from ginkgo.data.crud.validation import ValidationError
    from sqlalchemy import text
except ImportError as e:
    print(f"Import error: {e}")
    OrderCRUD = None
    GCONF = None


class OrderCRUDTest(unittest.TestCase):
    """
    OrderCRUD database integration tests.
    Tests Order-specific CRUD operations with actual database.
    """

    @classmethod
    def setUpClass(cls):
        """Class-level setup: check database configuration and connection"""
        if OrderCRUD is None or GCONF is None:
            raise AssertionError("OrderCRUD or GCONF not available")

        # Set model for table size verification
        cls.model = MOrder

        # Recreate table for clean testing
        try:
            drop_table(cls.model, no_skip=True)
            create_table(cls.model, no_skip=True)
            print(":white_check_mark: Order table recreated for testing")
        except Exception as e:
            print(f":warning: Order table recreation failed: {e}")

        # Verify database configuration (MOrder uses MySQL)
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

        # Create OrderCRUD instance
        cls.crud = OrderCRUD()

        # Test database connection
        try:
            connection = get_db_connection(MOrder)
            with connection.get_session() as session:
                session.execute(text("SELECT 1"))
            print(":white_check_mark: Order database connection successful")
        except Exception as e:
            raise AssertionError(f"Database connection failed: {e}")

    def setUp(self):
        """Setup for each test: prepare unique test data"""
        self.test_id = str(uuid.uuid4())[:8]
        self.test_portfolio_id = f"PORTFOLIO_{self.test_id}"
        self.test_engine_id = f"ENGINE_{self.test_id}"
        self.test_timestamp = datetime(2023, 6, 15, 14, 30, 0)

        # Test order data based on actual MOrder fields
        self.test_order_params = {
            "portfolio_id": self.test_portfolio_id,
            "engine_id": self.test_engine_id,
            "code": f"ORDERTEST{self.test_id}.SZ",
            "direction": DIRECTION_TYPES.LONG,
            "order_type": ORDER_TYPES.LIMITORDER,
            "status": ORDERSTATUS_TYPES.NEW,
            "volume": 1000,
            "limit_price": to_decimal(10.50),
            "frozen": to_decimal(10500),
            "transaction_price": to_decimal(0),
            "transaction_volume": 0,
            "remain": to_decimal(0),
            "fee": to_decimal(0),
            "timestamp": self.test_timestamp,
            "source": SOURCE_TYPES.SIM,
        }

    def tearDown(self):
        """Cleanup after each test"""
        try:
            # Remove test records by portfolio and engine patterns
            self.crud.remove({"portfolio_id__like": f"PORTFOLIO_{self.test_id}%"})
            self.crud.remove({"engine_id__like": f"ENGINE_{self.test_id}%"})
            self.crud.remove({"code__like": f"ORDERTEST{self.test_id}%"})
            print(f":broom: Cleaned up test data for order {self.test_id}")
        except Exception as e:
            print(f":warning: Cleanup failed: {e}")
            # Fallback: try table recreation if remove fails
            try:
                drop_table(self.model, no_skip=True)
                create_table(self.model, no_skip=True)
                print(f":arrows_counterclockwise: Fallback cleanup: recreated order table")
            except Exception as fallback_error:
                print(f":warning: Fallback cleanup also failed: {fallback_error}")

    @classmethod
    def tearDownClass(cls):
        """Class-level cleanup: remove any remaining test data"""
        try:
            # Final cleanup using portfolio, engine, and code patterns
            cls.crud.remove({"portfolio_id__like": "PORTFOLIO_%"})
            cls.crud.remove({"engine_id__like": "ENGINE_%"})
            cls.crud.remove({"code__like": "ORDERTEST%"})
            print(":broom: Final cleanup of all order test records completed")
        except Exception as e:
            print(f":warning: Final cleanup failed: {e}")
            # Fallback final cleanup
            try:
                drop_table(cls.model, no_skip=True)
                create_table(cls.model, no_skip=True)
                print(f":arrows_counterclockwise: Final fallback cleanup: recreated order table")
            except Exception as fallback_error:
                print(f":warning: Final fallback cleanup also failed: {fallback_error}")

    def test_OrderCRUD_Create_From_Params_Real(self):
        """Test OrderCRUD create from parameters with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create order from parameters
        created_order = self.crud.create(**self.test_order_params)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify creation
        self.assertIsNotNone(created_order)
        self.assertIsInstance(created_order, MOrder)
        self.assertEqual(created_order.portfolio_id, self.test_portfolio_id)
        self.assertEqual(created_order.engine_id, self.test_engine_id)
        self.assertEqual(created_order.code, f"ORDERTEST{self.test_id}.SZ")
        self.assertEqual(created_order.direction, DIRECTION_TYPES.LONG)
        self.assertEqual(created_order.order_type, ORDER_TYPES.LIMITORDER)
        self.assertEqual(created_order.status, ORDERSTATUS_TYPES.NEW)
        self.assertEqual(created_order.volume, 1000)
        self.assertEqual(created_order.limit_price, to_decimal(10.50))
        self.assertEqual(created_order.frozen, to_decimal(10500))
        self.assertEqual(created_order.source, SOURCE_TYPES.SIM)

        # Verify in database
        found_orders = self.crud.find(filters={"portfolio_id": self.test_portfolio_id})
        self.assertEqual(len(found_orders), 1)
        self.assertEqual(found_orders[0].engine_id, self.test_engine_id)

    def test_OrderCRUD_Add_Order_Object_Real(self):
        """Test OrderCRUD add Order object with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create Order object using the actual Order class
        order_obj = Order(
            code=f"ORDEROBJ{self.test_id}.SH",
            direction=DIRECTION_TYPES.SHORT,
            order_type=ORDER_TYPES.MARKETORDER,
            volume=2000,
            limit_price=to_decimal(15.75),
            timestamp=datetime(2023, 6, 16, 10, 0, 0),
            status=ORDERSTATUS_TYPES.SUBMITTED
        )
        # Set additional attributes that may not be in constructor
        order_obj.portfolio_id = f"PORTFOLIO_OBJ_{self.test_id}"
        order_obj.engine_id = f"ENGINE_OBJ_{self.test_id}"
        order_obj.frozen = to_decimal(31500)
        order_obj.transaction_price = to_decimal(0)
        order_obj.transaction_volume = 0
        order_obj.remain = to_decimal(0)
        order_obj.fee = to_decimal(5.0)

        # Convert order to MOrder and add
        morder = self.crud._convert_input_item(order_obj)
        added_order = self.crud.add(morder)

        # Get table size after operation
        size1 = get_table_size(self.model)

        # Verify table size increased by 1
        self.assertEqual(size0 + 1, size1)

        # Verify addition
        self.assertIsNotNone(added_order)
        self.assertEqual(added_order.portfolio_id, f"PORTFOLIO_OBJ_{self.test_id}")
        self.assertEqual(added_order.code, f"ORDEROBJ{self.test_id}.SH")
        self.assertEqual(added_order.direction, DIRECTION_TYPES.SHORT)
        self.assertEqual(added_order.order_type, ORDER_TYPES.MARKETORDER)
        self.assertEqual(added_order.status, ORDERSTATUS_TYPES.SUBMITTED)

        # Verify in database
        found_orders = self.crud.find(filters={"code": f"ORDEROBJ{self.test_id}.SH"})
        self.assertEqual(len(found_orders), 1)

    def test_OrderCRUD_Add_Batch_Real(self):
        """Test OrderCRUD batch addition with real database"""
        # Get table size before operation
        size0 = get_table_size(self.model)

        # Create multiple order objects
        orders = []
        batch_count = 3
        for i in range(batch_count):
            order = self.crud._create_from_params(
                portfolio_id=f"PORTFOLIO_BATCH_{self.test_id}_{i}",
                engine_id=f"ENGINE_BATCH_{self.test_id}_{i}",
                code=f"BATCHORDER{self.test_id}_{i}.SZ",
                direction=DIRECTION_TYPES.LONG if i % 2 == 0 else DIRECTION_TYPES.SHORT,
                order_type=ORDER_TYPES.LIMITORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=1000 + i * 100,
                limit_price=to_decimal(10.00 + i * 0.50),
                frozen=to_decimal((1000 + i * 100) * (10.00 + i * 0.50)),
                timestamp=datetime(2023, 6, 15 + i, 10, 0, 0),
                source=SOURCE_TYPES.SIM,
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
            found_orders = self.crud.find(filters={"code": f"BATCHORDER{self.test_id}_{i}.SZ"})
            self.assertEqual(len(found_orders), 1)
            self.assertEqual(found_orders[0].volume, 1000 + i * 100)
            self.assertEqual(found_orders[0].limit_price, to_decimal(10.00 + i * 0.50))

    def test_OrderCRUD_Order_Status_Management_Real(self):
        """Test OrderCRUD order status management with real database"""
        # Create order with NEW status
        created_order = self.crud.create(**self.test_order_params)
        self.assertEqual(created_order.status, ORDERSTATUS_TYPES.NEW)

        # Update to SUBMITTED status
        updated_params = self.test_order_params.copy()
        updated_params["status"] = ORDERSTATUS_TYPES.SUBMITTED
        submitted_order = self.crud.create(**updated_params)

        # Update to FILLED status with transaction details
        filled_params = self.test_order_params.copy()
        filled_params["status"] = ORDERSTATUS_TYPES.FILLED
        filled_params["transaction_price"] = to_decimal(10.45)
        filled_params["transaction_volume"] = 1000
        filled_params["remain"] = to_decimal(0)
        filled_params["fee"] = to_decimal(5.22)
        filled_order = self.crud.create(**filled_params)

        # Verify different status orders in database
        new_orders = self.crud.find(filters={"status": ORDERSTATUS_TYPES.NEW})
        submitted_orders = self.crud.find(filters={"status": ORDERSTATUS_TYPES.SUBMITTED})
        filled_orders = self.crud.find(filters={"status": ORDERSTATUS_TYPES.FILLED})

        # Should have at least one order of each status
        self.assertGreaterEqual(len(new_orders), 1)
        self.assertGreaterEqual(len(submitted_orders), 1)
        self.assertGreaterEqual(len(filled_orders), 1)

        # Verify filled order has transaction details
        matching_filled = [o for o in filled_orders if o.transaction_volume == 1000]
        self.assertEqual(len(matching_filled), 1)
        self.assertEqual(matching_filled[0].transaction_price, to_decimal(10.45))

    def test_OrderCRUD_Find_By_Portfolio_Real(self):
        """Test OrderCRUD find by portfolio with real database"""
        # Create orders for different portfolios
        portfolios = [f"PORTFOLIO_FIND_{self.test_id}_{i}" for i in range(3)]

        for i, portfolio in enumerate(portfolios):
            params = self.test_order_params.copy()
            params["portfolio_id"] = portfolio
            params["code"] = f"FINDTEST{self.test_id}_{i}.SZ"
            params["volume"] = 1000 + i * 100
            self.crud.create(**params)

        # Test find by specific portfolio
        portfolio_orders = self.crud.find(filters={"portfolio_id": portfolios[1]})
        self.assertEqual(len(portfolio_orders), 1)
        self.assertEqual(portfolio_orders[0].volume, 1100)

        # Test find by portfolio pattern
        pattern_orders = self.crud.find(filters={"portfolio_id__like": f"PORTFOLIO_FIND_{self.test_id}_%"})
        self.assertEqual(len(pattern_orders), 3)

    def test_OrderCRUD_Find_By_Direction_Real(self):
        """Test OrderCRUD find by direction with real database"""
        # Create orders with different directions
        directions_data = [
            {"direction": DIRECTION_TYPES.LONG, "code": f"LONGORDER{self.test_id}.SZ"},
            {"direction": DIRECTION_TYPES.SHORT, "code": f"SHORTORDER{self.test_id}.SZ"},
            {"direction": DIRECTION_TYPES.LONG, "code": f"LONGORDER2{self.test_id}.SZ"},
        ]

        for data in directions_data:
            params = self.test_order_params.copy()
            params.update(data)
            self.crud.create(**params)

        # Test find LONG orders
        long_orders = self.crud.find(filters={"direction": DIRECTION_TYPES.LONG})
        long_test_orders = [o for o in long_orders if f"{self.test_id}" in o.code]
        self.assertEqual(len(long_test_orders), 2)

        # Test find SHORT orders
        short_orders = self.crud.find(filters={"direction": DIRECTION_TYPES.SHORT})
        short_test_orders = [o for o in short_orders if f"{self.test_id}" in o.code]
        self.assertEqual(len(short_test_orders), 1)

    def test_OrderCRUD_DataFrame_Output_Real(self):
        """Test OrderCRUD DataFrame output with real database"""
        # Create test order
        created_order = self.crud.create(**self.test_order_params)

        # Get as DataFrame
        df_result = self.crud.find(filters={"portfolio_id": self.test_portfolio_id}, as_dataframe=True)

        # Verify DataFrame
        import pandas as pd

        self.assertIsInstance(df_result, pd.DataFrame)
        self.assertEqual(len(df_result), 1)
        self.assertEqual(df_result.iloc[0]["portfolio_id"], self.test_portfolio_id)
        self.assertEqual(df_result.iloc[0]["code"], f"ORDERTEST{self.test_id}.SZ")

    def test_OrderCRUD_Complex_Filters_Real(self):
        """Test OrderCRUD complex filters with real database"""
        # Create orders with different attributes
        test_data = [
            {"status": ORDERSTATUS_TYPES.NEW, "volume": 1000, "limit_price": to_decimal(10.0)},
            {"status": ORDERSTATUS_TYPES.SUBMITTED, "volume": 2000, "limit_price": to_decimal(15.0)},
            {"status": ORDERSTATUS_TYPES.FILLED, "volume": 1500, "limit_price": to_decimal(12.0)},
        ]

        for i, data in enumerate(test_data):
            params = self.test_order_params.copy()
            params.update(data)
            params["code"] = f"COMPLEXTEST{self.test_id}_{i}.SZ"
            self.crud.create(**params)

        # Test combined filters
        filtered_orders = self.crud.find(
            filters={
                "code__like": f"COMPLEXTEST{self.test_id}_%",
                "volume__gte": 1500,
                "limit_price__lte": to_decimal(12.0),
            }
        )

        # Should find 1 order (volume >= 1500 AND price <= 12.0)
        self.assertEqual(len(filtered_orders), 1)
        self.assertEqual(filtered_orders[0].status, ORDERSTATUS_TYPES.FILLED)
        self.assertGreaterEqual(filtered_orders[0].volume, 1500)
        self.assertLessEqual(filtered_orders[0].limit_price, to_decimal(12.0))

    def test_OrderCRUD_Exception_Handling_Real(self):
        """Test OrderCRUD exception handling with real database"""
        # Test find with empty filters (should not cause issues)
        all_orders = self.crud.find(filters={})
        self.assertIsInstance(all_orders, list)

        # Test create with all required parameters (OrderCRUD requires all fields)
        required_params = {
            "portfolio_id": f"MINIMAL_{self.test_id}",
            "engine_id": f"MINIMAL_ENGINE_{self.test_id}",
            "code": f"MINIMAL{self.test_id}.SZ",
            "direction": DIRECTION_TYPES.LONG,
            "order_type": ORDER_TYPES.MARKETORDER,
            "status": ORDERSTATUS_TYPES.NEW,
            "volume": 100,
            "limit_price": 10.0,  # Required field
            "frozen": 1000.0,  # Required field
            "transaction_price": 0.0,  # Required field (initial value)
            "transaction_volume": 0,  # Required field (initial value)
            "remain": 100.0,  # Required field (initial = volume)
            "fee": 0.0,  # Required field (initial value)
            "timestamp": self.test_timestamp,  # Required field
            "source": SOURCE_TYPES.SIM
        }

        try:
            minimal_order = self.crud.create(**required_params)
            self.assertIsNotNone(minimal_order)
            # Verify all required fields are set correctly
            self.assertEqual(minimal_order.direction, DIRECTION_TYPES.LONG)
            self.assertEqual(minimal_order.order_type, ORDER_TYPES.MARKETORDER)
            self.assertEqual(minimal_order.status, ORDERSTATUS_TYPES.NEW)
            self.assertEqual(minimal_order.volume, 100)
            self.assertEqual(minimal_order.limit_price, Decimal("10.0"))
            self.assertEqual(minimal_order.frozen, Decimal("1000.0"))
            self.assertEqual(minimal_order.transaction_price, Decimal("0.0"))
            self.assertEqual(minimal_order.transaction_volume, 0)
            self.assertEqual(minimal_order.remain, Decimal("100.0"))
            self.assertEqual(minimal_order.fee, Decimal("0.0"))
            self.assertEqual(minimal_order.timestamp, self.test_timestamp)
            self.assertEqual(minimal_order.source, SOURCE_TYPES.SIM)
        except Exception as e:
            self.fail(f"Creating order with all required parameters should not fail: {e}")

        # Test conversion with invalid object
        invalid_conversion = self.crud._convert_input_item("invalid_object")
        self.assertIsNone(invalid_conversion)

    def test_OrderCRUD_ValidationError_Tests(self):
        """Test OrderCRUD field validation functionality"""
        # Test empty portfolio_id
        with self.assertRaises(ValidationError):
            self.crud.create(
                portfolio_id="",
                engine_id=self.test_engine_id,
                code=self.test_order_params["code"],
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.LIMITORDER,
                volume=1000,
                source=SOURCE_TYPES.SIM
            )

        # Test empty engine_id  
        with self.assertRaises(ValidationError):
            self.crud.create(
                portfolio_id=self.test_portfolio_id,
                engine_id="",
                code=self.test_order_params["code"],
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.LIMITORDER,
                volume=1000,
                source=SOURCE_TYPES.SIM
            )

        # Test empty code
        with self.assertRaises(ValidationError):
            self.crud.create(
                portfolio_id=self.test_portfolio_id,
                engine_id=self.test_engine_id,
                code="",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.LIMITORDER,
                volume=1000,
                source=SOURCE_TYPES.SIM
            )

        # Test invalid volume (zero or negative)
        with self.assertRaises(ValidationError):
            self.crud.create(
                portfolio_id=self.test_portfolio_id,
                engine_id=self.test_engine_id,
                code=self.test_order_params["code"],
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.LIMITORDER,
                volume=0,  # Invalid: must be >= 1
                source=SOURCE_TYPES.SIM
            )

        # Test negative limit_price
        with self.assertRaises(ValidationError):
            self.crud.create(
                portfolio_id=self.test_portfolio_id,
                engine_id=self.test_engine_id,
                code=self.test_order_params["code"],
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.LIMITORDER,
                volume=1000,
                limit_price=-10.0,  # Invalid: must be >= 0
                source=SOURCE_TYPES.SIM
            )

        # Test invalid direction enum
        with self.assertRaises(ValidationError):
            self.crud.create(
                portfolio_id=self.test_portfolio_id,
                engine_id=self.test_engine_id,
                code=self.test_order_params["code"],
                direction="INVALID_DIRECTION",
                order_type=ORDER_TYPES.LIMITORDER,
                volume=1000,
                source=SOURCE_TYPES.SIM
            )

        # Test invalid order_type enum
        with self.assertRaises(ValidationError):
            self.crud.create(
                portfolio_id=self.test_portfolio_id,
                engine_id=self.test_engine_id,
                code=self.test_order_params["code"],
                direction=DIRECTION_TYPES.LONG,
                order_type="INVALID_ORDER_TYPE",
                volume=1000,
                source=SOURCE_TYPES.SIM
            )

        # Test invalid status enum
        with self.assertRaises(ValidationError):
            self.crud.create(
                portfolio_id=self.test_portfolio_id,
                engine_id=self.test_engine_id,
                code=self.test_order_params["code"],
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.LIMITORDER,
                status="INVALID_STATUS",
                volume=1000,
                source=SOURCE_TYPES.SIM
            )

        # Test invalid source enum
        with self.assertRaises(ValidationError):
            self.crud.create(
                portfolio_id=self.test_portfolio_id,
                engine_id=self.test_engine_id,
                code=self.test_order_params["code"],
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.LIMITORDER,
                volume=1000,
                source="INVALID_SOURCE"
            )
