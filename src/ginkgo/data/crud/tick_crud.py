# Upstream: TickService (逐笔成交数据业务服务)、Data Query (查询tick数据)
# Downstream: BaseCRUD (继承提供标准CRUD能力)、MTick模型(动态分区表每个股票代码对应独立表)
# Role: TickCRUD Tick数据CRUD继承BaseCRUD提供Tick数据管理功能支持交易系统功能和组件集成提供完整业务支持






from ginkgo.data.access_control import restrict_crud_access

from typing import List, Optional, Union, Any, Dict
import pandas as pd
from datetime import datetime

from sqlalchemy.orm import Session

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models import MTick
from ginkgo.entities import Tick
from ginkgo.enums import TICKDIRECTION_TYPES, SOURCE_TYPES
from ginkgo.libs import datetime_normalize, GLOG, Number, to_decimal
from ginkgo.data.drivers import drop_table

# Global registry for dynamically created tick models
tick_model_registry = {}


def get_tick_model(code: str) -> type:
    """
    Get or create dynamic Tick model for specific stock code.
    Tick data uses partitioning - each stock code has its own table.

    Args:
        code: Stock code (e.g., "000001.SZ")

    Returns:
        Dynamically created MTick subclass for the specific code
    """
    global tick_model_registry
    table_name = f"{code.replace('.', '_')}_Tick"

    if table_name not in tick_model_registry:
        # Dynamically create new model class (不继承ModelConversion)
        newclass = type(
            table_name,
            (MTick,),  # 只继承MTick，转换功能由TickCRUD处理
            {
                "__tablename__": table_name,
                "__abstract__": False,
                "_stock_code": code,  # 存储股票代码用于转换
            },
        )
        tick_model_registry[table_name] = newclass
        GLOG.DEBUG(f"Created dynamic tick model: {table_name}")

    return tick_model_registry[table_name]


