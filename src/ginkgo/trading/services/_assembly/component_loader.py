# Upstream: EngineAssemblyService, TaskEngineBuilder
# Downstream: PortfolioT1Backtest, GLOG, file_service
# Role: 组件加载器，从数据库源码文件实例化策略/选股器/分析器等组件并绑定到Portfolio


"""
ComponentLoader - 组件加载器

负责从数据库文件加载组件源码，动态实例化并绑定到 Portfolio。
所有组件统一通过 _instantiate_component_from_file() 加载。
"""

import json
from typing import Dict, Any, List
from ginkgo.libs import GLOG, GinkgoLogger
from ginkgo.trading.portfolios import PortfolioT1Backtest


def resolve_param_kwargs(
    component_params: list,
    param_indices: List[int],
    param_names: Dict[int, str],
) -> Dict[str, Any]:
    """将 DB 参数值映射到组件构造函数的 kwargs。

    #5974: 支持新旧两种索引方案：
    - 新组合（#5955 后创建）：索引从 0 开始，name 已跳过
    - 旧组合（#5955 前创建）：索引从 1 开始（0=name）

    策略（两轮打分择优）：
    1. 直接匹配：param_indices[i] → param_names[该索引]。当全部命中且
       min(param_indices)==0（确属新组合 0 起始）时立即返回。
    2. 偏移匹配：整体 -1（name 曾占 index 0）。
    选择规则：按 _score_mapping 的「命中数」优先；命中数相同时，若为多参数
    旧组合（min>0）则偏好偏移方案，避免 [1,2] 被误读为第二、第三业务参数。
    """
    if not component_params or not param_indices:
        return {}

    def _score_mapping(mapped_kwargs: Dict[str, Any], source_indices: List[int]) -> tuple[int, int, int]:
        """给候选映射打分，优先保留业务参数映射更完整、索引起点更合理的方案。"""
        mapped_count = len(mapped_kwargs)
        if not source_indices:
            return (mapped_count, 0, 0)

        min_index = min(source_indices)
        # 更偏向 0 起始的新索引；旧索引在平分时由调用方显式选择
        zero_based_bonus = 1 if min_index == 0 else 0
        contiguous_bonus = 1 if source_indices == list(range(min_index, min_index + len(source_indices))) else 0
        return (mapped_count, zero_based_bonus, contiguous_bonus)

    # 第一轮：直接匹配（新组合）
    kwargs: Dict[str, Any] = {}
    for i, val in enumerate(component_params):
        orig_idx = param_indices[i]
        if orig_idx in param_names:
            kwargs[param_names[orig_idx]] = val

    if len(kwargs) == len(component_params) and (not param_indices or min(param_indices) == 0):
        return kwargs

    # 第二轮：旧组合，索引整体偏移 -1（name 曾在 index 0）
    shifted: Dict[str, Any] = {}
    shifted_indices: List[int] = []
    for i, val in enumerate(component_params):
        orig_idx = param_indices[i]
        shifted_idx = orig_idx - 1
        if shifted_idx >= 0 and shifted_idx in param_names:
            shifted[param_names[shifted_idx]] = val
            shifted_indices.append(shifted_idx)

    direct_score = _score_mapping(kwargs, param_indices)
    shifted_score = _score_mapping(shifted, shifted_indices)

    # #6159: 提取器跳过了框架参数(如 name) → param_names 比 component_params 少一项，
    # 而 DB 仍把被跳过的值(如 name)存在 index0。直接映射会把该值错绑给第一个
    # 业务参数(如 FixedSelector codes 拿到 'default_selector')。此时偏移映射才正确：
    # index1→param_names[0] 把真业务值绑对。仅当 len 相等(DB 未存 name)时不触发。
    if shifted and len(param_names) < len(component_params):
        return shifted

    # 平分时优先旧索引兼容方案，避免 [1,2] 被误解释为第二、第三个业务参数
    if shifted_score[0] > direct_score[0]:
        return shifted
    if (
        shifted_score[0] == direct_score[0]
        and shifted
        and param_indices
        and len(component_params) > 1
        and min(param_indices) > 0
    ):
        return shifted

    return kwargs


