# Ginkgo Examples

此目录包含了Ginkgo量化交易平台的各种使用示例。

## 快速开始

### 1. 安装Ginkgo

确保您在项目根目录执行以下命令：

```bash
# 安装Ginkgo包（可编辑模式）
pip install -e .

# 或者使用安装脚本
python install.py
```

### 2. 配置环境

```bash
# 启用调试模式（数据库操作必需）
ginkgo system config set --debug on

# 初始化数据库表结构
ginkgo data init
```

### 3. 运行示例

```bash
# 运行因子管理系统演示
python examples/factor_management_demo.py

# 运行其他策略示例
python examples/事件驱动\ EventDriven/volume_activate.py
```

## 示例说明

### 📊 因子管理系统 (factor_management_demo.py)

演示新的因子管理系统功能：

- **多实体类型支持**: 股票、市场、宏观、行业、商品、汇率、债券、基金、加密货币
- **CRUD操作**: 因子数据的增删改查
- **分析功能**: 因子相关性分析、分布分析等
- **DI容器集成**: 通过`services.data.factor_service()`访问

**特性展示**:
```python
from ginkgo import services
from ginkgo.enums import ENTITY_TYPES

# 获取因子服务
factor_service = services.data.factor_service()

# 添加因子数据
result = factor_service.add_factor_batch([
    {
        "entity_type": ENTITY_TYPES.STOCK,
        "entity_id": "000001.SZ",
        "factor_name": "rsi_14",
        "factor_value": 0.6234,
        "factor_category": "technical"
    }
])

# 查询因子数据
result = factor_service.get_factors_by_entity(
    entity_type=ENTITY_TYPES.STOCK,
    entity_id="000001.SZ"
)
```

### 🎯 事件驱动策略

`事件驱动 EventDriven/` 目录包含基于事件的交易策略示例：

- **volume_activate.py**: 基于成交量激活的策略
- **no_volume.py**: 无成交量条件策略

### 📈 策略示例

项目包含多种策略示例：

- **均值回归 MeanReversion**: 均值回归策略
- **趋势跟踪 TrendFollowing**: 趋势跟踪策略  
- **统计套利 Statistical Arbitrage**: 统计套利策略
- **多因子策略 Multi-Factor Models**: 多因子模型策略
- **机器学习**: 机器学习策略
- **强化学习 ReinforcementLearning**: 强化学习策略
- **资产配置 投资组合优化**: 资产配置优化策略
- **期权策略 衍生品策略**: 期权和衍生品策略

### 🛠️ 开发工具 (tools/)

开发和维护过程中使用的实用工具：

- **collect_real_data_samples.py**: 真实数据样本收集工具
  - 从TDX和Tushare获取真实API数据格式样本
  - 用于构建准确的Mock数据进行测试
  
- **component_validator.py**: 自定义组件验证工具  
  - CLI工具验证用户自定义回测组件
  - 提供详细的合规性报告和修复建议

```bash
# 使用工具示例
python examples/tools/collect_real_data_samples.py
python examples/tools/component_validator.py --component-type strategy --file your_strategy.py
```

## 注意事项

### ✅ 正确的导入方式

```python
# ✅ 正确 - 直接导入已安装的包
from ginkgo import services
from ginkgo.enums import ENTITY_TYPES
```

### ❌ 错误的导入方式

```python
# ❌ 错误 - 不要手动修改sys.path
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
```

### 🔧 故障排除

如果遇到导入问题：

1. **检查包安装**: `pip list | grep ginkgo`
2. **检查导入路径**: `python -c "import ginkgo; print(ginkgo.__file__)"`
3. **重新安装**: `pip install -e . --force-reinstall`
4. **检查虚拟环境**: 确保在正确的虚拟环境中

### 📋 前置条件

运行示例前请确保：

- ✅ Python 3.8+ 已安装
- ✅ 虚拟环境已激活（推荐）
- ✅ Ginkgo包已正确安装
- ✅ 数据库服务正常运行（Docker）
- ✅ 调试模式已启用

## 更多信息

- 📖 [主项目文档](../README.md)
- 🔧 [配置指南](../CLAUDE.md)
- 🐛 [问题反馈](https://github.com/Kaoruha/GinkGO/issues)