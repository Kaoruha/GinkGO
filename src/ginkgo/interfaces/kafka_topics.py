# Upstream: 所有使用Kafka的模块
# Downstream: 无（常量定义）
# Role: 定义所有Kafka Topic名称常量，统一管理，避免硬编码


"""
Kafka Topics 常量定义

统一管理所有Kafka Topic名称，避免硬编码。
命名规范：
  - ginkgo.live.*: 实盘交易专用
  - ginkgo.*: 全局通用

Topic分类：
  1. 市场数据 (Market Data)
  2. 订单 (Orders)
  3. 控制 (Control)
  4. 调度 (Schedule)
  5. 系统事件 (System Events)
  6. 通知 (Notifications)
"""


class KafkaTopics:
    """
    Kafka Topic 常量定义

    所有Topic名称统一管理，避免字符串硬编码
    """

    # ============================================
    # 市场数据 Topics (Market Data)
    # ============================================

    # 实时市场数据（EventPriceUpdate, EventBar）
    MARKET_DATA = "ginkgo.live.market.data"

    # 按市场细分的Topic（可选，用于高吞吐场景）
    MARKET_DATA_CN = "ginkgo.live.market.data.cn"      # A股
    MARKET_DATA_HK = "ginkgo.live.market.data.hk"      # 港股
    MARKET_DATA_US = "ginkgo.live.market.data.us"      # 美股
    MARKET_DATA_FUTURES = "ginkgo.live.market.data.futures"  # 期货

    # 订阅更新（Portfolio订阅标的变更）
    INTEREST_UPDATES = "ginkgo.live.interest.updates"

    # ============================================
    # 订单 Topics (Orders)
    # ============================================

    # 订单提交（ExecutionNode → LiveEngine）
    ORDERS_SUBMISSION = "ginkgo.live.orders.submission"

    # 订单回报（LiveEngine → ExecutionNode）
    ORDERS_FEEDBACK = "ginkgo.live.orders.feedback"

    # ============================================
    # 控制 Topics (Control)
    # ============================================

    # 控制命令（API Gateway → LiveEngine, ExecutionNode, DataManager等）
    CONTROL_COMMANDS = "ginkgo.live.control.commands"

    # ============================================
    # 调度 Topics (Schedule)
    # ============================================

    # 调度更新（Scheduler → ExecutionNode）
    SCHEDULE_UPDATES = "ginkgo.schedule.updates"
    SCHEDULE_UPDATES_LIVE = "ginkgo.live.schedule.updates"

    # ============================================
    # 数据更新 Topics (Data Update)
    # ============================================

    # 数据更新信号（stockinfo, bar, tick, adjustfactor 等）
    DATA_UPDATE = "ginkgo.data.update"

    # ============================================
    # 数据采集 Topics (Data Collection)
    # ============================================

    # 数据采集命令（TaskTimer → DataWorker）
    # 命令类型: bar_snapshot, stockinfo, adjustfactor, tick
    DATA_COMMANDS = "ginkgo.data.commands"

    # ============================================
    # 系统事件 Topics (System Events)
    # ============================================

    # 系统事件（兴趣集同步、Node离线等）
    SYSTEM_EVENTS = "ginkgo.live.system.events"

    # ============================================
    # 通知 Topics (Notifications)
    # ============================================

    # 系统通知（告警、状态变化等）
    NOTIFICATIONS = "ginkgo.notifications"

    # ============================================
    # Topic 分组（便于批量操作）
    # ============================================

    # 实盘交易专用Topics
    LIVE_TOPICS = [
        MARKET_DATA,
        MARKET_DATA_CN,
        MARKET_DATA_HK,
        MARKET_DATA_US,
        MARKET_DATA_FUTURES,
        INTEREST_UPDATES,
        ORDERS_SUBMISSION,
        ORDERS_FEEDBACK,
        CONTROL_COMMANDS,
        SCHEDULE_UPDATES_LIVE,
        SYSTEM_EVENTS,
    ]

    # 所有市场数据Topics
    MARKET_DATA_TOPICS = [
        MARKET_DATA,
        MARKET_DATA_CN,
        MARKET_DATA_HK,
        MARKET_DATA_US,
        MARKET_DATA_FUTURES,
    ]

    # 所有Topics
    ALL_TOPICS = [
        MARKET_DATA,
        MARKET_DATA_CN,
        MARKET_DATA_HK,
        MARKET_DATA_US,
        MARKET_DATA_FUTURES,
        INTEREST_UPDATES,
        ORDERS_SUBMISSION,
        ORDERS_FEEDBACK,
        CONTROL_COMMANDS,
        SCHEDULE_UPDATES,
        SCHEDULE_UPDATES_LIVE,
        DATA_UPDATE,
        DATA_COMMANDS,  # 新增：数据采集命令
        SYSTEM_EVENTS,
        NOTIFICATIONS,
    ]
