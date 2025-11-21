"""
Engine Assembly Service

This service handles the assembly and configuration of backtest engines,
replacing the direct function calls in engine_assembler_factory.py with
a proper service-oriented approach using dependency injection.
"""

from typing import Optional, Dict, Any, List, Union
import datetime
import yaml
import uuid
from pathlib import Path
from datetime import date

from ginkgo.libs import GLOG, GinkgoLogger, datetime_normalize
from ginkgo.enums import FILE_TYPES, EVENT_TYPES, ENGINESTATUS_TYPES
from ginkgo.trading.engines import BaseEngine, BacktestEngine
from ginkgo.trading.routing import BrokerMatchMaking
from ginkgo.trading.feeders import BacktestFeeder
from ginkgo.trading.brokers.sim_broker import SimBroker
try:
    from ginkgo.trading.brokers.okx_broker import OKXBroker as OkxBroker
except Exception:
    OkxBroker = None  # Optional dependency
from ginkgo.trading.portfolios import PortfolioT1Backtest
from ginkgo.trading.time.clock import now as clock_now

# Import data services through dependency injection instead of direct container access
from ginkgo.data.services.base_service import BaseService, ServiceResult


class EngineConfigurationError(Exception):
    """引擎配置错误"""
    pass


class EngineAssemblyService(BaseService):
    """
    统一引擎装配服务
    
    此服务整合了所有引擎装配功能，包括：
    - 程序化装配（来自原 engine_assembler_factory）
    - YAML配置驱动装配（来自原 engine_factory）
    - 统一的服务化接口和依赖注入管理
    """
    
    def __init__(self, engine_service=None, portfolio_service=None, component_service=None,
                 analyzer_record_crud=None, config_manager=None):
        """
        Initialize the unified engine assembly service.

        Args:
            engine_service: Service for engine data operations
            portfolio_service: Service for portfolio data operations
            component_service: Service for component management operations
            analyzer_record_crud: CRUD service for analyzer record cleanup
            config_manager: Configuration manager for YAML processing
        """
        super().__init__()
        self._engine_service = engine_service
        self._portfolio_service = portfolio_service
        self._component_service = component_service
        self._analyzer_record_crud = analyzer_record_crud
        self._logger = GLOG

        # 装配上下文 - 用于ID注入
        self._current_engine_id = None
        self._current_run_id = None

        # 配置管理器已统一使用GCONF
        self.config_manager = config_manager
        
        # 支持的引擎类型映射
        self._engine_type_mapping = {
            "historic": "BacktestEngine", 
            "backtest": "BacktestEngine",  # 别名
            "live": "LiveEngine",
            "realtime": "LiveEngine",  # 别名
            "time_controlled": "TimeControlledEventEngine",
            "time_based": "TimeControlledEventEngine",  # 别名
        }
        
        # 延迟初始化的组件
        self._component_factory = None
        self._routing_center = None

    def _get_current_engine_id(self) -> str:
        """获取当前装配上下文中的引擎ID"""
        return self._current_engine_id or ""

    def _get_current_run_id(self) -> str:
        """获取当前装配上下文中的运行ID"""
        return self._current_run_id or ""

    def _inject_ids_to_components(self, components: Dict[str, Any], engine_id: str,
                                 portfolio_id: str, run_id: str) -> None:
        """统一为所有组件注入运行时ID"""
        injected_count = 0
        total_count = 0

        for component_type, component_list in components.items():
            for component in component_list:
                total_count += 1
                if hasattr(component, 'set_backtest_ids'):
                    component.set_backtest_ids(
                        engine_id=engine_id,
                        portfolio_id=portfolio_id,
                        run_id=run_id
                    )
                    injected_count += 1
                    self._logger.DEBUG(f"✅ Injected IDs to {component_type}: {component.__class__.__name__}")
                else:
                    self._logger.WARN(f"⚠️ Component {component.__class__.__name__} doesn't support ID injection")

        self._logger.INFO(f"ID injection completed: {injected_count}/{total_count} components updated")

    def _inject_ids_to_single_component(self, component: Any, engine_id: str,
                                       portfolio_id: str, run_id: str) -> bool:
        """为单个组件注入运行时ID"""
        if hasattr(component, 'set_backtest_ids'):
            component.set_backtest_ids(
                engine_id=engine_id,
                portfolio_id=portfolio_id,
                run_id=run_id
            )
            self._logger.DEBUG(f"✅ Injected IDs to component: {component.__class__.__name__}")
            return True
        else:
            self._logger.WARN(f"⚠️ Component {component.__class__.__name__} doesn't support ID injection")
            return False
    
    def initialize(self) -> bool:
        """Initialize the engine assembly service."""
        try:
            self._logger.INFO("EngineAssemblyService initialized")
            return True
        except Exception as e:
            self._logger.ERROR(f"Failed to initialize EngineAssemblyService: {e}")
            return False
    
    def assemble_backtest_engine(self, 
                                engine_id: str = None, 
                                engine_data: Dict[str, Any] = None,
                                portfolio_mappings: List[Dict[str, Any]] = None,
                                portfolio_configs: Dict[str, Dict[str, Any]] = None,
                                portfolio_components: Dict[str, Dict[str, Any]] = None,
                                logger: Optional[GinkgoLogger] = None) -> ServiceResult:
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
            
        Returns:
            ServiceResult containing the assembled engine or error information
        """
        if engine_id is None and engine_data is None:
            return ServiceResult(success=False, error="Either engine_id or engine_data must be provided")
        
        self._logger.WARN(f"Assembling backtest engine --> {engine_id or 'from_config'}")
        
        try:
            # 方式1：从数据服务准备数据
            if engine_data is None:
                preparation_result = self._prepare_engine_data(engine_id)
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
                    logger_name="engine_logger", 
                    file_names=[f"bt_{engine_id or 'config'}_{now}"], 
                    console_log=False
                )
            
            # 执行核心装配逻辑
            engine = self._perform_backtest_engine_assembly(
                engine_id=engine_id or engine_data.get("name", "config_engine"),
                engine_data=engine_data,
                portfolio_mappings=portfolio_mappings or [],
                portfolio_configs=portfolio_configs or {},
                portfolio_components=portfolio_components or {},
                logger=logger
            )
            
            if engine is None:
                return ServiceResult(
                    success=False,
                    error=f"Failed to assemble engine {engine_id}"
                )
            
            # 清理历史记录（仅当从数据服务获取时）
            if engine_id and portfolio_configs:
                self._cleanup_historic_records(engine_id, portfolio_configs)
            
            self._logger.INFO(f"Engine {engine_id or 'config_engine'} assembly completed successfully")
            result = ServiceResult(success=True)
            result.data = engine
            return result
            
        except Exception as e:
            self._logger.ERROR(f"Failed to assemble backtest engine {engine_id}: {e}")
            return ServiceResult(
                success=False,
                error=f"Engine assembly failed: {str(e)}"
            )
    
    def _prepare_engine_data(self, engine_id: str) -> ServiceResult:
        """Prepare all data needed for engine assembly."""
        try:
            # Get engine configuration
            engine_df = self._engine_service.get_engine(engine_id, as_dataframe=True)
            if engine_df.shape[0] == 0:
                return ServiceResult(
                    success=False,
                    error=f"No engine found for id: {engine_id}"
                )
            
            engine_data = engine_df.iloc[0].to_dict()
            
            # Get portfolio mappings
            portfolio_mappings = self._engine_service.get_engine_portfolio_mappings(engine_id=engine_id)
            if portfolio_mappings.shape[0] == 0:
                return ServiceResult(
                    success=False,
                    error=f"No portfolios found for engine {engine_id}"
                )
            
            # Convert DataFrame to list of dicts for easier processing
            portfolio_mapping_list = portfolio_mappings.to_dict('records')
            
            # Get portfolio configurations and components
            portfolio_configs = {}
            portfolio_components = {}
            
            for mapping in portfolio_mapping_list:
                portfolio_id = mapping["portfolio_id"]
                
                # Get portfolio configuration
                portfolio_df = self._portfolio_service.get_portfolio(portfolio_id, as_dataframe=True)
                if portfolio_df.shape[0] == 0:
                    self._logger.WARN(f"No portfolio found for id: {portfolio_id}")
                    continue
                    
                portfolio_configs[portfolio_id] = portfolio_df.iloc[0].to_dict()
                
                # Get portfolio components
                components = self._get_portfolio_components(portfolio_id)
                if components is None:
                    self._logger.WARN(f"Failed to get components for portfolio {portfolio_id}")
                    continue
                    
                portfolio_components[portfolio_id] = components
            
            result = ServiceResult(success=True)
            result.data = {
                "engine_data": engine_data,
                "portfolio_mappings": portfolio_mapping_list,
                "portfolio_configs": portfolio_configs,
                "portfolio_components": portfolio_components
            }
            return result
            
        except Exception as e:
            return ServiceResult(
                success=False,
                error=f"Failed to prepare engine data: {str(e)}"
            )
    
    def _get_portfolio_components(self, portfolio_id: str) -> Optional[dict]:
        """Get all components for a portfolio."""
        try:
            components = {}
            
            # Get strategies (required)
            strategies = self._component_service.get_strategies_by_portfolio(portfolio_id)
            components["strategies"] = strategies
            
            # Get selectors (required)
            selectors = self._component_service.get_selectors_by_portfolio(portfolio_id)
            components["selectors"] = selectors
            
            # Get sizers (required)
            sizers = self._component_service.get_sizers_by_portfolio(portfolio_id)
            components["sizers"] = sizers
            
            # Get risk managers (optional)
            risk_managers = self._component_service.get_risk_managers_by_portfolio(portfolio_id)
            components["risk_managers"] = risk_managers
            
            # Get analyzers (required)
            analyzers = self._component_service.get_analyzers_by_portfolio(portfolio_id)
            components["analyzers"] = analyzers
            
            return components
            
        except Exception as e:
            self._logger.ERROR(f"Failed to get components for portfolio {portfolio_id}: {e}")
            return None
    
    def _cleanup_historic_records(self, engine_id: str, portfolio_configs: dict):
        """Clean up historic records for all portfolios in the engine."""
        if self._analyzer_record_crud is None:
            self._logger.WARN("No analyzer record CRUD provided, skipping record cleanup")
            return
            
        try:
            for portfolio_id in portfolio_configs.keys():
                self._logger.DEBUG(f"Cleaning historic records for portfolio {portfolio_id}")
                self._analyzer_record_crud.delete_filtered(portfolio_id=portfolio_id, engine_id=engine_id)
                
        except Exception as e:
            self._logger.WARN(f"Failed to clean historic records: {e}")
            # Non-critical error, continue execution
    
    # ========== YAML配置驱动方法（迁移自 engine_factory.py） ==========
    
    def create_engine_from_yaml(self, config_path: Union[str, Path]) -> ServiceResult:
        """
        从YAML配置文件创建交易引擎
        
        Args:
            config_path: YAML配置文件路径
            
        Returns:
            ServiceResult containing the created engine or error information
        """
        try:
            config_path = Path(config_path)
            if not config_path.exists():
                return ServiceResult(
                    success=False,
                    error=f"Configuration file not found: {config_path}"
                )
            
            # 加载YAML配置文件
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            self._logger.INFO(f"Configuration loaded from YAML: {config_path}")
            
            return self.create_engine_from_config(config)
            
        except Exception as e:
            self._logger.ERROR(f"Failed to create engine from YAML {config_path}: {e}")
            return ServiceResult(
                success=False,
                error=f"Failed to create engine from YAML: {str(e)}"
            )
    
    def create_engine_from_config(self, config: Dict[str, Any]) -> ServiceResult:
        """
        从配置字典创建交易引擎
        
        Args:
            config: 引擎配置字典
            
        Returns:
            ServiceResult containing the created engine or error information
        """
        try:
            # 验证配置
            self._validate_config(config)
            working_config = config
            
            # 提取核心配置
            engine_config = working_config.get("engine", {})
            engine_type = engine_config.get("type", "historic").lower()
            run_id = engine_config.get("run_id") or str(uuid.uuid4())
            
            self._logger.INFO(f"🔧 Assembling {engine_type} engine with run_id: {run_id}")
            
            # 创建基础引擎
            engine = self._create_base_engine_from_config(engine_type, run_id, engine_config)
            if engine is None:
                return ServiceResult(
                    success=False,
                    error=f"Failed to create base engine for type: {engine_type}"
                )
            
            # 配置数据馈送器
            self._setup_data_feeder(engine, working_config.get("data_feeder", {}))
            
            # 配置路由中心
            self._setup_routing_center(engine, working_config.get("routing", {}))
            
            # 配置投资组合
            portfolios_config = working_config.get("portfolios", [])
            self._setup_portfolios(engine, portfolios_config)
            
            # 配置全局设置
            self._apply_global_settings(engine, working_config.get("settings", {}))
            
            self._logger.INFO(f"✅ Engine {engine_type} ({run_id}) created successfully")
            result = ServiceResult(success=True)
            result.data = engine
            return result
            
        except EngineConfigurationError as e:
            self._logger.ERROR(f"Configuration error: {e}")
            return ServiceResult(success=False, error=str(e))
        except Exception as e:
            self._logger.ERROR(f"Failed to create engine from config: {e}")
            return ServiceResult(
                success=False,
                error=f"Engine creation failed: {str(e)}"
            )
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """验证配置的有效性"""
        required_sections = ["engine"]
        for section in required_sections:
            if section not in config:
                raise EngineConfigurationError(f"Missing required section: {section}")
        
        engine_config = config["engine"]
        if "type" not in engine_config:
            raise EngineConfigurationError("Missing engine type")
        
        engine_type = engine_config["type"].lower()
        if engine_type not in self._engine_type_mapping:
            supported_types = list(self._engine_type_mapping.keys())
            raise EngineConfigurationError(f"Unsupported engine type: {engine_type}. Supported: {supported_types}")
    
    def _create_base_engine_from_config(self, engine_type: str, run_id: str, config: Dict[str, Any]) -> Optional[Any]:
        """创建基础引擎实例（用于YAML配置）"""
        try:
            # 延迟导入避免循环依赖
            engine_class_name = self._engine_type_mapping[engine_type]
            
            if engine_class_name == "LiveEngine":
                from ginkgo.trading.engines.live_engine import LiveEngine
                engine_class = LiveEngine
            elif engine_class_name == "TimeControlledEventEngine":
                from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
                engine_class = TimeControlledEventEngine
            else:  # BacktestEngine
                from ginkgo.trading.engines.backtest_engine import BacktestEngine
                engine_class = BacktestEngine
            
            if engine_type in ["live", "realtime"]:
                # LiveEngine需要run_id参数
                engine = engine_class(run_id=run_id)
            elif engine_type in ["time_controlled", "time_based"]:
                # TimeControlledEventEngine需要特殊处理
                name = config.get("name", "TimeControlledEngine")
                engine = engine_class(name=name)
                engine.set_run_id(run_id)
            else:
                # BacktestEngine等其他引擎
                name = config.get("name", f"{engine_type.title()}Engine")
                engine = engine_class(name=name)
                engine.set_run_id(run_id)
            
            # 设置引擎特定配置
            if "start_date" in config:
                engine.start_date = self._parse_date(config["start_date"])
            if "end_date" in config:
                engine.end_date = self._parse_date(config["end_date"])
                
            self._logger.DEBUG(f"✅ Created base engine: {engine.__class__.__name__}")
            return engine
            
        except Exception as e:
            self._logger.ERROR(f"Failed to create base engine: {e}")
            return None
    
    # ========== 核心装配逻辑方法（迁移自 engine_assembler_factory.py） ==========
    
    def _perform_backtest_engine_assembly(self,
                                         engine_id: str,
                                         engine_data: Dict[str, Any],
                                         portfolio_mappings: List[Dict[str, Any]],
                                         portfolio_configs: Dict[str, Dict[str, Any]],
                                         portfolio_components: Dict[str, Dict[str, Any]],
                                         logger: GinkgoLogger) -> Optional[BaseEngine]:
        """
        执行回测引擎装配的核心逻辑（来自原 assembler_backtest_engine）
        增加了统一的ID注入机制
        """
        # 设置装配上下文
        self._current_engine_id = engine_id
        self._current_run_id = engine_data.get('run_id', engine_id)

        try:
            self._logger.INFO(f"🔧 Starting engine assembly with context: engine_id={self._current_engine_id}, run_id={self._current_run_id}")

            # Create base engine
            engine = self._create_base_engine(engine_data, engine_id, logger)
            if engine is None:
                return None

            # Setup engine infrastructure (matchmaking, feeder)
            self._setup_engine_infrastructure(engine, logger, engine_data)

            # Process all portfolios with ID injection
            for portfolio_mapping in portfolio_mappings:
                portfolio_id = portfolio_mapping["portfolio_id"]

                if portfolio_id not in portfolio_configs:
                    self._logger.WARN(f"No configuration found for portfolio {portfolio_id}")
                    continue

                if portfolio_id not in portfolio_components:
                    self._logger.WARN(f"No components found for portfolio {portfolio_id}")
                    continue

                success = self._bind_portfolio_to_engine_with_ids(
                    engine=engine,
                    portfolio_config=portfolio_configs[portfolio_id],
                    components=portfolio_components[portfolio_id],
                    logger=logger
                )

                if not success:
                    self._logger.ERROR(f"Failed to bind portfolio {portfolio_id} to engine")
                    continue

            # Start the engine
            self._logger.INFO("✅ Starting assembled engine")
            engine.start()
            return engine

        except Exception as e:
            self._logger.ERROR(f"Failed to perform backtest engine assembly {engine_id}: {e}")
            return None
        finally:
            # 清理装配上下文
            self._current_engine_id = None
            self._current_run_id = None

    def _create_base_engine(self, engine_data: Dict[str, Any], engine_id: str, logger: GinkgoLogger) -> Optional[BacktestEngine]:
        """Create and configure the base historic engine."""
        try:
            engine = BacktestEngine(engine_data["name"])
            engine.engine_id = engine_id
            engine.add_logger(logger)
            
            self._logger.DEBUG(f"Created base engine: {engine_data['name']}")
            return engine
            
        except Exception as e:
            self._logger.ERROR(f"Failed to create base engine: {e}")
            return None

    def _setup_engine_infrastructure(self, engine: BacktestEngine, logger: GinkgoLogger, engine_data: Dict[str, Any] = None) -> bool:
        """Set up matchmaking and data feeding for the engine."""
        try:
            # Resolve broker from config (default: SimBroker for backtest)
            broker = self._create_broker_from_config(engine_data or {})
            match = Router(broker)
            engine.bind_matchmaking(match)
            # 明确注入事件回注接口，匹配 set_event_publisher 约定
            if hasattr(match, "set_event_publisher"):
                match.set_event_publisher(engine.put)
            engine.register(EVENT_TYPES.ORDERSUBMITTED, match.on_order_received)
            engine.register(EVENT_TYPES.PRICEUPDATE, match.on_price_received)
            
            # Set up data feeder
            feeder = BacktestFeeder("ExampleFeeder")
            feeder.add_logger(logger)
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
            
            self._logger.DEBUG("Engine infrastructure setup completed")
            return True
            
        except Exception as e:
            self._logger.ERROR(f"Failed to setup engine infrastructure: {e}")
            return False

    def _create_broker_from_config(self, engine_data: Dict[str, Any]):
        """Create broker instance based on engine configuration."""
        mode = (engine_data.get("broker")
                or engine_data.get("broker_mode")
                or engine_data.get("execution_mode")
                or "backtest")
        mode = str(mode).lower()
        cfg = engine_data.get("broker_config") or {}

        # Map mode to broker implementation
        if mode in ("backtest", "simulation", "sim"):
            return SimBroker(cfg)
        if mode in ("okx", "okx_live", "live") and OkxBroker is not None:
            return OkxBroker(cfg)
        # Fallback to SimBroker
        return SimBroker(cfg)

    def _bind_portfolio_to_engine_with_ids(self,
                                           engine: BacktestEngine,
                                           portfolio_config: Dict[str, Any],
                                           components: Dict[str, Any],
                                           logger: GinkgoLogger) -> bool:
        """绑定Portfolio到Engine，包含统一的ID注入机制"""
        try:
            portfolio_id = portfolio_config["uuid"]
            engine_id = self._get_current_engine_id()
            run_id = self._get_current_run_id()

            self._logger.INFO(f"🔧 Binding portfolio {portfolio_id} with ID context: engine_id={engine_id}, run_id={run_id}")

            # Update engine date range based on portfolio
            self._update_engine_date_range(engine, portfolio_config)

            # Create portfolio instance
            portfolio = self._create_portfolio_instance(portfolio_config, logger)
            if portfolio is None:
                return False

            # 为Portfolio注入ID（如果Portfolio支持BacktestBase）
            self._inject_ids_to_single_component(portfolio, engine_id, portfolio_id, run_id)

            # 为所有组件注入ID，然后绑定到Portfolio
            success = self._bind_components_to_portfolio_with_ids(portfolio, components, logger)
            if not success:
                return False

            # Bind portfolio to engine and register events
            self._register_portfolio_with_engine(engine, portfolio)

            self._logger.INFO(f"✅ Portfolio {portfolio_id} bound to engine successfully with ID injection")
            return True

        except Exception as e:
            self._logger.ERROR(f"Failed to bind portfolio to engine: {e}")
            return False

    def _bind_portfolio_to_engine(self,
                                 engine: BacktestEngine,
                                 portfolio_config: Dict[str, Any],
                                 components: Dict[str, Any],
                                 logger: GinkgoLogger) -> bool:
        """原有的Portfolio绑定方法（保持向后兼容）"""
        try:
            portfolio_id = portfolio_config["uuid"]

            # Update engine date range based on portfolio
            self._update_engine_date_range(engine, portfolio_config)

            # Create portfolio instance
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

    def _update_engine_date_range(self, engine: BacktestEngine, portfolio_config: Dict[str, Any]):
        """Update engine date range to encompass all portfolios."""
        date_start = datetime_normalize(portfolio_config["backtest_start_date"])
        date_end = datetime_normalize(portfolio_config["backtest_end_date"])
        
        if engine.start_date is None or engine.start_date > date_start:
            engine.start_date = date_start
        if engine.end_date is None or engine.end_date < date_end:
            engine.end_date = date_end

    def _create_portfolio_instance(self, portfolio_config: Dict[str, Any], logger: GinkgoLogger) -> Optional[PortfolioT1Backtest]:
        """Create a portfolio instance with proper configuration."""
        try:
            portfolio = PortfolioT1Backtest()
            portfolio.add_logger(logger)
            portfolio.set_portfolio_name(portfolio_config["name"])
            portfolio.set_portfolio_id(portfolio_config["uuid"])
            
            return portfolio
            
        except Exception as e:
            self._logger.ERROR(f"Failed to create portfolio instance: {e}")
            return None

    def _bind_components_to_portfolio_with_ids(self,
                                               portfolio: PortfolioT1Backtest,
                                               components: Dict[str, Any],
                                               logger: GinkgoLogger) -> bool:
        """绑定组件到Portfolio，包含统一的ID注入机制"""
        try:
            portfolio_id = getattr(portfolio, '_portfolio_id', getattr(portfolio, 'uuid', 'unknown'))
            engine_id = self._get_current_engine_id()
            run_id = self._get_current_run_id()

            # 统一为所有组件注入ID
            self._inject_ids_to_components(components, engine_id, portfolio_id, run_id)

            # 执行原有的组件绑定逻辑
            return self._perform_component_binding(portfolio, components, logger)

        except Exception as e:
            self._logger.ERROR(f"Failed to bind components with ID injection: {e}")
            return False

    def _perform_component_binding(self,
                                  portfolio: PortfolioT1Backtest,
                                  components: Dict[str, Any],
                                  logger: GinkgoLogger) -> bool:
        """执行实际的组件绑定逻辑"""
        try:
            portfolio_id = getattr(portfolio, 'uuid', getattr(portfolio, '_portfolio_id', 'unknown'))

            # Add strategies (required)
            strategies = components.get("strategies", [])
            if len(strategies) == 0:
                self._logger.CRITICAL(f"No strategy found for portfolio {portfolio_id}")
                return False

            for strategy in strategies:
                strategy.add_logger(logger)
                portfolio.add_strategy(strategy)
                self._logger.DEBUG(f"✅ Added strategy: {strategy.__class__.__name__}")

            # Add selector (required)
            selectors = components.get("selectors", [])
            if len(selectors) == 0:
                self._logger.ERROR(f"No selector found for portfolio {portfolio_id}")
                return False
            selector = selectors[0]
            portfolio.bind_selector(selector)
            self._logger.DEBUG(f"✅ Bound selector: {selector.__class__.__name__}")

            # Add sizer (required)
            sizers = components.get("sizers", [])
            if len(sizers) == 0:
                self._logger.ERROR(f"No sizer found for portfolio {portfolio_id}")
                return False
            sizer = sizers[0]
            sizer.add_logger(logger)
            portfolio.bind_sizer(sizer)
            self._logger.DEBUG(f"✅ Bound sizer: {sizer.__class__.__name__}")

            # Add risk managers (optional)
            risk_managers = components.get("risk_managers", [])
            if len(risk_managers) == 0:
                self._logger.WARN(f"No risk manager found for portfolio {portfolio_id}. Backtest will go on without risk control.")
            else:
                for risk_manager in risk_managers:
                    risk_manager.add_logger(logger)
                    portfolio.add_risk_manager(risk_manager)
                    self._logger.DEBUG(f"✅ Added risk manager: {risk_manager.__class__.__name__}")

            # Add analyzers (required)
            analyzers = components.get("analyzers", [])
            if len(analyzers) == 0:
                self._logger.ERROR(f"No analyzer found for portfolio {portfolio_id}")
                return False
            for analyzer in analyzers:
                analyzer.add_logger(logger)
                portfolio.add_analyzer(analyzer)
                self._logger.DEBUG(f"✅ Added analyzer: {analyzer.__class__.__name__}")

            return True

        except Exception as e:
            self._logger.ERROR(f"Failed to perform component binding: {e}")
            return False

    def _bind_components_to_portfolio(self,
                                     portfolio: PortfolioT1Backtest,
                                     components: Dict[str, Any],
                                     logger: GinkgoLogger) -> bool:
        """原有的组件绑定方法（保持向后兼容）"""
        return self._perform_component_binding(portfolio, components, logger)

    def _register_portfolio_with_engine(self, engine: BacktestEngine, portfolio: PortfolioT1Backtest):
        """Register the configured portfolio with the engine and bind event handlers."""
        # 首先注入事件回注接口，便于组合在绑定前也能回注（保持一致性）
        if hasattr(portfolio, "set_event_publisher"):
            portfolio.set_event_publisher(engine.put)
        # Bind portfolio to engine
        engine.bind_portfolio(portfolio)
        
        # Register portfolio event handlers
        engine.register(EVENT_TYPES.PRICEUPDATE, portfolio.on_price_received)
        engine.register(EVENT_TYPES.ORDERFILLED, portfolio.on_order_filled)
        engine.register(EVENT_TYPES.ORDERCANCELACK, portfolio.on_order_cancel_ack)
        engine.register(EVENT_TYPES.SIGNALGENERATION, portfolio.on_signal)
        # Lifecycle events (ACK/Partial/Reject/Expire/CancelAck)
        engine.register(EVENT_TYPES.ORDERACK, portfolio.on_order_ack)
        engine.register(EVENT_TYPES.ORDERPARTIALLYFILLED, portfolio.on_order_partially_filled)
        engine.register(EVENT_TYPES.ORDERREJECTED, portfolio.on_order_rejected)
        engine.register(EVENT_TYPES.ORDEREXPIRED, portfolio.on_order_expired)
        engine.register(EVENT_TYPES.ORDERCANCELACK, portfolio.on_order_cancel_ack)
    
    def _setup_data_feeder(self, engine: Any, feeder_config: Dict[str, Any]) -> None:
        """配置数据馈送器"""
        try:
            feeder_type = feeder_config.get("type", "historical").lower()
            
            # 映射馈送器类型
            feeder_type_mapping = {
                "backtest": "historical",
                "historical": "historical",
                "live": "live",
                "realtime": "live",
            }
            mapped_type = feeder_type_mapping.get(feeder_type, feeder_type)
            
            # 延迟获取DI容器，避免循环依赖
            try:
                from ginkgo.trading.core.containers import container
                
                # 从DI容器获取数据馈送器
                if mapped_type == "historical":
                    feeder = container.feeders.historical()
                elif mapped_type == "live":
                    feeder = container.feeders.live()
                else:
                    raise EngineConfigurationError(f"Unsupported feeder type: {feeder_type}")
            except ImportError:
                # 如果DI容器不可用，跳过数据馈送器配置
                self._logger.WARN("DI container not available, skipping data feeder setup")
                return
            
            # 配置馈送器
            if hasattr(feeder, "initialize"):
                feeder_settings = feeder_config.get("settings", {})
                feeder.initialize(feeder_settings)
            
            # 绑定到引擎（兼容多种引擎类型）
            if hasattr(engine, "set_data_feeder"):
                engine.set_data_feeder(feeder)
            elif hasattr(engine, "bind_datafeeder"):
                engine.bind_datafeeder(feeder)
            elif hasattr(engine, "bind_feeder"):
                engine.bind_feeder(feeder)
            
            self._logger.DEBUG(f"✅ Setup data feeder: {mapped_type}")
            
        except Exception as e:
            self._logger.ERROR(f"Failed to setup data feeder: {e}")
    
    def _setup_routing_center(self, engine: Any, routing_config: Dict[str, Any]) -> None:
        """配置路由中心"""
        try:
            if not routing_config:
                # 使用默认路由配置
                routing_config = {"enabled": True}
            
            if routing_config.get("enabled", True):
                # 延迟获取路由中心
                try:
                    from ginkgo.trading.core.containers import container
                    routing_center = container.routing.center()
                    
                    # 注册引擎处理器到路由中心
                    if hasattr(routing_center, "register_engine_handlers"):
                        routing_center.register_engine_handlers(engine)
                except (ImportError, AttributeError):
                    self._logger.WARN("Routing center not available, skipping setup")
                
                self._logger.DEBUG("✅ Setup routing center")
                
        except Exception as e:
            self._logger.ERROR(f"Failed to setup routing center: {e}")
    
    def _setup_portfolios(self, engine: Any, portfolios_config: List[Dict[str, Any]]) -> None:
        """配置投资组合"""
        try:
            if not portfolios_config:
                self._logger.WARN("No portfolios configured")
                return
            
            for portfolio_config in portfolios_config:
                portfolio = self._create_portfolio_from_config(portfolio_config)
                if portfolio:
                    # 统一使用引擎绑定接口
                    if hasattr(engine, "bind_portfolio"):
                        engine.bind_portfolio(portfolio)
                    elif hasattr(engine, "add_portfolio"):
                        engine.add_portfolio(portfolio)
                    self._logger.DEBUG(f"✅ Added portfolio: {portfolio.name}")
            
        except Exception as e:
            self._logger.ERROR(f"Failed to setup portfolios: {e}")
    
    def _create_portfolio_from_config(self, config: Dict[str, Any]) -> Optional[Any]:
        """从配置创建投资组合实例"""
        try:
            portfolio_type = config.get("type", "base").lower()
            name = config.get("name", f"Portfolio_{uuid.uuid4().hex[:8]}")
            
            # 延迟获取DI容器
            try:
                from ginkgo.trading.core.containers import container
                
                # 从DI容器获取投资组合
                if portfolio_type == "base":
                    portfolio = container.portfolios.base(name=name)
                else:
                    # 支持扩展其他类型的投资组合
                    portfolio = container.portfolios.base(name=name)
            except ImportError:
                self._logger.WARN("DI container not available, skipping portfolio creation")
                return None
            
            # 配置投资组合组件
            self._setup_portfolio_components_from_config(portfolio, config)
            
            return portfolio
            
        except Exception as e:
            self._logger.ERROR(f"Failed to create portfolio: {e}")
            return None
    
    def _setup_portfolio_components_from_config(self, portfolio: Any, config: Dict[str, Any]) -> None:
        """从配置设置投资组合组件"""
        try:
            portfolio_id = getattr(portfolio, 'uuid', None)
            if not portfolio_id:
                self._logger.WARN("Portfolio missing UUID, skipping component setup")
                return
            
            # 延迟初始化组件工厂
            if self._component_factory is None:
                try:
                    from ginkgo.trading.core.containers import container
                    self._component_factory = container.component_factory()
                except ImportError:
                    self._logger.WARN("Component factory not available, skipping component setup")
                    return
            
            # 配置策略
            strategies_config = config.get("strategies", [])
            for strategy_config in strategies_config:
                if "file_id" in strategy_config:
                    strategy = self._component_factory.create_component(
                        file_id=strategy_config["file_id"],
                        mapping_id=strategy_config.get("mapping_id", str(uuid.uuid4())),
                        file_type="STRATEGY"
                    )
                    if strategy:
                        portfolio.add_strategy(strategy)
            
            # 配置风险管理器
            risk_managers_config = config.get("risk_managers", [])
            for risk_config in risk_managers_config:
                if "file_id" in risk_config:
                    risk_manager = self._component_factory.create_component(
                        file_id=risk_config["file_id"],
                        mapping_id=risk_config.get("mapping_id", str(uuid.uuid4())),
                        file_type="RISKMANAGER"
                    )
                    if risk_manager:
                        portfolio.add_risk_manager(risk_manager)
            
            # 配置分析器
            analyzers_config = config.get("analyzers", [])
            for analyzer_config in analyzers_config:
                if "file_id" in analyzer_config:
                    analyzer = self._component_factory.create_component(
                        file_id=analyzer_config["file_id"],
                        mapping_id=analyzer_config.get("mapping_id", str(uuid.uuid4())),
                        file_type="ANALYZER"
                    )
                    if analyzer:
                        portfolio.add_analyzer(analyzer)
            
        except Exception as e:
            self._logger.ERROR(f"Failed to setup portfolio components: {e}")
    
    def _apply_global_settings(self, engine: Any, settings: Dict[str, Any]) -> None:
        """应用全局设置"""
        try:
            # 设置日志级别
            if "log_level" in settings:
                log_level = settings["log_level"].upper()
                if hasattr(engine, "set_log_level"):
                    engine.set_log_level(log_level)
            
            # 设置调试模式
            if "debug" in settings:
                debug_mode = settings["debug"]
                if hasattr(engine, "set_debug"):
                    engine.set_debug(debug_mode)
            
            self._logger.DEBUG("✅ Applied global settings")
            
        except Exception as e:
            self._logger.ERROR(f"Failed to apply global settings: {e}")
    
    def _parse_date(self, date_str: Union[str, date]) -> date:
        """解析日期字符串"""
        from datetime import date, datetime
        
        if isinstance(date_str, date):
            return date_str
        
        try:
            return datetime.strptime(str(date_str), "%Y-%m-%d").date()
        except ValueError:
            try:
                return datetime.strptime(str(date_str), "%Y%m%d").date()
            except ValueError:
                raise EngineConfigurationError(f"Invalid date format: {date_str}")
    
    def get_sample_config(self, engine_type: str = "historic") -> Dict[str, Any]:
        """
        获取示例配置
        
        Args:
            engine_type: 引擎类型
            
        Returns:
            示例配置字典
        """
        sample_configs = {
            "historic": {
                "engine": {
                    "type": "historic",
                    "name": "BacktestEngine",
                    "run_id": "bt_sample_001",
                    "start_date": "2023-01-01",
                    "end_date": "2023-12-31"
                },
                "data_feeder": {
                    "type": "historical",
                    "settings": {
                        "symbols": ["000001.SZ", "000002.SZ"],
                        "preload_data": True
                    }
                },
                "routing": {
                    "enabled": True
                },
                "portfolios": [
                    {
                        "type": "base",
                        "name": "SamplePortfolio",
                        "strategies": [],
                        "risk_managers": [],
                        "analyzers": []
                    }
                ],
                "settings": {
                    "log_level": "INFO",
                    "debug": False
                }
            },
            "live": {
                "engine": {
                    "type": "live",
                    "name": "LiveEngine",
                    "run_id": "live_sample_001"
                },
                "data_feeder": {
                    "type": "live",
                    "settings": {
                        "symbols": ["000001.SZ"],
                        "subscription_timeout": 30.0
                    }
                },
                "routing": {
                    "enabled": True
                },
                "portfolios": [
                    {
                        "type": "base",
                        "name": "LivePortfolio",
                        "strategies": [],
                        "risk_managers": []
                    }
                ],
                "settings": {
                    "log_level": "INFO",
                    "debug": True
                }
            }
        }
        
        return sample_configs.get(engine_type, sample_configs["historic"])
    
    def save_sample_config(self, output_path: Union[str, Path], engine_type: str = "historic") -> ServiceResult:
        """
        保存示例配置到文件
        
        Args:
            output_path: 输出文件路径
            engine_type: 引擎类型
            
        Returns:
            ServiceResult indicating success or failure
        """
        try:
            config = self.get_sample_config(engine_type)
            output_path = Path(output_path)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True, indent=2)
            
            self._logger.INFO(f"✅ Sample config saved to: {output_path}")
            return ServiceResult(success=True)
            
        except Exception as e:
            self._logger.ERROR(f"Failed to save sample config: {e}")
            return ServiceResult(
                success=False,
                error=f"Failed to save sample config: {str(e)}"
            )
    
    def get_engine_by_id(self, engine_id: str) -> ServiceResult:
        """Get engine configuration by ID."""
        try:
            engine_df = self._engine_service.get_engine(engine_id, as_dataframe=True)
            if engine_df.shape[0] == 0:
                return ServiceResult(
                    success=False,
                    error=f"No engine found for id: {engine_id}"
                )
            
            result = ServiceResult(success=True)
            result.data = engine_df.iloc[0].to_dict()
            return result
            
        except Exception as e:
            return ServiceResult(
                success=False,
                error=f"Failed to get engine: {str(e)}"
            )
    
