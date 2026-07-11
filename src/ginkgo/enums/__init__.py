"""ginkgo.enums — 全项目枚举中心。

#3838: 原 ``ginkgo/enums.py``（917 行 / 52 枚举 + EnumBase 基类）按领域拆分为 10 个子模块。
向后兼容契约：``from ginkgo.enums import XXX`` 全部保留（子模块符号在此 re-export）。
新代码推荐领域路径：``from ginkgo.enums.trading import DIRECTION_TYPES``。

子模块（按事件链路与既有分节注释划分）：
    base       EnumBase 基类（转换方法）
    trading    交易订单（方向/订单/状态/资金/币种）
    data       数据源（价格/源/频率/市场/复权）
    event      事件链路
    strategy   策略（态度/类型/模型/分析器集合）
    execution  引擎与执行（架构/模式/账户/状态）
    portfolio  Portfolio 运行时（Phase 5 优雅重启）
    system     系统通用（文件/组件/日志/环境/权限/部署）
    account    实盘账户（交易所/状态/订阅/Broker 状态机，#3880）
    user       用户与通知（US2）
"""
from .base import *
from .trading import *
from .data import *
from .event import *
from .strategy import *
from .execution import *
from .portfolio import *
from .system import *
from .account import *
from .user import *

__all__ = (
    "EnumBase",
    "CURRENCY_TYPES",
    "DIRECTION_TYPES",
    "TRANSFERDIRECTION_TYPES",
    "ORDER_TYPES",
    "ORDERSTATUS_TYPES",
    "TRANSFERSTATUS_TYPES",
    "CAPITALADJUSTMENT_TYPES",
    "TRACKINGSTATUS_TYPES",
    "TICKDIRECTION_TYPES",
    "PRICEINFO_TYPES",
    "SOURCE_TYPES",
    "FREQUENCY_TYPES",
    "MARKET_TYPES",
    "ADJUSTMENT_TYPES",
    "EVENT_TYPES",
    "ATTITUDE_TYPES",
    "STRATEGY_TYPES",
    "MODEL_TYPES",
    "DEFAULT_ANALYZER_SET",
    "LIVE_MODE",
    "ENGINESTATUS_TYPES",
    "ENGINE_TYPES",
    "ENGINE_ARCHITECTURE",
    "EXECUTION_MODE",
    "EXECUTION_STATUS",
    "ACCOUNT_TYPE",
    "PORTFOLIO_MODE_TYPES",
    "PORTFOLIO_RUNSTATE_TYPES",
    "WORKER_STATUS_TYPES",
    "FILE_TYPES",
    "RECORDSTAGE_TYPES",
    "GRAPHY_TYPES",
    "PARAMETER_TYPES",
    "COMPONENT_TYPES",
    "ENTITY_TYPES",
    "TIME_MODE",
    "LEVEL_TYPES",
    "LOG_CATEGORY_TYPES",
    "EnvironmentType",
    "PermissionType",
    "DEPLOYMENT_STATUS",
    "VALIDATION_STATUS",
    "ExchangeType",
    "AccountStatusType",
    "SubscriptionDataType",
    "BrokerStateType",
    "USER_TYPES",
    "CONTACT_TYPES",
    "CONTACT_METHOD_STATUS_TYPES",
    "NOTIFICATION_STATUS_TYPES",
    "RECIPIENT_TYPES",
    "TEMPLATE_TYPES",
)
