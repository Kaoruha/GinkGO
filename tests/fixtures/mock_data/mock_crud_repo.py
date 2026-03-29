"""
Mock CRUD Repository for Testing

提供不依赖真实数据库的Mock CRUD实现，用于隔离测试。
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional

from ginkgo.data.models.model_bar import MBar
from ginkgo.enums import FREQUENCY_TYPES


class MockBarCRUD:
    """
    Mock BarCRUD实现

    不连接真实数据库，返回预定义的测试数据。
    用于DataService和BacktestFeeder的单元测试。
    """

    def __init__(self):
        """初始化Mock数据存储"""
        self._data: List[MBar] = []
        self._setup_default_data()

    def _setup_default_data(self):
        """设置默认测试数据"""
        # 创建2天的测试Bar数据
        self._data = [
            MBar(
                code="000001.SZ",
                timestamp=datetime(2023, 1, 3, 9, 30),
                open=Decimal('10.0'),
                high=Decimal('10.5'),
                low=Decimal('9.8'),
                close=Decimal('10.2'),
                volume=1000000,
                amount=Decimal('10200000.0'),
                frequency=FREQUENCY_TYPES.DAY
            ),
            MBar(
                code="000001.SZ",
                timestamp=datetime(2023, 1, 4, 9, 30),
                open=Decimal('10.2'),
                high=Decimal('10.8'),
                low=Decimal('10.0'),
                close=Decimal('10.6'),
                volume=1200000,
                amount=Decimal('12720000.0'),
                frequency=FREQUENCY_TYPES.DAY
            ),
            MBar(
                code="000002.SZ",
                timestamp=datetime(2023, 1, 3, 9, 30),
                open=Decimal('20.0'),
                high=Decimal('20.5'),
                low=Decimal('19.8'),
                close=Decimal('20.2'),
                volume=800000,
                amount=Decimal('16160000.0'),
                frequency=FREQUENCY_TYPES.DAY
            ),
        ]

    def find(
        self,
        filters: Optional[Dict[str, Any]] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        order_by: Optional[str] = None,
        desc_order: bool = False,
        as_dataframe: bool = False,
        **kwargs
    ):
        """
        Mock find方法 - 从内存中过滤数据

        Args:
            filters: 过滤条件字典
            as_dataframe: 是否返回DataFrame格式
            其他参数：为了接口兼容

        Returns:
            List[MBar] 或 DataFrame: 过滤后的Bar数据
        """
        if filters is None:
            result = self._data.copy()
        else:
            result = self._data.copy()

            # 处理code过滤
            if "code" in filters:
                code = filters["code"]
                result = [bar for bar in result if bar.code == code]

            # 处理timestamp范围过滤（包含边界）
            if "timestamp__gte" in filters:
                gte_time = filters["timestamp__gte"]
                # 统一转换为datetime进行比较
                gte_time = self._normalize_datetime(gte_time, start_of_day=True)
                result = [bar for bar in result if bar.timestamp >= gte_time]

            if "timestamp__lte" in filters:
                lte_time = filters["timestamp__lte"]
                # 统一转换为datetime进行比较
                lte_time = self._normalize_datetime(lte_time, start_of_day=False)
                result = [bar for bar in result if bar.timestamp <= lte_time]

            # 处理frequency过滤
            if "frequency" in filters:
                freq = filters["frequency"]
                # 支持枚举对象
                freq_value = freq.value if hasattr(freq, 'value') else freq
                result = [bar for bar in result if bar.frequency == freq_value]

            # 处理volume范围过滤
            if "volume__gte" in filters:
                volume_gte = filters["volume__gte"]
                result = [bar for bar in result if bar.volume >= volume_gte]

            if "volume__lte" in filters:
                volume_lte = filters["volume__lte"]
                result = [bar for bar in result if bar.volume <= volume_lte]

        # 应用排序
        if order_by and result:
            reverse = desc_order
            if hasattr(result[0], order_by):
                result = sorted(result, key=lambda x: getattr(x, order_by), reverse=reverse)

        # 应用分页
        if page is not None and page_size is not None:
            start = page * page_size
            end = start + page_size
            result = result[start:end]

        # 转换为DataFrame（如果需要）
        if as_dataframe:
            import pandas as pd
            if not result:
                return pd.DataFrame()

            # 转换为字典列表
            data = []
            for bar in result:
                data.append({
                    'code': bar.code,
                    'timestamp': bar.timestamp,
                    'open': float(bar.open) if bar.open else None,
                    'high': float(bar.high) if bar.high else None,
                    'low': float(bar.low) if bar.low else None,
                    'close': float(bar.close) if bar.close else None,
                    'volume': bar.volume,
                    'frequency': bar.frequency,
                })
            return pd.DataFrame(data)

        return result

    def add(self, item: MBar, session=None) -> MBar:
        """Mock单条插入 - 添加到内存"""
        self._data.append(item)
        return item

    def add_batch(self, models: List[MBar], session=None) -> None:
        """Mock批量插入 - 添加到内存"""
        self._data.extend(models)

    def count(self, filters: Optional[Dict[str, Any]] = None, session=None) -> int:
        """Mock计数 - 返回过滤后的数据数量"""
        # 复用find逻辑，但只返回计数
        result = self.find(filters=filters, as_dataframe=False)
        return len(result)

    def exists(self, filters: Optional[Dict[str, Any]] = None, session=None) -> bool:
        """Mock存在性检查"""
        return self.count(filters=filters) > 0

    def remove(self, filters: Dict[str, Any], session=None) -> None:
        """Mock删除 - 从内存中移除"""
        if "code" in filters:
            code = filters["code"]
            self._data = [bar for bar in self._data if bar.code != code]

    def add_test_data(self, bars: List[MBar]):
        """添加自定义测试数据"""
        self._data.extend(bars)

    def clear(self):
        """清空所有数据"""
        self._data = []

    def reset(self):
        """重置为默认数据"""
        self._data = []
        self._setup_default_data()

    def _normalize_datetime(self, value, start_of_day=True):
        """统一date和datetime类型为datetime对象

        Args:
            value: date或datetime对象
            start_of_day: True返回当天开始时间(00:00:00)，False返回结束时间(23:59:59)

        Returns:
            datetime对象
        """
        from datetime import datetime as dt_class, date, time as time_class

        # 如果已经是datetime
        if isinstance(value, dt_class):
            # 如果是00:00:00且需要结束时间，扩展到23:59:59
            if not start_of_day and value.time() == time_class(0, 0):
                return value.replace(hour=23, minute=59, second=59)
            return value

        # 如果是date，转换为datetime
        if isinstance(value, date):
            if start_of_day:
                return dt_class.combine(value, time_class(0, 0, 0))
            else:
                return dt_class.combine(value, time_class(23, 59, 59))

        # 其他类型直接返回
        return value
