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
from ginkgo.trading.routing import Router
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

        # 支持的引擎类型映射
        self._engine_type_mapping = {
            "historic": "TimeControlledEventEngine",
            "backtest": "TimeControlledEventEngine",  # 别名
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
            )

            if engine is None:
                return ServiceResult(success=False, error=f"Failed to assemble engine {engine_id}")

            # 清理历史记录（仅当从数据服务获取时）
            if engine_id and portfolio_configs:
                self._cleanup_historic_records(engine_id, portfolio_configs)

            self._logger.INFO(f"Engine {engine_id or 'config_engine'} assembly completed successfully")
            result = ServiceResult(success=True)
            result.data = engine
            return result

        except Exception as e:
            self._logger.ERROR(f"Failed to assemble backtest engine {engine_id}: {e}")
            return ServiceResult(success=False, error=f"Engine assembly failed: {str(e)}")

    def _prepare_engine_data(self, engine_id: str) -> ServiceResult:
        """Prepare all data needed for engine assembly (重构后的版本)."""
        try:
            engine_data = self._fetch_engine_config(engine_id)

            # Get portfolio mappings
            portfolio_result = self._engine_service.get_portfolios(engine_id=engine_id)
            if not portfolio_result.success or not portfolio_result.data:
                return ServiceResult(success=False, error=f"No portfolios found for engine {engine_id}")

            portfolio_mappings = portfolio_result.data
            # portfolio_mappings is already a dict, no need to check shape
            if not portfolio_mappings:
                return ServiceResult(success=False, error=f"No portfolios found for engine {engine_id}")

            # Extract the actual mappings from the response
            if isinstance(portfolio_mappings, dict) and "mappings" in portfolio_mappings:
                portfolio_mapping_list = portfolio_mappings["mappings"]
            else:
                portfolio_mapping_list = portfolio_mappings

            # Get portfolio configurations and components
            portfolio_configs = {}
            portfolio_components = {}

            for mapping in portfolio_mapping_list:
                portfolio_id = mapping.portfolio_id

                # Get portfolio configuration
                portfolio_result = self._portfolio_service.get(portfolio_id=portfolio_id)
                if not portfolio_result.success or not portfolio_result.data:
                    self._logger.WARN(f"No portfolio found for id: {portfolio_id}")
                    continue

                # Convert to DataFrame if needed
                if hasattr(portfolio_result.data, "to_dataframe"):
                    portfolio_df = portfolio_result.data.to_dataframe()
                else:
                    portfolio_df = portfolio_result.data

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
                "portfolio_components": portfolio_components,
            }
            return result

        except Exception as e:
            return ServiceResult(success=False, error=f"Failed to prepare engine data: {str(e)}")

    def _get_portfolio_components(self, portfolio_id: str) -> Optional[dict]:
        """Get all components for a portfolio."""
        try:
            components = {}

            # Use container to get portfolio_file_mapping CRUD directly
            from ginkgo.data.containers import container
            portfolio_file_mapping_crud = container.cruds.portfolio_file_mapping()
            file_mappings = portfolio_file_mapping_crud.find(filters={"portfolio_id": portfolio_id})
            if not file_mappings or len(file_mappings) == 0:
                self._logger.WARN(f"No file mappings found for portfolio {portfolio_id}")
                return {"strategies": [], "selectors": [], "sizers": [], "risk_managers": [], "analyzers": []}

            # Group by file type
            strategies = []
            selectors = []
            sizers = []
            risk_managers = []
            analyzers = []

            for mapping in file_mappings:
                # 使用正确的type属性，而不是file_type
                if hasattr(mapping, "type"):
                    file_type = mapping.type
                    if file_type == 6:  # STRATEGY
                        strategies.append(mapping)
                    elif file_type == 4:  # SELECTOR
                        selectors.append(mapping)
                    elif file_type == 5:  # SIZER
                        sizers.append(mapping)
                    elif file_type == 7:  # RISK_MANAGER
                        risk_managers.append(mapping)
                    elif file_type == 1:  # ANALYZER (FILE_TYPES.ANALYZER = 1)
                        analyzers.append(mapping)
                    else:
                        self._logger.WARN(f"Unknown file type: {file_type} for mapping {getattr(mapping, 'name', 'UNKNOWN')}")
                else:
                    self._logger.WARN(f"Mapping {mapping.name} has no type attribute")

            components["strategies"] = strategies
            components["selectors"] = selectors
            components["sizers"] = sizers
            components["risk_managers"] = risk_managers
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

    # ========== 重构后的辅助方法 ==========

    def _fetch_engine_config(self, engine_id: str) -> dict:
        """获取引擎配置数据 (重构后的辅助方法)"""
        engine_result = self._engine_service.get(engine_id=engine_id)
        if not engine_result.success or not engine_result.data:
            raise ValueError(f"No engine found for id: {engine_id}")

        # Convert to DataFrame if needed
        if hasattr(engine_result.data, "to_dataframe"):
            engine_df = engine_result.data.to_dataframe()
        else:
            engine_df = engine_result.data

        if engine_df.shape[0] == 0:
            raise ValueError(f"No engine data found for id: {engine_id}")

        return engine_df.iloc[0].to_dict()

    def _fetch_portfolio_mappings(self, engine_id: str) -> list:
        """获取引擎绑定的Portfolio映射 (重构后的辅助方法)"""
        portfolio_result = self._engine_service.get_portfolios(engine_id=engine_id)
        if not portfolio_result.success or not portfolio_result.data:
            raise ValueError(f"No portfolios found for engine {engine_id}")

        portfolio_mappings = portfolio_result.data
        if not portfolio_mappings:
            raise ValueError(f"No portfolio mappings found for engine {engine_id}")

        # Extract the actual mappings from the response
        if isinstance(portfolio_mappings, dict) and "mappings" in portfolio_mappings:
            return portfolio_mappings["mappings"]
        else:
            return portfolio_mappings

    def _build_portfolio_configs(self, portfolio_mapping_list: list) -> tuple:
        """构建Portfolio配置和组件字典 (重构后的辅助方法)"""
        portfolio_configs = {}
        portfolio_components = {}

        for mapping in portfolio_mapping_list:
            portfolio_id = mapping.portfolio_id

            try:
                portfolio_config = self._get_portfolio_config_refactored(portfolio_id)
                portfolio_configs[portfolio_id] = portfolio_config

                components = self._get_portfolio_components(portfolio_id)
                if components:
                    portfolio_components[portfolio_id] = components

            except Exception as e:
                self._logger.WARN(f"Failed to process portfolio {portfolio_id}: {e}")
                continue

        return portfolio_configs, portfolio_components

    def _get_portfolio_config_refactored(self, portfolio_id: str) -> dict:
        """获取Portfolio配置 (重构后的辅助方法)"""
        portfolio_result = self._portfolio_service.get(portfolio_id=portfolio_id)
        if not portfolio_result.success or not portfolio_result.data:
            raise ValueError(f"No portfolio found for id: {portfolio_id}")

        # Convert to DataFrame if needed
        if hasattr(portfolio_result.data, "to_dataframe"):
            portfolio_df = portfolio_result.data.to_dataframe()
        else:
            portfolio_df = portfolio_result.data

        if portfolio_df.shape[0] == 0:
            raise ValueError(f"No portfolio data found for id: {portfolio_id}")

        return portfolio_df.iloc[0].to_dict()

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
                return ServiceResult(success=False, error=f"Configuration file not found: {config_path}")

            # 加载YAML配置文件
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            self._logger.INFO(f"Configuration loaded from YAML: {config_path}")

            return self.create_engine_from_config(config)

        except Exception as e:
            self._logger.ERROR(f"Failed to create engine from YAML {config_path}: {e}")
            return ServiceResult(success=False, error=f"Failed to create engine from YAML: {str(e)}")

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
                return ServiceResult(success=False, error=f"Failed to create base engine for type: {engine_type}")

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
            return ServiceResult(success=False, error=f"Engine creation failed: {str(e)}")

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
            start_date = None
            end_date = None
            if "start_date" in config:
                start_date = self._parse_date(config["start_date"])
            if "end_date" in config:
                end_date = self._parse_date(config["end_date"])

            # 对于TimeControlledEventEngine，统一设置时间范围
            from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
            if isinstance(engine, TimeControlledEventEngine):
                engine.set_time_range(start_date, end_date)

            self._logger.DEBUG(f"✅ Created base engine: {engine.__class__.__name__}")
            return engine

        except Exception as e:
            self._logger.ERROR(f"Failed to create base engine: {e}")
            return None

    # ========== 核心装配逻辑方法（迁移自 engine_assembler_factory.py） ==========

    def _perform_backtest_engine_assembly(
        self,
        engine_id: str,
        engine_data: Dict[str, Any],
        portfolio_mappings: List[Dict[str, Any]],
        portfolio_configs: Dict[str, Dict[str, Any]],
        portfolio_components: Dict[str, Dict[str, Any]],
        logger: GinkgoLogger,
    ) -> Optional[BaseEngine]:
        """
        执行回测引擎装配的核心逻辑（来自原 assembler_backtest_engine）
        增加了统一的ID注入机制
        """
        # 设置装配上下文
        self._current_engine_id = engine_id
        self._current_run_id = engine_data.get("run_id", engine_id)

        try:
            self._logger.INFO(
                f"🔧 Starting engine assembly with context: engine_id={self._current_engine_id}, run_id={self._current_run_id}"
            )

            # Create base engine
            engine = self._create_base_engine(engine_data, engine_id, logger)
            if engine is None:
                return None

            # 监控：创建引擎后的状态
            self._logger.INFO(f"🔍 [STATE] After create_base_engine: {engine.status} (state: {engine.state})")

            # Setup basic engine infrastructure (router only, not feeder yet)
            self._setup_engine_infrastructure(engine, logger, engine_data, skip_feeder=True)

            # 监控：设置基础设施后的状态
            self._logger.INFO(f"🔍 [STATE] After setup_engine_infrastructure: {engine.status} (state: {engine.state})")

            # Process all portfolios with ID injection
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

            # 监控：portfolio绑定后的状态
            self._logger.INFO(f"🔍 [STATE] After portfolio binding: {engine.status} (state: {engine.state})")

            # Setup data feeder AFTER all portfolios are bound (matching Example order)
            self._setup_data_feeder_for_engine(engine, logger)

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

    def _create_base_engine(
        self, engine_data: Dict[str, Any], engine_id: str, logger: GinkgoLogger
    ) -> Optional[Any]:
        """Create and configure the base historic engine."""
        try:
            # 默认使用TimeControlledEventEngine，它支持时间控制
            from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
            from ginkgo.enums import EXECUTION_MODE

            engine = TimeControlledEventEngine(
                name=engine_data["name"],
                mode=EXECUTION_MODE.BACKTEST,
                timer_interval=0.01  # 与示例保持一致，提高性能
            )
            engine.set_engine_id(engine_id)
            engine.add_logger(logger)

            # 设置时间范围 - 使用引擎数据库中的时间配置
            if "backtest_start_date" in engine_data and "backtest_end_date" in engine_data:
                from ginkgo.libs import datetime_normalize

                start_date = datetime_normalize(engine_data["backtest_start_date"])
                end_date = datetime_normalize(engine_data["backtest_end_date"])

                engine.set_time_range(start_date, end_date)
                self._logger.INFO(f"📅 Set engine time range: {start_date} to {end_date}")
            else:
                self._logger.WARN("⚠️ No time range found in engine data")

            self._logger.DEBUG(f"Created base engine: {engine_data['name']} ({type(engine).__name__})")
            return engine

        except Exception as e:
            self._logger.ERROR(f"Failed to create base engine: {e}")
            return None

    def _setup_data_feeder_for_engine(self, engine: Any, logger: GinkgoLogger) -> bool:
        """Setup data feeder after all portfolios are bound (matching Example order)"""
        try:
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

            self._logger.DEBUG("✅ Data feeder setup completed after portfolio binding")
            return True
        except Exception as e:
            self._logger.ERROR(f"Failed to setup data feeder: {e}")
            return False

    def _setup_engine_infrastructure(
        self, engine: Any, logger: GinkgoLogger, engine_data: Dict[str, Any] = None, skip_feeder: bool = False
    ) -> bool:
        """Set up matchmaking and data feeding for the engine."""
        try:
            # 📝 修复事件处理顺序：先添加Portfolio，后添加Router，与Example保持一致
            # 将在后面Portfolio添加完成后再绑定Router

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

            # Set up router and broker (restored original binding logic)
            from ginkgo.trading.routing.router import Router
            broker = self._create_broker_from_config(engine_data or {})
            router = Router(brokers=[broker])
            engine.bind_router(router)
            # 明确注入事件回注接口，匹配 set_event_publisher 约定
            if hasattr(router, "set_event_publisher"):
                router.set_event_publisher(engine.put)

            self._logger.DEBUG("Engine infrastructure setup completed")
            return True

        except Exception as e:
            self._logger.ERROR(f"Failed to setup engine infrastructure: {e}")
            return False

    def _create_broker_from_config(self, engine_data: Dict[str, Any]):
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
        if mode in ("backtest", "simulation", "sim"):
            # 🔧 修复：SimBroker需要关键字参数而不是config字典
            return SimBroker(**cfg)
        if mode in ("okx", "okx_live", "live") and OkxBroker is not None:
            return OkxBroker(cfg)
        # Fallback to SimBroker
        return SimBroker(**cfg)

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

            # 为所有组件注入ID，然后绑定到Portfolio
            success = self._bind_components_to_portfolio_with_ids(portfolio, components, logger)
            if not success:
                return False

            # Bind portfolio to engine and register events
            self._logger.DEBUG(f"About to call _register_portfolio_with_engine with portfolio {portfolio_id}")
            self._register_portfolio_with_engine(engine, portfolio)

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
            portfolio.add_logger(logger)
            portfolio.set_portfolio_name(portfolio_config["name"])
            portfolio.set_portfolio_id(portfolio_config["uuid"])

            # 🎯 关键修复：设置初始资金
            initial_capital = portfolio_config.get("initial_capital", 100000.00)
            from decimal import Decimal
            portfolio.add_cash(Decimal(str(initial_capital)))
            logger.INFO(f"🎯 [PORTFOLIO INIT] Set initial capital: {initial_capital}")

            return portfolio

        except Exception as e:
            self._logger.ERROR(f"Failed to create portfolio instance: {e}")
            return None

    def _bind_components_to_portfolio_with_ids(
        self, portfolio: PortfolioT1Backtest, components: Dict[str, Any], logger: GinkgoLogger
    ) -> bool:
        """绑定组件到Portfolio（简化版：移除ID注入，保留动态实例化）"""
        try:
            # 直接执行组件绑定逻辑，不进行ID注入
            return self._perform_component_binding(portfolio, components, logger)

        except Exception as e:
            self._logger.ERROR(f"Failed to bind components with ID injection: {e}")
            return False

    def _perform_component_binding(
        self, portfolio: PortfolioT1Backtest, components: Dict[str, Any], logger: GinkgoLogger
    ) -> bool:
        """执行组件绑定和实例化"""
        try:
            portfolio_id = getattr(portfolio, "uuid", getattr(portfolio, "_portfolio_id", "unknown"))

            # 记录组件信息
            strategies = components.get("strategies", [])
            selectors = components.get("selectors", [])
            sizers = components.get("sizers", [])
            risk_managers = components.get("risk_managers", [])
            analyzers = components.get("analyzers", [])

            self._logger.INFO(f"Portfolio {portfolio_id} component summary:")
            self._logger.INFO(f"  Strategies: {len(strategies)}")
            self._logger.INFO(f"  Selectors: {len(selectors)}")
            self._logger.INFO(f"  Sizers: {len(sizers)}")
            self._logger.INFO(f"  Risk managers: {len(risk_managers)}")
            self._logger.INFO(f"  Analyzers: {len(analyzers)}")

            def _instantiate_component_from_file(file_id: str, component_type: int, mapping_uuid: str):
                """从文件内容实例化组件"""
                try:
                    # 获取文件内容
                    self._logger.DEBUG(f"Attempting to load component from file_id: {file_id}")
                    file_result = self._file_service.get_by_uuid(file_id)
                    if not file_result.success or not file_result.data:
                        return None, f"Failed to get file content: {file_result.error}"

                    file_info = file_result.data
                    if isinstance(file_info, dict) and "file" in file_info:
                        mfile = file_info["file"]
                        if hasattr(mfile, "data") and mfile.data:
                            if isinstance(mfile.data, bytes):
                                code_content = mfile.data.decode("utf-8", errors="ignore")
                            else:
                                code_content = str(mfile.data)
                        else:
                            # Fallback: 如果数据库中没有策略文件，尝试直接从源码导入
                            component_name = mapping_info.get('component_name', '').lower()
                            if 'random_signal_strategy' in component_name:
                                self._logger.INFO(f"🔧 [FALLBACK] Using source code for RandomSignalStrategy")
                                from ginkgo.trading.strategies.random_signal_strategy import RandomSignalStrategy
                                return RandomSignalStrategy, "Used source code fallback for RandomSignalStrategy"
                            return None, "No file data found"
                    else:
                        return None, "Invalid file data structure"

                    # 获取组件参数（按索引顺序）
                    from ginkgo.data.containers import container

                    param_crud = container.cruds.param()
                    # 🔍 调试：添加详细的参数查询日志
                    self._logger.INFO(f"🔍 [PARAM QUERY] Querying params for mapping_id: {mapping_uuid}")
                    param_records = param_crud.find(filters={"mapping_id": mapping_uuid})
                    component_params = []
                    if param_records:
                        # 按index排序
                        sorted_params = sorted(param_records, key=lambda p: p.index)
                        component_params = [param.value for param in sorted_params]
                        param_details = [(p.index, p.value) for p in sorted_params]
                        self._logger.INFO(f"✅ [PARAM QUERY] Found {len(component_params)} params: {param_details}")
                    else:
                        self._logger.WARNING(f"❌ [PARAM QUERY] No params found for mapping_id: {mapping_uuid}")
                        # 尝试查询所有参数来调试
                        all_params = param_crud.find()
                        if all_params:
                            self._logger.WARNING(f"🔍 [DEBUG] Total params in database: {len(all_params)}")
                            # 显示前5个参数的mapping_id
                            for i, param in enumerate(all_params[:5]):
                                self._logger.WARNING(f"🔍 [DEBUG] Param {i+1}: mapping_id={param.mapping_id}, index={param.index}, value={param.value}")

                    # 动态执行代码来获取组件类
                    import importlib.util
                    import tempfile
                    import os

                    # 创建临时文件
                    self._logger.DEBUG(f"Creating temp file for component code (length: {len(code_content)})")
                    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as temp_file:
                        temp_file.write(code_content)
                        temp_file_path = temp_file.name

                    self._logger.DEBUG(f"Temp file created: {temp_file_path}")

                    try:
                        # 为兼容性添加get_bars函数到模块的全局命名空间
                        import sys
                        from ginkgo.data.containers import container as data_container

                        def get_bars_stub(*args, **kwargs):
                            """兼容性存根，提供bar_service().get()"""
                            bar_service = data_container.bar_service()
                            return bar_service.get(*args, **kwargs)

                        sys.modules["ginkgo.data"] = type(sys)("ginkgo.data")
                        sys.modules["ginkgo.data"].get_bars = get_bars_stub

                        # 动态导入模块
                        self._logger.DEBUG(f"Importing module from {temp_file_path}")
                        spec = importlib.util.spec_from_file_location("dynamic_component", temp_file_path)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        self._logger.DEBUG(f"Module imported successfully")

                        # 查找组件类
                        self._logger.DEBUG("Starting component class detection")
                        component_class = None
                        all_classes = []
                        for attr_name in dir(module):
                            if attr_name.startswith("_"):
                                continue
                            attr = getattr(module, attr_name)
                            if isinstance(attr, type) and hasattr(attr, "__bases__"):
                                all_classes.append(attr_name)
                                # 检查是否是组件类（更宽松的检测逻辑）
                                is_component = False

                                # 方法1：检查__abstract__属性（原有逻辑）
                                if hasattr(attr, "__abstract__") and not getattr(attr, "__abstract__", True):
                                    is_component = True

                                # 方法2：检查基类名称（更宽松的检测）
                                for base in attr.__bases__:
                                    if hasattr(base, "__name__"):
                                        base_name = base.__name__
                                        if (
                                            base_name.endswith("Strategy")
                                            or base_name.endswith("Selector")
                                            or base_name.endswith("SelectorBase")
                                            or base_name.endswith("Sizer")
                                            or base_name.endswith("RiskManagement")
                                            or base_name.endswith("Analyzer")
                                            or base_name == "BaseStrategy"
                                            or base_name == "BaseSelector"
                                            or base_name == "BaseSizer"
                                            or base_name == "BaseRiskManagement"
                                            or base_name == "BaseAnalyzer"
                                        ):
                                            is_component = True
                                            break

                                # 方法3：检查类名本身
                                if (
                                    attr_name.endswith("Strategy")
                                    or attr_name.endswith("Selector")
                                    or attr_name.endswith("Sizer")
                                    or attr_name.endswith("RiskManagement")
                                    or attr_name.endswith("Analyzer")
                                ) and attr_name not in ["BaseStrategy", "BaseSelector", "BaseSizer", "BaseRiskManagement", "BaseAnalyzer"]:
                                    is_component = True

                                if is_component:
                                    component_class = attr
                                    self._logger.DEBUG(f"Found component class: {attr.__name__}")
                                    break

                        self._logger.DEBUG(f"Component detection completed. Found classes: {all_classes}")
                        if component_class is None:
                            # 调试信息：列出模块中所有的类
                            class_names = [name for name in dir(module) if not name.startswith("_") and isinstance(getattr(module, name), type)]
                            class_details = []
                            for name in class_names:
                                cls = getattr(module, name)
                                bases = [base.__name__ for base in cls.__bases__ if hasattr(base, "__name__")]
                                abstract_info = f"abstract={getattr(cls, '__abstract__', 'NOT_FOUND')}"
                                class_details.append(f"{name}(bases={bases}, {abstract_info})")
                            self._logger.ERROR(f"No component class found in file. Available classes: {class_details}")
                            return None, f"No component class found in file. Available classes: {class_details}"

                        # 实例化组件（使用位置参数，提供默认值fallback）
                        if component_params:
                            # 🔍 调试：打印组件实例化信息
                            print(f"🔍 [COMPONENT INSTANTIATION] Creating {component_class.__name__} with params: {component_params}")
                            component = component_class(*component_params)
                            print(f"🔍 [COMPONENT INSTANTIATION] Component created: {type(component).__name__}")
                            # 如果是RandomSignalStrategy，设置固定随机种子以确保可重现性
                            if "RandomSignalStrategy" in component_class.__name__:
                                print(f"🔍 [COMPONENT INSTANTIATION] Setting random_seed=12345 for RandomSignalStrategy")
                                component.set_random_seed(12345)
                                # 🔍 强制打印策略配置信息进行对比
                                print(f"🔍 [STRATEGY DEBUG] Dynamic Assembly Strategy Config:")
                                print(f"   - buy_probability: {component.buy_probability}")
                                print(f"   - sell_probability: {component.sell_probability}")
                                print(f"   - max_signals: {component.max_signals}")
                                print(f"   - random_seed: {component.random_seed}")
                                print(f"   - name: {component.name}")
                        else:
                            # 提供默认参数fallback
                            if "Selector" in component_class.__name__:
                                # FixedSelector默认参数: name, codes (使用多个股票)
                                component = component_class("default_selector", ["000001.SZ", "000002.SZ"])
                            elif "Sizer" in component_class.__name__:
                                # FixedSizer默认参数: volume
                                component = component_class(1000)
                            elif "Strategy" in component_class.__name__:
                                # RandomSignalStrategy参数: buy_probability, sell_probability, signal_reason_template, max_signals
                                if "RandomSignalStrategy" in component_class.__name__:
                                    component = component_class(
                                        buy_probability=0.9, sell_probability=0.05, max_signals=4
                                    )
                                else:
                                    # 其他策略使用name参数作为默认
                                    component = component_class("RandomStrategy")
                            else:
                                component = component_class()

                        return component, None

                    finally:
                        # 清理临时文件
                        try:
                            os.unlink(temp_file_path)
                        except:
                            pass

                except Exception as e:
                    return None, f"Failed to instantiate component: {str(e)}"

            # Add strategies (required)
            strategies = components.get("strategies", [])
            if len(strategies) == 0:
                self._logger.CRITICAL(f"No strategy found for portfolio {portfolio_id}")
                return False

            for strategy_mapping in strategies:
                strategy, error = _instantiate_component_from_file(
                    strategy_mapping.file_id, strategy_mapping.type, strategy_mapping.uuid
                )
                if strategy is None:
                    self._logger.ERROR(f"Failed to instantiate strategy: {error}")
                    return False

                strategy.add_logger(logger)
                portfolio.add_strategy(strategy)
                self._logger.DEBUG(f"✅ Added strategy: {strategy.__class__.__name__}")

            # Add selector (required)
            selectors = components.get("selectors", [])
            if len(selectors) == 0:
                self._logger.ERROR(f"No selector found for portfolio {portfolio_id}")
                return False
            selector_mapping = selectors[0]
            selector, error = _instantiate_component_from_file(
                selector_mapping.file_id, selector_mapping.type, selector_mapping.uuid
            )
            if selector is None:
                self._logger.ERROR(f"Failed to instantiate selector: {error}")
                return False

            selector.add_logger(logger)
            portfolio.bind_selector(selector)
            self._logger.DEBUG(f"✅ Bound selector: {selector.__class__.__name__}")

            # Selector的兴趣集应该通过Portfolio自动传播到DataFeeder
            if hasattr(selector, '_interested') and len(selector._interested) > 0:
                self._logger.INFO(f"📅 Selector interested codes: {selector._interested}")
            else:
                self._logger.WARN("Selector has no interested codes or _interested attribute")

            # Add sizer (required)
            sizers = components.get("sizers", [])
            if len(sizers) == 0:
                self._logger.ERROR(f"No sizer found for portfolio {portfolio_id}")
                return False
            sizer_mapping = sizers[0]
            sizer, error = _instantiate_component_from_file(
                sizer_mapping.file_id, sizer_mapping.type, sizer_mapping.uuid
            )
            if sizer is None:
                self._logger.ERROR(f"Failed to instantiate sizer: {error}")
                return False

            sizer.add_logger(logger)
            portfolio.bind_sizer(sizer)
            self._logger.DEBUG(f"✅ Bound sizer: {sizer.__class__.__name__}")

            # Add risk managers (optional)
            risk_managers = components.get("risk_managers", [])
            if len(risk_managers) == 0:
                self._logger.WARN(
                    f"No risk manager found for portfolio {portfolio_id}. Backtest will go on without risk control."
                )
            else:
                for risk_manager_mapping in risk_managers:
                    risk_manager, error = _instantiate_component_from_file(
                        risk_manager_mapping.file_id, risk_manager_mapping.type, risk_manager_mapping.uuid
                    )
                    if risk_manager is None:
                        self._logger.ERROR(f"Failed to instantiate risk manager: {error}")
                        continue

                    risk_manager.add_logger(logger)
                    portfolio.add_risk_manager(risk_manager)
                    self._logger.DEBUG(f"✅ Added risk manager: {risk_manager.__class__.__name__}")

            # Add analyzers (optional)
            analyzers = components.get("analyzers", [])
            if len(analyzers) == 0:
                self._logger.WARN(f"No analyzer found for portfolio {portfolio_id}. Backtest will go on without analysis.")
            else:
                for analyzer_mapping in analyzers:
                    analyzer, error = _instantiate_component_from_file(
                        analyzer_mapping.file_id, analyzer_mapping.type, analyzer_mapping.uuid
                    )
                    if analyzer is None:
                        self._logger.ERROR(f"Failed to instantiate analyzer: {error}")
                        continue  # Continue with other analyzers instead of failing completely

                    analyzer.add_logger(logger)
                    portfolio.add_analyzer(analyzer)
                    self._logger.DEBUG(f"✅ Added analyzer: {analyzer.__class__.__name__}")

            return True

        except Exception as e:
            self._logger.ERROR(f"Failed to perform component binding: {e}")
            return False

    def _bind_components_to_portfolio(
        self, portfolio: PortfolioT1Backtest, components: Dict[str, Any], logger: GinkgoLogger
    ) -> bool:
        """原有的组件绑定方法（保持向后兼容）"""
        return self._perform_component_binding(portfolio, components, logger)

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
                    # 统一使用引擎添加接口
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
            portfolio_id = getattr(portfolio, "uuid", None)
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
                        file_type="STRATEGY",
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
                        file_type="RISKMANAGER",
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
                        file_type="ANALYZER",
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
                    "end_date": "2023-12-31",
                },
                "data_feeder": {
                    "type": "historical",
                    "settings": {"symbols": ["000001.SZ", "000002.SZ"], "preload_data": True},
                },
                "routing": {"enabled": True},
                "portfolios": [
                    {"type": "base", "name": "SamplePortfolio", "strategies": [], "risk_managers": [], "analyzers": []}
                ],
                "settings": {"log_level": "INFO", "debug": False},
            },
            "live": {
                "engine": {"type": "live", "name": "LiveEngine", "run_id": "live_sample_001"},
                "data_feeder": {"type": "live", "settings": {"symbols": ["000001.SZ"], "subscription_timeout": 30.0}},
                "routing": {"enabled": True},
                "portfolios": [{"type": "base", "name": "LivePortfolio", "strategies": [], "risk_managers": []}],
                "settings": {"log_level": "INFO", "debug": True},
            },
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

            with open(output_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True, indent=2)

            self._logger.INFO(f"✅ Sample config saved to: {output_path}")
            return ServiceResult(success=True)

        except Exception as e:
            self._logger.ERROR(f"Failed to save sample config: {e}")
            return ServiceResult(success=False, error=f"Failed to save sample config: {str(e)}")

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
