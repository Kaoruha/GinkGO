# Upstream: EngineAssemblyService, TaskEngineBuilder
# Downstream: BacktestFeeder, OKXDataFeeder, SimBroker, OKXBroker, EXECUTION_MODE, EVENT_TYPES
# Role: 基础设施工厂（无状态），提供DataFeeder/Broker/引擎基础设施的静态创建方法


"""
InfrastructureFactory - 基础设施工厂

从 engine_assembly_service.py 提取，所有方法均为 @staticmethod，无状态。
负责：
- 解析执行模式
- 创建 DataFeeder
- 创建基础引擎
- 创建 Broker
- 设置 DataFeeder
- 设置引擎基础设施（路由、网关等）
"""

from typing import Optional, Dict, Any

from ginkgo.libs import GLOG, GinkgoLogger, datetime_normalize
from ginkgo.enums import EVENT_TYPES, EXECUTION_MODE
from ginkgo.trading.feeders import BacktestFeeder
from ginkgo.trading.brokers.sim_broker import SimBroker

try:
    from ginkgo.trading.feeders import OKXDataFeeder
except ImportError:
    OKXDataFeeder = None  # Optional dependency

try:
    from ginkgo.trading.brokers.okx_broker import OKXBroker as OkxBroker
except Exception:
    OkxBroker = None  # Optional dependency


