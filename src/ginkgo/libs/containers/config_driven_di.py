"""
配置驱动的依赖注入系统

支持通过配置文件定义服务、依赖关系和容器配置，实现声明式的DI管理。
"""

import os
import yaml
import json
from typing import Dict, Any, List, Optional, Type, Union
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from .base_container import BaseContainer
from .container_registry import registry
from .dependency_manager import dependency_manager, DependencyRule, DependencyType
from ginkgo.libs import GLOG, GCONF


class ConfigFormat(Enum):
    """配置文件格式"""
    YAML = "yaml"
    JSON = "json"


@dataclass
class ServiceConfig:
    """服务配置"""
    name: str
    class_path: str
    dependencies: List[str] = None
    singleton: bool = True
    lazy: bool = True
    factory_method: Optional[str] = None
    parameters: Dict[str, Any] = None


@dataclass
class ContainerConfig:
    """容器配置"""
    module_name: str
    services: List[ServiceConfig]
    dependencies: List[Dict[str, Any]] = None
    auto_register: bool = True


class ConfigDrivenDI:
    """
    配置驱动的依赖注入系统
    
    功能：
    - 从配置文件加载服务定义
    - 动态创建和配置容器
    - 自动注册跨模块依赖
    - 热重载配置支持
    """
    
    def __init__(self, config_dir: str = None):
        """
        初始化配置驱动DI系统
        
        Args:
            config_dir: 配置文件目录，默认使用 ~/.ginkgo/di/
        """
        self._config_dir = Path(config_dir or os.path.expanduser("~/.ginkgo/di/"))
        self._logger = GLOG
        
        # 确保配置目录存在
        self._config_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置缓存
        self._container_configs: Dict[str, ContainerConfig] = {}
        self._loaded_files: Dict[str, float] = {}  # 文件路径 -> 最后修改时间
        
        # 动态创建的容器
        self._dynamic_containers: Dict[str, BaseContainer] = {}
    
    def load_config_file(self, file_path: Union[str, Path], format: ConfigFormat = None) -> None:
        """
        加载配置文件
        
        Args:
            file_path: 配置文件路径
            format: 配置文件格式，如果不指定则根据文件扩展名判断
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {file_path}")
        
        # 确定文件格式
        if format is None:
            if file_path.suffix.lower() in ['.yml', '.yaml']:
                format = ConfigFormat.YAML
            elif file_path.suffix.lower() == '.json':
                format = ConfigFormat.JSON
            else:
                raise ValueError(f"无法确定配置文件格式: {file_path}")
        
        # 读取配置内容
        with open(file_path, 'r', encoding='utf-8') as f:
            if format == ConfigFormat.YAML:
                config_data = yaml.safe_load(f)
            else:
                config_data = json.load(f)
        
        # 解析配置
        container_config = self._parse_config(config_data, file_path.name)
        
        # 缓存配置
        self._container_configs[container_config.module_name] = container_config
        self._loaded_files[str(file_path)] = file_path.stat().st_mtime
        
        self._logger.INFO(f"已加载配置文件: {file_path}")
    
    def load_config_directory(self, directory: Union[str, Path] = None) -> None:
        """
        加载配置目录中的所有配置文件
        
        Args:
            directory: 配置目录，默认使用构造函数中指定的目录
        """
        if directory is None:
            directory = self._config_dir
        else:
            directory = Path(directory)
        
        if not directory.exists():
            self._logger.WARNING(f"配置目录不存在: {directory}")
            return
        
        # 加载所有配置文件
        config_files = list(directory.glob("*.yml")) + list(directory.glob("*.yaml")) + list(directory.glob("*.json"))
        
        for config_file in config_files:
            try:
                self.load_config_file(config_file)
            except Exception as e:
                self._logger.ERROR(f"加载配置文件失败 {config_file}: {e}")
    
    def _parse_config(self, config_data: Dict[str, Any], file_name: str) -> ContainerConfig:
        """解析配置数据"""
        if 'container' not in config_data:
            raise ValueError(f"配置文件中缺少 'container' 节点: {file_name}")
        
        container_data = config_data['container']
        module_name = container_data.get('module_name')
        if not module_name:
            raise ValueError(f"配置文件中缺少 'module_name': {file_name}")
        
        # 解析服务配置
        services = []
        if 'services' in container_data:
            for service_data in container_data['services']:
                service_config = ServiceConfig(
                    name=service_data['name'],
                    class_path=service_data['class_path'],
                    dependencies=service_data.get('dependencies', []),
                    singleton=service_data.get('singleton', True),
                    lazy=service_data.get('lazy', True),
                    factory_method=service_data.get('factory_method'),
                    parameters=service_data.get('parameters', {})
                )
                services.append(service_config)
        
        # 解析依赖配置
        dependencies = container_data.get('dependencies', [])
        auto_register = container_data.get('auto_register', True)
        
        return ContainerConfig(
            module_name=module_name,
            services=services,
            dependencies=dependencies,
            auto_register=auto_register
        )
    
    def create_containers(self) -> None:
        """根据配置创建所有容器"""
        for module_name, config in self._container_configs.items():
            try:
                self._create_container(config)
            except Exception as e:
                self._logger.ERROR(f"创建容器失败 {module_name}: {e}")
    
    def _create_container(self, config: ContainerConfig) -> BaseContainer:
        """创建单个容器"""
        if config.module_name in self._dynamic_containers:
            self._logger.DEBUG(f"容器已存在，跳过创建: {config.module_name}")
            return self._dynamic_containers[config.module_name]
        
        # 创建动态容器类
        DynamicContainer = self._create_container_class(config)
        
        # 实例化容器
        container = DynamicContainer()
        
        # 缓存容器
        self._dynamic_containers[config.module_name] = container
        
        # 自动注册到全局注册表
        if config.auto_register:
            registry.register(container)
        
        # 配置跨模块依赖
        self._configure_dependencies(config)
        
        self._logger.INFO(f"已创建容器: {config.module_name}")
        return container
    
    def _create_container_class(self, config: ContainerConfig) -> Type[BaseContainer]:
        """动态创建容器类"""
        
        class DynamicContainer(BaseContainer):
            module_name = config.module_name
            
            def __init__(self):
                super().__init__()
                self._config = config
            
            def configure(self) -> None:
                """配置容器服务"""
                for service_config in self._config.services:
                    try:
                        # 动态导入服务类
                        service_class = self._import_class(service_config.class_path)
                        
                        # 创建工厂方法（如果指定）
                        factory_method = None
                        if service_config.factory_method:
                            factory_method = getattr(service_class, service_config.factory_method)
                        
                        # 绑定服务
                        self.bind(
                            name=service_config.name,
                            service_class=service_class,
                            dependencies=service_config.dependencies,
                            singleton=service_config.singleton,
                            factory_method=factory_method,
                            lazy=service_config.lazy
                        )
                        
                        GLOG.DEBUG(f"已绑定服务: {service_config.name}")
                        
                    except Exception as e:
                        GLOG.ERROR(f"绑定服务失败 {service_config.name}: {e}")
                        raise
            
            def _import_class(self, class_path: str) -> Type:
                """动态导入类"""
                try:
                    module_path, class_name = class_path.rsplit('.', 1)
                    module = __import__(module_path, fromlist=[class_name])
                    return getattr(module, class_name)
                except Exception as e:
                    raise ImportError(f"无法导入类 {class_path}: {e}")
        
        return DynamicContainer
    
    def _configure_dependencies(self, config: ContainerConfig) -> None:
        """配置跨模块依赖"""
        if not config.dependencies:
            return
        
        for dep_config in config.dependencies:
            try:
                rule = DependencyRule(
                    source_module=config.module_name,
                    target_module=dep_config['target_module'],
                    service_name=dep_config['service_name'],
                    dependency_type=DependencyType(dep_config.get('type', 'required')),
                    alias=dep_config.get('alias'),
                    conditions=dep_config.get('conditions', {}),
                    timeout=dep_config.get('timeout', 30.0)
                )
                
                dependency_manager.add_dependency_rule(rule)
                
            except Exception as e:
                self._logger.ERROR(f"配置依赖失败 {dep_config}: {e}")
    
    def reload_configs(self) -> None:
        """重新加载配置文件（检查文件修改时间）"""
        reloaded_files = []
        
        for file_path, last_mtime in self._loaded_files.items():
            current_mtime = Path(file_path).stat().st_mtime
            if current_mtime > last_mtime:
                try:
                    self.load_config_file(file_path)
                    reloaded_files.append(file_path)
                except Exception as e:
                    self._logger.ERROR(f"重新加载配置失败 {file_path}: {e}")
        
        if reloaded_files:
            self._logger.INFO(f"已重新加载配置文件: {reloaded_files}")
            # 重新创建受影响的容器
            self._recreate_affected_containers(reloaded_files)
    
    def _recreate_affected_containers(self, reloaded_files: List[str]) -> None:
        """重新创建受影响的容器"""
        # 简单实现：重新创建所有容器
        # 更复杂的实现可以分析哪些容器受到影响
        for module_name in list(self._dynamic_containers.keys()):
            try:
                # 注销旧容器
                registry.unregister(module_name)
                del self._dynamic_containers[module_name]
                
                # 重新创建容器
                if module_name in self._container_configs:
                    self._create_container(self._container_configs[module_name])
                
            except Exception as e:
                self._logger.ERROR(f"重新创建容器失败 {module_name}: {e}")
    
    def export_config_template(self, output_path: Union[str, Path], format: ConfigFormat = ConfigFormat.YAML) -> None:
        """
        导出配置模板文件
        
        Args:
            output_path: 输出文件路径
            format: 输出格式
        """
        template = {
            'container': {
                'module_name': 'example_module',
                'auto_register': True,
                'services': [
                    {
                        'name': 'example_service',
                        'class_path': 'ginkgo.example.services.ExampleService',
                        'dependencies': ['dependency_service'],
                        'singleton': True,
                        'lazy': True,
                        'factory_method': None,
                        'parameters': {
                            'param1': 'value1',
                            'param2': 42
                        }
                    }
                ],
                'dependencies': [
                    {
                        'target_module': 'other_module',
                        'service_name': 'dependency_service',
                        'type': 'required',
                        'alias': None,
                        'conditions': {
                            'container_state': 'ready'
                        },
                        'timeout': 30.0
                    }
                ]
            }
        }
        
        output_path = Path(output_path)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            if format == ConfigFormat.YAML:
                yaml.dump(template, f, default_flow_style=False, allow_unicode=True)
            else:
                json.dump(template, f, indent=2, ensure_ascii=False)
        
        self._logger.INFO(f"已导出配置模板: {output_path}")
    
    def validate_configs(self) -> List[str]:
        """
        验证所有配置
        
        Returns:
            验证错误列表
        """
        errors = []
        
        for module_name, config in self._container_configs.items():
            # 验证服务类是否可导入
            for service_config in config.services:
                try:
                    module_path, class_name = service_config.class_path.rsplit('.', 1)
                    __import__(module_path, fromlist=[class_name])
                except Exception as e:
                    errors.append(f"无法导入服务类 {service_config.class_path}: {e}")
            
            # 验证依赖关系
            for dep_config in config.dependencies:
                if 'target_module' not in dep_config:
                    errors.append(f"依赖配置缺少 target_module: {dep_config}")
                if 'service_name' not in dep_config:
                    errors.append(f"依赖配置缺少 service_name: {dep_config}")
        
        return errors
    
    def get_config_info(self) -> Dict[str, Any]:
        """获取配置信息"""
        return {
            'config_directory': str(self._config_dir),
            'loaded_files': list(self._loaded_files.keys()),
            'container_configs': {
                module_name: {
                    'services_count': len(config.services),
                    'dependencies_count': len(config.dependencies or []),
                    'auto_register': config.auto_register
                }
                for module_name, config in self._container_configs.items()
            },
            'dynamic_containers': list(self._dynamic_containers.keys())
        }


# 全局配置驱动DI实例
config_driven_di = ConfigDrivenDI()