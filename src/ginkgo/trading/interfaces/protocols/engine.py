"""
IEngine Protocol Interface

This module defines the IEngine Protocol interface for trading engines,
providing type safety and IDE support for engine development.
"""

from typing import Protocol, Dict, Any, List, Optional, runtime_checkable


@runtime_checkable
class IEngine(Protocol):
    """交易引擎接口协议 (Trading Engine Interface Protocol)

    这个Protocol定义了所有交易引擎系统必须实现的核心接口，提供类型安全的
    编译时检查和运行时验证能力。

    主要功能：
    1. 生命周期管理 - 引擎的启动、暂停、停止控制
    2. 状态管理 - 引擎状态转换和监控
    3. 事件处理 - 事件队列管理和事件分发
    4. 组件管理 - 投资组合、数据源、撮合中心等组件管理
    5. 身份管理 - 引擎ID和运行会话管理
    6. 配置管理 - 动态配置和参数调整

    使用示例：
        class MyEngine(BaseEngine, EngineMixin):
            def run(self) -> Any:
                # 实现具体的运行逻辑
                return execution_result

            def handle_event(self, event: EventBase) -> None:
                # 实现具体的事件处理逻辑
                pass

    类型检查：
        def validate_engine(engine: IEngine) -> bool:
            return isinstance(engine, IEngine)
    """

    # ========== 基础属性 ==========

    @property
    def name(self) -> str:
        """
        引擎名称 (Engine Name)

        Returns:
            str: 引擎的唯一名称标识

        Note:
            - 名称应该在系统内保持唯一性
            - 建议使用描述性名称，便于识别管理
        """
        ...

    @property
    def engine_id(self) -> str:
        """
        引擎ID (Engine ID)

        Returns:
            str: 引擎的唯一标识符

        Note:
            - ID应该全局唯一
            - 用于数据库存储和检索
            - 通常基于配置生成
        """
        ...

    @property
    def run_id(self) -> Optional[str]:
        """
        运行会话ID (Run Session ID)

        Returns:
            Optional[str]: 当前运行会话ID，未运行时返回None

        Note:
            - 每次运行生成新的会话ID
            - 用于区分不同的执行会话
            - 暂停恢复时保持相同会话ID
        """
        ...

    @property
    def status(self) -> str:
        """
        引擎状态 (Engine Status)

        Returns:
            str: 引擎状态的字符串表示

        可能的值：
            - "Void": 初始状态
            - "Idle": 空闲状态
            - "Initializing": 初始化中
            - "Running": 运行中
            - "Paused": 暂停中
            - "Stopped": 已停止
        """
        ...

    @property
    def state(self) -> Any:
        """
        引擎状态枚举 (Engine State Enum)

        Returns:
            ENGINESTATUS_TYPES: 引擎当前状态枚举

        Note:
            - 返回枚举类型，便于程序化处理
            - 支持状态转换验证
        """
        ...

    @property
    def is_active(self) -> bool:
        """
        引擎是否活跃 (Is Engine Active)

        Returns:
            bool: 引擎是否处于运行状态

        Note:
            - 运行状态为RUNNING时返回True
            - 用于快速检查引擎是否在工作
        """
        ...

    @property
    def mode(self) -> Any:
        """
        引擎运行模式 (Engine Mode)

        Returns:
            EXECUTION_MODE: 引擎运行模式枚举

        可能的值：
            - BACKTEST: 回测模式
            - LIVE: 实盘模式
            - PAPER: 模拟盘模式
        """
        ...

    @mode.setter
    def mode(self, value: Any) -> None:
        """
        设置引擎运行模式 (Set Engine Mode)

        Args:
            value: 新的运行模式

        Note:
            - 应该在引擎启动前设置
            - 模式变更需要重启引擎
        """
        ...

    @property
    def run_sequence(self) -> int:
        """
        运行序列号 (Run Sequence Number)

        Returns:
            int: 当前运行序列号

        Note:
            - 每次运行会话递增
            - 用于跟踪运行历史
            - 从1开始计数
        """
        ...

    # ========== 生命周期管理 ==========

    def start(self) -> bool:
        """
        启动引擎 (Start Engine)

        启动引擎开始运行，包括初始化组件、启动线程等。

        Returns:
            bool: 启动操作是否成功

        典型操作：
            1. 验证状态转换合法性
            2. 生成或恢复运行会话ID
            3. 设置引擎状态为RUNNING
            4. 启动必要的工作线程
            5. 初始化组件状态

        状态转换：
            - IDLE → RUNNING
            - PAUSED → RUNNING
            - STOPPED → RUNNING（新会话）

        Note:
            - 从无效状态启动会失败
            - 暂停恢复保持原有会话ID
            - 停止后启动会创建新会话
        """
        ...

    def pause(self) -> bool:
        """
        暂停引擎 (Pause Engine)

        暂停引擎运行，保持当前状态，可以后续恢复。

        Returns:
            bool: 暂停操作是否成功

        典型操作：
            1. 验证状态转换合法性
            2. 设置引擎状态为PAUSED
            3. 通知组件暂停处理
            4. 保持当前会话状态

        状态转换：
            - RUNNING → PAUSED

        Note:
            - 只有运行状态可以暂停
            - 暂停保持当前会话
            - 可以通过start()恢复
        """
        ...

    def stop(self) -> bool:
        """
        停止引擎 (Stop Engine)

        停止引擎运行，结束当前运行会话。

        Returns:
            bool: 停止操作是否成功

        典型操作：
            1. 验证状态转换合法性
            2. 设置引擎状态为STOPPED
            3. 停止所有工作线程
            4. 清理资源
            5. 记录会话结束

        状态转换：
            - RUNNING → STOPPED
            - PAUSED → STOPPED

        Note:
            - 结束当前运行会话
            - 后续启动会创建新会话
            - 应该优雅停止所有组件
        """
        ...

    # ========== 事件管理 ==========

    def put_event(self, event: Any) -> None:
        """
        投递事件 (Put Event)

        向引擎的事件队列投递事件。

        Args:
            event: 要投递的事件

        典型操作：
            1. 增强事件信息（添加引擎ID、运行ID等）
            2. 分配事件序列号
            3. 投递到事件队列
            4. 更新事件统计

        Note:
            - 事件会按投递顺序处理
            - 队列满时会阻塞等待
            - 支持事件增强功能
        """
        ...

    def get_event(self, timeout: Optional[float] = None) -> Any:
        """
        获取事件 (Get Event)

        从事件队列中获取事件进行处理。

        Args:
            timeout: 超时时间（秒），None表示无限等待

        Returns:
            EventBase: 获取到的事件

        典型操作：
            1. 从队列中获取事件
            2. 设置超时机制
            3. 线程安全访问队列

        Note:
            - 主循环中调用此方法
            - 支持超时机制避免无限等待
            - 队列为空时会等待或超时
        """
        ...

    def handle_event(self, event: Any) -> None:
        """
        处理事件 (Handle Event)

        处理单个事件的具体逻辑。

        Args:
            event: 要处理的事件

        典型操作：
            1. 记录事件处理开始
            2. 分发到注册的处理器
            3. 执行通用处理器
            4. 记录处理结果
            5. 更新统计信息

        Note:
            - 抽象方法，子类必须实现
            - 应该包含异常处理逻辑
            - 处理失败不应该影响其他事件
        """
        ...

    def run(self) -> Any:
        """
        运行引擎 (Run Engine)

        引擎的主要运行逻辑。

        Returns:
            Any: 运行结果

        典型操作：
            1. 启动引擎
            2. 进入主事件循环
            3. 处理事件直到停止
            4. 返回运行结果

        Note:
            - 抽象方法，子类必须实现
            - 包含引擎的主要业务逻辑
            - 应该支持各种运行模式
        """
        ...

    # ========== 组件管理 ==========

    @property
    def portfolios(self) -> List[Any]:
        """
        投资组合列表 (Portfolios List)

        Returns:
            List[PortfolioBase]: 引擎管理的投资组合列表

        Note:
            - 返回所有投资组合的引用
            - 投资组合通过引擎进行协调
            - 支持动态添加和移除
        """
        ...

    def add_portfolio(self, portfolio: Any) -> None:
        """
        添加投资组合 (Add Portfolio)

        向引擎添加投资组合。

        Args:
            portfolio: 投资组合实例，必须实现IPortfolio接口

        典型操作：
            1. 验证投资组合有效性
            2. 检查重复添加
            3. 绑定引擎到投资组合
            4. 注入事件发布器
            5. 绑定数据源（如果存在）

        Note:
            - 避免重复添加相同投资组合
            - 自动建立双向绑定关系
            - 记录添加操作日志
        """
        ...

    def remove_portfolio(self, portfolio: Any) -> None:
        """
        移除投资组合 (Remove Portfolio)

        从引擎中移除投资组合。

        Args:
            portfolio: 要移除的投资组合实例

        典型操作：
            1. 验证投资组合存在
            2. 清理绑定关系
            3. 从列表中移除
            4. 记录移除操作

        Note:
            - 移除不会影响投资组合的内部状态
            - 建议先停止投资组合再移除
            - 记录移除操作日志
        """
        ...

    # ========== 配置管理 ==========

    @property
    def event_timeout(self) -> float:
        """
        事件超时时间 (Event Timeout)

        Returns:
            float: 事件处理超时时间（秒）

        Note:
            - 用于事件获取的超时设置
            - 避免主循环无限等待
            - 可以动态调整
        """
        ...

    def set_event_timeout(self, timeout: float) -> None:
        """
        设置事件超时时间 (Set Event Timeout)

        设置事件处理的超时时间。

        Args:
            timeout: 超时时间（秒）

        Note:
            - 用于主循环的事件获取
            - 应该设置为合理的值
            - 太长可能导致响应迟缓
        """
        ...

    def set_event_queue_size(self, size: int) -> bool:
        """
        设置事件队列大小 (Set Event Queue Size)

        动态调整事件队列的大小。

        Args:
            size: 新的队列大小

        Returns:
            bool: 调整操作是否成功启动

        典型操作：
            1. 验证队列大小有效性
            2. 检查是否正在调整中
            3. 创建新的队列
            4. 转移现有事件
            5. 原子性切换队列

        Note:
            - 使用双缓冲方案确保事件不丢失
            - 调整过程中会阻塞新事件
            - 调整失败时会保持原队列
        """
        ...

    @property
    def is_resizing_queue(self) -> bool:
        """
        队列是否正在调整中 (Is Queue Resizing)

        Returns:
            bool: 事件队列是否正在调整大小

        Note:
            - 用于检查队列调整状态
            - 调整过程中不能重复调整
            - 可以用于状态监控
        """
        ...

    # ========== 监控和统计 ==========

    def get_engine_summary(self) -> Dict[str, Any]:
        """
        获取引擎摘要 (Get Engine Summary)

        返回引擎的状态摘要信息。

        Returns:
            Dict[str, Any]: 引擎状态摘要

        包含信息：
            - name: 引擎名称
            - engine_id: 引擎ID
            - run_id: 运行会话ID
            - status: 状态字符串
            - is_active: 是否活跃
            - run_sequence: 运行序列号
            - mode: 运行模式
            - portfolios_count: 投资组合数量

        Note:
            - 用于监控和调试
            - 信息应该实时更新
            - 适合序列化和传输
        """
        ...

    def put(self, event: Any) -> None:
        """
        发布事件 (Publish Event)

        向引擎发布事件，别名方法。

        Args:
            event: 要发布的事件

        Note:
            - 实际调用put_event方法
            - 提供更简洁的接口
            - 保持向后兼容性
        """
        ...

    # ========== 身份管理 ==========

    @property
    def component_type(self) -> Any:
        """
        组件类型 (Component Type)

        Returns:
            COMPONENT_TYPES: 组件类型枚举

        Note:
            - 通常为COMPONENT_TYPES.ENGINE
            - 用于组件分类和管理
        """
        ...

    @property
    def uuid(self) -> str:
        """
        唯一标识符 (Unique Identifier)

        Returns:
            str: 组件的唯一标识符

        Note:
            - 与engine_id通常相同
            - 用于全局标识
        """
        ...

    # ========== 线程和并发管理 ==========

    def _get_next_sequence_number(self) -> int:
        """
        获取下一个序列号 (Get Next Sequence Number)

        生成递增的事件序列号。

        Returns:
            int: 递增的序列号

        Note:
            - 线程安全操作
            - 用于事件排序和追踪
            - 每个会话重新开始计数
        """
        ...

    def _enhance_event(self, event: Any) -> Any:
        """
        增强事件 (Enhance Event)

        为事件添加运行时上下文信息。

        Args:
            event: 原始事件

        Returns:
            EventBase: 增强后的事件

        典型增强：
            - 设置engine_id
            - 设置run_id
            - 设置时间戳
            - 分配序列号

        Note:
            - 增强失败时返回原事件
            - 确保事件流程不中断
            - 提供丰富的上下文信息
        """
        ...

    def _transfer_events_with_buffer(self, old_queue: Any, temp_queue: Any,
                                   new_queue: Any, old_size: int, new_size: int) -> None:
        """
        转移事件（带缓冲） (Transfer Events with Buffer)

        在队列大小调整过程中安全转移事件。

        Args:
            old_queue: 旧的事件队列
            temp_queue: 临时缓冲队列
            new_queue: 新的事件队列
            old_size: 旧队列大小
            new_size: 新队列大小

        转移阶段：
            1. 转移旧队列中的事件
            2. 转移临时队列中的事件
            3. 原子性切换到新队列

        Note:
            - 确保事件不丢失
            - 使用双缓冲方案
            - 在后台线程中执行
        """
        ...