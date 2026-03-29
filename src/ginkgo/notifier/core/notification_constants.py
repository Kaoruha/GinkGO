# Upstream: NotificationService, WebhookDispatcher (通知发送和Webhook调度)
# Downstream: 无（纯常量模块）
# Role: 通知系统常量定义，包括 Discord 颜色方案和颜色映射表

"""
通知系统常量

定义 Discord Webhook 使用的颜色方案和颜色映射表：
- 交易信号颜色（做多/做空/平仓）
- 系统通知颜色（信息/警告/错误等）
"""

# ============================================================================
# Discord 颜色方案（十进制整数）
# ============================================================================

# 交易信号颜色（鲜亮醒目）
DISCORD_COLOR_LONG = 5797806      # 🟢 鲜绿色 - 做多信号
DISCORD_COLOR_SHORT = 16711735    # 🔴 鲜红色 - 做空信号
DISCORD_COLOR_VOID = 34886848     # 🔷 鲜蓝色 - 平仓信号

# 系统级别通知颜色
DISCORD_COLOR_WHITE = 16777215    # ⚪ 白色 - 普通系统通知
DISCORD_COLOR_ORANGE = 16744272   # 🟠 橙色 - 警告
DISCORD_COLOR_YELLOW = 16776960   # 🟡 黄色 - 异常

# 颜色映射表
TRADING_SIGNAL_COLORS = {
    "LONG": DISCORD_COLOR_LONG,
    "SHORT": DISCORD_COLOR_SHORT,
    "VOID": DISCORD_COLOR_VOID,
}

SYSTEM_LEVEL_COLORS = {
    "INFO": DISCORD_COLOR_WHITE,       # 白色 - 普通信息
    "SUCCESS": DISCORD_COLOR_WHITE,    # 白色 - 成功操作
    "UPDATE": DISCORD_COLOR_WHITE,     # 白色 - 数据更新
    "WARNING": DISCORD_COLOR_ORANGE,   # 橙色 - 警告提醒
    "ERROR": DISCORD_COLOR_YELLOW,     # 黄色 - 错误信息
    "ALERT": DISCORD_COLOR_ORANGE,     # 橙色 - 紧急告警
}
