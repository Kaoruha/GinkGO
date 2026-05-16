# Upstream: 数据服务层(BaseService), API层, 回测引擎
# Downstream: BaseCRUD, ClickHouse/MySQL/MongoDB/Redis数据库模型
# Role: CRUD包入口，统一导出全部CRUD类(BarCRUD、OrderCRUD、PortfolioCRUD等40+个)，供服务层和容器注册使用

# See #2715: PEP 562 懒加载（models/ 包除外，见该目录注释）
_LAZY_IMPORTS = {
    "AdjustfactorCRUD": ("ginkgo.data.crud.adjustfactor_crud", "AdjustfactorCRUD"),
    "AnalyzerRecordCRUD": ("ginkgo.data.crud.analyzer_record_crud", "AnalyzerRecordCRUD"),
    "BacktestTaskCRUD": ("ginkgo.data.crud.backtest_task_crud", "BacktestTaskCRUD"),
    "BarCRUD": ("ginkgo.data.crud.bar_crud", "BarCRUD"),
    "BaseCRUD": ("ginkgo.data.crud.base_crud", "BaseCRUD"),
    "BaseMongoCRUD": ("ginkgo.data.crud.base_mongo_crud", "BaseMongoCRUD"),
    "CapitalAdjustmentCRUD": ("ginkgo.data.crud.capital_adjustment_crud", "CapitalAdjustmentCRUD"),
    "EngineCRUD": ("ginkgo.data.crud.engine_crud", "EngineCRUD"),
    "EngineHandlerMappingCRUD": ("ginkgo.data.crud.engine_handler_mapping_crud", "EngineHandlerMappingCRUD"),
    "EnginePortfolioMappingCRUD": ("ginkgo.data.crud.engine_portfolio_mapping_crud", "EnginePortfolioMappingCRUD"),
    "FactorCRUD": ("ginkgo.data.crud.factor_crud", "FactorCRUD"),
    "FileCRUD": ("ginkgo.data.crud.file_crud", "FileCRUD"),
    "HandlerCRUD": ("ginkgo.data.crud.handler_crud", "HandlerCRUD"),
    "KafkaCRUD": ("ginkgo.data.crud.kafka_crud", "KafkaCRUD"),
    "OrderCRUD": ("ginkgo.data.crud.order_crud", "OrderCRUD"),
    "OrderRecordCRUD": ("ginkgo.data.crud.order_record_crud", "OrderRecordCRUD"),
    "ParamCRUD": ("ginkgo.data.crud.param_crud", "ParamCRUD"),
    "PortfolioCRUD": ("ginkgo.data.crud.portfolio_crud", "PortfolioCRUD"),
    "PortfolioFileMappingCRUD": ("ginkgo.data.crud.portfolio_file_mapping_crud", "PortfolioFileMappingCRUD"),
    "PositionCRUD": ("ginkgo.data.crud.position_crud", "PositionCRUD"),
    "PositionRecordCRUD": ("ginkgo.data.crud.position_record_crud", "PositionRecordCRUD"),
    "RedisCRUD": ("ginkgo.data.crud.redis_crud", "RedisCRUD"),
    "SignalCRUD": ("ginkgo.data.crud.signal_crud", "SignalCRUD"),
    "SignalTrackerCRUD": ("ginkgo.data.crud.signal_tracker_crud", "SignalTrackerCRUD"),
    "StockInfoCRUD": ("ginkgo.data.crud.stock_info_crud", "StockInfoCRUD"),
    "TickCRUD": ("ginkgo.data.crud.tick_crud", "TickCRUD"),
    "TickSummaryCRUD": ("ginkgo.data.crud.tick_summary_crud", "TickSummaryCRUD"),
    "TradeDayCRUD": ("ginkgo.data.crud.trade_day_crud", "TradeDayCRUD"),
    "TransferCRUD": ("ginkgo.data.crud.transfer_crud", "TransferCRUD"),
    "TransferRecordCRUD": ("ginkgo.data.crud.transfer_record_crud", "TransferRecordCRUD"),
    "UserCRUD": ("ginkgo.data.crud.user_crud", "UserCRUD"),
    "UserContactCRUD": ("ginkgo.data.crud.user_contact_crud", "UserContactCRUD"),
    "DeploymentCRUD": ("ginkgo.data.crud.deployment_crud", "DeploymentCRUD"),
    "UserCredentialCRUD": ("ginkgo.data.crud.user_credential_crud", "UserCredentialCRUD"),
    "UserGroupCRUD": ("ginkgo.data.crud.user_group_crud", "UserGroupCRUD"),
    "UserGroupMappingCRUD": ("ginkgo.data.crud.user_group_mapping_crud", "UserGroupMappingCRUD"),
    "LiveAccountCRUD": ("ginkgo.data.crud.live_account_crud", "LiveAccountCRUD"),
    "BrokerInstanceCRUD": ("ginkgo.data.crud.broker_instance_crud", "BrokerInstanceCRUD"),
    "TradeRecordCRUD": ("ginkgo.data.crud.trade_record_crud", "TradeRecordCRUD"),
    "NotificationTemplateCRUD": ("ginkgo.data.crud.notification_template_crud", "NotificationTemplateCRUD"),
    "NotificationRecordCRUD": ("ginkgo.data.crud.notification_record_crud", "NotificationRecordCRUD"),
    "NotificationRecipientCRUD": ("ginkgo.data.crud.notification_recipient_crud", "NotificationRecipientCRUD"),
    "MarketSubscriptionCRUD": ("ginkgo.data.crud.market_subscription_crud", "MarketSubscriptionCRUD"),
    "ApiKeyCRUD": ("ginkgo.data.crud.api_key_crud", "ApiKeyCRUD"),
    "ValidationError": ("ginkgo.data.crud.validation", "ValidationError"),
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
    "AdjustfactorCRUD",
    "AnalyzerRecordCRUD",
    "BacktestTaskCRUD",
    "BarCRUD",
    "BaseCRUD",
    "BaseMongoCRUD",
    "CapitalAdjustmentCRUD",
    "EngineCRUD",
    "EngineHandlerMappingCRUD",
    "EnginePortfolioMappingCRUD",
    "FactorCRUD",
    "FileCRUD",
    "HandlerCRUD",
    "KafkaCRUD",
    "OrderCRUD",
    "OrderRecordCRUD",
    "ParamCRUD",
    "PortfolioCRUD",
    "PortfolioFileMappingCRUD",
    "PositionCRUD",
    "PositionRecordCRUD",
    "RedisCRUD",
    "SignalCRUD",
    "SignalTrackerCRUD",
    "StockInfoCRUD",
    "TickCRUD",
    "TickSummaryCRUD",
    "TradeDayCRUD",
    "TransferCRUD",
    "TransferRecordCRUD",
    "UserCRUD",
    "UserContactCRUD",
    "DeploymentCRUD",
    "UserCredentialCRUD",
    "UserGroupCRUD",
    "UserGroupMappingCRUD",
    "LiveAccountCRUD",
    "BrokerInstanceCRUD",
    "TradeRecordCRUD",
    "NotificationTemplateCRUD",
    "NotificationRecordCRUD",
    "NotificationRecipientCRUD",
    "MarketSubscriptionCRUD",
    "ApiKeyCRUD",
    "ValidationError",
]
