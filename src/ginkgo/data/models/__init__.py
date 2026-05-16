# Upstream: CRUD层, 服务层, 数据层容器(containers.py), 回测引擎
# Downstream: 全部ORM模型类(MBar/MTick/MOrder/MPosition等)
# Role: 数据模型包入口，统一导出所有ClickHouse/MySQL/MongoDB ORM模型类

# See #2715: PEP 562 懒加载
_LAZY_IMPORTS = {
    "MAdjustfactor": ("ginkgo.data.models.model_adjustfactor", "MAdjustfactor"),
    "MAnalyzerRecord": ("ginkgo.data.models.model_analyzer_record", "MAnalyzerRecord"),
    "MBacktestRecordBase": ("ginkgo.data.models.model_backtest_record_base", "MBacktestRecordBase"),
    "MBacktestTask": ("ginkgo.data.models.model_backtest_task", "MBacktestTask"),
    "MBar": ("ginkgo.data.models.model_bar", "MBar"),
    "MCapitalAdjustment": ("ginkgo.data.models.model_capital_adjustment", "MCapitalAdjustment"),
    "MClickBase": ("ginkgo.data.models.model_clickbase", "MClickBase"),
    "MEngine": ("ginkgo.data.models.model_engine", "MEngine"),
    "MEngineHandlerMapping": ("ginkgo.data.models.model_engine_handler_mapping", "MEngineHandlerMapping"),
    "MEnginePortfolioMapping": ("ginkgo.data.models.model_engine_portfolio_mapping", "MEnginePortfolioMapping"),
    "MFactor": ("ginkgo.data.models.model_factor", "MFactor"),
    "MFile": ("ginkgo.data.models.model_file", "MFile"),
    "MHandler": ("ginkgo.data.models.model_handler", "MHandler"),
    "MParam": ("ginkgo.data.models.model_param", "MParam"),
    "MMysqlBase": ("ginkgo.data.models.model_mysqlbase", "MMysqlBase"),
    "MMongoBase": ("ginkgo.data.models.model_mongobase", "MMongoBase"),
    "MOrder": ("ginkgo.data.models.model_order", "MOrder"),
    "MOrderRecord": ("ginkgo.data.models.model_order_record", "MOrderRecord"),
    "MPortfolio": ("ginkgo.data.models.model_portfolio", "MPortfolio"),
    "MPortfolioFileMapping": ("ginkgo.data.models.model_portfolio_file_mapping", "MPortfolioFileMapping"),
    "MPosition": ("ginkgo.data.models.model_position", "MPosition"),
    "MPositionRecord": ("ginkgo.data.models.model_position_record", "MPositionRecord"),
    "MSignal": ("ginkgo.data.models.model_signal", "MSignal"),
    "MStockInfo": ("ginkgo.data.models.model_stock_info", "MStockInfo"),
    "MLiveAccount": ("ginkgo.data.models.model_live_account", "MLiveAccount"),
    "MBrokerInstance": ("ginkgo.data.models.model_broker_instance", "MBrokerInstance"),
    "MTradeRecord": ("ginkgo.data.models.model_trade_record", "MTradeRecord"),
    "MTick": ("ginkgo.data.models.model_tick", "MTick"),
    "MTickSummary": ("ginkgo.data.models.model_tick_summary", "MTickSummary"),
    "MTradeDay": ("ginkgo.data.models.model_trade_day", "MTradeDay"),
    "MTransfer": ("ginkgo.data.models.model_transfer", "MTransfer"),
    "MTransferRecord": ("ginkgo.data.models.model_transfer_record", "MTransferRecord"),
    "MRunRecord": ("ginkgo.data.models.model_run_record", "MRunRecord"),
    "MUser": ("ginkgo.data.models.model_user", "MUser"),
    "MUserContact": ("ginkgo.data.models.model_user_contact", "MUserContact"),
    "MDeployment": ("ginkgo.data.models.model_deployment", "MDeployment"),
    "MUserCredential": ("ginkgo.data.models.model_user_credential", "MUserCredential"),
    "MUserGroup": ("ginkgo.data.models.model_user_group", "MUserGroup"),
    "MUserGroupMapping": ("ginkgo.data.models.model_user_group_mapping", "MUserGroupMapping"),
    "MNotificationTemplate": ("ginkgo.data.models.model_notification_template", "MNotificationTemplate"),
    "MNotificationRecord": ("ginkgo.data.models.model_notification_record", "MNotificationRecord"),
    "MNotificationRecipient": ("ginkgo.data.models.model_notification_recipient", "MNotificationRecipient"),
    "MBacktestLog": ("ginkgo.data.models.model_logs", "MBacktestLog"),
    "MComponentLog": ("ginkgo.data.models.model_logs", "MComponentLog"),
    "MPerformanceLog": ("ginkgo.data.models.model_logs", "MPerformanceLog"),
    "MValidationResult": ("ginkgo.data.models.model_validation_result", "MValidationResult"),
}


def __getattr__(name):
    if name in _LAZY_IMPORTS:
        import importlib

        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        return getattr(module, attr_name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(_LAZY_IMPORTS.keys() | set(globals().keys()))


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
    # 日志系统模型 (011-distributed-logging)
    "MBacktestLog",
    "MComponentLog",
    "MPerformanceLog",
    # 验证系统模型
    "MValidationResult",
]
