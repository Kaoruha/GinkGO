# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: 引擎装配服务门面类，委托子模块完成具体装配逻辑


"""
Engine Assembly Service

This service handles the assembly and configuration of backtest engines,
replacing the direct function calls in engine_assembler_factory.py with
a proper service-oriented approach using dependency injection.

重构说明：
原文件（2182行）已拆分为以下子模块：
- _assembly/component_loader.py: 组件实例化和绑定
- _assembly/infrastructure_factory.py: 引擎基础设施创建（无状态工具类）
- _assembly/task_engine_builder.py: 从 BacktestTask 构建引擎
- _assembly/data_preparer.py: 数据准备和 YAML 配置驱动装配

本文件保留 EngineAssemblyService 类名和公共 API，内部委托到子模块。
"""

from typing import Optional, Dict, Any, List, Union
from pathlib import Path
from decimal import Decimal

from ginkgo.libs import GLOG, GinkgoLogger
from ginkgo.enums import EVENT_TYPES
from ginkgo.trading.engines import BaseEngine, BacktestEngine
from ginkgo.trading.portfolios import PortfolioT1Backtest
from ginkgo.trading.time.clock import now as clock_now

# Import data services through dependency injection instead of direct container access
from ginkgo.data.services.base_service import BaseService, ServiceResult

# 导入子模块
from ginkgo.trading.services._assembly.component_loader import ComponentLoader
from ginkgo.trading.services._assembly.infrastructure_factory import InfrastructureFactory
from ginkgo.trading.services._assembly.task_engine_builder import TaskEngineBuilder
from ginkgo.trading.services._assembly.data_preparer import DataPreparer, EngineConfigurationError


