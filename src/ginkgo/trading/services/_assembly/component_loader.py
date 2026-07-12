# Upstream: EngineAssemblyService, TaskEngineBuilder
# Downstream: PortfolioT1Backtest, GLOG, file_service
# Role: 组件加载器，从数据库源码文件实例化策略/选股器/分析器等组件并绑定到Portfolio


"""
ComponentLoader - 组件加载器（组件创建的单一接缝，ADR-022 原则 3）

负责从数据库文件加载组件源码，动态实例化并绑定到 Portfolio。
所有组件统一通过 _instantiate_component_from_file() 加载。

ADR-022 原则 3:ComponentLoader.perform_component_binding 是「从 DB 源码文件
实例化组件并绑定到 Portfolio」的**唯一接缝**。历史上并存过多层死抽象
（ComponentFactoryService / core.factories / core.adapters / AnalyzerRegistry）,
均无业务调用方,已于 #6476 删除。新增组件创建逻辑应在此处扩展,勿另起工厂层。
"""

import json
from typing import Dict, Any, List
from ginkgo.libs import GLOG, GinkgoLogger
from ginkgo.trading.portfolios import PortfolioT1Backtest
from ginkgo.enums import FILE_TYPES


# 组件类型元数据 —— 单一映射源（#4630: 原 type_map 与 SOURCE_FALLBACK_IMPORT_MAP
# 双映射各写一份、键集相同却无单一真相源，曾致 #5880 缺陷4a 漂移）。
# key 必须用 FILE_TYPES 的 .value（int），与传入的 component_type(int) 比较一致。
# ENGINE(=7) 不在此映射 —— engine 是内置回测/实盘引擎，非用户上传 .py 组件，无需源码回退。
COMPONENT_TYPE_INFO: Dict[int, Dict[str, str]] = {
    FILE_TYPES.STRATEGY.value: {
        "name": "strategy",
        "module_path": "ginkgo.trading.strategies",
        "subpackage": "strategies",
    },
    FILE_TYPES.SELECTOR.value: {
        "name": "selector",
        "module_path": "ginkgo.trading.selectors",
        "subpackage": "selectors",
    },
    FILE_TYPES.SIZER.value: {
        "name": "sizer",
        "module_path": "ginkgo.trading.sizers",
        "subpackage": "sizers",
    },
    FILE_TYPES.RISKMANAGER.value: {
        "name": "risk_manager",
        "module_path": "ginkgo.trading.risk_management",
        "subpackage": "risk_management",
    },
    FILE_TYPES.ANALYZER.value: {
        "name": "analyzer",
        "module_path": "ginkgo.trading.analysis.analyzers",
        "subpackage": "analyzers",
    },
}

# 源码回退导入映射：从单一源派生，保持 (module_path, subpackage) 元组形状不变
# （test_component_loader_source_fallback.py 锁定了元组值）。
SOURCE_FALLBACK_IMPORT_MAP = {
    ftype: (info["module_path"], info["subpackage"]) for ftype, info in COMPONENT_TYPE_INFO.items()
}


# --------------------------------------------------------------------------- #
# 组件类检测（#4630: 主路径与源码 fallback 路径原各写一份检测循环，收敛为单一 helper）
# --------------------------------------------------------------------------- #

# method 2 命中的基类名后缀（含 SelectorBase）与精确基类名（Base* 抽象基类）
_COMPONENT_BASE_SUFFIXES = ("Strategy", "Selector", "SelectorBase", "Sizer", "RiskManagement", "Analyzer")
_COMPONENT_BASE_EXACT = ("BaseStrategy", "BaseSelector", "BaseSizer", "BaseRiskManagement", "BaseAnalyzer")

# method 3 命中的类名后缀（不含 SelectorBase —— 与主路径原逻辑一致）
_COMPONENT_NAME_SUFFIXES = ("Strategy", "Selector", "Sizer", "RiskManagement", "Analyzer")


def _is_component_class(attr: type, attr_name: str) -> bool:
    """判定一个类是否为组件类。

    三种检测方法（任一命中即判定为组件类）：
    1. ``__abstract__`` 属性存在且为 False（非抽象）；
    2. 任一基类名匹配组件基类后缀（含 SelectorBase）或精确基类名（Base*）；
    3. 类名本身匹配组件后缀，且不在 Base* 抽象基类排除清单内。
    """
    # method 1：__abstract__ 属性
    if hasattr(attr, "__abstract__") and not getattr(attr, "__abstract__", True):
        return True
    # method 2：基类名
    for base in getattr(attr, "__bases__", ()):
        base_name = getattr(base, "__name__", "")
        if any(base_name.endswith(s) for s in _COMPONENT_BASE_SUFFIXES) or base_name in _COMPONENT_BASE_EXACT:
            return True
    # method 3：类名本身（排除 Base* 抽象基类）
    if attr_name not in _COMPONENT_BASE_EXACT and any(attr_name.endswith(s) for s in _COMPONENT_NAME_SUFFIXES):
        return True
    return False


