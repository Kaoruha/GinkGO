# Upstream: Signal实体(业务信号继承提供时间戳管理)
# Downstream: TimeMixin(继承提供时间戳管理timestamp/business_timestamp)、Base(继承提供组件基础能力uuid/component_type/to_dataframe)
# Role: SignalBase信号组件基类，组合TimeMixin和Base提供时间戳管理和组件基础功能，为所有信号组件提供统一接口






"""
信号组件基类

组合时间管理能力，为所有信号组件提供基础功能
"""

from ginkgo.trading.core.base import Base
from ginkgo.trading.mixins.time_mixin import TimeMixin


class SignalBase(TimeMixin, Base):
    """
    信号组件基类

    组合时间管理能力，为所有信号组件提供基础功能：
    - 时间戳管理 (timestamp, business_timestamp)
    - 时间更新API (set_business_timestamp)
    - 组件基础功能 (uuid, component_type, dataframe转换)
    """

    def __init__(self, **kwargs):
        """
        初始化信号基类

        Args:
            **kwargs: 传递给父类的参数
        """
        # 显式初始化各个Mixin，确保正确的初始化顺序
        TimeMixin.__init__(self, **kwargs)
        Base.__init__(self)