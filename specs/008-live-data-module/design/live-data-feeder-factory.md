# LiveDataFeeder工厂模式设计

**Feature**: 008-live-data-module
**Date**: 2026-01-11
**Purpose**: 通过工厂模式解耦DataManager与具体LiveDataFeeder实现

---

## 一、当前问题分析

### 1.1 硬编码问题

**当前实现**:
```python
class DataManager(Thread):
    def __init__(self):
        # 硬编码创建Feeder - 违反开闭原则
        self.feeders = {
            "cn": EastMoneyFeeder(queue),
            "hk": FuShuFeeder(queue),
            "us": AlpacaFeeder(queue)
        }
```

**问题**:
1. ❌ 添加新数据源需要修改DataManager代码
2. ❌ 不同环境无法灵活配置（如测试环境用Mock）
3. ❌ 违反开闭原则（对扩展开放，对修改封闭）
4. ❌ 无法动态启用/禁用数据源

### 1.2 影响

- **扩展性**: 添加新数据源需要修改DataManager
- **可测试性**: 无法注入Mock Feeder进行单元测试
- **灵活性**: 无法根据环境选择不同数据源组合

---

## 二、工厂模式设计

### 2.1 配置文件设计

**路径**: `~/.ginkgo/data_sources.yml`

```yaml
# 数据源配置文件
data_sources:
  # A股市场数据源
  cn:
    type: "EastMoneyFeeder"  # Feeder类名
    enabled: true
    config:
      websocket_uri: "wss://push2.eastmoney.com/ws/qt/stock/klt.min"
      ping_interval: 30
      ping_timeout: 60
      reconnect_attempts: 5

  # 港股市场数据源
  hk:
    type: "FuShuFeeder"
    enabled: true
    config:
      http_uri: "https://api.fushu.com/v1/tick"
      poll_interval: 5
      timeout: 10

  # 美股市场数据源
  us:
    type: "AlpacaFeeder"
    enabled: true
    config:
      websocket_uri: "wss://stream.data.alpaca.markets/v2/iex"
      api_key: "${ALPACA_API_KEY}"  # 环境变量
      api_secret: "${ALPACA_API_SECRET}"

  # 未来可扩展：添加新数据源
  # jp:
  #   type: "JapanDataFeeder"
  #   enabled: false
  #   config: {...}
```

### 2.2 工厂类实现

```python
from abc import ABC, abstractmethod
from typing import Dict, Set
from queue import Queue
import yaml
from pathlib import Path

class LiveDataFeederFactory:
    """
    LiveDataFeeder工厂类

    职责：
    1. 从配置文件加载数据源配置
    2. 根据配置动态创建Feeder实例
    3. 支持环境变量替换
    4. 支持启用/禁用数据源
    """

    # Feeder类注册表（类名 -> 类）
    _feeder_registry: Dict[str, type] = {}

    @classmethod
    def register_feeder(cls, feeder_class: type) -> None:
        """
        注册Feeder类

        Args:
            feeder_class: LiveDataFeeder子类

        示例:
            LiveDataFeederFactory.register_feeder(EastMoneyFeeder)
        """
        cls._feeder_registry[feeder_class.__name__] = feeder_class

    @classmethod
    def create_from_config(
        cls,
        config_path: str = None,
        queue: Queue = None
    ) -> Dict[str, 'LiveDataFeeder']:
        """
        从配置文件创建Feeder实例

        Args:
            config_path: 配置文件路径（默认: ~/.ginkgo/data_sources.yml）
            queue: Tick数据队列

        Returns:
            Dict[str, LiveDataFeeder]: market -> feeder 映射

        Raises:
            FileNotFoundError: 配置文件不存在
            ValueError: 配置格式错误或Feeder类不存在
        """
        if config_path is None:
            config_path = Path.home() / ".ginkgo" / "data_sources.yml"

        # 加载配置
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        feeders = {}
        data_sources = config.get('data_sources', {})

        for market, cfg in data_sources.items():
            # 跳过禁用的数据源
            if not cfg.get('enabled', True):
                continue

            # 获取Feeder类
            feeder_type = cfg['type']
            if feeder_type not in cls._feeder_registry:
                raise ValueError(f"Unknown feeder type: {feeder_type}")

            feeder_class = cls._feeder_registry[feeder_type]

            # 替换环境变量
            feeder_config = cls._substitute_env_vars(cfg.get('config', {}))

            # 创建Feeder实例
            feeder = feeder_class(queue, **feeder_config)
            feeders[market] = feeder

        return feeders

    @classmethod
    def _substitute_env_vars(cls, config: dict) -> dict:
        """
        替换配置中的环境变量

        支持 ${VAR_NAME} 格式

        Args:
            config: 原始配置

        Returns:
            dict: 替换后的配置
        """
        import os
        import re

        def replace_env(value):
            if isinstance(value, str):
                # 匹配 ${VAR_NAME} 格式
                match = re.match(r'\$\{(\w+)\}', value)
                if match:
                    env_var = match.group(1)
                    return os.environ.get(env_var, value)
            return value

        return {k: replace_env(v) for k, v in config.items()}
```