class EngineAssemblyService(BaseService):
    """
    统一引擎装配服务（门面类）

    此服务整合了所有引擎装配功能，内部委托到子模块完成具体逻辑：
    - DataPreparer: 数据准备和 YAML 配置
    - InfrastructureFactory: 引擎基础设施创建
    - ComponentLoader: 组件实例化和绑定
    - TaskEngineBuilder: 从 BacktestTask 构建引擎
    """

    def __init__(
        self,
        engine_service=None,
        portfolio_service=None,
        file_service=None,
        analyzer_record_crud=None,
        config_manager=None,
    ):
        """
        Initialize the unified engine assembly service.

        Args:
            engine_service: Service for engine data operations
            portfolio_service: Service for portfolio data operations
            analyzer_record_crud: CRUD service for analyzer record cleanup
            config_manager: Configuration manager for YAML processing
        """
        super().__init__()
        self._engine_service = engine_service
        self._portfolio_service = portfolio_service
        self._file_service = file_service
        self._analyzer_record_crud = analyzer_record_crud
        self._logger = GLOG

        # 装配上下文 - 用于ID注入
        self._current_engine_id = None
        self._current_run_id = None

        # 配置管理器已统一使用GCONF
        self.config_manager = config_manager

        # 初始化子模块
        self._component_loader = ComponentLoader(file_service=file_service, logger=self._logger)
        self._task_engine_builder = TaskEngineBuilder(
            file_service=file_service,
            portfolio_service=portfolio_service,
            engine_service=engine_service,
            logger=self._logger,
        )
        self._data_preparer = DataPreparer(
            engine_service=engine_service,
            portfolio_service=portfolio_service,
            file_service=file_service,
            analyzer_record_crud=analyzer_record_crud,
            logger=self._logger,
        )

    # ========== ID 注入方法 ==========

    def _get_current_engine_id(self) -> str:
        """获取当前装配上下文中的引擎ID"""
        return self._current_engine_id or ""

    def _get_current_run_id(self) -> str:
        """获取当前装配上下文中的运行ID"""
        return self._current_run_id or ""

    def _inject_ids_to_components(
        self, components: Dict[str, Any], engine_id: str, portfolio_id: str, run_id: str
    ) -> None:
        """统一为所有组件注入运行时ID"""
        injected_count = 0
        total_count = 0

        for component_type, component_list in components.items():
            for component in component_list:
                total_count += 1
                if hasattr(component, "set_backtest_ids"):
                    component.set_backtest_ids(engine_id=engine_id, portfolio_id=portfolio_id, run_id=run_id)
                    injected_count += 1
                    self._logger.DEBUG(f"✅ Injected IDs to {component_type}: {component.__class__.__name__}")
                else:
                    self._logger.WARN(f"⚠️ Component {component.__class__.__name__} doesn't support ID injection")

        self._logger.INFO(f"ID injection completed: {injected_count}/{total_count} components updated")

    def _inject_ids_to_single_component(self, component: Any, engine_id: str, portfolio_id: str, run_id: str) -> bool:
        """为单个组件注入运行时ID"""
        if hasattr(component, "set_backtest_ids"):
            component.set_backtest_ids(engine_id=engine_id, portfolio_id=portfolio_id, run_id=run_id)
            self._logger.DEBUG(f"✅ Injected IDs to component: {component.__class__.__name__}")
            return True
        else:
            self._logger.WARN(f"⚠️ Component {component.__class__.__name__} doesn't support ID injection")
            return False

    # ========== 公共 API ==========

    def initialize(self) -> bool:
        """Initialize the engine assembly service."""
        try:
            self._logger.INFO("EngineAssemblyService initialized")
            return True
        except Exception as e:
            self._logger.ERROR(f"Failed to initialize EngineAssemblyService: {e}")
            return False

    def assemble_backtest_engine(
        self,
        engine_id: str = None,
        engine_data: Dict[str, Any] = None,
        portfolio_mappings: List[Dict[str, Any]] = None,
        portfolio_configs: Dict[str, Dict[str, Any]] = None,
        portfolio_components: Dict[str, Dict[str, Any]] = None,
        logger: Optional[GinkgoLogger] = None,
        progress_callback: Optional[callable] = None,
    ) -> ServiceResult:
        """
        统一回测引擎装配方法

        支持两种调用方式：
        1. 仅传入 engine_id：从数据服务获取配置数据（原有方式）
        2. 传入完整参数：直接使用提供的数据进行装配（来自原 assembler_backtest_engine）

        Args:
            engine_id: 引擎配置ID
            engine_data: 引擎配置数据（可选）
            portfolio_mappings: 投资组合映射列表（可选）
            portfolio_configs: 投资组合配置字典（可选）
            portfolio_components: 投资组合组件字典（可选）
            logger: 可选的日志器实例
            progress_callback: 进度回调函数，签名 callback(progress: float, current_date: str)

        Returns:
            ServiceResult containing the assembled engine or error information
        """
        if engine_id is None and engine_data is None:
            return ServiceResult(success=False, error="Either engine_id or engine_data must be provided")

        self._logger.WARN(f"Assembling backtest engine --> {engine_id or 'from_config'}")

        try:
            # 方式1：从数据服务准备数据
            if engine_data is None:
                preparation_result = self._data_preparer.prepare_engine_data(engine_id)
                if not preparation_result.success:
                    return preparation_result

                engine_data = preparation_result.data["engine_data"]
                portfolio_mappings = preparation_result.data["portfolio_mappings"]
                portfolio_configs = preparation_result.data["portfolio_configs"]
                portfolio_components = preparation_result.data["portfolio_components"]

            # 方式2：直接使用提供的数据
            if logger is None:
                now = clock_now().strftime("%Y%m%d%H%M%S")
                logger = GinkgoLogger(
                    logger_name="engine_logger", file_names=[f"bt_{engine_id or 'config'}_{now}"], console_log=False
                )

            # 执行核心装配逻辑
            engine = self._perform_backtest_engine_assembly(
                engine_id=engine_id or engine_data.get("name", "config_engine"),
                engine_data=engine_data,
                portfolio_mappings=portfolio_mappings or [],
                portfolio_configs=portfolio_configs or {},
                portfolio_components=portfolio_components or {},
                logger=logger,
                progress_callback=progress_callback,
            )

            if engine is None:
                return ServiceResult(success=False, error=f"No portfolios bound to engine {engine_id}")

            # 清理历史记录（仅当从数据服务获取时）
            if engine_id and portfolio_configs:
                self._data_preparer.cleanup_historic_records(engine_id, portfolio_configs)

            self._logger.INFO(f"Engine {engine_id or 'config_engine'} assembly completed successfully")
            result = ServiceResult(success=True)
            result.data = engine
            return result

        except Exception as e:
            self._logger.ERROR(f"Failed to assemble backtest engine {engine_id}: {e}")
            return ServiceResult(success=False, error=f"Engine assembly failed: {str(e)}")

    def create_engine_from_yaml(self, config_path: Union[str, Path]) -> ServiceResult:
        """从YAML配置文件创建交易引擎，委托到 DataPreparer"""
        return self._data_preparer.create_engine_from_yaml(config_path)

    def create_engine_from_config(self, config: Dict[str, Any]) -> ServiceResult:
        """从配置字典创建交易引擎，委托到 DataPreparer"""
        return self._data_preparer.create_engine_from_config(config)

    def build_engine_from_task(self, task) -> "TimeControlledEventEngine":
        """从 BacktestTask 构建回测引擎，委托到 TaskEngineBuilder"""
        return self._task_engine_builder.build_engine_from_task(task)

    def get_engine_by_id(self, engine_id: str) -> ServiceResult:
        """Get engine configuration by ID."""
        try:
            engine_result = self._engine_service.get(engine_id=engine_id)
            if not engine_result.success or not engine_result.data:
                return ServiceResult(success=False, error=f"No engine found for id: {engine_id}")

            # Convert to DataFrame if needed
            if hasattr(engine_result.data, "to_dataframe"):
                engine_df = engine_result.data.to_dataframe()
            else:
                engine_df = engine_result.data

            if engine_df.shape[0] == 0:
                return ServiceResult(success=False, error=f"No engine found for id: {engine_id}")

            result = ServiceResult(success=True)
            result.data = engine_df.iloc[0].to_dict()
            return result

        except Exception as e:
            return ServiceResult(success=False, error=f"Failed to get engine: {str(e)}")

    def get_sample_config(self, engine_type: str = "historic") -> Dict[str, Any]:
        """获取示例配置，委托到 DataPreparer"""
        return self._data_preparer.get_sample_config(engine_type)

    def save_sample_config(self, output_path: Union[str, Path], engine_type: str = "historic") -> ServiceResult:
        """保存示例配置到文件，委托到 DataPreparer"""
        return self._data_preparer.save_sample_config(output_path, engine_type)

    # ========== 核心装配逻辑（编排子模块） ==========

    def _perform_backtest_engine_assembly(
        self,
        engine_id: str,
        engine_data: Dict[str, Any],
        portfolio_mappings: List[Dict[str, Any]],
        portfolio_configs: Dict[str, Dict[str, Any]],
        portfolio_components: Dict[str, Dict[str, Any]],
        logger: GinkgoLogger,
        progress_callback: Optional[callable] = None,
    ) -> Optional[BaseEngine]:
        """
        执行回测引擎装配的核心逻辑（编排 DataPreparer + InfrastructureFactory + ComponentLoader）
        增加了统一的ID注入机制
        """
        # 设置装配上下文
        self._current_engine_id = engine_id
        self._current_run_id = engine_data.get("run_id", engine_id)

        try:
            self._logger.INFO(
                f"🔧 Starting engine assembly with context: engine_id={self._current_engine_id}, run_id={self._current_run_id}"
            )

            # Create base engine (委托到 InfrastructureFactory)
            engine = InfrastructureFactory.create_base_engine(engine_data, engine_id, logger, progress_callback)
            if engine is None:
                return None

            # 监控：创建引擎后的状态
            self._logger.INFO(f"🔍 [STATE] After create_base_engine: {engine.status} (state: {engine.state})")

            # Setup basic engine infrastructure (router only, not feeder yet)
            InfrastructureFactory.setup_engine_infrastructure(engine, logger, engine_data, skip_feeder=True)

            # 监控：设置基础设施后的状态
            self._logger.INFO(f"🔍 [STATE] After setup_engine_infrastructure: {engine.status} (state: {engine.state})")

            # Process all portfolios with ID injection
            bound_portfolio_count = 0
            for portfolio_mapping in portfolio_mappings:
                portfolio_id = portfolio_mapping.portfolio_id

                if portfolio_id not in portfolio_configs:
                    self._logger.WARN(f"No configuration found for portfolio {portfolio_id}")
                    continue

                if portfolio_id not in portfolio_components:
                    self._logger.WARN(f"No components found for portfolio {portfolio_id}")
                    continue

                self._logger.INFO(f"🔧 Attempting to bind portfolio {portfolio_id} to engine")
                self._logger.DEBUG(
                    f"Portfolio config keys: {list(portfolio_configs[portfolio_id].keys()) if portfolio_id in portfolio_configs else 'NOT_FOUND'}"
                )
                self._logger.DEBUG(
                    f"Components keys: {list(portfolio_components[portfolio_id].keys()) if portfolio_id in portfolio_components else 'NOT_FOUND'}"
                )

                success = self._bind_portfolio_to_engine_with_ids(
                    engine=engine,
                    portfolio_config=portfolio_configs[portfolio_id],
                    components=portfolio_components[portfolio_id],
                    logger=logger,
                )

                if not success:
                    self._logger.ERROR(f"Failed to bind portfolio {portfolio_id} to engine")
                    continue
                else:
                    self._logger.INFO(f"✅ Successfully bound portfolio {portfolio_id} to engine")
                    bound_portfolio_count += 1

            # 检查是否至少有一个Portfolio成功绑定
            if bound_portfolio_count == 0:
                error_msg = f"No portfolios were successfully bound to engine {engine_id}"
                self._logger.ERROR(error_msg)
                return None

            # 监控：portfolio绑定后的状态
            self._logger.INFO(f"🔍 [STATE] After portfolio binding: {engine.status} (state: {engine.state}), bound_portfolios={bound_portfolio_count}")

            # Setup data feeder AFTER all portfolios are bound (matching Example order)
            InfrastructureFactory.setup_data_feeder_for_engine(engine, logger, engine_data)

            # 监控：feeder设置后的状态
            self._logger.INFO(f"🔍 [STATE] After feeder setup: {engine.status} (state: {engine.state})")

            # 装配完成，但不启动引擎 - 装配和启动分离
            self._logger.INFO("✅ Engine assembly completed (engine not started)")
            self._logger.INFO(f"🔍 [STATE] Final assembly state: {engine.status} (state: {engine.state})")

            return engine

        except Exception as e:
            self._logger.ERROR(f"Failed to perform backtest engine assembly {engine_id}: {e}")
            return None
        finally:
            # 清理装配上下文
            self._current_engine_id = None
            self._current_run_id = None

    # ========== Portfolio 绑定方法（编排多个子模块） ==========

    def _bind_portfolio_to_engine_with_ids(
        self, engine: BacktestEngine, portfolio_config: Dict[str, Any], components: Dict[str, Any], logger: GinkgoLogger
    ) -> bool:
        """绑定Portfolio到Engine，包含统一的ID注入机制"""
        try:
            portfolio_id = portfolio_config["uuid"]
            engine_id = self._get_current_engine_id()
            run_id = self._get_current_run_id()

            self._logger.INFO(
                f"🔧 Binding portfolio {portfolio_id} with ID context: engine_id={engine_id}, run_id={run_id}"
            )

            # Create portfolio instance (引擎使用自身的时间配置)
            portfolio = self._create_portfolio_instance(portfolio_config, logger)
            if portfolio is None:
                return False

            # 为Portfolio注入ID（如果Portfolio支持BacktestBase）
            self._inject_ids_to_single_component(portfolio, engine_id, portfolio_id, run_id)

            # 🔥 延迟查找设计：先绑定组件到Portfolio，此时Portfolio还没有context
            # 但组件会在调用 run_id 等属性时，通过 _bound_portfolio 延迟查找获取
            GLOG.DEBUG(f"[BIND PORTFOLIO] Calling _bind_components_to_portfolio_with_ids for {portfolio_id}")
            success = self._bind_components_to_portfolio_with_ids(portfolio, components, logger)
            GLOG.DEBUG(f"[BIND PORTFOLIO] _bind_components_to_portfolio_with_ids returned: {success}")
            if not success:
                self._logger.ERROR(f"[BIND PORTFOLIO] Failed to bind components for portfolio {portfolio_id}")
                return False

            # 然后绑定Portfolio到Engine，Portfolio获得context
            # 组件后续通过 _bound_portfolio 延迟查找即可获取到 run_id
            GLOG.DEBUG(f"[BIND PORTFOLIO] About to call _register_portfolio_with_engine for {portfolio_id}")
            self._register_portfolio_with_engine(engine, portfolio)
            GLOG.DEBUG(f"[BIND PORTFOLIO] _register_portfolio_with_engine completed for {portfolio_id}")

            # 调试：验证 Portfolio 绑定后的 context
            if hasattr(portfolio, '_context') and portfolio._context:
                self._logger.INFO(f"🔍 [CONTEXT CHECK] Portfolio._context.run_id = {portfolio._context.run_id}")
                self._logger.INFO(f"🔍 [CONTEXT CHECK] Portfolio._context.engine_id = {portfolio._context.engine_id}")
                # 检查 analyzers 的 run_id
                if hasattr(portfolio, '_analyzers'):
                    for name, analyzer in portfolio._analyzers.items():
                        analyzer_run_id = analyzer.run_id if hasattr(analyzer, 'run_id') else 'N/A'
                        self._logger.INFO(f"🔍 [CONTEXT CHECK] Analyzer {name}.run_id = {analyzer_run_id}")
            else:
                self._logger.WARN(f"⚠️ Portfolio has no _context after binding to engine!")

            self._logger.INFO(f"✅ Portfolio {portfolio_id} bound to engine successfully")
            return True

        except Exception as e:
            self._logger.ERROR(f"Failed to bind portfolio to engine: {e}")
            import traceback
            self._logger.ERROR(f"Traceback: {traceback.format_exc()}")
            return False

    def _bind_portfolio_to_engine(
        self, engine: BacktestEngine, portfolio_config: Dict[str, Any], components: Dict[str, Any], logger: GinkgoLogger
    ) -> bool:
        """原有的Portfolio绑定方法（保持向后兼容）"""
        try:
            portfolio_id = portfolio_config["uuid"]

            # Create portfolio instance (引擎使用自身的时间配置)
            portfolio = self._create_portfolio_instance(portfolio_config, logger)
            if portfolio is None:
                return False

            # Bind components to portfolio
            success = self._bind_components_to_portfolio(portfolio, components, logger)
            if not success:
                return False

            # Bind portfolio to engine and register events
            self._register_portfolio_with_engine(engine, portfolio)

            self._logger.DEBUG(f"Portfolio {portfolio_id} bound to engine successfully")
            return True

        except Exception as e:
            self._logger.ERROR(f"Failed to bind portfolio to engine: {e}")
            return False

    def _create_portfolio_instance(
        self, portfolio_config: Dict[str, Any], logger: GinkgoLogger
    ) -> Optional[PortfolioT1Backtest]:
        """Create a portfolio instance with proper configuration."""
        try:
            portfolio = PortfolioT1Backtest()

            portfolio.set_portfolio_name(portfolio_config["name"])
            portfolio.set_portfolio_id(portfolio_config["uuid"])

            # 🎯 关键修复：设置初始资金
            initial_capital = portfolio_config.get("initial_capital", 100000.00)
            portfolio.add_cash(Decimal(str(initial_capital)))
            logger.INFO(f"🎯 [PORTFOLIO INIT] Set initial capital: {initial_capital}")

            return portfolio

        except Exception as e:
            self._logger.ERROR(f"Failed to create portfolio instance: {e}")
            return None

    def _bind_components_to_portfolio_with_ids(
        self, portfolio: PortfolioT1Backtest, components: Dict[str, Any], logger: GinkgoLogger
    ) -> bool:
        """绑定组件到Portfolio（简化版：移除ID注入，保留动态实例化），委托到 ComponentLoader"""
        try:
            # 直接执行组件绑定逻辑，不进行ID注入
            GLOG.DEBUG(f"[BIND COMPONENTS] Calling _perform_component_binding")
            result = self._component_loader.perform_component_binding(portfolio, components, logger)
            GLOG.DEBUG(f"[BIND COMPONENTS] _perform_component_binding returned: {result}")
            return result

        except Exception as e:
            self._logger.ERROR(f"Failed to bind components with ID injection: {e}")
            import traceback
            GLOG.ERROR(f"[BIND COMPONENTS] Exception: {e}")
            import traceback; traceback.print_exc()
            return False

    def _bind_components_to_portfolio(
        self, portfolio: PortfolioT1Backtest, components: Dict[str, Any], logger: GinkgoLogger
    ) -> bool:
        """原有的组件绑定方法（保持向后兼容），委托到 ComponentLoader"""
        return self._component_loader.perform_component_binding(portfolio, components, logger)

    def _register_portfolio_with_engine(self, engine: BacktestEngine, portfolio: PortfolioT1Backtest):
        """Register the configured portfolio with the engine and bind event handlers."""
        # 首先注入事件回注接口，便于组合在绑定前也能回注（保持一致性）
        if hasattr(portfolio, "set_event_publisher"):
            portfolio.set_event_publisher(engine.put)
        # Bind portfolio to engine
        engine.add_portfolio(portfolio)

        # Portfolio事件已在add_portfolio中自动注册，这里只注册额外的事件
        # 手动注册未在auto_register中包含的 Portfolio 特有事件
        engine.register(EVENT_TYPES.ORDERFILLED, portfolio.on_order_filled)
        engine.register(EVENT_TYPES.ORDERCANCELACK, portfolio.on_order_cancel_ack)
        # ORDERACK is handled by Router auto-registration to avoid duplicate processing
        # ORDERREJECTED 和 ORDEREXPIRED 等 Portfolio 特有事件
        engine.register(EVENT_TYPES.ORDERREJECTED, portfolio.on_order_rejected)
        engine.register(EVENT_TYPES.ORDEREXPIRED, portfolio.on_order_expired)
