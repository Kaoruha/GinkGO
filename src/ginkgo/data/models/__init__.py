# Upstream: CRUD层, 服务层, 数据层容器(containers.py), 回测引擎
# Downstream: 全部ORM模型类(MBar/MTick/MOrder/MPosition等)
# Role: 数据模型包入口，统一导出所有ClickHouse/MySQL/MongoDB ORM模型类

# 注意：这里使用 eager import 而非框架其他地方采用的懒加载（PEP 562）。
# 原因：SQLAlchemy 的 relationship() 使用字符串引用目标类（如 "MUserCredential"），
# 在 mapper 配置阶段需要所有引用的类已在同一个 registry 中。
# 懒加载会导致只加载单个模型时，其 relationship 目标类不在 registry 中，
# 从而抛出 InvalidRequestError。
# ORM 模型类只是声明式定义，import 时不连接数据库，开销可忽略。

from ginkgo.data.models.model_adjustfactor import MAdjustfactor
from ginkgo.data.models.model_analyzer_record import MAnalyzerRecord
from ginkgo.data.models.model_backtest_record_base import MBacktestRecordBase
from ginkgo.data.models.model_backtest_task import MBacktestTask
from ginkgo.data.models.model_bar import MBar
from ginkgo.data.models.model_capital_adjustment import MCapitalAdjustment
from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.data.models.model_engine import MEngine
from ginkgo.data.models.model_engine_handler_mapping import MEngineHandlerMapping
from ginkgo.data.models.model_engine_portfolio_mapping import MEnginePortfolioMapping
from ginkgo.data.models.model_factor import MFactor
from ginkgo.data.models.model_file import MFile
from ginkgo.data.models.model_handler import MHandler
from ginkgo.data.models.model_param import MParam
from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.data.models.model_mongobase import MMongoBase
from ginkgo.data.models.model_order import MOrder
from ginkgo.data.models.model_order_record import MOrderRecord
from ginkgo.data.models.model_portfolio import MPortfolio
from ginkgo.data.models.model_portfolio_file_mapping import MPortfolioFileMapping
from ginkgo.data.models.model_position import MPosition
from ginkgo.data.models.model_position_record import MPositionRecord
from ginkgo.data.models.model_signal import MSignal
from ginkgo.data.models.model_stock_info import MStockInfo
from ginkgo.data.models.model_live_account import MLiveAccount
from ginkgo.data.models.model_broker_instance import MBrokerInstance
from ginkgo.data.models.model_trade_record import MTradeRecord
from ginkgo.data.models.model_tick import MTick
from ginkgo.data.models.model_tick_summary import MTickSummary
from ginkgo.data.models.model_trade_day import MTradeDay
from ginkgo.data.models.model_transfer import MTransfer
from ginkgo.data.models.model_transfer_record import MTransferRecord
from ginkgo.data.models.model_run_record import MRunRecord
from ginkgo.data.models.model_user import MUser
from ginkgo.data.models.model_user_contact import MUserContact
from ginkgo.data.models.model_deployment import MDeployment
from ginkgo.data.models.model_user_credential import MUserCredential
from ginkgo.data.models.model_user_group import MUserGroup
from ginkgo.data.models.model_user_group_mapping import MUserGroupMapping
from ginkgo.data.models.model_notification_template import MNotificationTemplate
from ginkgo.data.models.model_notification_record import MNotificationRecord
from ginkgo.data.models.model_notification_recipient import MNotificationRecipient
from ginkgo.data.models.model_logs import MBacktestLog, MComponentLog, MPerformanceLog
from ginkgo.data.models.model_validation_result import MValidationResult

__all__ = [
    "MAdjustfactor",
    "MAnalyzerRecord",
    "MBacktestRecordBase",
    "MBacktestTask",
    "MBar",
    "MCapitalAdjustment",
    "MClickBase",
    "MEngine",
    "MEngineHandlerMapping",
    "MEnginePortfolioMapping",
    "MFactor",
    "MFile",
    "MHandler",
    "MLiveAccount",
    "MBrokerInstance",
    "MParam",
    "MMysqlBase",
    "MMongoBase",
    "MOrder",
    "MOrderRecord",
    "MPortfolio",
    "MPortfolioFileMapping",
    "MPosition",
    "MPositionRecord",
    "MSignal",
    "MStockInfo",
    "MTradeRecord",
    "MTick",
    "MTickSummary",
    "MTradeDay",
    "MTransfer",
    "MTransferRecord",
    "MRunRecord",
    "MUser",
    "MUserContact",
    "MDeployment",
    "MUserCredential",
    "MUserGroup",
    "MUserGroupMapping",
    "MNotificationTemplate",
    "MNotificationRecord",
    "MNotificationRecipient",
    "MBacktestLog",
    "MComponentLog",
    "MPerformanceLog",
    "MValidationResult",
]
