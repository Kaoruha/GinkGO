# LoggableMixin 移除方案

## 目标

完全移除 `LoggableMixin`，所有日志直接使用全局 `GLOG`。

---

## 影响分析

### 依赖 LoggableMixin 的类

```python
# 继承 LoggableMixin 的类
- BaseEngine
- BaseStrategy  
- BasePortfolio
- BaseBroker
- BaseAnalyzer
- BaseRiskManagement
- BaseSelector
- BaseSizer
- ... 以及它们的子类
```

### 需要替换的模式

```python
# 模式1: 直接调用
self.log("INFO", msg)        → GLOG.INFO(msg)
self.log("WARN", msg)        → GLOG.WARN(msg)
self.log("ERROR", msg)        → GLOG.ERROR(msg)
self.log("DEBUG", msg)        → GLOG.DEBUG(msg)

# 模式2: add_logger 调用（删除）
component.add_logger(logger)  → 删除

# 模式3: 继承 LoggableMixin（删除）
class Foo(LoggableMixin, Base)  → class Foo(Base)
```

---

## 迁移步骤

### 阶段1：准备

1. 确保所有文件都导入了 `GLOG`
2. 添加 `from ginkgo.libs import GLOG` 到需要的文件

### 阶段2：批量替换

```bash
# 在项目根目录执行
find src -name "*.py" -type f -exec sed -i 's/self\.log("INFO",/GLOG.INFO("/g' {} \;
find src -name "*.py" -type f -exec sed -i 's/self\.log("WARN",/GLOG.WARN("/g' {} \;
find src -name "*.py" -type f -exec sed -i 's/self\.log("ERROR",/GLOG.ERROR("/g' {} \;
find src -name "*.py" -type f -exec sed -i 's/self\.log("DEBUG",/GLOG.DEBUG("/g' {} \;
find src -name "*.py" -type f -exec sed -i 's/self\.log("CRITICAL",/GLOG.CRITICAL("/g' {} \;
```

### 阶段3：清理 LoggableMixin 引用

```python
# 删除继承
class Portfolio(LoggableMixin, PortfolioBase):
↓
class Portfolio(PortfolioBase):

# 删除 add_logger 调用
portfolio.add_logger(logger)  # 删除
engine.add_logger(logger)      # 删除
```

### 阶段4：删除 LoggableMixin 文件

```bash
rm src/ginkgo/trading/mixins/loggable_mixin.py
```

### 阶段5：更新引用

```python
# 更新 import 语句
from ginkgo.trading.mixins.loggable_mixin import LoggableMixin  # 删除
from ginkgo.trading.mixins.time_mixin import TimeMixin         # 保留
```

---

## 具体文件替换清单

### 核心基类

| 文件 | 操作 |
|------|------|
| `bases/base_engine.py` | 移除 LoggableMixin 导入和继承 |
| `bases/portfolio_base.py` | 移除 LoggableMixin 导入和继承 |
| `bases/risk_base.py` | 移除 LoggableMixin 导入和继承 |
| `bases/selector_base.py` | 移除 LoggableMixin 导入和继承 |

### 服务层

| 文件 | 操作 |
|------|------|
| `services/engine_assembly_service.py` | 删除所有 `add_logger()` 调用 |
| `services/portfolio_management_service.py` | 删除所有 `add_logger()` 调用 |

### Mixin

| 文件 | 操作 |
|------|------|
| `mixins/loggable_mixin.py` | 删除整个文件 |

---

## 验证清单

- [ ] 所有 `self.log()` 调用已替换为 `GLOG.*()`
- [ ] 所有 `add_logger()` 调用已删除
- [ ] 所有 LoggableMixin 继承已移除
- [ ] 导入语句已清理
- [ ] 测试通过
- [ ] 日志输出正常

---

## 注意事项

1. **保持日志级别不变**：INFO→INFO, WARN→WARN, ERROR→ERROR
2. **检查导入**：确保文件已导入 `GLOG`
3. **备份代码**：执行前建议先提交当前代码
4. **渐进式迁移**：可以先在几个文件上测试，确认无问题后再批量替换

---

## 执行命令

```bash
# 1. 检查影响范围
grep -r "LoggableMixin" src/ginkgo/trading --include="*.py" | wc -l

# 2. 执行替换（建议先在 git 分支测试）
cd /home/kaoru/Ginkgo
find src -name "*.py" -type f -exec sed -i '
s/self\.log("INFO",/GLOG.INFO("/g
s/self\.log("WARN",/GLOG.WARN("/g
s/self\.log("ERROR",/GLOG.ERROR("/g
s/self\.log("DEBUG",/GLOG.DEBUG("/g
s/self\.log("CRITICAL",/GLOG.CRITICAL("/g
' {} \;

# 3. 验证替换结果
grep -r "self\.log(" src/ginkgo/trading --include="*.py" | wc -l
```
