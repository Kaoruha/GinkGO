# Ginkgo 模块化DI容器架构 - 快速开始

## 概述

Ginkgo的新模块化依赖注入(DI)容器架构允许每个模块拥有独立的容器，同时保持跨模块的依赖解析和协调能力。

## 核心组件

- **BaseContainer**: 所有模块容器的抽象基类
- **ContainerRegistry**: 全局容器注册表，管理所有模块容器
- **ApplicationContainer**: 应用级容器，提供统一的服务访问接口
- **CrossContainerProxy**: 跨容器服务代理，实现透明的跨模块服务访问

## 快速开始

### 1. 使用现有的数据模块容器

```python
from ginkgo.libs.containers import app_container
from ginkgo.data.module_container import data_container

# 注册数据模块容器
app_container.register_module_container(data_container)

# 初始化应用
app_container.initialize()

# 访问服务
stockinfo_service = app_container.get_service("stockinfo_service")
bar_service = app_container.get_service("bar_service")
```

### 2. 创建自定义模块容器

```python
from ginkgo.libs.containers import BaseContainer

class MyModuleContainer(BaseContainer):
    module_name = "my_module"
    
    def configure(self):
        # 绑定服务
        self.bind("my_service", MyService)
        self.bind(
            "dependent_service", 
            DependentService,
            dependencies=["my_service"]
        )

# 注册和使用
my_container = MyModuleContainer()
app_container.register_module_container(my_container)
```

### 3. 跨容器服务访问

```python
# 创建服务代理
proxy = app_container.create_service_proxy(
    "stockinfo_service",
    preferred_container="data"
)

# 使用代理访问服务
result = proxy.some_method()  # 透明调用实际服务方法
```

### 4. 上下文管理器模式

```python
with ApplicationContainer() as app:
    app.register_module_container(data_container)
    
    # 使用服务
    service = app.get_service("stockinfo_service")
    service.do_something()
    
# 自动清理和关闭
```

## 主要特性

### 服务发现
```python
# 列出所有模块
modules = app_container.list_modules()

# 列出所有服务
services = app_container.list_all_services()

# 获取健康状态
health = app_container.get_health_status()
```

### 依赖追踪
```python
# 获取模块信息
module_info = app_container.get_module_info("data")

# 获取服务依赖
deps = app_container.get_service_dependencies("stockinfo_service")
```

### 错误处理
框架提供专门的异常类型：
- `ServiceNotFoundError`: 服务未找到
- `ContainerNotRegisteredError`: 容器未注册
- `CircularDependencyError`: 循环依赖
- `ContainerLifecycleError`: 容器生命周期错误

## 与现有代码的兼容性

新的容器架构与现有的`ginkgo.data.containers`完全兼容：

```python
# 现有方式仍然有效
from ginkgo.data.containers import container
bar_crud = container.bar_crud()

# 新方式
from ginkgo.data.module_container import data_container
app_container.register_module_container(data_container)
bar_service = app_container.get_service("bar_service")
```

## 设计优势

1. **模块化**: 每个模块有独立的容器，便于管理和测试
2. **松耦合**: 跨容器依赖通过代理实现，减少模块间耦合
3. **可扩展**: 新模块可以轻松添加自己的容器
4. **线程安全**: 所有操作都是线程安全的
5. **生命周期管理**: 完整的初始化和关闭流程
6. **错误处理**: 全面的异常处理机制
7. **向后兼容**: 与现有代码完全兼容

## 最佳实践

1. **使用ApplicationContainer**: 推荐通过ApplicationContainer管理所有容器
2. **明确依赖**: 在`configure()`方法中明确声明服务依赖
3. **单例模式**: 大多数服务应该使用单例模式
4. **错误处理**: 捕获并处理容器相关异常
5. **上下文管理**: 使用`with`语句确保正确清理
6. **服务发现**: 利用内置的服务发现功能进行调试和监控

## 完整示例

参见 `examples/containers/usage_examples.py` 获取更多详细示例。

## 下一步

1. 为其他模块(backtest, client等)创建容器
2. 实现容器配置的持久化
3. 添加更多监控和诊断功能
4. 集成到现有的CLI命令中