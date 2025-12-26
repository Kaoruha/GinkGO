"""
因子库自动发现和注册机制

通过扫描definitions目录自动发现继承BaseDefinition的类，
实现动态注册，无需手动修改容器代码。
"""

import os
import importlib
import inspect
from typing import Dict, Type, List, Tuple, Any
from pathlib import Path
from ginkgo.libs import GLOG


class FactorLibraryRegistry:
    """因子库注册表 - 自动发现和管理因子库"""
    
    def __init__(self):
        self._libraries: Dict[str, Type] = {}
        self._metadata: Dict[str, dict] = {}
        self._discovery_cache: Dict[str, Tuple[str, Type]] = {}
        self._factor_index: Dict[str, dict] = {}  # 因子索引: {library: {factor: expression}}
    
    def discover_factor_libraries(self, definitions_path: str = None) -> Dict[str, Type]:
        """
        自动发现definitions目录下的所有因子库
        
        Args:
            definitions_path: definitions目录路径，默认为当前模块所在目录
            
        Returns:
            Dict: {library_name: library_class} 的映射
        """
        if definitions_path is None:
            definitions_path = os.path.dirname(__file__)
            
        discovered_libraries = {}
        
        try:
            # 获取所有Python文件
            python_files = [f for f in os.listdir(definitions_path) 
                          if f.endswith('.py') and not f.startswith('_')]
            
            for py_file in python_files:
                module_name = py_file[:-3]  # 移除.py后缀
                
                # 跳过特殊模块
                if module_name in ['base', 'registry']:
                    continue
                    
                try:
                    # 动态导入模块
                    module_path = f"ginkgo.features.definitions.{module_name}"
                    module = importlib.import_module(module_path)
                    
                    # 扫描模块中的类
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        # 检查是否继承BaseDefinition且不是BaseDefinition本身
                        if (hasattr(obj, '__bases__') and 
                            any(base.__name__ == 'BaseDefinition' for base in obj.__bases__) and
                            obj.__name__ != 'BaseDefinition'):
                            
                            # 生成库名称 (转换为snake_case)
                            library_name = self._generate_library_name(obj.__name__)
                            discovered_libraries[library_name] = obj
                            
                            # 缓存发现结果
                            self._discovery_cache[library_name] = (module_name, obj)
                            
                            # 收集元数据
                            self._collect_metadata(library_name, obj)
                            
                            GLOG.INFO(f"发现因子库: {library_name} ({obj.__name__})")
                            
                except ImportError as e:
                    GLOG.WARN(f"无法导入模块 {module_name}: {e}")
                except Exception as e:
                    GLOG.ERROR(f"处理模块 {module_name} 时出错: {e}")
                    
        except Exception as e:
            GLOG.ERROR(f"扫描definitions目录时出错: {e}")
            
        self._libraries.update(discovered_libraries)
        GLOG.INFO(f"自动发现 {len(discovered_libraries)} 个因子库")
        
        return discovered_libraries
    
    def _generate_library_name(self, class_name: str) -> str:
        """
        将类名转换为库名称 (CamelCase -> snake_case)
        
        Args:
            class_name: 类名，如 "Alpha158Factors"
            
        Returns:
            str: 库名称，如 "alpha158_factors" -> "alpha158"
        """
        # 将CamelCase转换为snake_case
        import re
        snake_case = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', class_name)
        snake_case = re.sub('([a-z0-9])([A-Z])', r'\1_\2', snake_case).lower()
        
        # 移除常见的后缀
        suffixes_to_remove = ['_factors', '_indicators', '_library', '_collection']
        for suffix in suffixes_to_remove:
            if snake_case.endswith(suffix):
                snake_case = snake_case[:-len(suffix)]
                break
                
        return snake_case
    
    def _collect_metadata(self, library_name: str, library_class: Type):
        """收集因子库的元数据并执行因子去重"""
        try:
            # 获取原始表达式和分类
            raw_expressions = getattr(library_class, 'EXPRESSIONS', {})
            categories = getattr(library_class, 'CATEGORIES', {})
            
            # 执行因子去重逻辑
            deduplicated_expressions, duplicate_stats = self._deduplicate_factors(
                library_name, raw_expressions
            )
            
            # 构建元数据
            metadata = {
                'class_name': library_class.__name__,
                'name': getattr(library_class, 'NAME', library_name),
                'description': getattr(library_class, 'DESCRIPTION', ''),
                'raw_expression_count': len(raw_expressions),
                'expression_count': len(deduplicated_expressions),
                'duplicate_count': duplicate_stats['duplicate_count'],
                'duplicate_factors': duplicate_stats['duplicates'],
                'category_count': len(categories),
                'module': library_class.__module__,
                'file_path': inspect.getfile(library_class) if hasattr(library_class, '__file__') else None
            }
            
            # 获取分类信息
            if categories:
                metadata['categories'] = list(categories.keys())
                metadata['largest_category'] = max(categories.keys(), 
                                                 key=lambda k: len(categories[k]))
            
            # 存储去重后的表达式到索引
            if not hasattr(self, '_factor_index'):
                self._factor_index = {}
            self._factor_index[library_name] = deduplicated_expressions
            
            self._metadata[library_name] = metadata
            
            # 输出统计信息
            if duplicate_stats['duplicate_count'] > 0:
                GLOG.INFO(f"库 '{library_name}' 注册完成: {len(raw_expressions)}个原始因子 → "
                         f"{len(deduplicated_expressions)}个唯一因子 "
                         f"({duplicate_stats['duplicate_count']}个重复已跳过)")
            else:
                GLOG.INFO(f"库 '{library_name}' 注册完成: {len(deduplicated_expressions)}个因子")
            
        except Exception as e:
            GLOG.WARN(f"收集 {library_name} 元数据时出错: {e}")

    def _deduplicate_factors(self, library_name: str, expressions: dict) -> tuple:
        """
        因子去重处理 - 先到先得策略
        
        Args:
            library_name: 库名称
            expressions: 原始表达式字典
            
        Returns:
            tuple: (去重后表达式字典, 统计信息)
        """
        deduplicated = {}
        seen_factors = set()
        duplicates = []
        
        # 遍历表达式，保留首次遇到的因子
        for factor_name, expression in expressions.items():
            if factor_name in seen_factors:
                # 发现重复因子
                duplicates.append({
                    'factor_name': factor_name,
                    'expression': expression,
                    'position': len(deduplicated) + len(duplicates)  # 在原始字典中的位置
                })
                
                # 记录警告但不中断流程
                GLOG.WARN(f"库 '{library_name}' 跳过重复因子 '{factor_name}' "
                           f"(首次定义已在position {list(expressions.keys()).index(factor_name)})")
            else:
                # 首次遇到的因子，正常注册
                deduplicated[factor_name] = expression
                seen_factors.add(factor_name)
        
        # 构建统计信息
        stats = {
            'duplicate_count': len(duplicates),
            'duplicates': duplicates,
            'unique_count': len(deduplicated),
            'original_count': len(expressions)
        }
        
        return deduplicated, stats
    
    def get_registered_libraries(self) -> Dict[str, Type]:
        """获取所有已注册的因子库"""
        return self._libraries.copy()
    
    def get_library_metadata(self, library_name: str = None) -> dict:
        """获取因子库元数据"""
        if library_name:
            return self._metadata.get(library_name, {})
        return self._metadata.copy()
    
    def register_library(self, library_name: str, library_class: Type):
        """手动注册因子库"""
        self._libraries[library_name] = library_class
        self._collect_metadata(library_name, library_class)
        GLOG.INFO(f"手动注册因子库: {library_name}")
    
    def unregister_library(self, library_name: str):
        """注销因子库"""
        if library_name in self._libraries:
            del self._libraries[library_name]
            self._metadata.pop(library_name, None)
            self._discovery_cache.pop(library_name, None)
            GLOG.INFO(f"注销因子库: {library_name}")
    
    def get_library_summary(self) -> dict:
        """获取因子库汇总信息"""
        total_expressions = sum(meta.get('expression_count', 0) 
                              for meta in self._metadata.values())
        total_categories = sum(meta.get('category_count', 0) 
                             for meta in self._metadata.values())
        
        return {
            'total_libraries': len(self._libraries),
            'total_expressions': total_expressions,
            'total_categories': total_categories,
            'libraries': list(self._libraries.keys()),
            'largest_library': max(self._metadata.keys(), 
                                 key=lambda k: self._metadata[k].get('expression_count', 0))
                                 if self._metadata else None
        }
    
    def reload_library(self, library_name: str):
        """重新加载指定的因子库"""
        if library_name in self._discovery_cache:
            module_name, old_class = self._discovery_cache[library_name]
            try:
                # 重新导入模块
                module_path = f"ginkgo.features.definitions.{module_name}"
                module = importlib.reload(importlib.import_module(module_path))
                
                # 重新获取类
                new_class = getattr(module, old_class.__name__)
                
                # 更新注册表
                self._libraries[library_name] = new_class
                self._discovery_cache[library_name] = (module_name, new_class)
                self._collect_metadata(library_name, new_class)
                
                GLOG.INFO(f"重新加载因子库: {library_name}")
                
            except Exception as e:
                GLOG.ERROR(f"重新加载 {library_name} 失败: {e}")
    
    def validate_libraries(self) -> Dict[str, List[str]]:
        """验证所有注册的因子库"""
        validation_results = {}
        
        for library_name, library_class in self._libraries.items():
            errors = []
            
            # 检查必需属性
            required_attrs = ['NAME', 'DESCRIPTION', 'EXPRESSIONS', 'CATEGORIES']
            for attr in required_attrs:
                if not hasattr(library_class, attr):
                    errors.append(f"缺少必需属性: {attr}")
            
            # 检查表达式格式
            if hasattr(library_class, 'EXPRESSIONS'):
                expressions = getattr(library_class, 'EXPRESSIONS')
                if not isinstance(expressions, dict):
                    errors.append("EXPRESSIONS 必须是字典类型")
                elif not expressions:
                    errors.append("EXPRESSIONS 不能为空")
            
            # 检查分类格式
            if hasattr(library_class, 'CATEGORIES'):
                categories = getattr(library_class, 'CATEGORIES')
                if not isinstance(categories, dict):
                    errors.append("CATEGORIES 必须是字典类型")
            
            validation_results[library_name] = errors
            
        return validation_results

    # ===== 因子查询API =====
    
    def get_all_factors(self) -> Dict[str, Dict[str, str]]:
        """
        获取所有库的所有因子
        
        Returns:
            Dict: {library: {factor: expression}}
        """
        return self._factor_index.copy()
    
    def get_factors_by_library(self, library_name: str) -> Dict[str, str]:
        """
        获取指定库的所有因子
        
        Args:
            library_name: 库名称
            
        Returns:
            Dict: {factor: expression}
        """
        return self._factor_index.get(library_name, {}).copy()
    
    def find_factor(self, factor_name: str, library_name: str = None) -> Dict[str, Any]:
        """
        查找因子 - 支持精确和模糊查询
        
        Args:
            factor_name: 因子名称
            library_name: 可选的库名称，用于精确查询
            
        Returns:
            Dict: 查询结果
        """
        result = {
            'factor_name': factor_name,
            'matches': [],
            'total_matches': 0
        }
        
        if library_name:
            # 精确查询：library.factor
            if library_name in self._factor_index:
                library_factors = self._factor_index[library_name]
                if factor_name in library_factors:
                    match = {
                        'library': library_name,
                        'factor_name': factor_name,
                        'expression': library_factors[factor_name],
                        'library_metadata': self._metadata.get(library_name, {})
                    }
                    result['matches'].append(match)
                    result['total_matches'] = 1
        else:
            # 模糊查询：在所有库中搜索
            for lib_name, factors in self._factor_index.items():
                if factor_name in factors:
                    match = {
                        'library': lib_name,
                        'factor_name': factor_name,
                        'expression': factors[factor_name],
                        'library_metadata': self._metadata.get(lib_name, {})
                    }
                    result['matches'].append(match)
            
            result['total_matches'] = len(result['matches'])
        
        return result
    
    def search_factors(self, keyword: str) -> Dict[str, Any]:
        """
        关键词搜索因子
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            Dict: 搜索结果
        """
        result = {
            'keyword': keyword,
            'matches': [],
            'total_matches': 0
        }
        
        keyword_lower = keyword.lower()
        
        for lib_name, factors in self._factor_index.items():
            for factor_name, expression in factors.items():
                if (keyword_lower in factor_name.lower() or 
                    keyword_lower in expression.lower()):
                    
                    match = {
                        'library': lib_name,
                        'factor_name': factor_name,
                        'expression': expression,
                        'match_type': 'name' if keyword_lower in factor_name.lower() else 'expression'
                    }
                    result['matches'].append(match)
        
        result['total_matches'] = len(result['matches'])
        return result
    
    def get_factors_by_category(self, category: str, library_name: str = None) -> Dict[str, Any]:
        """
        按分类获取因子
        
        Args:
            category: 分类名称
            library_name: 可选的库名称过滤
            
        Returns:
            Dict: 分类查询结果
        """
        result = {
            'category': category,
            'matches': [],
            'total_matches': 0
        }
        
        libraries_to_search = ([library_name] if library_name else 
                              list(self._libraries.keys()))
        
        for lib_name in libraries_to_search:
            if lib_name not in self._libraries:
                continue
                
            library_class = self._libraries[lib_name]
            categories = getattr(library_class, 'CATEGORIES', {})
            
            if category in categories:
                factor_names = categories[category]
                library_factors = self._factor_index.get(lib_name, {})
                
                for factor_name in factor_names:
                    if factor_name in library_factors:
                        match = {
                            'library': lib_name,
                            'factor_name': factor_name,
                            'expression': library_factors[factor_name],
                            'category': category
                        }
                        result['matches'].append(match)
        
        result['total_matches'] = len(result['matches'])
        return result


# 全局注册表实例
factor_registry = FactorLibraryRegistry()


def auto_discover_factor_libraries() -> Dict[str, Type]:
    """便捷函数：自动发现因子库"""
    return factor_registry.discover_factor_libraries()


def get_factor_library_info() -> dict:
    """便捷函数：获取因子库汇总信息"""
    return factor_registry.get_library_summary()