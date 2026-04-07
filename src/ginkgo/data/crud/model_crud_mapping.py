# Upstream: ModelConversion, CRUD自动注册机制
# Downstream: GLOG日志
# Role: Model-CRUD映射注册表，维护数据库Model类到CRUD类的映射关系，支持注册和查询






"""
Model-CRUD映射表

管理Model类到CRUD类的映射关系，支持自动注册和手动注册
"""

from typing import Type, Dict, List, Optional
from ginkgo.libs import GLOG


class ModelCRUDMapping:
    """
    Model-CRUD映射表

    维护Model类到CRUD类的映射关系，支持自动注册和手动注册
    """
    _registry: Dict[Type, Type] = {}

    @classmethod
    def register(cls, model_class: Type, crud_class: Type) -> None:
        """
        注册Model-CRUD映射关系

        Args:
            model_class: Model类 (如 MBar)
            crud_class: CRUD类 (如 BarCRUD)
        """
        cls._registry[model_class] = crud_class
        GLOG.DEBUG(f"Registered mapping: {model_class.__name__} → {crud_class.__name__}")

    @classmethod
    def get_crud_class(cls, model_class: Type) -> Optional[Type]:
        """
        获取Model对应的CRUD类

        Args:
            model_class: Model类

        Returns:
            CRUD类或None
        """
        return cls._registry.get(model_class)

    @classmethod
    def get_all_mappings(cls) -> Dict[Type, Type]:
        """获取所有注册的映射关系"""
        return cls._registry.copy()

    @classmethod
    def is_registered(cls, model_class: Type) -> bool:
        """检查Model类是否已注册"""
        return model_class in cls._registry

    @classmethod
    def debug_print_relationships(cls) -> None:
        """调试：打印所有关系"""
        GLOG.INFO("🔗 Model-CRUD 关系映射:")
        for model_class, crud_class in cls._registry.items():
            GLOG.INFO(f"  {model_class.__name__} ↔ {crud_class.__name__}")

    @classmethod
    def validate_all_relationships(cls) -> List[str]:
        """验证所有注册关系"""
        issues = []
        for model_class, crud_class in cls._registry.items():
            try:
                # 验证是否可以实例化
                crud_instance = crud_class()
                # 验证泛型类型匹配
                if hasattr(crud_instance, 'model_class'):
                    if crud_instance.model_class != model_class:
                        issues.append(f"类型不匹配: {model_class.__name__} ≠ {crud_instance.model_class.__name__}")
            except Exception as e:
                issues.append(f"实例化失败: {crud_class.__name__} - {e}")

        if issues:
            GLOG.ERROR(f"Model-CRUD关系验证发现问题: {issues}")
        else:
            GLOG.INFO("✅ 所有Model-CRUD关系验证通过")

        return issues

    @classmethod
    def clear_mapping(cls) -> None:
        """清空映射表（主要用于测试）"""
        cls._registry.clear()
        GLOG.DEBUG("ModelCRUDMapping cleared")


# 开发时辅助工具
class MappingDevelopmentTools:
    @staticmethod
    def manually_register_relationships() -> None:
        """手动注册所有关系"""
        try:
            from ginkgo.data.models import MBar, MTradeDay, MStockInfo
            from ginkgo.data.crud.bar_crud import BarCRUD
            from ginkgo.data.crud.trade_day_crud import TradeDayCRUD
            from ginkgo.data.crud.stock_info_crud import StockInfoCRUD

            ModelCRUDMapping.register(MBar, BarCRUD)
            ModelCRUDMapping.register(MTradeDay, TradeDayCRUD)
            ModelCRUDMapping.register(MStockInfo, StockInfoCRUD)

            GLOG.INFO("✅ 手动注册完成")
        except ImportError as e:
            GLOG.ERROR(f"手动注册失败: {e}")

    @staticmethod
    def check_missing_registrations() -> List[str]:
        """检查哪些Model缺少CRUD注册"""
        try:
            from ginkgo.data.models import MBar, MTradeDay, MStockInfo

            models = [MBar, MTradeDay, MStockInfo]
            missing = []

            for model in models:
                if not ModelCRUDMapping.is_registered(model):
                    missing.append(model.__name__)

            if missing:
                GLOG.WARN(f"❌ 缺少注册的Model: {missing}")
            else:
                GLOG.INFO("✅ 所有Model都已注册")

            return missing
        except ImportError as e:
            GLOG.ERROR(f"检查注册失败: {e}")
            return []
