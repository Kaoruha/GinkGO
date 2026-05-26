# Ginkgo 开发工具集

本目录包含Ginkgo开发和维护过程中使用的实用工具。

## 工具列表

### 数据工具
- `collect_real_data_samples.py` - 真实数据样本收集工具
  - 从TDX和Tushare获取真实API数据格式样本
  - 用于构建准确的Mock数据进行测试
  - 支持多种数据源的样本收集

### 组件验证工具  
- `component_validator.py` - 自定义组件验证工具
  - CLI工具，验证用户自定义回测组件是否符合系统要求
  - 提供详细的合规性报告和修复建议
  - 帮助开发者快速集成自定义组件

## 使用方法

### 数据样本收集
```bash
# 收集TDX和Tushare数据样本
python collect_real_data_samples.py

# 确保配置了正确的API Token和网络连接
```

### 组件验证
```bash
# 验证自定义策略组件
python component_validator.py --component-type strategy --file your_strategy.py

# 验证分析器组件
python component_validator.py --component-type analyzer --file your_analyzer.py
```

## 注意事项

- 使用前请确保相关API配置正确
- 数据收集工具需要网络连接
- 组件验证工具需要目标组件遵循Ginkgo接口规范