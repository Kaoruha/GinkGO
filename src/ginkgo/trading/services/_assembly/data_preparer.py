# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: 数据准备器，负责数据获取和 YAML 配置驱动装配


"""
DataPreparer - 数据准备器

从 engine_assembly_service.py 提取，负责：
- 从数据服务获取引擎装配所需数据
- YAML 配置文件驱动的引擎创建
- 配置验证、示例配置生成
"""

from typing import Optional, Dict, Any, List, Union
import uuid
import yaml
from pathlib import Path
from datetime import date

from ginkgo.libs import GLOG, GinkgoLogger
from ginkgo.data.services.base_service import BaseService, ServiceResult


class EngineConfigurationError(Exception):
    """引擎配置错误"""

    pass


class DataPreparer:
    """
    数据准备器

    负责从数据服务获取引擎装配所需数据，以及 YAML 配置驱动的引擎创建。
    """

    def __init__(self, engine_service=None, portfolio_service=None, file_service=None, analyzer_record_crud=None, logger=None):
        """
        初始化数据准备器

        Args:
            engine_service: 引擎数据服务
            portfolio_service: Portfolio 数据服务
            file_service: 文件服务
            analyzer_record_crud: 分析记录 CRUD（用于清理历史记录）
            logger: 日志记录器
        """
        self._engine_service = engine_service
        self._portfolio_service = portfolio_service
        self._file_service = file_service
        self._analyzer_record_crud = analyzer_record_crud
        self._logger = logger or GLOG

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

    # ========== 数据准备方法 ==========

    def prepare_engine_data(self, engine_id: str) -> ServiceResult:
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

    def cleanup_historic_records(self, engine_id: str, portfolio_configs: dict):
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
