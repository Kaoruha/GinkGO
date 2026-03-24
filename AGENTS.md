# AGENT.md

## 核心沟通原则

**一屏原则**: 输出内容控制在一屏内，不要滚动。反复滚动影响效率。

## 简洁输出指南

### DO
- 直接回答问题，先给结论
- 代码只改必要部分
- 错误只显示关键行
- 列表用简洁格式

### DON'T
- 长篇铺垫解释
- 重复用户已知信息
- 粘贴大段代码
- 过度解释概念

## 项目快速参考

### 核心结构
```
src/ginkgo/
├── core/       # 核心基础
├── trading/    # 交易引擎
├── data/       # 数据层
└── livecore/   # 实盘交易
```

### 常用命令
```bash
ginkgo system config set --debug on   # 数据库操作必须
ginkgo serve api                      # API服务器
ginkgo serve webui                    # Web界面
```

### 关键文件
- `CLAUDE.md` - 完整项目指南
- `docs/entity-relationships.md` - 实体关系
- `MEMORY.md` - 上下文记忆

## 编码规范
- Python 3.12.8 + 类型提示
- Black格式化 (120列)
- 测试优先: `pytest -m "unit and not slow"`

## 重要提醒
- 数据库操作前必须开debug模式
- 修改BaseCRUD等基础组件需谨慎
- 验证修复从前端最终结果判断