class ComponentLoader:
    """
    组件加载器

    从数据库 File 表读取组件源码，动态执行并实例化，绑定到 Portfolio。
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
                    component_params, param_indices = self._resolve_component_params(mapping_uuid)
                    component_kwargs = {}
                    if component_params:
                        # 用动态参数提取器获取参数名，构建 kwargs
                        # #5974: 使用 resolve_param_kwargs 处理新旧索引兼容
                        try:
                            from ginkgo.data.services.component_parameter_extractor import get_component_parameter_names
                            # #6103: 复用已取的 mfile.name，取代 container.cruds.file() 重复查询
                            comp_name = getattr(mfile, "name", None)
                            type_map = {6: "strategy", 4: "selector", 5: "sizer", 3: "risk_manager", 1: "analyzer"}
                            file_type_str = type_map.get(component_type)
                            if comp_name and file_type_str:
                                param_names = get_component_parameter_names(comp_name, code_content, file_type_str, file_id)
                                component_kwargs = resolve_param_kwargs(
                                    component_params, param_indices, param_names,
                                )
                        except Exception as e:
                            self._logger.WARN(f"Failed to resolve param names, falling back to positional: {e}")

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
                                is_component = False

                                # 方法1：检查__abstract__属性
                                if hasattr(attr, "__abstract__") and not getattr(attr, "__abstract__", True):
                                    is_component = True

                                # 方法2：检查基类名称
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
                            class_names = [name for name in dir(module) if not name.startswith("_") and isinstance(getattr(module, name), type)]
                            class_details = []
                            for name in class_names:
                                cls = getattr(module, name)
                                bases = [base.__name__ for base in cls.__bases__ if hasattr(base, "__name__")]
                                abstract_info = f"abstract={getattr(cls, '__abstract__', 'NOT_FOUND')}"
                                class_details.append(f"{name}(bases={bases}, {abstract_info})")
                            self._logger.ERROR(f"No component class found in file. Available classes: {class_details}")
                            return None, f"No component class found in file. Available classes: {class_details}"

                        # 实例化组件
                        try:
                            if component_kwargs:
                                self._logger.DEBUG(f"Creating {component_class.__name__} with kwargs: {component_kwargs}")
                                component = component_class(**component_kwargs)
                            elif component_params:
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

                        source_import_map = {
                            6: ("ginkgo.trading.strategies", "strategies"),
                            4: ("ginkgo.trading.selectors", "selectors"),
                            5: ("ginkgo.trading.sizers", "sizers"),
                            7: ("ginkgo.trading.risk_managements", "risk_managements"),
                            1: ("ginkgo.trading.analysis.analyzers", "analyzers"),
                        }

                        if component_type not in source_import_map:
                            return None, f"No source fallback for component type {component_type}"

                        module_path, subpackage = source_import_map[component_type]
                        module_name = file_name.lower().replace("-", "_").replace(".py", "")

                        import importlib
                        full_module_path = f"{module_path}.{module_name}"
                        self._logger.INFO(f"🔧 [SOURCE FALLBACK] Trying to import: {full_module_path}")
                        module = importlib.import_module(full_module_path)

                        component_class = None
                        for attr_name in dir(module):
                            if attr_name.startswith("_"):
                                continue
                            attr = getattr(module, attr_name)
                            if isinstance(attr, type) and hasattr(attr, "__bases__"):
                                is_component = False
                                if hasattr(attr, "__abstract__") and not getattr(attr, "__abstract__", True):
                                    is_component = True
                                else:
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

                        if component_kwargs:
                            component = component_class(**component_kwargs)
                        elif component_params:
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