def _detect_component_class(module, logger=None):
    """从模块属性中扫描首个组件类，找不到返回 None。

    跳过下划线开头与非 type 属性。主路径与源码 fallback 路径共用此 helper，
    保证 fallback 获得与主路径相同的检测能力（AC#2）。
    """
    for attr_name in dir(module):
        if attr_name.startswith("_"):
            continue
        attr = getattr(module, attr_name)
        if isinstance(attr, type) and hasattr(attr, "__bases__") and _is_component_class(attr, attr_name):
            if logger is not None:
                logger.DEBUG(f"Found component class: {attr.__name__}")
            return attr
    return None


class ComponentLoader:
    """
    组件加载器 —— 组件创建的单一接缝（ADR-022 原则 3）

    从数据库 File 表读取组件源码，动态执行并实例化，绑定到 Portfolio。
    这是全仓唯一执行「DB 源码 → exec_module → 组件实例」的路径;
    perform_component_binding 为对外入口,新增组件类型应在此扩展。
    """

    def __init__(self, file_service=None, param_service=None, logger=None):
        self._file_service = file_service
        self._param_service = param_service
        self._logger = logger or GLOG

    def _resolve_component_params(self, mapping_uuid: str):
        """通过注入的 param_service 取组件参数记录，解析为 (params, indices)。

        #6103: 取代 container.cruds.param() service locator（复刻 #3943 到 loader 路径）。
        从 _instantiate_component_from_file 提取，使其可独立测试（避开动态 exec_module）。
        """
        component_params = []
        param_indices = []
        if self._param_service is None:
            # #6103: param_service 未注入 = 装配接线 bug，禁止静默 WARN+返空
            # （否则组件以默认参数实例化，用户策略阈值/手数/风控比例静默丢失）。
            # 生产链路必须经 containers.py DI 注入，或显式传 services.data.param_service()。
            raise ValueError(
                "param_service not injected; cannot resolve component params. "
                "Inject via ComponentLoader(param_service=...) / "
                "EngineAssemblyService(param_service=...) — wiring must come from "
                "containers.py DI or services.data.param_service()."
            )
        param_records = self._param_service.find_by_mapping_id(mapping_uuid)
        if not param_records:
            self._logger.WARN(f"No params found for mapping_id: {mapping_uuid}")
            return component_params, param_indices
        for p in sorted(param_records, key=lambda p: p.index):
            try:
                component_params.append(json.loads(p.value) if p.value else p.value)
            except (json.JSONDecodeError, TypeError):
                component_params.append(p.value)
            param_indices.append(p.index)
        self._logger.DEBUG(f"Found {len(component_params)} params: {component_params}")
        return component_params, param_indices

    def perform_component_binding(
        self, portfolio: PortfolioT1Backtest, components: Dict[str, Any], logger: GinkgoLogger
    ) -> bool:
        """执行组件绑定和实例化（ADR-022 原则 3 的单一对外入口）。

        从 components dict 取各类型组件元信息,逐个经 _instantiate_component_from_file
        从 DB 源码实例化并绑定到 portfolio。所有组件创建必经此方法,勿绕开另建工厂。
        """
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
                """从数据库文件内容实例化组件"""
                try:
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
                            return None, "No file data found"
                    else:
                        return None, "Invalid file data structure"

                    # 获取组件参数（#6103: 走注入的 param_service，取代 container.cruds.param()）
                    # ADR-020: 纯位置装配 — 按 MParam.index 排序后 splat，装配不再依赖提取器/kwargs
                    component_params, _ = self._resolve_component_params(mapping_uuid)

                    # 动态执行代码来获取组件类
                    import importlib.util
                    import tempfile
                    import os

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

                        # 查找组件类（#4630: 提取为 _detect_component_class，与源码 fallback 共用）
                        self._logger.DEBUG("Starting component class detection")
                        component_class = _detect_component_class(module, self._logger)
                        if component_class is None:
                            class_names = [name for name in dir(module) if not name.startswith("_") and isinstance(getattr(module, name), type)]
                            class_details = []
                            for name in class_names:
                                cls = getattr(module, name)
                                bases = [base.__name__ for base in cls.__bases__ if hasattr(base, "__name__")]
                                abstract_info = f"abstract={getattr(cls, '__abstract__', 'NOT_FOUND')}"
                                class_details.append(f"{name}(bases={bases}, {abstract_info})")
                            self._logger.ERROR(f"No component class found in file. Available classes: {class_details}")
                            return None, f"No component class found in file. Available classes: {class_details}"

                        # 实例化组件（ADR-020: 纯位置 splat，无 kwargs 分支）
                        try:
                            if component_params:
                                self._logger.DEBUG(f"Creating {component_class.__name__} with positional params: {component_params}")
                                component = component_class(*component_params)
                            else:
                                self._logger.INFO(f"No params found for {component_class.__name__}, attempting instantiation with defaults")
                                component = component_class()

                            self._logger.DEBUG(f"Component {type(component).__name__} created successfully")

                            if "RandomSignalStrategy" in component_class.__name__:
                                if hasattr(component, 'set_random_seed'):
                                    component.set_random_seed(12345)
                                    self._logger.DEBUG(f"Set random_seed=12345 for RandomSignalStrategy")

                        except TypeError as e:
                            error_msg = f"Component {component_class.__name__} requires parameters but none found: {e}"
                            self._logger.ERROR(f"🔥 [INSTANTIATION ERROR] {error_msg}")
                            return None, error_msg
                        except Exception as e:
                            error_msg = f"Unexpected error instantiating {component_class.__name__}: {e}"
                            self._logger.ERROR(f"🔥 [INSTANTIATION ERROR] {error_msg}")
                            return None, error_msg

                        return component, None

                    finally:
                        try:
                            os.unlink(temp_file_path)
                        except Exception as e:
                            GLOG.ERROR(f"Failed to clean up temp file {temp_file_path}: {e}")

                except Exception as e:
                    # 源码fallback：数据库代码执行失败时，尝试从源码导入
                    error_msg = str(e)
                    self._logger.WARN(f"🔥 [DYNAMIC LOAD FAILED] {error_msg}, trying source code fallback...")

                    try:
                        file_result = self._file_service.get_by_uuid(file_id)
                        if file_result.success and file_result.data:
                            if isinstance(file_result.data, dict) and "file" in file_result.data:
                                file_name = file_result.data["file"].name
                            else:
                                file_name = file_result.data.name
                        else:
                            return None, f"Failed to get file info for fallback: {file_result.error}"

                        source_import_map = SOURCE_FALLBACK_IMPORT_MAP

                        if component_type not in source_import_map:
                            return None, f"No source fallback for component type {component_type}"

                        module_path, subpackage = source_import_map[component_type]
                        module_name = file_name.lower().replace("-", "_").replace(".py", "")

                        import importlib
                        full_module_path = f"{module_path}.{module_name}"
                        self._logger.INFO(f"🔧 [SOURCE FALLBACK] Trying to import: {full_module_path}")
                        module = importlib.import_module(full_module_path)

                        # #4630: 与主路径共用 _detect_component_class。原 fallback 缺 method 3
                        # （类名后缀检测）、base.__name__ 未防 object 致 AttributeError，现统一修复。
                        component_class = _detect_component_class(module, self._logger)

                        if component_class is None:
                            return None, f"No component class found in source module {full_module_path}"

                        if component_params:
                            component = component_class(*component_params)
                        else:
                            component = component_class()

                        self._logger.INFO(f"✅ [SOURCE FALLBACK] Successfully loaded {component_class.__name__} from source")
                        return component, f"Loaded from source code (fallback)"

                    except ImportError as ie:
                        if component_type == 6:  # STRATEGY
                            self._logger.WARN(f"🔧 [DEFAULT FALLBACK] Using RandomSignalStrategy as default strategy")
                            from ginkgo.trading.strategies.random_signal_strategy import RandomSignalStrategy
                            component = RandomSignalStrategy()
                            if hasattr(component, 'set_random_seed'):
                                component.set_random_seed(12345)
                            return component, f"Used default RandomSignalStrategy (fallback for {file_name})"
                        elif component_type == 1:  # ANALYZER
                            self._logger.WARN(f"🔧 [DEFAULT FALLBACK] Using NetValue as default analyzer")
                            from ginkgo.trading.analysis.analyzers.net_value import NetValue
                            component = NetValue()
                            return component, f"Used default NetValue analyzer (fallback for {file_name})"
                        elif component_type == 4:  # SELECTOR
                            self._logger.WARN(f"🔧 [DEFAULT FALLBACK] Using CNAllSelector as default selector")
                            from ginkgo.trading.selectors.cn_all_selector import CNAllSelector
                            component = CNAllSelector()
                            return component, f"Used default CNAllSelector (fallback for {file_name})"
                        elif component_type == 5:  # SIZER
                            self._logger.WARN(f"🔧 [DEFAULT FALLBACK] Using FixedSizer as default sizer")
                            from ginkgo.trading.sizers.fixed_sizer import FixedSizer
                            component = FixedSizer()
                            return component, f"Used default FixedSizer (fallback for {file_name})"
                        return None, f"Source fallback failed (ImportError): {str(ie)}"
                    except Exception as fallback_err:
                        return None, f"Source fallback failed: {str(fallback_err)}"

            def _load_component(mapping, component_type_int):
                """统一加载组件：ORM 对象或 dict（必须含 file_id）"""
                if isinstance(mapping, dict) and "file_id" in mapping:
                    return _instantiate_component_from_file(
                        mapping["file_id"], mapping.get("type", component_type_int), mapping.get("mapping_uuid") or mapping.get("mount_id")
                    )
                else:
                    return _instantiate_component_from_file(
                        mapping.file_id, mapping.type, mapping.uuid
                    )

            # Add strategies (required)
            if len(strategies) == 0:
                self._logger.CRITICAL(f"No strategy found for portfolio {portfolio_id}")
                return False

            for strategy_mapping in strategies:
                strategy, error = _load_component(strategy_mapping, 6)
                if strategy is None:
                    self._logger.ERROR(f"Failed to instantiate strategy: {error}")
                    return False
                portfolio.add_strategy(strategy)
                self._logger.DEBUG(f"✅ Added strategy: {strategy.__class__.__name__}")

            # Add selector (required)
            if len(selectors) == 0:
                self._logger.ERROR(f"No selector found for portfolio {portfolio_id}")
                return False
            selector, error = _load_component(selectors[0], 4)
            if selector is None:
                self._logger.ERROR(f"Failed to instantiate selector: {error}")
                return False
            portfolio.bind_selector(selector)
            self._logger.DEBUG(f"✅ Bound selector: {selector.__class__.__name__}")

            if hasattr(selector, '_interested') and len(selector._interested) > 0:
                self._logger.INFO(f"📅 Selector interested codes: {selector._interested}")
            else:
                self._logger.WARN("Selector has no interested codes or _interested attribute")

            # Add sizer (required)
            sizers_list = components.get("sizers", [])
            if len(sizers_list) == 0:
                sizer_single = components.get("sizer")
                if sizer_single:
                    sizers_list = [sizer_single]

            if len(sizers_list) == 0:
                self._logger.ERROR(f"No sizer found for portfolio {portfolio_id}")
                return False
            sizer, error = _load_component(sizers_list[0], 5)
            if sizer is None:
                self._logger.ERROR(f"Failed to instantiate sizer: {error}")
                return False
            portfolio.bind_sizer(sizer)
            self._logger.DEBUG(f"✅ Bound sizer: {sizer.__class__.__name__}")

            # Add risk managers (optional)
            if len(risk_managers) == 0:
                self._logger.WARN(
                    f"No risk manager found for portfolio {portfolio_id}. Backtest will go on without risk control."
                )
            else:
                for risk_manager_mapping in risk_managers:
                    risk_manager, error = _load_component(risk_manager_mapping, 3)
                    if risk_manager is None:
                        self._logger.ERROR(f"Failed to instantiate risk manager: {error}")
                        continue
                    portfolio.add_risk_manager(risk_manager)
                    self._logger.DEBUG(f"✅ Added risk manager: {risk_manager.__class__.__name__}")

            # Add analyzers (optional, skip duplicates)
            if len(analyzers) > 0:
                self._logger.INFO(f"🔧 [ANALYZER] Loading {len(analyzers)} user-configured analyzers...")
                existing_names = set(portfolio.analyzers.keys()) if hasattr(portfolio, 'analyzers') else set()
                user_loaded = 0
                user_skipped = 0

                GLOG.INFO(f"Loading user analyzers (existing: {len(existing_names)})...")

                for idx, analyzer_mapping in enumerate(analyzers):
                    analyzer, error = _load_component(analyzer_mapping, 1)
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
