# Upstream: External Applications
# Downstream: Trading Strategies, Analysis Tools
# Role: Features因子模块依赖注入容器管理表达式/因子等引擎的依赖注入支持交易系统功能和组件集成提供完整业务支持






"""
Features Module DI Container - 特征模块依赖注入容器

参考data模块设计，实现完整的三层架构：
- Definitions: 因子定义层 (动态自动发现)
- Engines: 引擎层  
- Services: 服务层
"""

from dependency_injector import containers, providers
from ginkgo.libs import GLOG

# 导入引擎层
from ginkgo.features.engines import FactorEngine, ExpressionEngine, ExpressionParser, OperatorRegistry
# 导入服务层
from ginkgo.features.services import FactorService, ExpressionService
# 导入自动发现机制
from ginkgo.features.definitions.registry import factor_registry, auto_discover_factor_libraries


class FeatureContainer(containers.DynamicContainer):
    """动态特征模块DI容器 - 自动发现因子库"""
    
    # 引擎层 - 核心计算引擎
    expression_parser = providers.Singleton(ExpressionParser)
    operator_registry = providers.Singleton(OperatorRegistry)
    
    expression_engine = providers.Singleton(
        ExpressionEngine,
        parser=expression_parser
    )
    
    # FactorEngine需要外部依赖注入
    factor_engine = providers.Singleton(
        FactorEngine,
        factor_service=providers.Dependency(),  # 来自data模块
        bar_service=providers.Dependency(),     # 来自data模块  
        expression_parser=expression_parser
    )
    
    # 服务层 - 高级业务逻辑
    expression_service = providers.Singleton(
        ExpressionService,
        expression_engine=expression_engine
    )
    
    factor_service = providers.Singleton(
        FactorService,
        factor_engine=factor_engine,
        expression_engine=expression_engine
    )
    
    def __init__(self):
        """初始化容器并设置动态definitions"""
        super().__init__()
        self._setup_dynamic_definitions()
    
    def _setup_dynamic_definitions(self):
        """动态设置definitions聚合"""
        try:
            # 自动发现所有因子库
            discovered_libraries = auto_discover_factor_libraries()
            
            if not discovered_libraries:
                GLOG.WARN("未发现任何因子库，使用空的definitions聚合")
                # 动态设置空的definitions聚合
                self.set_provider('definitions', providers.FactoryAggregate())
                return
            
            # 动态创建Factory providers
            factory_providers = {}
            for lib_name, lib_class in discovered_libraries.items():
                # 使用正确的闭包捕获类 - 直接传递类而不是lambda
                factory_providers[lib_name] = providers.Factory(lib_class)
                GLOG.INFO(f"注册因子库: {lib_name} -> {lib_class.__name__}")
            
            # 动态设置definitions聚合
            definitions_aggregate = providers.FactoryAggregate(**factory_providers)
            self.set_provider('definitions', definitions_aggregate)
            GLOG.INFO(f"设置definitions聚合成功，包含 {len(factory_providers)} 个因子库")
            
            GLOG.INFO(f"动态注册完成，共发现 {len(discovered_libraries)} 个因子库")
            
        except Exception as e:
            GLOG.ERROR(f"动态设置definitions失败: {e}")
            import traceback
            GLOG.ERROR(f"详细错误: {traceback.format_exc()}")
            # 失败时设置空的聚合，确保容器能正常工作
            self.set_provider('definitions', providers.FactoryAggregate())
            # 不要重新抛出异常，让容器继续工作
    
    def reload_definitions(self):
        """重新加载所有因子库定义"""
        try:
            GLOG.INFO("重新加载因子库定义...")
            self._setup_dynamic_definitions()
            GLOG.INFO("因子库定义重新加载完成")
        except Exception as e:
            GLOG.ERROR(f"重新加载因子库定义失败: {e}")
            raise
    
    def get_registered_libraries(self) -> dict:
        """获取已注册的因子库信息"""
        return factor_registry.get_library_metadata()
    
    def validate_definitions(self) -> dict:
        """验证所有因子库定义"""
        return factor_registry.validate_libraries()


# 添加聚合层到容器
FeatureContainer.engines = providers.FactoryAggregate(
    factor=FeatureContainer.factor_engine,
    expression=FeatureContainer.expression_engine,
    parser=FeatureContainer.expression_parser,
    registry=FeatureContainer.operator_registry,
)

FeatureContainer.services = providers.FactoryAggregate(
    factor=FeatureContainer.factor_service,
    expression=FeatureContainer.expression_service,
)

# 保持向后兼容的Container别名
Container = FeatureContainer
DynamicContainer = FeatureContainer

# 导出容器实例
feature_container = Container()


def configure_features_container(data_container):
    """
    配置features容器的外部依赖
    
    Args:
        data_container: data模块的容器实例
    """
    try:
        # 注入data模块的服务到FactorEngine
        feature_container.factor_engine.override(
            providers.Singleton(
                FactorEngine,
                factor_service=data_container.factor_service,
                bar_service=data_container.bar_service,
                expression_parser=feature_container.expression_parser
            )
        )
        
        from ginkgo.libs import GLOG
        GLOG.INFO("Features container configured successfully")
        
    except Exception as e:
        from ginkgo.libs import GLOG
        GLOG.ERROR(f"Failed to configure features container: {e}")
        raise


def get_service_info():
    """获取服务信息的便捷函数 - 动态版本"""
    try:
        # 获取动态发现的因子库信息
        library_summary = factor_registry.get_library_summary()
        library_metadata = factor_registry.get_library_metadata()
        
        # 构建因子库详细信息
        factor_libraries_detail = []
        for lib_name, metadata in library_metadata.items():
            detail = f"{lib_name} - {metadata.get('name', lib_name)} ({metadata.get('expression_count', 0)}个因子)"
            factor_libraries_detail.append(detail)
        
        return {
            "definitions_count": library_summary.get('total_libraries', 0),
            "total_expressions": library_summary.get('total_expressions', 0),
            "total_categories": library_summary.get('total_categories', 0),
            "engines_count": 4,       # factor, expression, parser, registry  
            "services_count": 2,      # factor, expression
            "container_configured": True,
            "dynamic_discovery": True,
            "factor_libraries": library_summary.get('libraries', []),
            "factor_libraries_detail": factor_libraries_detail,
            "largest_library": library_summary.get('largest_library', None)
        }
    except Exception as e:
        GLOG.ERROR(f"获取服务信息失败: {e}")
        return {
            "definitions_count": 0,
            "engines_count": 4,
            "services_count": 2,
            "container_configured": False,
            "dynamic_discovery": True,
            "error": str(e)
        }


def get_factor_library_status():
    """获取因子库状态和验证结果"""
    try:
        validation_results = factor_registry.validate_libraries()
        library_summary = factor_registry.get_library_summary()
        
        # 统计验证结果
        valid_libraries = [lib for lib, errors in validation_results.items() if not errors]
        invalid_libraries = {lib: errors for lib, errors in validation_results.items() if errors}
        
        return {
            "total_libraries": library_summary.get('total_libraries', 0),
            "valid_libraries": len(valid_libraries),
            "invalid_libraries": len(invalid_libraries),
            "validation_details": validation_results,
            "library_summary": library_summary
        }
    except Exception as e:
        GLOG.ERROR(f"获取因子库状态失败: {e}")
        return {"error": str(e)}