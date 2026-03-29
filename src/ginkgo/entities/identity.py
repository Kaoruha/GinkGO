# Upstream: 所有Ginkgo组件(Base类的子类)、系统管理工具(身份验证和解析)
# Downstream: uuid/hashlib/datetime(Python标准库)
# Role: IdentityUtils身份管理工具类提供ID生成/验证/解析功能，IdentityMixin身份感知混入类提供标准身份属性和方法






"""
Ginkgo Identity Management Module

统一的三层ID管理工具类：
- Component UUID: 组件实例唯一标识
- Engine ID: 组件装配关系标识  
- Run ID: 执行会话标识

Author: Ginkgo Team
Version: 1.0.0
"""

import uuid
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional


class IdentityUtils:
    """
    ID生成和管理工具类
    
    提供统一的ID生成、验证和解析功能，确保系统中所有组件
    遵循统一的身份标识规范。
    """
    
    @staticmethod
    def generate_component_uuid(prefix: str = "") -> str:
        """
        生成组件UUID
        
        Args:
            prefix (str): 可选的前缀，通常为组件类型
            
        Returns:
            str: 格式为 {prefix}_{uuid12} 或纯uuid12
            
        Examples:
            >>> IdentityUtils.generate_component_uuid("engine")
            'engine_a1b2c3d4e5f6'
            >>> IdentityUtils.generate_component_uuid()
            'a1b2c3d4e5f6'
        """
        base_uuid = uuid.uuid4().hex[:12]
        return f"{prefix}_{base_uuid}" if prefix else base_uuid
    
    @staticmethod
    def generate_engine_id_from_config(config_dict: Dict[str, Any]) -> str:
        """
        从配置生成稳定的engine_id
        
        基于配置内容的哈希值生成engine_id，确保相同配置
        产生相同的engine_id，不同配置产生不同的engine_id。
        
        Args:
            config_dict (Dict): 引擎配置字典
            
        Returns:
            str: 格式为 engine_{config_hash}_{random}
            
        Examples:
            >>> config = {"type": "historic", "name": "test"}
            >>> IdentityUtils.generate_engine_id_from_config(config)
            'engine_a1b2c3d4_e5f67890'
        """
        # 排序配置字典确保一致的哈希值
        config_str = str(sorted(config_dict.items()))
        config_hash = hashlib.md5(config_str.encode()).hexdigest()[:8]
        random_suffix = uuid.uuid4().hex[:8]
        return f"engine_{config_hash}_{random_suffix}"
    
    @staticmethod
    def generate_run_id(engine_id: str = None, sequence: int = 1) -> str:
        """
        生成运行ID（32位UUID格式，与uuid规则相同）

        Args:
            engine_id (str): 引擎ID（已废弃，保留用于兼容性）
            sequence (int): 执行序列号（已废弃，保留用于兼容性）

        Returns:
            str: 32位UUID hex字符串

        Examples:
            >>> IdentityUtils.generate_run_id()
            'a3b5c7d9e2f1a4b6c8d0e2f4a6b8c0d2'
        """
        import uuid
        return uuid.uuid4().hex
    
    @staticmethod
    def parse_run_id(run_id: str) -> Dict[str, Any]:
        """
        解析run_id获取组成信息

        注意：新格式的run_id是32位UUID，无时间戳信息。
        此方法主要用于验证格式。

        Args:
            run_id (str): 运行ID（32位UUID hex）

        Returns:
            Dict: 包含验证结果

        Examples:
            >>> IdentityUtils.parse_run_id("a3b5c7d9e2f1a4b6c8d0e2f4a6b8c0d2")
            {'valid': True, 'format': 'uuid32'}
        """
        import uuid
        try:
            # 尝试解析为 UUID
            if len(run_id) == 32:
                uuid.UUID(hex=run_id)
                return {'valid': True, 'format': 'uuid32'}
        except ValueError:
            pass

        return {'valid': False, 'error': 'Invalid run_id format'}

    @staticmethod
    def validate_uuid_format(uuid_str: str) -> bool:
        """
        验证UUID格式是否合法
        
        Args:
            uuid_str (str): 待验证的UUID字符串
            
        Returns:
            bool: True表示格式合法
        """
        if not uuid_str or not isinstance(uuid_str, str):
            return False
            
        # 支持标准UUID格式或简化格式
        if len(uuid_str) == 32:  # 简化格式：纯hex字符串
            try:
                int(uuid_str, 16)
                return True
            except ValueError:
                return False
        elif len(uuid_str) == 36:  # 标准格式：带连字符
            try:
                uuid.UUID(uuid_str)
                return True
            except ValueError:
                return False
        else:
            return False
    
    @staticmethod
    def validate_engine_id_format(engine_id: str) -> bool:
        """
        验证engine_id格式是否合法
        
        Args:
            engine_id (str): 待验证的引擎ID
            
        Returns:
            bool: True表示格式合法
        """
        if not engine_id or not isinstance(engine_id, str):
            return False
            
        parts = engine_id.split('_')
        return (
            len(parts) >= 3 and 
            parts[0] == 'engine' and
            len(parts[1]) == 8 and  # config hash
            len(parts[2]) == 8      # random suffix
        )
    
    @staticmethod
    def validate_run_id_format(run_id: str) -> bool:
        """
        验证run_id格式是否合法
        
        Args:
            run_id (str): 待验证的运行ID
            
        Returns:
            bool: True表示格式合法
        """
        parse_result = IdentityUtils.parse_run_id(run_id)
        return 'error' not in parse_result
    
    @staticmethod
    def get_identity_info(component_uuid: str = "", engine_id: str = "", 
                         run_id: str = "") -> Dict[str, Any]:
        """
        获取完整的身份信息摘要
        
        Args:
            component_uuid (str): 组件UUID
            engine_id (str): 引擎ID  
            run_id (str): 运行ID
            
        Returns:
            Dict: 包含身份验证结果和解析信息的字典
        """
        info = {
            'component_uuid': {
                'value': component_uuid,
                'valid': IdentityUtils.validate_uuid_format(component_uuid)
            },
            'engine_id': {
                'value': engine_id,
                'valid': IdentityUtils.validate_engine_id_format(engine_id)
            },
            'run_id': {
                'value': run_id,
                'valid': IdentityUtils.validate_run_id_format(run_id)
            }
        }
        
        # 解析run_id详细信息
        if run_id and info['run_id']['valid']:
            run_info = IdentityUtils.parse_run_id(run_id)
            if 'error' not in run_info:
                info['run_id']['parsed'] = run_info
        
        # 计算整体有效性
        info['all_valid'] = all(
            item['valid'] for item in info.values() 
            if isinstance(item, dict) and 'valid' in item
        )
        
        return info