### 2.3 DataManager使用工厂

```python
class DataManager(Thread):
    """
    实时数据管理器（使用工厂模式）
    """

    def __init__(self, config_path: str = None):
        super().__init__()

        # 创建Queue
        self.queue = Queue(maxsize=10000)

        # 使用工厂创建Feeder（从配置文件）
        self.feeders = LiveDataFeederFactory.create_from_config(
            config_path=config_path,
            queue=self.queue
        )

        # Queue消费者（仍由DataManager管理）
        self.queue_consumers = []
```

### 2.4 Feeder类注册

**推荐方式: 显式注册**

```python
# 在模块初始化时注册
class EastMoneyFeeder(LiveDataFeeder):
    """东方财富数据源"""
    pass

class FuShuFeeder(LiveDataFeeder):
    """FuShu数据源"""
    pass

class AlpacaFeeder(LiveDataFeeder):
    """Alpaca数据源"""
    pass

# 注册到工厂（在模块__init__.py或统一注册模块中）
LiveDataFeederFactory.register_feeder(EastMoneyFeeder)
LiveDataFeederFactory.register_feeder(FuShuFeeder)
LiveDataFeederFactory.register_feeder(AlpacaFeeder)
```

**说明**:
- 使用显式注册更简单直接，避免装饰器语法
- 可以在运行时动态决定是否注册
- 保持与Ginkgo ServiceHub风格一致

---

## 三、单元测试支持

### 3.1 Mock Feeder测试

```python
class MockLiveDataFeeder(LiveDataFeeder):
    """测试用Mock Feeder"""

    def __init__(self, queue: Queue):
        super().__init__(queue, market="test")
        self.connected = False

    async def _connect(self) -> None:
        self.connected = True

    async def _subscribe(self, symbols: Set[str]) -> None:
        pass

    async def _unsubscribe(self, symbols: Set[str]) -> None:
        pass

# 注册Mock Feeder（仅测试环境）
LiveDataFeederFactory.register_feeder(MockLiveDataFeeder)
```

### 3.2 测试配置文件

```yaml
# 测试环境配置: tests/fixtures/test_data_sources.yml
data_sources:
  test:
    type: "MockLiveDataFeeder"
    enabled: true
    config: {}
```

### 3.3 单元测试示例

```python
import pytest
from ginkgo.livecore.data_manager import DataManager
from ginkgo.livecore.data_feeders.factory import LiveDataFeederFactory

def test_data_manager_with_factory():
    """测试DataManager使用工厂模式"""
    # 使用测试配置
    manager = DataManager(
        config_path="tests/fixtures/test_data_sources.yml"
    )

    # 验证Feeder创建
    assert "test" in manager.feeders
    assert isinstance(manager.feeders["test"], MockLiveDataFeeder)

    # 验证Queue共享
    assert manager.feeders["test"].queue is manager.queue
```

---

## 四、扩展性示例

### 4.1 添加新数据源

**步骤1: 实现Feeder类**

```python
class JapanDataFeeder(LiveDataFeeder):
    """日本股市数据源"""

    def __init__(self, queue: Queue, api_url: str):
        super().__init__(queue, market="jp")
        self.api_url = api_url

    async def _connect(self) -> None:
        # 实现连接逻辑
        pass

    async def _subscribe(self, symbols: Set[str]) -> None:
        # 实现订阅逻辑
        pass

    async def _unsubscribe(self, symbols: Set[str]) -> None:
        # 实现取消订阅逻辑
        pass
```

**步骤2: 注册Feeder**

```python
@LiveDataFeederFactory.register_feeder
class JapanDataFeeder(LiveDataFeeder):
    pass
```

**步骤3: 更新配置文件**

