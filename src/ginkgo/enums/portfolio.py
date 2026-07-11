"""Portfolio 运行时域枚举：运行模式/运行状态/Worker 状态（Phase 5 优雅重启）。

从 ginkgo/enums.py 拆分（#3838）。聚合 re-export 入口：ginkgo/enums/__init__.py。
"""

from .base import EnumBase


class PORTFOLIO_MODE_TYPES(EnumBase):
    """Portfolio 运行模式枚举"""

    VOID = -1
    BACKTEST = 0                  # 回测模式
    PAPER = 1                     # 模拟盘模式
    LIVE = 2                      # 实盘模式


class PORTFOLIO_RUNSTATE_TYPES(EnumBase):
    """Portfolio 运行时状态枚举（Phase 5: 优雅重启机制）"""

    VOID = -1
    INITIALIZED = 0               # 已初始化
    RUNNING = 1                   # 正常运行
    PAUSED = 2                    # 已暂停
    STOPPING = 3                  # 正在停止（准备重载）
    STOPPED = 4                   # 已停止
    RELOADING = 5                 # 正在重载配置
    MIGRATING = 6                 # 正在迁移到其他节点
    OFFLINE = 7                   # 已下线（人工停止策略执行，保留持仓）


class WORKER_STATUS_TYPES(EnumBase):
    """Worker 状态枚举（Data Worker 容器化部署）"""

    VOID = -1
    STOPPED = 0      # 已停止
    STARTING = 1     # 启动中
    RUNNING = 2      # 运行中
    STOPPING = 3     # 停止中
    ERROR = 4        # 错误状态


__all__ = ['PORTFOLIO_MODE_TYPES', 'PORTFOLIO_RUNSTATE_TYPES', 'WORKER_STATUS_TYPES']
