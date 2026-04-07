# Upstream: EngineAssemblyService, TaskEngineBuilder
# Downstream: PortfolioT1Backtest, GLOG, file_service
# Role: 组件加载器，从字典配置或源码文件实例化策略/选股器/分析器等组件并绑定到Portfolio


"""
ComponentLoader - 组件加载器

从 engine_assembly_service.py 提取，负责：
- 从字典配置实例化组件（WebUI 创建的 portfolio）
- 执行组件绑定和实例化（从文件/数据库加载组件）
"""

from typing import Optional, Dict, Any
from ginkgo.libs import GLOG, GinkgoLogger
from ginkgo.trading.portfolios import PortfolioT1Backtest


class ComponentLoader:
    """
    组件加载器

    负责从配置或文件中实例化组件，并将其绑定到 Portfolio。
    包含完整的动态代码加载、fallback 机制和组件类检测逻辑。
    """

    def __init__(self, file_service=None, logger=None):
        """
        初始化组件加载器

        Args:
            file_service: 文件服务，用于获取组件源码
            logger: 日志记录器
        """
        self._file_service = file_service
        self._logger = logger or GLOG

    def instantiate_component_from_dict(
        self, component_dict: Dict[str, Any], component_type: str, logger: GinkgoLogger = None
    ):
        """从字典配置实例化组件（支持 WebUI 创建的 portfolio）

        Args:
            component_dict: 包含 uuid, name, config 的字典
            component_type: 组件类型 (strategy, selector, sizer, analyzer)
            logger: 日志记录器

        Returns:
            tuple: (component_instance, error_message)
        """
        try:
            component_uuid = component_dict.get("uuid", "")
            component_name = component_dict.get("name", "")
            component_config = component_dict.get("config", {})

            # 组件名称到类的映射
            component_registry = {
                "strategy": {
                    "random_signal_strategy": ("ginkgo.trading.strategies.random_signal_strategy", "RandomSignalStrategy"),
                    "randomsignalstrategy": ("ginkgo.trading.strategies.random_signal_strategy", "RandomSignalStrategy"),
                },
                "selector": {
                    "fixed_selector": ("ginkgo.trading.selectors.fixed_selector", "FixedSelector"),
                    "fixedselector": ("ginkgo.trading.selectors.fixed_selector", "FixedSelector"),
                    "cnall_selector": ("ginkgo.trading.selectors.cnall_selector", "CNAllSelector"),
                    "cnallselector": ("ginkgo.trading.selectors.cnall_selector", "CNAllSelector"),
                },
                "sizer": {
                    "fixed_sizer": ("ginkgo.trading.sizers.fixed_sizer", "FixedSizer"),
                    "fixedsizer": ("ginkgo.trading.sizers.fixed_sizer", "FixedSizer"),
                },
                "analyzer": {
                    "net_value": ("ginkgo.trading.analysis.analyzers.net_value", "NetValue"),
                    "netvalue": ("ginkgo.trading.analysis.analyzers.net_value", "NetValue"),
                },
            }

            # 查找组件类
            registry = component_registry.get(component_type, {})
            name_lower = component_name.lower()

            # 尝试匹配（去掉前缀如 strategy_, selector_ 等）
            for key in [name_lower, name_lower.split("_")[-1] if "_" in name_lower else name_lower]:
                if key in registry:
                    module_path, class_name = registry[key]
                    break
            else:
                return None, f"Unknown {component_type}: {component_name}"

            # 动态导入
            import importlib
            module = importlib.import_module(module_path)
            component_class = getattr(module, class_name)

            # 创建实例
            component = component_class()

            # 应用配置
            for key, value in component_config.items():
                if hasattr(component, key):
                    setattr(component, key, value)
                elif key == "codes" and hasattr(component, "set_codes"):
                    # 处理 selector 的 codes 配置
                    if isinstance(value, str):
                        value = [c.strip() for c in value.split(",") if c.strip()]
                    component.set_codes(value)
                elif key == "volume" and hasattr(component, "set_volume"):
                    component.set_volume(value)

            self._logger.INFO(f"✅ Instantiated {component_type} from dict: {class_name}")
            return component, None

        except Exception as e:
            import traceback
            return None, f"Failed to instantiate {component_type} from dict: {e}\n{traceback.format_exc()}"

    def perform_component_binding(
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

            # 🔥 优先加载 BASIC_ANALYZERS（在任何其他组件之前）
            # 这样即使其他组件加载失败，分析器也能记录数据
            self._logger.INFO(f"🔧 [ANALYZER] Loading BASIC_ANALYZERS first...")
            try:
                from ginkgo.trading.analysis.analyzers import BASIC_ANALYZERS

                GLOG.INFO(f"Loading BASIC_ANALYZERS ({len(BASIC_ANALYZERS)} analyzers)...")
                basic_loaded = 0

                for analyzer_class in BASIC_ANALYZERS:
                    try:
                        analyzer = analyzer_class()

                        portfolio.add_analyzer(analyzer)
                        basic_loaded += 1
                        GLOG.DEBUG(f"  {analyzer_class.__name__} loaded")
                    except Exception as e:
                        self._logger.ERROR(f"Failed to load {analyzer_class.__name__}: {e}")
                        GLOG.ERROR(f"  {analyzer_class.__name__} failed: {e}")

                GLOG.INFO(f"BASIC_ANALYZERS: {basic_loaded}/{len(BASIC_ANALYZERS)} loaded")
                self._logger.INFO(f"✅ [ANALYZER] BASIC_ANALYZERS: {basic_loaded}/{len(BASIC_ANALYZERS)} loaded")

            except Exception as e:
                self._logger.ERROR(f"Failed to load BASIC_ANALYZERS: {e}")
                GLOG.ERROR(f"Failed to load BASIC_ANALYZERS: {e}")

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
                        self._logger.WARN(f"❌ [PARAM QUERY] No params found for mapping_id: {mapping_uuid}")
                        # 尝试查询所有参数来调试
                        all_params = param_crud.find()
                        if all_params:
                            self._logger.WARN(f"🔍 [DEBUG] Total params in database: {len(all_params)}")
                            # 显示前5个参数的mapping_id
                            for i, param in enumerate(all_params[:5]):
                                self._logger.WARN(f"🔍 [DEBUG] Param {i+1}: mapping_id={param.mapping_id}, index={param.index}, value={param.value}")

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
                        sys.modules["ginkgo.data"].container = data_container

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

                        # 实例化组件（使用位置参数，如果无参数则尝试无参实例化）
                        try:
                            if component_params:
                                # 有参数：使用参数实例化
                                self._logger.DEBUG(f"Creating {component_class.__name__} with params: {component_params}")
                                component = component_class(*component_params)
                            else:
                                # 无参数：尝试无参实例化（允许使用默认值）
                                self._logger.INFO(f"No params found for {component_class.__name__}, attempting instantiation with defaults")
                                component = component_class()

                            self._logger.DEBUG(f"Component {type(component).__name__} created successfully")

                            # 如果是RandomSignalStrategy，设置固定随机种子以确保可重现性
                            if "RandomSignalStrategy" in component_class.__name__:
                                if hasattr(component, 'set_random_seed'):
                                    component.set_random_seed(12345)
                                    self._logger.DEBUG(f"Set random_seed=12345 for RandomSignalStrategy")

                        except TypeError as e:
                            # 无参实例化失败，说明必须有参数
                            error_msg = f"Component {component_class.__name__} requires parameters but none found: {e}"
                            self._logger.ERROR(f"🔥 [INSTANTIATION ERROR] {error_msg}")
                            return None, error_msg
                        except Exception as e:
                            error_msg = f"Unexpected error instantiating {component_class.__name__}: {e}"
                            self._logger.ERROR(f"🔥 [INSTANTIATION ERROR] {error_msg}")
                            return None, error_msg

                        return component, None

                    finally:
                        # 清理临时文件
                        try:
                            os.unlink(temp_file_path)
                        except Exception as e:
                            GLOG.ERROR(f"Failed to clean up temp file {temp_file_path}: {e}")
                            pass

                except Exception as e:
                    # 源码fallback机制：当数据库代码执行失败时，尝试从源码导入
                    error_msg = str(e)
                    self._logger.WARN(f"🔥 [DYNAMIC LOAD FAILED] {error_msg}, trying source code fallback...")

                    # 尝试从源码导入组件
                    try:
                        # 获取文件名作为组件名
                        file_result = self._file_service.get_by_uuid(file_id)
                        if file_result.success and file_result.data:
                            if isinstance(file_result.data, dict) and "file" in file_result.data:
                                file_name = file_result.data["file"].name
                            else:
                                file_name = file_result.data.name
                        else:
                            return None, f"Failed to get file info for fallback: {file_result.error}"

                        # 根据组件类型确定源码路径
                        source_import_map = {
                            6: ("ginkgo.trading.strategies", "strategies"),
                            4: ("ginkgo.trading.selectors", "selectors"),  # 修复: selectors not selector
                            5: ("ginkgo.trading.sizers", "sizers"),
                            7: ("ginkgo.trading.risk_managements", "risk_managements"),
                            1: ("ginkgo.trading.analysis.analyzers", "analyzers"),
                        }

                        if component_type not in source_import_map:
                            return None, f"No source fallback for component type {component_type}"

                        module_path, subpackage = source_import_map[component_type]

                        # 将文件名转换为模块名（去掉后缀，转为小写，替换-为_）
                        module_name = file_name.lower().replace("-", "_").replace(".py", "")

                        # 导入源码模块
                        import importlib
                        full_module_path = f"{module_path}.{module_name}"
                        self._logger.INFO(f"🔧 [SOURCE FALLBACK] Trying to import: {full_module_path}")
                        module = importlib.import_module(full_module_path)

                        # 查找组件类
                        component_class = None
                        for attr_name in dir(module):
                            if attr_name.startswith("_"):
                                continue
                            attr = getattr(module, attr_name)
                            if isinstance(attr, type) and hasattr(attr, "__bases__"):
                                # 检查是否是组件类
                                is_component = False
                                if hasattr(attr, "__abstract__") and not getattr(attr, "__abstract__", True):
                                    is_component = True
                                else:
                                    # 检查基类名称
                                    for base in attr.__bases__:
                                        base_name = base.__name__
                                        if base_name.endswith("Strategy") or base_name.endswith("Selector") or \
                                           base_name.endswith("Sizer") or base_name.endswith("RiskManagement") or \
                                           base_name.endswith("Analyzer") or base_name == "BaseStrategy" or \
                                           base_name == "BaseSelector" or base_name == "BaseSizer" or \
                                           base_name == "BaseRiskManagement" or base_name == "BaseAnalyzer":
                                            is_component = True
                                            break

                                if is_component:
                                    component_class = attr
                                    break

                        if component_class is None:
                            return None, f"No component class found in source module {full_module_path}"

                        # 实例化组件
                        if component_params:
                            component = component_class(*component_params)
                        else:
                            component = component_class()

                        self._logger.INFO(f"✅ [SOURCE FALLBACK] Successfully loaded {component_class.__name__} from source")
                        return component, f"Loaded from source code (fallback)"

                    except ImportError as ie:
                        # 如果是策略失败，使用默认的RandomSignalStrategy作为fallback
                        if component_type == 6:  # STRATEGY
                            self._logger.WARN(f"🔧 [DEFAULT FALLBACK] Using RandomSignalStrategy as default strategy")
                            from ginkgo.trading.strategies.random_signal_strategy import RandomSignalStrategy
                            component = RandomSignalStrategy()
                            if hasattr(component, 'set_random_seed'):
                                component.set_random_seed(12345)
                            return component, f"Used default RandomSignalStrategy (fallback for {file_name})"
                        # 如果是分析器失败，使用默认的NetValue作为fallback
                        elif component_type == 1:  # ANALYZER
                            self._logger.WARN(f"🔧 [DEFAULT FALLBACK] Using NetValue as default analyzer")
                            from ginkgo.trading.analysis.analyzers.net_value import NetValue
                            component = NetValue()
                            return component, f"Used default NetValue analyzer (fallback for {file_name})"
                        # 如果是selector失败，使用默认的CNAllSelector作为fallback
                        elif component_type == 4:  # SELECTOR
                            self._logger.WARN(f"🔧 [DEFAULT FALLBACK] Using CNAllSelector as default selector")
                            from ginkgo.trading.selectors.cn_all_selector import CNAllSelector
                            component = CNAllSelector()
                            return component, f"Used default CNAllSelector (fallback for {file_name})"
                        # 如果是sizer失败，使用默认的FixedSizer作为fallback
                        elif component_type == 5:  # SIZER
                            self._logger.WARN(f"🔧 [DEFAULT FALLBACK] Using FixedSizer as default sizer")
                            from ginkgo.trading.sizers.fixed_sizer import FixedSizer
                            component = FixedSizer()
                            return component, f"Used default FixedSizer (fallback for {file_name})"
                        return None, f"Source fallback failed (ImportError): {str(ie)}"
                    except Exception as fallback_err:
                        return None, f"Source fallback failed: {str(fallback_err)}"

            # Add strategies (required)
            strategies = components.get("strategies", [])
            if len(strategies) == 0:
                self._logger.CRITICAL(f"No strategy found for portfolio {portfolio_id}")
                return False

            for strategy_mapping in strategies:
                # 支持两种格式：dict 或 ORM 对象
                # 如果 dict 中包含 file_id，使用文件加载方式
                if isinstance(strategy_mapping, dict) and "file_id" in strategy_mapping:
                    strategy, error = _instantiate_component_from_file(
                        strategy_mapping["file_id"], strategy_mapping.get("type", 6), strategy_mapping["mapping_uuid"]
                    )
                elif isinstance(strategy_mapping, dict):
                    strategy, error = self.instantiate_component_from_dict(strategy_mapping, "strategy", logger)
                else:
                    strategy, error = _instantiate_component_from_file(
                        strategy_mapping.file_id, strategy_mapping.type, strategy_mapping.uuid
                    )
                if strategy is None:
                    self._logger.ERROR(f"Failed to instantiate strategy: {error}")
                    return False

                portfolio.add_strategy(strategy)
                self._logger.DEBUG(f"✅ Added strategy: {strategy.__class__.__name__}")

            # Add selector (required)
            selectors = components.get("selectors", [])
            if len(selectors) == 0:
                self._logger.ERROR(f"No selector found for portfolio {portfolio_id}")
                return False
            selector_mapping = selectors[0]
            # 支持两种格式：dict 或 ORM 对象
            # 如果 dict 中包含 file_id，使用文件加载方式
            if isinstance(selector_mapping, dict) and "file_id" in selector_mapping:
                selector, error = _instantiate_component_from_file(
                    selector_mapping["file_id"], selector_mapping.get("type", 4), selector_mapping["mapping_uuid"]
                )
            elif isinstance(selector_mapping, dict):
                selector, error = self.instantiate_component_from_dict(selector_mapping, "selector", logger)
            else:
                selector, error = _instantiate_component_from_file(
                    selector_mapping.file_id, selector_mapping.type, selector_mapping.uuid
                )
            if selector is None:
                self._logger.ERROR(f"Failed to instantiate selector: {error}")
                return False

            portfolio.bind_selector(selector)
            self._logger.DEBUG(f"✅ Bound selector: {selector.__class__.__name__}")

            # Selector的兴趣集应该通过Portfolio自动传播到DataFeeder
            if hasattr(selector, '_interested') and len(selector._interested) > 0:
                self._logger.INFO(f"📅 Selector interested codes: {selector._interested}")
            else:
                self._logger.WARN("Selector has no interested codes or _interested attribute")

            # Add sizer (required)
            # 兼容两种格式：sizers (列表) 或 sizer (单个对象)
            sizers = components.get("sizers", [])
            if len(sizers) == 0:
                # 尝试单数形式
                sizer_single = components.get("sizer")
                if sizer_single:
                    sizers = [sizer_single]

            if len(sizers) == 0:
                self._logger.ERROR(f"No sizer found for portfolio {portfolio_id}")
                return False
            sizer_mapping = sizers[0]
            # 支持两种格式：dict 或 ORM 对象
            # 如果 dict 中包含 file_id，使用文件加载方式
            if isinstance(sizer_mapping, dict) and "file_id" in sizer_mapping:
                sizer, error = _instantiate_component_from_file(
                    sizer_mapping["file_id"], sizer_mapping.get("type", 5), sizer_mapping["mapping_uuid"]
                )
            elif isinstance(sizer_mapping, dict):
                sizer, error = self.instantiate_component_from_dict(sizer_mapping, "sizer", logger)
            else:
                sizer, error = _instantiate_component_from_file(
                    sizer_mapping.file_id, sizer_mapping.type, sizer_mapping.uuid
                )
            if sizer is None:
                self._logger.ERROR(f"Failed to instantiate sizer: {error}")
                return False

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
                    # 支持两种格式：dict 或 ORM 对象
                    if isinstance(risk_manager_mapping, dict) and "file_id" in risk_manager_mapping:
                        risk_manager, error = _instantiate_component_from_file(
                            risk_manager_mapping["file_id"], risk_manager_mapping.get("type", 3), risk_manager_mapping["mapping_uuid"]
                        )
                    else:
                        risk_manager, error = _instantiate_component_from_file(
                            risk_manager_mapping.file_id, risk_manager_mapping.type, risk_manager_mapping.uuid
                        )
                    if risk_manager is None:
                        self._logger.ERROR(f"Failed to instantiate risk manager: {error}")
                        continue

                    portfolio.add_risk_manager(risk_manager)
                    self._logger.DEBUG(f"✅ Added risk manager: {risk_manager.__class__.__name__}")

            # 加载用户配置的分析器（跳过已存在的 BASIC_ANALYZERS）
            if len(analyzers) > 0:
                self._logger.INFO(f"🔧 [ANALYZER] Loading {len(analyzers)} user-configured analyzers...")
                existing_names = set(portfolio.analyzers.keys()) if hasattr(portfolio, 'analyzers') else set()
                user_loaded = 0
                user_skipped = 0

                GLOG.INFO(f"Loading user analyzers (existing: {len(existing_names)})...")

                for idx, analyzer_mapping in enumerate(analyzers):
                    # 支持两种格式：dict 或 ORM 对象
                    if isinstance(analyzer_mapping, dict) and "file_id" in analyzer_mapping:
                        analyzer, error = _instantiate_component_from_file(
                            analyzer_mapping["file_id"], analyzer_mapping.get("type", 1), analyzer_mapping["mapping_uuid"]
                        )
                    else:
                        analyzer, error = _instantiate_component_from_file(
                            analyzer_mapping.file_id, analyzer_mapping.type, analyzer_mapping.uuid
                        )
                    if analyzer is None:
                        self._logger.ERROR(f"Failed to instantiate analyzer: {error}")
                        GLOG.ERROR(f"  Analyzer failed: {error}")
                        continue

                    analyzer_name = analyzer.name
                    if analyzer_name in existing_names:
                        GLOG.DEBUG(f"  {analyzer.__class__.__name__} ({analyzer_name}) already exists, skipping")
                        user_skipped += 1
                        continue

                    portfolio.add_analyzer(analyzer)
                    user_loaded += 1
                    GLOG.DEBUG(f"  {analyzer.__class__.__name__} ({analyzer_name}) added")
                    self._logger.INFO(f"✅ [ANALYZER] Added: {analyzer.__class__.__name__}")

                GLOG.INFO(f"User analyzers: {user_loaded} added, {user_skipped} skipped")
                self._logger.INFO(f"✅ [ANALYZER] User analyzers: {user_loaded} added, {user_skipped} skipped")

            GLOG.DEBUG("_perform_component_binding completed successfully")
            return True

        except Exception as e:
            self._logger.ERROR(f"Failed to perform component binding: {e}")
            import traceback
            GLOG.ERROR(f"Exception in _perform_component_binding: {e}")
            import traceback; traceback.print_exc()
            return False
