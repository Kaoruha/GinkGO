"""#3838: enums.py 拆分为领域包的契约测试（characterization）。

拆分 ginkgo/enums.py（917 行 / 53 个类）为 ginkgo/enums/ 领域包后，
所有枚举必须仍可从 ``ginkgo.enums`` 顶层 import（re-export 向后兼容），
且值 / 成员 / classmethod 零变更。本测试是拆分的安全网：拆分前先绿，
拆分全程保持绿，即证明行为不变。

域内既有测试覆盖零散（转换 / 别名 / 迁移），无一验证"全部枚举可导入"，
而 re-export 最易漏；本测试补此缺口。
"""
import ginkgo.enums as enums

# 全部类名（含 EnumBase 基类 + 52 枚举/常量类），拆分前后必须一致可导入。
ENUM_NAMES = [
    "EnumBase",
    # 交易
    "CURRENCY_TYPES", "TICKDIRECTION_TYPES",
    "DIRECTION_TYPES", "TRANSFERDIRECTION_TYPES", "ORDER_TYPES",
    "ORDERSTATUS_TYPES", "TRANSFERSTATUS_TYPES", "TRACKINGSTATUS_TYPES",
    "CAPITALADJUSTMENT_TYPES",
    # 数据
    "PRICEINFO_TYPES", "SOURCE_TYPES", "FREQUENCY_TYPES", "MARKET_TYPES",
    "ADJUSTMENT_TYPES",
    # 事件
    "EVENT_TYPES",
    # 策略
    "ATTITUDE_TYPES", "STRATEGY_TYPES", "MODEL_TYPES", "DEFAULT_ANALYZER_SET",
    # 系统
    "FILE_TYPES", "RECORDSTAGE_TYPES", "GRAPHY_TYPES", "PARAMETER_TYPES",
    "ENGINESTATUS_TYPES", "ENGINE_TYPES", "ENGINE_ARCHITECTURE",
    "EXECUTION_STATUS", "COMPONENT_TYPES", "ENTITY_TYPES", "TIME_MODE",
    "USER_TYPES", "PORTFOLIO_MODE_TYPES", "PORTFOLIO_RUNSTATE_TYPES",
    "WORKER_STATUS_TYPES", "LEVEL_TYPES", "LOG_CATEGORY_TYPES",
    "EnvironmentType", "PermissionType", "DEPLOYMENT_STATUS", "VALIDATION_STATUS",
    # 执行模式
    "LIVE_MODE", "EXECUTION_MODE", "ACCOUNT_TYPE",
    # 实盘账户 (#3880)
    "ExchangeType", "AccountStatusType", "SubscriptionDataType", "BrokerStateType",
    # 通知 (US2)
    "CONTACT_TYPES", "CONTACT_METHOD_STATUS_TYPES", "NOTIFICATION_STATUS_TYPES",
    "RECIPIENT_TYPES", "TEMPLATE_TYPES",
]


def test_all_enums_importable_from_top_level():
    """所有类可从 ginkgo.enums 顶层 import（re-export 向后兼容契约）。"""
    missing = [n for n in ENUM_NAMES if not hasattr(enums, n)]
    assert missing == [], f"以下类从 ginkgo.enums 顶层丢失: {missing}"


def test_enumbase_methods_preserved():
    """EnumBase 的 5 个转换方法保留（所有枚举依赖）。"""
    for method in ("enum_convert", "from_int", "to_int", "validate_input"):
        assert hasattr(enums.EnumBase, method), f"EnumBase 缺方法 {method}"


def test_key_enum_values_unchanged():
    """关键枚举代表值不变（抽样跨领域，防值漂移）。"""
    assert enums.DIRECTION_TYPES.LONG.value == 1
    assert enums.DIRECTION_TYPES.VOID.value == -1
    assert enums.EXECUTION_MODE.BACKTEST.value == 0
    assert enums.EXECUTION_MODE.LIVE.value == 1
    assert enums.ENGINE_TYPES.EVENT_DRIVEN.value == 1
    assert enums.ACCOUNT_TYPE.PAPER.value == 1
    assert enums.LEVEL_TYPES.INFO.value == 1
    assert enums.PORTFOLIO_RUNSTATE_TYPES.RUNNING.value == 1
    assert enums.WORKER_STATUS_TYPES.RUNNING.value == 2


