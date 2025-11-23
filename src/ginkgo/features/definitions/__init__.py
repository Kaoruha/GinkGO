"""
因子和指标定义模块 - 动态自动发现

通过自动发现机制，无需手动导入每个因子库。
所有继承BaseDefinition的类都会被自动发现和导出。
"""

import sys
from ginkgo.features.definitions.registry import factor_registry

# 自动发现所有因子库
try:
    discovered_libraries = factor_registry.discover_factor_libraries()
    
    # 动态导入所有发现的因子库类到当前模块
    _all_classes = []
    for lib_name, lib_class in discovered_libraries.items():
        # 将类添加到当前模块的全局命名空间
        globals()[lib_class.__name__] = lib_class
        _all_classes.append(lib_class.__name__)
    
    # 动态设置 __all__
    __all__ = _all_classes
    
    # 记录发现的因子库数量
    _discovery_info = {
        'discovered_count': len(discovered_libraries),
        'libraries': list(discovered_libraries.keys()),
        'classes': _all_classes
    }
    
except Exception as e:
    # 发现失败时的备用方案
    import warnings
    warnings.warn(f"因子库自动发现失败: {e}，将使用空的导出列表")
    __all__ = []
    _discovery_info = {
        'discovered_count': 0,
        'libraries': [],
        'classes': [],
        'error': str(e)
    }


def get_discovery_info():
    """获取自动发现的信息"""
    return _discovery_info.copy()


def reload_all_libraries():
    """重新加载所有因子库"""
    global __all__, _discovery_info
    
    try:
        # 清理当前导入的类
        for class_name in __all__:
            if class_name in globals():
                del globals()[class_name]
        
        # 重新发现
        discovered_libraries = factor_registry.discover_factor_libraries()
        
        # 重新导入
        _all_classes = []
        for lib_name, lib_class in discovered_libraries.items():
            globals()[lib_class.__name__] = lib_class
            _all_classes.append(lib_class.__name__)
        
        # 更新导出列表
        __all__ = _all_classes
        _discovery_info = {
            'discovered_count': len(discovered_libraries),
            'libraries': list(discovered_libraries.keys()),
            'classes': _all_classes
        }
        
        return True, f"成功重新加载 {len(discovered_libraries)} 个因子库"
        
    except Exception as e:
        return False, f"重新加载失败: {e}"


# 为了向后兼容，提供常用的因子库别名
def get_alpha158_factors():
    """获取Alpha158因子库"""
    return globals().get('Alpha158Factors', None)


def get_fama_french_factors():
    """获取Fama-French因子库"""
    return globals().get('FamaFrenchFactors', None)


def get_barra_factors():
    """获取Barra因子库"""
    return globals().get('BarraFactors', None)


# 便捷访问函数
def list_available_libraries():
    """列出所有可用的因子库"""
    return _discovery_info.get('libraries', [])


def list_available_classes():
    """列出所有可用的因子库类"""
    return _discovery_info.get('classes', [])