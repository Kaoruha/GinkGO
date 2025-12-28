"""
Component Parameter Extractor - 动态组件参数提取服务

通过分析组件源代码来获取真实的构造函数参数名称，而不是使用预定义映射。
支持多种Python语法模式和组件结构。
"""

import ast
import inspect
import os
import importlib.util
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from ginkgo.libs import GLOG


class ComponentParameterExtractor:
    """动态组件参数提取器"""

    def __init__(self):
        self._component_cache = {}  # 缓存已分析的组件参数信息

    def extract_component_parameters(self, component_name: str, file_content: str = None,
                                   component_type: str = None, file_id: str = None) -> Dict[int, str]:
        """
        动态提取组件的构造函数参数

        Args:
            component_name: 组件名称 (如 "fixed_selector", "random_signal")
            file_content: 组件文件内容 (可选，优先使用数据库内容)
            component_type: 组件类型 (strategy/selector/sizer/risk_manager/analyzer)
            file_id: 文件ID (用于从数据库获取内容)

        Returns:
            Dict[int, str]: 参数索引到参数名称的映射，如 {0: "codes", 1: "volume"}
        """
        cache_key = f"{component_name}_{component_type}_{file_id}"

        # 检查缓存
        if cache_key in self._component_cache:
            return self._component_cache[cache_key]

        # 1. 优先使用提供的文件内容进行分析
        if file_content:
            result = self._extract_from_content(file_content, component_name)
            self._component_cache[cache_key] = result
            return result

        # 2. 如果提供了file_id，尝试从数据库获取内容
        if file_id:
            try:
                from ginkgo.data.containers import container
                file_service = container.file_service()
                result = file_service.get_by_uuid(file_id)

                if result.success and result.data:
                    file_info = result.data
                    db_content = None

                    # 处理字典格式 {"file": MFile, "exists": True}
                    if isinstance(file_info, dict) and 'file' in file_info:
                        mfile = file_info['file']
                        if hasattr(mfile, 'data') and mfile.data:
                            db_content = mfile.data
                    # 直接处理对象格式
                    elif hasattr(file_info, 'data') and file_info.data:
                        db_content = file_info.data

                    if db_content:
                        # 处理字节类型内容
                        if isinstance(db_content, bytes):
                            content_str = db_content.decode('utf-8', errors='ignore')
                        else:
                            content_str = str(db_content)

                        result = self._extract_from_content(content_str, component_name)
                        self._component_cache[cache_key] = result
                        return result
            except Exception as e:
                GLOG.DEBUG(f"从数据库获取文件内容失败 {file_id}: {e}")

        # 3. 回退到本地文件系统查找
        file_path = self._find_component_file(component_name, component_type)
        if file_path and os.path.exists(file_path):
            result = self._extract_from_file(file_path, component_name)
            self._component_cache[cache_key] = result
            return result

        # 4. 如果都找不到，返回空映射
        GLOG.WARN(f"未找到组件内容: {component_name} (类型: {component_type}, file_id: {file_id})")
        return {}

    def _find_component_file(self, component_name: str, component_type: str) -> Optional[str]:
        """在trading目录中查找组件文件"""
        # 获取trading目录路径
        trading_dir = Path(__file__).parent.parent.parent / "trading"

        # 组件类型到子目录的映射
        type_dirs = {
            "strategy": "strategies",
            "strategies": "strategies",
            "selector": "selectors",
            "selectors": "selectors",
            "sizer": "sizers",
            "sizers": "sizers",
            "risk_manager": "risk_management",
            "risk_managers": "risk_management",
            "analyzer": "analyzers",
            "analyzers": "analyzers",
        }

        # 确定搜索目录
        search_dirs = []
        if component_type:
            search_dir = type_dirs.get(component_type.lower())
            if search_dir:
                search_dirs.append(trading_dir / search_dir)

        # 如果没有指定类型或类型不匹配，搜索所有可能的目录
        if not search_dirs:
            search_dirs = [trading_dir / subdir for subdir in type_dirs.values()]
            search_dirs = list(set(search_dirs))  # 去重

        # 在目录中查找文件
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue

            # 查找可能的文件名
            possible_names = [
                f"{component_name}.py",
                f"{component_name}_strategy.py",
                f"{component_name}_selector.py",
                f"{component_name}_sizer.py",
                f"{component_name}_risk.py",
                f"strategy_{component_name}.py",
                f"selector_{component_name}.py",
                f"sizer_{component_name}.py",
                f"risk_{component_name}.py",
            ]

            for possible_name in possible_names:
                file_path = search_dir / possible_name
                if file_path.exists():
                    return str(file_path)

        return None

    def _extract_from_content(self, content: str, component_name: str) -> Dict[int, str]:
        """从字符串内容中提取参数信息"""
        try:
            # 使用AST静态分析字符串内容
            ast_result = self._extract_via_ast_analysis_content(content, component_name)
            if ast_result:
                return ast_result
        except Exception as e:
            GLOG.DEBUG(f"从内容分析提取参数失败 {component_name}: {e}")

        return {}

    def _extract_from_file(self, file_path: str, component_name: str) -> Dict[int, str]:
        """从Python文件中提取参数信息"""
        try:
            # 方法1: 尝试动态导入组件类并使用inspect
            dynamic_result = self._extract_via_dynamic_import(file_path, component_name)
            if dynamic_result:
                return dynamic_result

            # 方法2: 使用AST静态分析源代码
            ast_result = self._extract_via_ast_analysis(file_path, component_name)
            if ast_result:
                return ast_result

        except Exception as e:
            GLOG.ERROR(f"分析组件文件失败 {file_path}: {e}")

        return {}

    def _extract_via_dynamic_import(self, file_path: str, component_name: str) -> Optional[Dict[int, str]]:
        """通过动态导入组件类提取参数"""
        try:
            # 动态导入模块
            spec = importlib.util.spec_from_file_location("component_module", file_path)
            if not spec or not spec.loader:
                return None

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 查找组件类
            component_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (inspect.isclass(attr) and
                    attr_name.lower().replace('_', '') in component_name.lower().replace('_', '')):
                    component_class = attr
                    break

            if not component_class:
                # 尝试其他匹配方式
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (inspect.isclass(attr) and
                        any(keyword in attr_name.lower() for keyword in
                           ['strategy', 'selector', 'sizer', 'risk', 'analyzer'])):
                        component_class = attr
                        break

            if not component_class:
                return None

            # 使用inspect获取构造函数签名
            init_signature = inspect.signature(component_class.__init__)

            # 提取参数信息
            parameters = {}
            param_index = 0

            for param_name, param in init_signature.parameters.items():
                # 跳过self和name参数
                if param_name in ['self', 'args', 'kwargs']:
                    continue
                if param_name == 'name':
                    continue  # name是通用参数，跳过

                # 记录参数
                parameters[param_index] = param_name
                param_index += 1

            GLOG.DEBUG(f"通过动态导入提取到组件 {component_name} 的参数: {parameters}")
            return parameters

        except Exception as e:
            GLOG.DEBUG(f"动态导入分析失败 {file_path}: {e}")
            return None

    def _extract_via_ast_analysis_content(self, content: str, component_name: str) -> Optional[Dict[int, str]]:
        """通过AST静态分析字符串内容提取参数"""
        try:
            # 解析AST
            tree = ast.parse(content)

            # 查找组件类
            component_class = None
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_name = node.name.lower()
                    if (component_name.lower() in class_name or
                        any(keyword in class_name for keyword in
                           ['strategy', 'selector', 'sizer', 'risk', 'analyzer'])):
                        component_class = node
                        break

            if not component_class:
                return None

            # 查找__init__方法
            init_method = None
            for node in component_class.body:
                if isinstance(node, ast.FunctionDef) and node.name == '__init__':
                    init_method = node
                    break

            if not init_method:
                return None

            # 提取参数
            parameters = {}
            param_index = 0

            for arg in init_method.args.args:
                arg_name = arg.arg

                # 跳过self和name参数
                if arg_name in ['self', 'args', 'kwargs']:
                    continue
                if arg_name == 'name':
                    continue  # name是通用参数，跳过

                # 记录参数
                parameters[param_index] = arg_name
                param_index += 1

            GLOG.DEBUG(f"通过AST内容分析提取到组件 {component_name} 的参数: {parameters}")
            return parameters

        except Exception as e:
            GLOG.DEBUG(f"AST内容分析失败 {component_name}: {e}")
            return None

    def _extract_via_ast_analysis(self, file_path: str, component_name: str) -> Optional[Dict[int, str]]:
        """通过AST静态分析提取参数"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            # 解析AST
            tree = ast.parse(source_code)

            # 查找组件类
            component_class = None
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_name = node.name.lower()
                    if (component_name.lower() in class_name or
                        any(keyword in class_name for keyword in
                           ['strategy', 'selector', 'sizer', 'risk', 'analyzer'])):
                        component_class = node
                        break

            if not component_class:
                return None

            # 查找__init__方法
            init_method = None
            for node in component_class.body:
                if isinstance(node, ast.FunctionDef) and node.name == '__init__':
                    init_method = node
                    break

            if not init_method:
                return None

            # 提取参数
            parameters = {}
            param_index = 0

            for arg in init_method.args.args:
                arg_name = arg.arg

                # 跳过self和name参数
                if arg_name in ['self', 'args', 'kwargs']:
                    continue
                if arg_name == 'name':
                    continue  # name是通用参数，跳过

                # 记录参数
                parameters[param_index] = arg_name
                param_index += 1

            GLOG.DEBUG(f"通过AST分析提取到组件 {component_name} 的参数: {parameters}")
            return parameters

        except Exception as e:
            GLOG.DEBUG(f"AST分析失败 {file_path}: {e}")
            return None

    def get_parameter_info(self, component_name: str, param_index: int,
                          file_content: str = None, component_type: str = None, file_id: str = None) -> str:
        """获取特定参数的名称"""
        param_mapping = self.extract_component_parameters(component_name, file_content, component_type, file_id)
        return param_mapping.get(param_index, f"param_{param_index}")

    def clear_cache(self):
        """清空缓存"""
        self._component_cache.clear()


# 全局实例
_component_extractor = ComponentParameterExtractor()


def get_component_parameter_names(component_name: str, file_content: str = None,
                                 component_type: str = None, file_id: str = None) -> Dict[int, str]:
    """便捷函数：获取组件参数名称映射"""
    return _component_extractor.extract_component_parameters(component_name, file_content, component_type, file_id)


def get_component_parameter_name(component_name: str, param_index: int,
                               file_content: str = None, component_type: str = None, file_id: str = None) -> str:
    """便捷函数：获取特定参数的名称"""
    return _component_extractor.get_parameter_info(component_name, param_index, file_content, component_type, file_id)