class InfrastructureFactory:
    """
    基础设施工厂（无状态）

    提供引擎基础设施的创建方法，所有方法均为 @staticmethod。
    """

    @staticmethod
    def resolve_execution_mode(engine_data: Dict[str, Any]) -> EXECUTION_MODE:
        """
        从 engine_data 中解析执行模式

        支持以下格式：
        - EXECUTION_MODE 枚举值（直接传入）
        - 整数值（0=BACKTEST, 1=LIVE, 2=PAPER, ...）
        - 字符串（"backtest", "live", "paper", ...）
        - 默认 BACKTEST
        """
        if engine_data is None:
            return EXECUTION_MODE.BACKTEST

        raw = engine_data.get("execution_mode") or engine_data.get("broker") or engine_data.get("broker_mode")

        if raw is None:
            return EXECUTION_MODE.BACKTEST

        # 已经是枚举值
        if isinstance(raw, EXECUTION_MODE):
            return raw

        # 字符串映射
        if isinstance(raw, str):
            mode_map = {
                "backtest": EXECUTION_MODE.BACKTEST,
                "live": EXECUTION_MODE.LIVE,
                "paper": EXECUTION_MODE.PAPER,
                "paper_manual": EXECUTION_MODE.PAPER_MANUAL,
                "paper_auto": EXECUTION_MODE.PAPER_AUTO,
                "live_manual": EXECUTION_MODE.LIVE_MANUAL,
                "live_auto": EXECUTION_MODE.LIVE_AUTO,
                "semi_auto": EXECUTION_MODE.SEMI_AUTO,
            }
            mapped = mode_map.get(raw.lower().strip())
            if mapped is not None:
                return mapped

        # 整数值映射
        try:
            return EXECUTION_MODE(int(raw))
        except (ValueError, TypeError):
            pass

        GLOG.WARN(f"Unknown execution_mode '{raw}', falling back to BACKTEST")
        return EXECUTION_MODE.BACKTEST

    @staticmethod
    def create_feeder_for_mode(mode: EXECUTION_MODE) -> Any:
        """
        根据执行模式创建对应的 DataFeeder

        - BACKTEST: BacktestFeeder（从数据库读取历史K线）
        - PAPER / LIVE: OKXDataFeeder（实时数据推送）
        """
        if mode == EXECUTION_MODE.BACKTEST:
            return BacktestFeeder("ExampleFeeder")

        # PAPER / LIVE 及其他非回测模式使用 OKXDataFeeder
        if OKXDataFeeder is not None:
            return OKXDataFeeder()

        GLOG.WARN(f"OKXDataFeeder not available for mode={mode.name}, falling back to BacktestFeeder")
        return BacktestFeeder("ExampleFeeder")

    @staticmethod
    def create_base_engine(
        engine_data: Dict[str, Any], engine_id: str, logger: GinkgoLogger = None,
        progress_callback: Optional[callable] = None,
    ) -> Optional[Any]:
        """Create and configure the base historic engine."""
        try:
            # 默认使用TimeControlledEventEngine，它支持时间控制
            from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine

            # 根据 engine_data 中的 execution_mode 决定引擎运行模式
            exec_mode = InfrastructureFactory.resolve_execution_mode(engine_data)

            engine = TimeControlledEventEngine(
                name=engine_data["name"],
                mode=exec_mode,
                timer_interval=0.01,  # 与示例保持一致，提高性能
                progress_callback=progress_callback,
            )
            engine.set_engine_id(engine_id)

            # 设置 task_id（用于回测结果聚合器和事件追踪）
            task_id = engine_data.get("task_id", engine_id)
            engine.set_task_id(task_id)

            # 调试：验证 task_id 是否正确设置到 EngineContext
            engine_context = engine.get_engine_context()
            _logger = logger or GLOG
            _logger.INFO(f"🔍 [RUN_ID CHECK] engine.set_task_id({task_id}) called")
            _logger.INFO(f"🔍 [RUN_ID CHECK] EngineContext.task_id = {engine_context.task_id}")
            _logger.INFO(f"🔍 [RUN_ID CHECK] EngineContext.engine_id = {engine_context.engine_id}")

            # 设置时间范围 - 使用引擎数据库中的时间配置
            if "backtest_start_date" in engine_data and "backtest_end_date" in engine_data:
                start_date = datetime_normalize(engine_data["backtest_start_date"])
                end_date = datetime_normalize(engine_data["backtest_end_date"])

                engine.set_time_range(start_date, end_date)
                _logger.INFO(f"📅 Set engine time range: {start_date} to {end_date}")
            else:
                _logger.WARN("⚠️ No time range found in engine data")

            _logger.DEBUG(f"Created base engine: {engine_data['name']} ({type(engine).__name__})")
            return engine

        except Exception as e:
            _logger = logger or GLOG
            _logger.ERROR(f"Failed to create base engine: {e}")
            return None

    @staticmethod
    def create_broker_from_config(engine_data: Dict[str, Any]):
        """Create broker instance based on engine configuration."""
        mode = (
            engine_data.get("broker")
            or engine_data.get("broker_mode")
            or engine_data.get("execution_mode")
            or "backtest"
        )
        mode = str(mode).lower()
        cfg = engine_data.get("broker_config") or {}

        # 🔧 修复：优先使用数据库中的broker_attitude配置，确保与Example一致
        from ginkgo.enums import ATTITUDE_TYPES

        # 从engine数据中获取broker_attitude，默认为OPTIMISTIC以保持一致性
        broker_attitude = ATTITUDE_TYPES.OPTIMISTIC  # 默认值
        if engine_data and hasattr(engine_data, 'broker_attitude'):
            try:
                # 如果是数字，转换为枚举
                if isinstance(engine_data.broker_attitude, int):
                    broker_attitude = ATTITUDE_TYPES(engine_data.broker_attitude)
                else:
                    broker_attitude = ATTITUDE_TYPES.validate_input(engine_data.broker_attitude)
            except Exception:
                broker_attitude = ATTITUDE_TYPES.OPTIMISTIC  # 出错时使用默认值
        elif engine_data and 'broker_attitude' in engine_data:
            try:
                broker_attitude = ATTITUDE_TYPES(engine_data['broker_attitude'])
            except Exception:
                broker_attitude = ATTITUDE_TYPES.OPTIMISTIC

        # 设置与broker_attitude一致的配置
        default_cfg = {
            "name": "SimBroker",
            "attitude": broker_attitude,
            "commission_rate": 0.0003,
            "commission_min": 5
        }

        # 合并用户配置（如果有）
        default_cfg.update(cfg)
        cfg = default_cfg

        # Map mode to broker implementation
        if mode in ("backtest", "simulation", "sim", "paper"):
            # SimBroker 用于回测和模拟盘（PAPER）
            return SimBroker(**cfg)
        if mode in ("okx", "okx_live", "live") and OkxBroker is not None:
            return OkxBroker(cfg)
        # Fallback to SimBroker
        return SimBroker(**cfg)

    @staticmethod
    def setup_data_feeder_for_engine(engine: Any, logger: GinkgoLogger = None, engine_data: Dict[str, Any] = None) -> bool:
        """Setup data feeder after all portfolios are bound (matching Example order)"""
        try:
            _logger = logger or GLOG

            # 根据 execution_mode 选择合适的 DataFeeder
            exec_mode = InfrastructureFactory.resolve_execution_mode(engine_data) if engine_data else EXECUTION_MODE.BACKTEST
            feeder = InfrastructureFactory.create_feeder_for_mode(exec_mode)

            # 使用时间控制引擎的数据馈送接入，以确保 advance_time_to 能触发数据更新
            if hasattr(engine, "set_data_feeder"):
                engine.set_data_feeder(feeder)
            else:
                # 兼容老接口
                engine.bind_datafeeder(feeder)
            # 去订阅/广播：由引擎推进直接调用 Feeder.advance_to_time 注入事件
            # 同时确保 Feeder 能够直接回注事件（可选）
            if hasattr(feeder, "set_event_publisher"):
                feeder.set_event_publisher(engine.put)
            # 注册兴趣更新事件给Feeder（仅 BacktestFeeder 支持）
            if hasattr(feeder, "on_interest_update"):
                from ginkgo.trading.events import EventInterestUpdate
                engine.register(EVENT_TYPES.INTERESTUPDATE, feeder.on_interest_update)

            _logger.DEBUG(f"✅ Data feeder setup completed after portfolio binding (mode={exec_mode.name})")
            return True
        except Exception as e:
            _logger = logger or GLOG
            _logger.ERROR(f"Failed to setup data feeder: {e}")
            return False

    @staticmethod
    def setup_engine_infrastructure(
        engine: Any, logger: GinkgoLogger = None, engine_data: Dict[str, Any] = None, skip_feeder: bool = False
    ) -> bool:
        """Set up matchmaking and data feeding for the engine."""
        try:
            _logger = logger or GLOG

            # 📝 修复事件处理顺序：先添加Portfolio，后添加Router，与Example保持一致
            # 将在后面Portfolio添加完成后再绑定Router

            # Set up data feeder
            feeder = BacktestFeeder("ExampleFeeder")

            # 使用时间控制引擎的数据馈送接入，以确保 advance_time_to 能触发数据更新
            if hasattr(engine, "set_data_feeder"):
                engine.set_data_feeder(feeder)
            else:
                # 兼容老接口
                engine.bind_datafeeder(feeder)
            # 去订阅/广播：由引擎推进直接调用 Feeder.advance_to_time 注入事件
            # 同时确保 Feeder 能够直接回注事件（可选）
            if hasattr(feeder, "set_event_publisher"):
                feeder.set_event_publisher(engine.put)
            # 注册兴趣更新事件给Feeder
            from ginkgo.trading.events import EventInterestUpdate

            engine.register(EVENT_TYPES.INTERESTUPDATE, feeder.on_interest_update)

            # Set up gateway and broker (restored original binding logic)
            from ginkgo.trading.gateway.trade_gateway import TradeGateway
            broker = InfrastructureFactory.create_broker_from_config(engine_data or {})
            gateway = TradeGateway(brokers=[broker])
            engine.bind_router(gateway)
            # 明确注入事件回注接口，匹配 set_event_publisher 约定
            if hasattr(gateway, "set_event_publisher"):
                gateway.set_event_publisher(engine.put)

            _logger.DEBUG("Engine infrastructure setup completed")
            return True

        except Exception as e:
            _logger = logger or GLOG
            _logger.ERROR(f"Failed to setup engine infrastructure: {e}")
            return False