def test_cancelled_aliases_preserved():
    """双 L 别名保留（#6061，6 枚举）。"""
    assert enums.ORDERSTATUS_TYPES.CANCELLED is enums.ORDERSTATUS_TYPES.CANCELED
    assert enums.TRANSFERSTATUS_TYPES.CANCELLED is enums.TRANSFERSTATUS_TYPES.CANCELED
    assert enums.RECORDSTAGE_TYPES.ORDERCANCELLED is enums.RECORDSTAGE_TYPES.ORDERCANCELED
    assert enums.ENGINE_TYPES.CANCELLED is enums.ENGINE_TYPES.CANCELED
    assert enums.EXECUTION_STATUS.CANCELLED is enums.EXECUTION_STATUS.CANCELED
    assert enums.TRACKINGSTATUS_TYPES.CANCELLED is enums.TRACKINGSTATUS_TYPES.CANCELED


def test_rich_classmethods_preserved():
    """带状态机/分类逻辑的 classmethod 仍可调（re-export 不能只搬常量）。"""
    EM = enums.EXECUTION_MODE
    assert EM.is_manual_mode(EM.PAPER_MANUAL) is True
    assert EM.is_auto_mode(EM.LIVE_AUTO) is True
    assert EM.is_paper_mode(EM.PAPER_AUTO) is True
    assert EM.is_live_mode(EM.LIVE_MANUAL) is True
    assert EM.get_account_type(EM.BACKTEST) == "backtest"

    BS = enums.BrokerStateType
    assert BS.is_terminal(BS.STOPPED) is True
    assert BS.is_active(BS.RUNNING) is True
    assert BS.can_transition(BS.UNINITIALIZED, BS.INITIALIZING) is True
    assert BS.can_transition(BS.RUNNING, BS.UNINITIALIZED) is False

    assert enums.ExchangeType.from_str("okx") == enums.ExchangeType.OKX
    assert enums.SubscriptionDataType.validate("ticker") is True
    assert enums.PermissionType.all_permissions() == ["read", "trade", "admin"]


def test_str_enums_identity_preserved():
    """str 子类枚举仍是 str 实例（DB 序列化依赖）。"""
    assert isinstance(enums.LIVE_MODE.ON, str)
    assert enums.LIVE_MODE.ON == "on"
    assert isinstance(enums.ExchangeType.OKX, str)
    assert enums.ExchangeType.OKX == "okx"
    assert enums.AccountStatusType.ENABLED == "enabled"


def test_namespace_classes_preserved():
    """普通命名空间类（无 Enum 基类）保留常量。"""
    assert enums.DEPLOYMENT_STATUS.PENDING == 0
    assert enums.DEPLOYMENT_STATUS.DEPLOYED == 1
    assert enums.VALIDATION_STATUS.RUNNING == 0
    assert enums.VALIDATION_STATUS.COMPLETED == 1


def test_domain_submodule_paths_available():
    """新领域路径可 import（拆分提供的新能力，re-export identity 一致）。

    新代码推荐 ``from ginkgo.enums.<domain> import X``；旧代码 ``from ginkgo.enums import X``
    仍可用。两条路径取到的对象必须同一（``is``），证明 re-export 而非复制。
    """
    import importlib

    cases = [
        ("ginkgo.enums.base", "EnumBase"),
        ("ginkgo.enums.trading", "DIRECTION_TYPES"),
        ("ginkgo.enums.data", "SOURCE_TYPES"),
        ("ginkgo.enums.event", "EVENT_TYPES"),
        ("ginkgo.enums.strategy", "STRATEGY_TYPES"),
        ("ginkgo.enums.execution", "EXECUTION_MODE"),
        ("ginkgo.enums.portfolio", "PORTFOLIO_RUNSTATE_TYPES"),
        ("ginkgo.enums.system", "FILE_TYPES"),
        ("ginkgo.enums.account", "BrokerStateType"),
        ("ginkgo.enums.user", "USER_TYPES"),
    ]
    for mod_name, sym in cases:
        mod = importlib.import_module(mod_name)
        assert hasattr(mod, sym), f"{mod_name} 缺 {sym}"
        assert getattr(mod, sym) is getattr(enums, sym), (
            f"{mod_name}.{sym} 非 re-export 同一对象（identity 漂移）"
        )
