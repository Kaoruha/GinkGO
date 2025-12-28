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



- 趋势与动量因子

    - 移动平均线（MA）及其衍生因子
    追踪市场的平均成本，当短期成本高于长期成本时候、，新进资金推动市场上行，趋势形成
        - 金叉死叉：短期MA上穿/下穿长期MA，是趋势启动的经典信号
        - 价格与MA的相对位置：价格在MA之上为多头市场，之下为空头市场
        - MA斜率：MA线自身的方向代表了趋势的强度

    - MACD（指数平滑异同移动平均线）
    对趋势的转变更为敏感，衡量的是短期和长期动量之间的收敛与乏善
        - DIF值
        - DIF与DEA的交叉
        - MACD柱状图（OSC）的面积和方向

    - RSI（相对强弱指数）
    衡量市场内部的动能速度与变化率，反映了市场在特定时期的“兴奋度”或“沮丧度”
        - RSI指数（通常看30/70超卖超买线）
        - RSI的背离（价格创新高但RSI未创新高，于是动能衰竭）

- 成交量确认因子

    - 价量背离（Price-Vol Divergence）
    当价格方向与成交量方向不一致时，往往预示着当前趋势不可持续
        - 价升量缩：价格上涨但成交量下降，表明追高意愿不足，是趋势见顶的警告
        - 价跌量缩：价格下跌但成交量猥琐，表明抛压减弱，可能接近底部

    - OBV（能量潮）
    如果价格盘整但OBV持续上升，说明有资金在暗中吸筹
        - OBV线的趋势
        - OBV与价格的背离

    - VWAP（成交量加权平均价格）
    价格在VWAP智商，意味着多数参与者处于盈利状态，市场情绪偏多
        - 当日价格与VWAP的相对位置，机构常用它作为衡量交易执行好坏的基准

- 波动与动能因子

    - 布林带（Bollinger Bands）
    讲价格的“位置”和“波动性”结合起来，提供了动态的，适应市场的支撑阻力框架
        - 带宽（Band Width）：带宽收债代表波动率极低，往往预示着即将出现大的方向性突破（“挤压”）
        - 价格触及上下轨：并非单纯的买卖信号，而是表明价格处于相对极端的位置。

    - ATR（平均真实波幅）
    衡量价格在一定时期内的波动剧烈成都，它不指示方向，只指示服务
        - 设定侄孙：根据ATR值来设定动态止损，例如2倍ATR，能更好的适应市场波动性的变化
        - 评估趋势强度：在强劲趋势中，ATR值通常会维持在高位

    - 动量 Momentum
    直到测量价格运动的“速度”，动量值越大，说明上涨或下跌的惯性越强
    
    - 资金流指标（MFI）
    试图识别“聪明钱”（机构、大户）的行为
        - MFI的指数与背离：当价格创新高但MFI走弱，表明是大资金在利用上涨出货

