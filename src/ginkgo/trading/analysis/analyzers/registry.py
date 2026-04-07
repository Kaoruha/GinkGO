# Upstream: BaseAnalyzer subclasses, MySQL file table (MFile)
# Downstream: ComponentLoader, Engine Assembly
# Role: AnalyzerRegistry 统一分析器发现和实例化，支持内置子类扫描 + MySQL 用户分析器加载


import importlib.util
import inspect
import os
import tempfile
from typing import Dict, List, Optional, Type, Any

from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.enums import ANALYZER_CATEGORY_TYPES, FILE_TYPES
from ginkgo.libs import GLOG


class AnalyzerRegistry:
    """统一分析器注册中心。

    扫描两个来源：
    1. 内置子类 — BaseAnalyzer.__subclasses__()
    2. 用户自定义 — MySQL file 表 (FILE_TYPES.ANALYZER)

    用法：
        registry = AnalyzerRegistry()
        registry.scan_builtin()
        registry.scan_user_from_db()

        core = registry.get_by_category(ANALYZER_CATEGORY_TYPES.CORE)
        for cls in core:
            analyzer = cls()
    """

    def __init__(self):
        self._registry: Dict[str, Type[BaseAnalyzer]] = {}
        self._by_category: Dict[ANALYZER_CATEGORY_TYPES, List[Type[BaseAnalyzer]]] = {
            c: [] for c in ANALYZER_CATEGORY_TYPES
        }

    @property
    def all_analyzers(self) -> Dict[str, Type[BaseAnalyzer]]:
        return dict(self._registry)

    def register(self, analyzer_class: Type[BaseAnalyzer]) -> None:
        """注册一个分析器类。"""
        if not (isinstance(analyzer_class, type) and issubclass(analyzer_class, BaseAnalyzer)):
            GLOG.WARN(f"Skipping non-BaseAnalyzer class: {analyzer_class}")
            return
        if analyzer_class is BaseAnalyzer:
            return

        name = self._get_default_name(analyzer_class)

        if name in self._registry:
            GLOG.DEBUG(f"Analyzer '{name}' already registered, keeping existing.")
            return

        self._registry[name] = analyzer_class
        category = self._get_category(analyzer_class)
        if category not in self._by_category:
            self._by_category[category] = []
        self._by_category[category].append(analyzer_class)
        GLOG.DEBUG(f"Registered analyzer: {name} ({analyzer_class.__name__}) [{category.name}]")

    def scan_builtin(self) -> int:
        """扫描内置 BaseAnalyzer 子类。

        要求所有分析器模块已被导入（__init__.py 的导入负责）。
        """
        count = 0
        for cls in BaseAnalyzer.__subclasses__():
            if cls.__module__.startswith('ginkgo.trading.analysis.analyzers'):
                self.register(cls)
                count += 1
        GLOG.INFO(f"AnalyzerRegistry: scanned {count} built-in analyzers")
        return count

    def scan_user_from_db(self, file_service=None) -> int:
        """从 MySQL file 表扫描用户分析器。

        数据库异常时跳过，不影响主流程。
        """
        if file_service is None:
            try:
                from ginkgo.data.containers import container
                file_service = container.file_service()
            except Exception as e:
                GLOG.WARN(f"AnalyzerRegistry: cannot access file_service, skipping user scan: {e}")
                return 0

        count = 0
        try:
            result = file_service.list_by_type(FILE_TYPES.ANALYZER)
            if not result.is_success() or not result.data:
                GLOG.DEBUG("AnalyzerRegistry: no user analyzers found in database")
                return 0

            for file_record in result.data:
                try:
                    analyzer_class = self._load_class_from_file(file_record)
                    if analyzer_class is not None:
                        self.register(analyzer_class)
                        count += 1
                except Exception as e:
                    GLOG.WARN(f"Failed to load user analyzer '{getattr(file_record, 'name', '?')}': {e}")
                    continue

            GLOG.INFO(f"AnalyzerRegistry: scanned {count} user analyzers from database")
        except Exception as e:
            GLOG.WARN(f"AnalyzerRegistry: database scan failed, skipping user analyzers: {e}")

        return count

    def get_by_category(self, category: ANALYZER_CATEGORY_TYPES) -> List[Type[BaseAnalyzer]]:
        """获取指定类别的分析器类列表。"""
        return self._by_category.get(category, [])

    def get(self, name: str) -> Optional[Type[BaseAnalyzer]]:
        """按名称获取分析器类。"""
        return self._registry.get(name)

    def instantiate_by_category(self, category: ANALYZER_CATEGORY_TYPES, **kwargs) -> List[BaseAnalyzer]:
        """实例化指定类别的所有分析器。"""
        instances = []
        for cls in self.get_by_category(category):
            try:
                instances.append(cls(**kwargs))
            except Exception as e:
                GLOG.ERROR(f"Failed to instantiate {cls.__name__}: {e}")
        return instances

    # ========== 内部方法 ==========

    def _get_default_name(self, analyzer_class: Type[BaseAnalyzer]) -> str:
        """从类签名中提取默认 name 参数。"""
        try:
            sig = inspect.signature(analyzer_class.__init__)
            default_name = sig.parameters.get('name')
            if default_name and default_name.default is not inspect.Parameter.empty:
                return default_name.default
        except Exception:
            pass
        return analyzer_class.__name__

    def _get_category(self, analyzer_class: Type[BaseAnalyzer]) -> ANALYZER_CATEGORY_TYPES:
        """从类定义中提取 category。"""
        try:
            source = inspect.getsource(analyzer_class.__init__)
            if 'ANALYZER_CATEGORY_TYPES.CORE' in source:
                return ANALYZER_CATEGORY_TYPES.CORE
            if 'ANALYZER_CATEGORY_TYPES.CUSTOM' in source:
                return ANALYZER_CATEGORY_TYPES.CUSTOM
        except Exception:
            pass
        return ANALYZER_CATEGORY_TYPES.EXTENDED

    def _load_class_from_file(self, file_record) -> Optional[Type[BaseAnalyzer]]:
        """从 file 记录动态加载分析器类。"""
        code_content = getattr(file_record, 'data', None)
        if code_content is None:
            return None
        if isinstance(code_content, bytes):
            code_content = code_content.decode("utf-8", errors="ignore")
        else:
            code_content = str(code_content)

        file_name = getattr(file_record, 'name', 'unknown')

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code_content)
            temp_path = f.name

        try:
            spec = importlib.util.spec_from_file_location(f"user_analyzer_{file_name}", temp_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            for attr_name in dir(module):
                if attr_name.startswith("_"):
                    continue
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, BaseAnalyzer) and attr is not BaseAnalyzer:
                    return attr
            return None
        except Exception as e:
            GLOG.WARN(f"Failed to load class from file '{file_name}': {e}")
            return None
        finally:
            try:
                os.unlink(temp_path)
            except Exception:
                pass