@restrict_crud_access
class TickCRUD:
    """
    Tick数据专用CRUD - 支持动态Model的标准CRUD接口

    TickCRUD是唯一需要动态Model生成的特殊CRUD类：
    - 基于分区表设计，每个股票代码对应独立表
    - 实现所有标准CRUD方法，内部适配动态Model
    - 保持与其他CRUD类相同的API一致性
    - 所有查询方法返回ModelList，支持链式调用

    特点：
    - 适配器模式：标准CRUD接口 + 动态Model适配
    - 唯一入口：一个实例处理所有股票代码
    - 链式调用：results.to_dataframe(), results.to_entities()

    Usage:
    # 创建唯一入口
    tick_crud = TickCRUD()

    # 标准CRUD操作 - 适配动态Model
    tick = tick_crud.create(code="000001.SZ", price=10.5, volume=1000)
    tick_crud.add_batch([tick1, tick2, tick3])

    # 查询操作 - 返回ModelList，支持链式调用
    results = tick_crud.find({"code": "000001.SZ", "price__gt": 10.0})
    df = results.to_dataframe()
    objs = results.to_entities()

    # 业务辅助方法 - 一致的API
    results = tick_crud.find_by_time_range("000001.SZ", "2024-01-01", "2024-01-02")
    df = results.to_dataframe()  # ✅ 链式调用
    objs = results.to_entities()  # ✅ 链式调用
    """

    def __init__(self):
        """初始化TickCRUD作为唯一入口"""
        pass

    # ========================
    # 标准CRUD方法 - 适配动态Model
    # ========================

    def create(self, **kwargs):
        """
        创建单个tick记录 - 适配动态Model

        Args:
            code: 股票代码（必需）
            **kwargs: 其他tick字段

        Returns:
            创建的MTick模型实例

        Example:
            tick = tick_crud.create(code="000001.SZ", price=10.5, volume=1000,
                                     direction=1, timestamp="2024-01-01 09:30:00")

        Raises:
            ValueError: 如果code参数无效或缺失
        """
        # 严格校验code参数
        code = kwargs.get("code")
        if not code or not isinstance(code, str):
            raise ValueError(
                f"Invalid stock code: {code}. "
                "Stock code must be a non-empty string. "
                "Example: '000001.SZ'"
            )

        # 获取动态Model类
        model_class = get_tick_model(code)

        # 创建临时CRUD实例用于操作
        temp_crud = self._create_temp_crud(model_class)

        # 调用标准create方法
        return temp_crud.create(**kwargs)

    def add(self, item):
        """
        添加单个tick记录 - 适配动态Model

        Args:
            item: Tick对象或MTick模型实例，必须包含code字段

        Returns:
            添加的记录

        Example:
            tick = tick_crud.add({"code": "000001.SZ", "price": 10.5, "volume": 1000})
        """
        # 提取code
        code = self._extract_code_from_item(item)
        if not code:
            raise ValueError("Item must contain 'code' field for dynamic Model generation")

        # 获取动态Model类
        model_class = get_tick_model(code)

        # 确保动态表存在
        self._ensure_table_exists_for_model(model_class, code)

        # 转换为目标Model
        model = self._convert_to_model(item, model_class)

        # 创建临时CRUD实例
        temp_crud = self._create_temp_crud(model_class)

        # 添加记录
        return temp_crud.add(model)

    def add_batch(self, items):
        """
        批量添加tick记录 - 适配动态Model

        Args:
            items: Tick对象或MTick模型实例列表

        Returns:
            添加的记录列表

        Example:
            results = tick_crud.add_batch([
                {"code": "000001.SZ", "price": 10.5, "volume": 1000},
                {"code": "000002.SZ", "price": 20.5, "volume": 2000},
            ])
        """
        if not items:
            return []

        # 按code分组处理（可能涉及不同的表）
        results = []
        items_by_code = {}

        # 分组
        for item in items:
            code = self._extract_code_from_item(item)
            if code not in items_by_code:
                items_by_code[code] = []
            items_by_code[code].append(item)

        # 分别处理每个code的记录
        for code, code_items in items_by_code.items():
            model_class = get_tick_model(code)

            # 确保动态表存在
            self._ensure_table_exists_for_model(model_class, code)

            temp_crud = self._create_temp_crud(model_class)

            # 转换并添加
            models = [self._convert_to_model(item, model_class) for item in code_items]
            batch_results = temp_crud.add_batch(models)
            results.extend(batch_results)

        return results

    def remove(self, filters):
        """
        删除tick记录 - 适配动态Model

        Args:
            filters: 过滤条件，必须包含code字段

        Returns:
            删除的记录数量

        Example:
            count = tick_crud.remove({"code": "000001.SZ", "timestamp__lt": "2024-01-01"})
        """
        # 提取code
        code = self._extract_code_from_filters(filters)
        if not code:
            raise ValueError("Filters must contain 'code' field for dynamic Model generation")

        # 获取动态Model类
        model_class = get_tick_model(code)

        # 创建临时CRUD实例
        temp_crud = self._create_temp_crud(model_class)

        # 删除记录
        return temp_crud.remove(filters)

    def count(self, filters=None):
        """
        统计tick记录数量 - 适配动态Model

        Args:
            filters: 过滤条件，必须包含code字段

        Returns:
            记录数量

        Example:
            count = tick_crud.count({"code": "000001.SZ", "price__gt": 10.0})
        """
        if filters is None:
            raise ValueError("Filters parameter is required for count operation")

        # 提取code
        code = self._extract_code_from_filters(filters)
        if not code:
            raise ValueError("Filters must contain 'code' field for dynamic Model generation")

        # 获取动态Model类
        model_class = get_tick_model(code)

        # 创建临时CRUD实例
        temp_crud = self._create_temp_crud(model_class)

        # 统计记录
        return temp_crud.count(filters)

    def exists(self, filters):
        """
        检查记录是否存在 - 适配动态Model

        Args:
            filters: 过滤条件，必须包含code字段

        Returns:
            是否存在记录

        Example:
            exists = tick_crud.exists({"code": "000001.SZ", "timestamp": "2024-01-01 09:30:00"})
        """
        # 提取code
        code = self._extract_code_from_filters(filters)
        if not code:
            raise ValueError("Filters must contain 'code' field for dynamic Model generation")

        # 获取动态Model类
        model_class = get_tick_model(code)

        # 创建临时CRUD实例
        temp_crud = self._create_temp_crud(model_class)

        # 检查存在性
        return temp_crud.exists(filters)

    def modify(self, filters, updates):
        """
        修改tick记录 - 适配动态Model

        Args:
            filters: 过滤条件，必须包含code字段
            updates: 更新字段

        Returns:
            修改的记录数量

        Example:
            count = tick_crud.modify(
                {"code": "000001.SZ", "timestamp": "2024-01-01 09:30:00"},
                {"volume": 2000}
            )
        """
        # 提取code
        code = self._extract_code_from_filters(filters)
        if not code:
            raise ValueError("Filters must contain 'code' field for dynamic Model generation")

        # 获取动态Model类
        model_class = get_tick_model(code)

        # 创建临时CRUD实例
        temp_crud = self._create_temp_crud(model_class)

        # 修改记录
        return temp_crud.modify(filters, updates)

    def _ensure_table_exists(self):
        """确保当前股票代码对应的tick表存在"""
        from ginkgo.libs import GLOG
        from ginkgo.data.drivers import create_table, is_table_exists

        try:
            if not is_table_exists(self.model_class):
                GLOG.INFO(f"Creating tick table for {self.code}: {self.model_class.__tablename__}")
                create_table(self.model_class)
                GLOG.INFO(f"Successfully created tick table: {self.model_class.__tablename__}")

                # 再次检查表是否创建成功
                if is_table_exists(self.model_class):
                    GLOG.DEBUG(f"Table creation verified: {self.model_class.__tablename__}")
                else:
                    GLOG.ERROR(f"Table creation failed - table still not exists: {self.model_class.__tablename__}")
            else:
                GLOG.DEBUG(f"Tick table already exists: {self.model_class.__tablename__}")
        except Exception as e:
            GLOG.ERROR(f"Failed to ensure tick table for {self.code}: {e}")
            # 不抛出异常，让调用者处理

    def _ensure_table_exists_for_model(self, model_class, code):
        """确保指定Model对应的tick表存在 - 通用版本"""
        from ginkgo.libs import GLOG
        from ginkgo.data.drivers import create_table, is_table_exists, get_db_connection

        try:
            if not is_table_exists(model_class):
                GLOG.INFO(f"Creating tick table for {code}: {model_class.__tablename__}")
                create_table(model_class, no_skip=True)  # 强制跳过缓存，确保表创建
                GLOG.INFO(f"Successfully created tick table: {model_class.__tablename__}")

                # 使用原生方法验证表创建成功
                if is_table_exists(model_class):
                    GLOG.DEBUG(f"Table creation verified: {model_class.__tablename__}")
                else:
                    GLOG.ERROR(f"Table creation failed - table still not exists: {model_class.__tablename__}")
            else:
                GLOG.DEBUG(f"Tick table already exists: {model_class.__tablename__}")
        except Exception as e:
            GLOG.ERROR(f"Failed to ensure tick table for {code}: {e}")
            # 不抛出异常，让调用者处理

    def _get_field_config(self) -> dict:
        """
        定义 Tick 数据的字段配置 - 所有字段都是必填的

        Returns:
            dict: 字段配置字典
        """
        return {
            # 股票代码 - 非空字符串，最大32字符
            "code": {"type": "string", "min": 1, "max": 32},
            # 成交价格 - 非负数值
            "price": {"type": ["decimal", "float", "int"], "min": 0},
            # 成交量 - 非负整数
            "volume": {"type": ["int", "float"], "min": 0},
            # 方向 - 枚举值或整数
            "direction": {
                "type": ["enum", "int"],
                "choices": [d for d in TICKDIRECTION_TYPES],
            },
            # 时间戳 - datetime 或字符串
            "timestamp": {"type": ["datetime", "string"]},
        }

    # ============================================================================
    # Hook Methods Only - These are called by BaseCRUD template methods
    # ============================================================================

    def _create_from_params(self, **kwargs):
        """
        Hook method: Create MTick from parameters.
        Called by BaseCRUD.create() template method.
        Automatically gets @time_logger + @retry effects.

        Note: TickCRUD.create() method should be called with filters containing 'code'
        to ensure proper dynamic model generation.
        """
        # 确保code参数存在，因为动态Model需要code来确定表名
        if "code" not in kwargs:
            raise ValueError(
                "TickCRUD.create() requires 'code' parameter. "
                "Example: tick_crud.create(code='000001.SZ', price=10.5, volume=1000)"
            )

        return self.model_class(
            code=kwargs.get("code"),
            price=to_decimal(kwargs.get("price", 0)),
            volume=kwargs.get("volume", 0),
            direction=TICKDIRECTION_TYPES.validate_input(kwargs.get("direction", TICKDIRECTION_TYPES.OTHER)) or -1,
            timestamp=datetime_normalize(kwargs.get("timestamp")),
            source=SOURCE_TYPES.validate_input(kwargs.get("source", SOURCE_TYPES.TDX)) or -1,
        )

    def _convert_input_item(self, item: Any):
        """
        Hook method: Convert various objects to the correct dynamic MTick subclass.
        Now handles both Tick business objects and dynamic MTick instances.
        Called by BaseCRUD.add_batch() template method.
        Automatically gets @time_logger + @retry effects.
        """
        if isinstance(item, self.model_class):
            # Item is already the correct dynamic model class, no conversion needed
            return item
        elif hasattr(item, '__class__') and issubclass(item.__class__, MTick):
            # Item is a different MTick subclass, create instance of our specific model
            return self.model_class(
                code=item.code,
                price=item.price,
                volume=item.volume,
                direction=TICKDIRECTION_TYPES.validate_input(getattr(item, 'direction', TICKDIRECTION_TYPES.VOID)) or -1,
                timestamp=item.timestamp,
                source=SOURCE_TYPES.validate_input(getattr(item, 'source', SOURCE_TYPES.TDX)) or -1,
            )
        elif isinstance(item, Tick):
            # Convert business Tick objects to database MTick objects
            return self.model_class(
                code=item.code,
                price=item.price,
                volume=item.volume,
                direction=TICKDIRECTION_TYPES.validate_input(item.direction) or -1,
                timestamp=item.timestamp,
                source=SOURCE_TYPES.validate_input(item.source if hasattr(item, "source") else SOURCE_TYPES.TDX) or -1,
            )
        return None

    def _get_enum_mappings(self) -> Dict[str, Any]:
        """
        🎯 Define field-to-enum mappings for Tick.

        Returns:
            Dictionary mapping field names to enum classes
        """
        return {
            'direction': TICKDIRECTION_TYPES,  # Tick方向字段映射
            'source': SOURCE_TYPES             # 数据源字段映射
        }

    # ============================================================================
    # Adapter Methods for Dynamic Model Handling
    # ============================================================================

    def _extract_code_from_item(self, item):
        """从item中提取code字段"""
        if hasattr(item, 'code'):
            return item.code
        elif isinstance(item, dict) and 'code' in item:
            return item['code']
        else:
            raise ValueError("Item must contain 'code' field for dynamic Model generation")

    def _extract_code_from_filters(self, filters: dict) -> str:
        """从filters中提取code字段"""
        if not filters or 'code' not in filters:
            raise ValueError("Filters must include 'code' field for dynamic Model generation")

        code = filters['code']
        if not code or not isinstance(code, str):
            raise ValueError(f"Invalid stock code: {code}. Stock code must be a non-empty string.")

        return code

    def _convert_to_model(self, item, model_class):
        """将item转换为指定的Model类 - 优先处理Tick业务对象"""
        # 优先处理Tick业务对象
        from ginkgo.entities import Tick
        if isinstance(item, Tick):
            # 获取source信息，如果业务对象有设置的话
            source = getattr(item, '_source', SOURCE_TYPES.TDX)

            return model_class(
                timestamp=datetime_normalize(item.timestamp),
                code=item.code,
                price=item.price,
                volume=item.volume,
                direction=TICKDIRECTION_TYPES.validate_input(item.direction),
                source=SOURCE_TYPES.validate_input(source),
                uuid=item.uuid if item.uuid else None
            )

        # 处理字典类型的数据
        elif isinstance(item, dict) and 'timestamp' in item and 'code' in item:
            return model_class(
                timestamp=datetime_normalize(item.get('timestamp')),
                code=item.get('code'),
                price=item.get('price', 0),
                volume=item.get('volume', 0),
                direction=TICKDIRECTION_TYPES.validate_input(item.get('direction', TICKDIRECTION_TYPES.VOID)) or -1,
                source=SOURCE_TYPES.validate_input(item.get('source', SOURCE_TYPES.TDX)) or -1,
            )
        # 处理其他对象类型的数据
        elif hasattr(item, 'timestamp') and hasattr(item, 'code'):
            return model_class(
                timestamp=datetime_normalize(getattr(item, 'timestamp')),
                code=getattr(item, 'code'),
                price=getattr(item, 'price', 0),
                volume=getattr(item, 'volume', 0),
                direction=TICKDIRECTION_TYPES.validate_input(getattr(item, 'direction', TICKDIRECTION_TYPES.VOID)) or -1,
                source=SOURCE_TYPES.validate_input(getattr(item, 'source', SOURCE_TYPES.TDX)) or -1,
            )
        return None

    def _create_temp_crud(self, model_class):
        """创建临时CRUD实例用于操作指定Model"""
        from ginkgo.data.crud.base_crud import BaseCRUD
        return BaseCRUD(model_class)

    def _convert_models_to_business_objects(self, models: List) -> List[Tick]:
        """
        🎯 Convert MTick models to Tick business objects.

        Args:
            models: List of MTick models with enum fields already fixed

        Returns:
            List of Tick business objects
        """
        business_objects = []
        for model in models:
            # 转换为业务对象 (此时枚举字段已经是正确的枚举对象)
            tick = Tick(
                code=model.code,
                price=model.price,
                volume=model.volume,
                direction=model.direction,
                timestamp=model.timestamp,
                source=model.source,
            )
            business_objects.append(tick)

        return business_objects

    def _safe_enum_convert(self, value, enum_class):
        """
        Utility method: Safe enum conversion with error handling.

        Args:
            value: Value to convert (typically int)
            enum_class: Enum class to convert to

        Returns:
            Enum instance or original value if conversion fails
        """
        try:
            if value is None:
                return None
            return enum_class(value)
        except (ValueError, TypeError):
            return value  # Return original value if conversion fails

    def _convert_output_items(self, items: List) -> List[Any]:
        """
        Hook method: Convert MTick objects to Tick objects for business layer.
        Called by BaseCRUD.find() template method.
        Automatically gets @time_logger effects.

        Note: This method is deprecated in favor of the new unified conversion architecture.
        ModelList will use _convert_to_business_objects() for conversion.
        """
        # 为了向后兼容，保留此方法，但不使用
        return items

    def _convert_models_to_dataframe(self, models) -> pd.DataFrame:
        """
        标准接口：转换Tick Models为DataFrame，包含枚举转换
        支持单个或多个models

        Args:
            models: 单个Tick Model或Tick Model列表

        Returns:
            pandas DataFrame
        """
        # 获取枚举映射
        enum_mappings = self._get_enum_mappings()

        # 处理单个model或多个models
        if not isinstance(models, list):
            models = [models]

        if not models:
            return pd.DataFrame()

        # 批量转换
        data = []
        for model in models:
            model_dict = model.__dict__.copy()
            model_dict.pop('_sa_instance_state', None)

            # 转换枚举字段
            for column, enum_class in enum_mappings.items():
                if column in model_dict:
                    current_value = model_dict[column]
                    converted_value = self._safe_enum_convert(current_value, enum_class)
                    if converted_value is not None:
                        model_dict[column] = converted_value

            data.append(model_dict)

        return pd.DataFrame(data)

    def _convert_to_business_objects(self, models) -> List:
        """
        标准接口：转换Tick Models为业务对象列表，包含枚举转换
        支持单个或多个models

        Args:
            models: 单个Tick Model或Tick Model列表

        Returns:
            业务对象列表
        """
        # 处理单个model或多个models
        if not isinstance(models, list):
            models = [models]

        if not models:
            return []

        # 批量转换枚举字段
        enum_mappings = self._get_enum_mappings()
        for model in models:
            for column, enum_class in enum_mappings.items():
                if hasattr(model, column):
                    current_value = getattr(model, column)
                    converted_value = self._safe_enum_convert(current_value, enum_class)
                    if converted_value is not None:
                        setattr(model, column, converted_value)

        # 调用业务对象转换Hook
        return self._convert_models_to_business_objects(models)

    # ============================================================================
    # Business Helper Methods - Use these for common query patterns
    # ============================================================================

    def find(
        self,
        filters: Optional[Dict[str, Any]] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        order_by: Optional[str] = None,
        desc_order: bool = False,
        distinct_field: Optional[str] = None,
        session: Optional[Session] = None,
    ):
        """
        Find tick data with dynamic stock code support.
        Extracts stock code from filters and uses corresponding dynamic model.

        Args:
            filters: Dictionary of field -> value filters (must include "code")
                    Examples: {"code": "000001.SZ", "timestamp__gte": "2023-01-01"}
            page: Page number (0-based)
            page_size: Number of items per page
            order_by: Field name to order by
            desc_order: Whether to use descending order
            distinct_field: Field name for DISTINCT query (returns unique values of this field)
            session: Optional SQLAlchemy session to use for the operation.

        Returns:
            ModelList - supports to_dataframe() and to_entities()

        Raises:
            ValueError: If filters don't include "code" field
        """
        try:
            # 严格校验股票代码
            if filters is None:
                raise ValueError(
                    "TickCRUD.find() requires 'filters' parameter with 'code' field. "
                    "Example: tick_crud.find(filters={'code': '000001.SZ', ...})"
                )

            if "code" not in filters:
                raise ValueError(
                    "TickCRUD.find() requires 'code' field in filters. "
                    "TickCRUD needs stock code to dynamically generate corresponding Model class. "
                    "Example: tick_crud.find(filters={'code': '000001.SZ', ...})"
                )

            stock_code = filters["code"]
            if not stock_code or not isinstance(stock_code, str):
                raise ValueError(
                    f"Invalid stock code: {stock_code}. "
                    "Stock code must be a non-empty string. "
                    "Example: '000001.SZ'"
                )

            # 使用动态模型类进行查询
            model_class = get_tick_model(stock_code)

            # 检查表是否存在，如果不存在直接返回空ModelList
            from ginkgo.data.drivers import is_table_exists
            if not is_table_exists(model_class):
                GLOG.DEBUG(f"Table {model_class.__tablename__} does not exist, returning empty ModelList")
                from ginkgo.data.crud.model_conversion import ModelList
                return ModelList([], self)

            # 创建临时BaseCRUD实例进行查询
            temp_crud = BaseCRUD(model_class)

            # 调用BaseCRUD的find方法
            results = temp_crud.find(
                filters=filters, page=page, page_size=page_size, order_by=order_by,
                desc_order=desc_order, distinct_field=distinct_field, session=session
            )

            # 返回ModelList以保持API一致性
            from ginkgo.data.crud.model_conversion import ModelList
            return ModelList(results, self)  # 传入self作为CRUD实例
        except Exception as e:
            GLOG.ERROR(f"Failed to find tick data: {e}")
            from ginkgo.data.crud.model_conversion import ModelList
            return ModelList([], self)

    def find_by_time_range(
        self,
        code: str,
        start_time: Optional[Any] = None,
        end_time: Optional[Any] = None,
        direction: Optional[TICKDIRECTION_TYPES] = None,
        min_volume: Optional[int] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ):
        """
        Business helper: Find ticks by time range and conditions.
        Calls BaseCRUD.find() template method to get all decorators.
        Returns ModelList for consistent API: results.to_dataframe(), results.to_entities()

        Args:
            code: Stock code (required for dynamic Model generation)
            start_time: Start time for the range
            end_time: End time for the range
            direction: Optional tick direction filter
            min_volume: Optional minimum volume filter
            page: Page number for pagination
            page_size: Page size for pagination

        Returns:
            ModelList - supports to_dataframe() and to_entities()

        Raises:
            ValueError: If code is not provided or invalid

        Example:
            results = tick_crud.find_by_time_range("000001.SZ", "2024-01-01", "2024-01-02")
            df = results.to_dataframe()
            objs = results.to_entities()
        """
        # 严格校验股票代码
        if not code or not isinstance(code, str):
            raise ValueError(
                f"Invalid stock code: {code}. "
                "Stock code must be a non-empty string. "
                "Example: '000001.SZ'"
            )

        filters = {"code": code}

        if start_time:
            filters["timestamp__gte"] = datetime_normalize(start_time)
        if end_time:
            filters["timestamp__lte"] = datetime_normalize(end_time)
        if direction:
            filters["direction"] = TICKDIRECTION_TYPES.validate_input(direction) or -1
        if min_volume:
            filters["volume__gte"] = min_volume

        return self.find(
            filters=filters,
            page=page,
            page_size=page_size,
            order_by="timestamp",
            desc_order=False,  # Ticks usually sorted chronologically
            as_dataframe=False,  # 总是返回ModelList
            output_type="model",
        )

    def find_by_price_range(
        self,
        code: str,
        min_price: Optional[Number] = None,
        max_price: Optional[Number] = None,
        start_time: Optional[Any] = None,
        end_time: Optional[Any] = None,
    ):
        """
        Business helper: Find ticks by price range.
        Calls BaseCRUD.find() template method to get all decorators.
        Returns ModelList for consistent API: results.to_dataframe(), results.to_entities()

        Args:
            code: Stock code (required for dynamic Model generation)
            min_price: Minimum price filter
            max_price: Maximum price filter
            start_time: Optional start time filter
            end_time: Optional end time filter

        Returns:
            ModelList - supports to_dataframe() and to_entities()

        Raises:
            ValueError: If code is not provided or invalid

        Example:
            results = tick_crud.find_by_price_range("000001.SZ", min_price=10.0, max_price=20.0)
            df = results.to_dataframe()
            objs = results.to_entities()
        """
        # 严格校验股票代码
        if not code or not isinstance(code, str):
            raise ValueError(
                f"Invalid stock code: {code}. "
                "Stock code must be a non-empty string. "
                "Example: '000001.SZ'"
            )

        filters = {"code": code}

        if min_price is not None:
            filters["price__gte"] = to_decimal(min_price)
        if max_price is not None:
            filters["price__lte"] = to_decimal(max_price)
        if start_time:
            filters["timestamp__gte"] = datetime_normalize(start_time)
        if end_time:
            filters["timestamp__lte"] = datetime_normalize(end_time)

        return self.find(
            filters=filters,
            order_by="timestamp",
            desc_order=False,
            as_dataframe=False,  # 总是返回ModelList
        )

    def find_large_volume_ticks(
        self,
        code: str,
        min_volume: int,
        start_time: Optional[Any] = None,
        end_time: Optional[Any] = None,
        limit: Optional[int] = None,
    ):
        """
        Business helper: Find large volume ticks.
        Calls BaseCRUD.find() template method to get all decorators.
        Returns ModelList for consistent API: results.to_dataframe(), results.to_entities()

        Args:
            code: Stock code (required for dynamic Model generation)
            min_volume: Minimum volume threshold
            start_time: Optional start time filter
            end_time: Optional end time filter
            limit: Optional limit on number of results

        Returns:
            ModelList - supports to_dataframe() and to_entities()

        Raises:
            ValueError: If code is not provided or invalid

        Example:
            results = tick_crud.find_large_volume_ticks("000001.SZ", min_volume=10000)
            df = results.to_dataframe()
            objs = results.to_entities()
        """
        # 严格校验股票代码
        if not code or not isinstance(code, str):
            raise ValueError(
                f"Invalid stock code: {code}. "
                "Stock code must be a non-empty string. "
                "Example: '000001.SZ'"
            )

        filters = {"code": code, "volume__gte": min_volume}

        if start_time:
            filters["timestamp__gte"] = datetime_normalize(start_time)
        if end_time:
            filters["timestamp__lte"] = datetime_normalize(end_time)

        return self.find(
            filters=filters,
            page_size=limit,
            order_by="volume",
            desc_order=True,  # Largest volume first
            as_dataframe=False,  # 总是返回ModelList
        )

    def get_latest_ticks(self, code: str, limit: int = 100):
        """
        Business helper: Get latest ticks for the stock.
        Calls BaseCRUD.find() template method to get all decorators.
        Returns ModelList for consistent API: results.to_dataframe(), results.to_entities()

        Args:
            code: Stock code (required for dynamic Model generation)
            limit: Optional limit on number of results

        Returns:
            ModelList - supports to_dataframe() and to_entities()

        Raises:
            ValueError: If code is not provided or invalid

        Example:
            results = tick_crud.get_latest_ticks("000001.SZ", limit=100)
            df = results.to_dataframe()
            objs = results.to_entities()
        """
        # 严格校验股票代码
        if not code or not isinstance(code, str):
            raise ValueError(
                f"Invalid stock code: {code}. "
                "Stock code must be a non-empty string. "
                "Example: '000001.SZ'"
            )

        return self.find(
            filters={"code": code},
            page_size=limit,
            order_by="timestamp",
            desc_order=True,
            as_dataframe=False,  # 总是返回ModelList
        )

    def remove(self, filters: Dict[str, Any], session: Optional[Session] = None) -> None:
        """
        删除tick记录 - 必须包含code字段

        Args:
            filters: 删除条件，必须包含code字段，可包含uuid等其他字段
            session: 可选的数据库会话

        Raises:
            ValueError: 如果code字段缺失
        """
        code = filters.get("code")
        if not code:
            raise ValueError("TickCRUD.remove() requires 'code' field in filters for dynamic Model generation")

        # 获取动态Model类
        model_class = get_tick_model(code)

        # 确保表存在
        self._ensure_table_exists_for_model(model_class, code)

        # 创建临时CRUD实例
        temp_crud = self._create_temp_crud(model_class)

        # 调用BaseCRUD的remove方法
        temp_crud.remove(filters=filters, session=session)

    def delete_by_time_range(self, code: str, start_time: Optional[Any] = None, end_time: Optional[Any] = None) -> None:
        """
        Business helper: Delete ticks by time range.
        Calls BaseCRUD.remove() template method to get all decorators.

        Args:
            code: Stock code (required for dynamic Model generation)
            start_time: Start time for the range
            end_time: End time for the range

        Raises:
            ValueError: If code is not provided or invalid, or if no time range specified
        """
        # 严格校验股票代码
        if not code or not isinstance(code, str):
            raise ValueError(
                f"Invalid stock code: {code}. "
                "Stock code must be a non-empty string. "
                "Example: '000001.SZ'"
            )

        if not start_time and not end_time:
            raise ValueError(
                "Must specify at least start_time or end_time for safety. "
                "This is a destructive operation and requires explicit time range."
            )

        filters = {"code": code}
        if start_time:
            filters["timestamp__gte"] = datetime_normalize(start_time)
        if end_time:
            filters["timestamp__lte"] = datetime_normalize(end_time)

        GLOG.WARN(f"删除股票 {code} 的tick数据，时间范围: {start_time} - {end_time}")
        return self.remove(filters)

    def delete_all(self, code: str) -> None:
        """
        Business helper: Delete all tick data for specified stock - DANGEROUS OPERATION.
        Calls BaseCRUD.remove() template method to get all decorators.

        Args:
            code: Stock code (required for dynamic Model generation)

        Raises:
            ValueError: If code is not provided or invalid
        """
        # 严格校验股票代码
        if not code or not isinstance(code, str):
            raise ValueError(
                f"Invalid stock code: {code}. "
                "Stock code must be a non-empty string. "
                "Example: '000001.SZ'"
            )

        GLOG.ERROR(f"危险操作：删除股票 {code} 的所有tick数据")
        # Use a condition that matches all records
        return self.remove({"code": code})

    def count_by_direction(self, code: str, direction: TICKDIRECTION_TYPES) -> int:
        """
        Business helper: Count ticks by direction.
        Calls BaseCRUD.count() template method to get @cache_with_expiration.

        Args:
            code: Stock code (required for dynamic Model generation)
            direction: Tick direction to count

        Returns:
            Count of ticks with specified direction

        Raises:
            ValueError: If code is not provided or invalid
        """
        # 严格校验股票代码
        if not code or not isinstance(code, str):
            raise ValueError(
                f"Invalid stock code: {code}. "
                "Stock code must be a non-empty string. "
                "Example: '000001.SZ'"
            )

        return self.count({"code": code, "direction": direction})

    def count_by_time_range(self, code: str, start_time: Optional[Any] = None, end_time: Optional[Any] = None) -> int:
        """
        Business helper: Count ticks in time range.
        Calls BaseCRUD.count() template method to get @cache_with_expiration.

        Args:
            code: Stock code (required for dynamic Model generation)
            start_time: Optional start time filter
            end_time: Optional end time filter

        Returns:
            Count of ticks in specified time range

        Raises:
            ValueError: If code is not provided or invalid
        """
        # 严格校验股票代码
        if not code or not isinstance(code, str):
            raise ValueError(
                f"Invalid stock code: {code}. "
                "Stock code must be a non-empty string. "
                "Example: '000001.SZ'"
            )

        filters = {"code": code}
        if start_time:
            filters["timestamp__gte"] = datetime_normalize(start_time)
        if end_time:
            filters["timestamp__lte"] = datetime_normalize(end_time)

        return self.count(filters)

    def get_trading_summary(self, code: str, start_time: Optional[Any] = None, end_time: Optional[Any] = None) -> dict:
        """
        Business helper: Get trading summary statistics.

        Args:
            code: Stock code (required for dynamic Model generation)
            start_time: Optional start time filter
            end_time: Optional end time filter

        Returns:
            Dictionary with trading summary statistics

        Raises:
            ValueError: If code is not provided or invalid
        """
        # 严格校验股票代码
        if not code or not isinstance(code, str):
            raise ValueError(
                f"Invalid stock code: {code}. "
                "Stock code must be a non-empty string. "
                "Example: '000001.SZ'"
            )

        filters = {"code": code}
        if start_time:
            filters["timestamp__gte"] = datetime_normalize(start_time)
        if end_time:
            filters["timestamp__lte"] = datetime_normalize(end_time)

        ticks = self.find(filters=filters, as_dataframe=False)

        if not ticks:
            return {
                "total_count": 0,
                "total_volume": 0,
                "avg_price": 0,
                "min_price": 0,
                "max_price": 0,
                "price_range": 0,
            }

        prices = [float(tick.price) for tick in ticks if tick.price]
        volumes = [tick.volume for tick in ticks if tick.volume]

        return {
            "total_count": len(ticks),
            "total_volume": sum(volumes) if volumes else 0,
            "avg_price": sum(prices) / len(prices) if prices else 0,
            "min_price": min(prices) if prices else 0,
            "max_price": max(prices) if prices else 0,
            "price_range": max(prices) - min(prices) if prices else 0,
        }

    def drop_dynamic_table(self, code: str) -> bool:
        """
        删除指定股票代码的动态Tick表

        Args:
            code: 股票代码 (e.g., "000001.SZ")

        Returns:
            bool: 删除是否成功

        Raises:
            ValueError: 如果股票代码无效
        """
        if not code or not isinstance(code, str):
            raise ValueError(f"Invalid stock code: {code}")

        try:
            # 获取动态模型类
            model_class = get_tick_model(code)

            # 删除表
            drop_table(model_class)
            GLOG.INFO(f"Successfully dropped tick table for {code}: {model_class.__tablename__}")

            # 从注册表中移除模型类
            table_name = f"{code.replace('.', '_')}_Tick"
            if table_name in tick_model_registry:
                del tick_model_registry[table_name]
                GLOG.DEBUG(f"Removed model {table_name} from registry")

            return True

        except Exception as e:
            GLOG.ERROR(f"Failed to drop tick table for {code}: {e}")
            return False

    def drop_all_test_tables(self) -> int:
        """
        删除所有测试相关的Tick表（表名包含TEST前缀的表）

        Returns:
            int: 成功删除的表数量
        """
        import re
        test_pattern = re.compile(r'^TEST.*_Tick$')
        tables_to_remove = []

        # 找出所有测试表
        for table_name in list(tick_model_registry.keys()):
            if test_pattern.match(table_name):
                tables_to_remove.append(table_name)

        deleted_count = 0
        for table_name in tables_to_remove:
            try:
                model_class = tick_model_registry[table_name]
                drop_table(model_class)
                GLOG.INFO(f"Successfully dropped test table: {table_name}")
                del tick_model_registry[table_name]
                deleted_count += 1
            except Exception as e:
                GLOG.ERROR(f"Failed to drop test table {table_name}: {e}")

        if deleted_count > 0:
            GLOG.INFO(f"Successfully dropped {deleted_count} test tick tables")
        else:
            GLOG.DEBUG("No test tick tables to drop")

        return deleted_count