class IdentityMixin:
    """
    身份感知混入类
    
    提供标准的身份属性和方法，可以被需要身份管理的类继承。
    简化了三层ID的管理和访问。
    """
    
    def __init__(self, component_type: str = "", engine_id: str = "", 
                 run_id: str = "", *args, **kwargs):
        """
        初始化身份信息
        
        Args:
            component_type (str): 组件类型，用于生成UUID前缀
            engine_id (str): 引擎ID
            run_id (str): 运行ID
        """
        super().__init__(*args, **kwargs)
        
        self._component_type = component_type
        self._engine_id = engine_id or ""
        self._run_id = run_id or ""
        
        # 生成组件UUID（如果未提供）
        if not hasattr(self, '_uuid') or not self._uuid:
            self._uuid = IdentityUtils.generate_component_uuid(component_type)
    
    @property
    def component_type(self) -> str:
        """组件类型"""
        return self._component_type
    
    @property
    def engine_id(self) -> str:
        """引擎装配ID"""
        return self._engine_id
    
    @engine_id.setter
    def engine_id(self, value: str) -> None:
        """设置引擎ID"""
        self._engine_id = value or ""
    
    @property
    def run_id(self) -> str:
        """运行会话ID"""
        return self._run_id
    
    @run_id.setter
    def run_id(self, value: str) -> None:
        """设置运行ID"""
        self._run_id = value or ""
    
    def get_identity_summary(self) -> Dict[str, Any]:
        """
        获取身份信息摘要
        
        Returns:
            Dict: 完整的身份信息和验证结果
        """
        return IdentityUtils.get_identity_info(
            component_uuid=getattr(self, '_uuid', ''),
            engine_id=self._engine_id,
            run_id=self._run_id
        )
    
    def bind_context(self, engine_id: str = "", run_id: str = "") -> None:
        """
        绑定执行上下文
        
        Args:
            engine_id (str): 引擎ID
            run_id (str): 运行ID
        """
        if engine_id:
            self._engine_id = engine_id
        if run_id:
            self._run_id = run_id