```yaml
data_sources:
  jp:
    type: "JapanDataFeeder"
    enabled: true
    config:
      api_url: "https://api.japan-market.com/v1/tick"
```

**步骤4: 无需修改DataManager代码**

```python
# DataManager代码无需改动，自动支持新数据源
manager = DataManager()  # 自动加载jp市场Feeder
```

---

## 五、配置验证

### 5.1 配置校验函数

```python
from pydantic import BaseModel, Field, validator
from typing import Optional

class DataSourceConfig(BaseModel):
    """数据源配置模型"""

    type: str = Field(..., description="Feeder类名")
    enabled: bool = Field(True, description="是否启用")
    config: dict = Field(default_factory=dict, description="Feeder配置")

    @validator('type')
    def validate_feeder_type(cls, v):
        """验证Feeder类型是否已注册"""
        if v not in LiveDataFeederFactory._feeder_registry:
            raise ValueError(f"Unknown feeder type: {v}")
        return v

class DataSourcesConfig(BaseModel):
    """数据源配置根模型"""

    data_sources: Dict[str, DataSourceConfig] = Field(
        default_factory=dict,
        description="市场到数据源配置的映射"
    )

# 使用示例
def validate_config(config_path: str) -> DataSourcesConfig:
    """验证配置文件"""
    with open(config_path, 'r') as f:
        config_data = yaml.safe_load(f)

    return DataSourcesConfig(**config_data)
```

### 5.2 启动时验证

```python
class DataManager(Thread):
    def __init__(self, config_path: str = None):
        # 验证配置
        try:
            validate_config(config_path)
        except ValidationError as e:
            raise DataManagerStartupException(f"Invalid config: {e}")

        # 创建Feeder
        self.feeders = LiveDataFeederFactory.create_from_config(
            config_path=config_path,
            queue=self.queue
        )
```

---

## 六、迁移计划

### 6.1 Phase 1: 创建工厂类（不影响现有代码）

1. 创建 `ginkgo/livecore/data_feeders/factory.py`
2. 实现 `LiveDataFeederFactory`
3. 为现有Feeder类添加装饰器注册
4. 编写单元测试

### 6.2 Phase 2: 创建默认配置文件

1. 创建 `~/.ginkgo/data_sources.yml`
2. 添加cn/hk/us市场配置
3. 支持环境变量替换

### 6.3 Phase 3: 修改DataManager使用工厂

1. 修改 `DataManager.__init__()` 使用工厂
2. 保持向后兼容（配置文件不存在时使用硬编码）
3. 添加配置验证

### 6.4 Phase 4: 文档和示例

1. 更新quickstart.md
2. 添加配置文件示例
3. 添加新数据源扩展示例

---

## 七、收益总结

### 7.1 架构收益

| 维度 | 改进前 | 改进后 |
|------|--------|--------|
| **扩展性** | 修改DataManager代码 | 修改配置文件即可 |
| **可测试性** | 难以Mock | 注入Mock Feeder |
| **灵活性** | 硬编码数据源 | 配置化数据源 |
| **符合SOLID** | ❌ 违反OCP | ✅ 符合OCP |

### 7.2 开发体验

**添加新数据源**:
```python
# 改进前: 需要修改DataManager
class DataManager:
    def __init__(self):
        self.feeders = {
            "cn": EastMoneyFeeder(queue),
            "hk": FuShuFeeder(queue),
            "us": AlpacaFeeder(queue),
            "jp": JapanDataFeeder(queue)  # ← 修改这里
        }

# 改进后: 只需修改配置文件
# yaml配置:
# jp:
#   type: "JapanDataFeeder"
#   enabled: true
```

---

## 八、实施检查清单

- [ ] 创建 `factory.py` 文件
- [ ] 实现 `LiveDataFeederFactory` 类
- [ ] 为现有Feeder添加 `@register_feeder` 装饰器
- [ ] 创建默认配置文件 `~/.ginkgo/data_sources.yml`
- [ ] 修改 `DataManager.__init__()` 使用工厂
- [ ] 添加配置验证（Pydantic模型）
- [ ] 编写单元测试（工厂模式、Mock Feeder）
- [ ] 更新quickstart.md文档
- [ ] 添加新数据源扩展示例
- [ ] 向后兼容测试（配置文件不存在时的行为）

---

**设计完成时间**: 2026-01-11
**下一步**: 创建factory.py实现文件
