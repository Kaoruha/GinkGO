# Backtest 模块测试重构总结

## 已完成重构的测试文件

### 核心模块 (本次完成)
- **test_portfolio_base.py** - 组合管理测试 (432行)
- **test_event_engine.py** - 事件引擎测试 (398行)
- **test_base_selector.py** - 选择器基础测试 (396行)
- **test_base_sizer.py** - 仓位管理器测试 (247行)
- **test_base_strategy.py** - 策略基础测试 (284行)
- **test_feeder_base.py** - 数据源基础测试 (169行)
- **test_matchmaking_base.py** - 撮合基础测试 (183行)

### 已完成的子模块
- indicators/ - 技术指标测试 (4个文件)
- risk_managements/ - 风险管理测试 (4个文件)

## 重构要点

### 1. 使用共享 fixtures
```python
@pytest.fixture
def portfolio():
    return PortfolioT1Backtest()

@pytest.fixture
def event_engine():
    engine = EventEngine("test")
    yield engine
    engine.stop()
```

### 2. 参数化测试
```python
@pytest.mark.parametrize("cash,volume,expected", [
    (10000, 100, 100),
    (50000, 500, 500),
])
def test_fixed_sizer_cal(self, cash, volume, expected):
    # 测试代码
```

### 3. 清晰的测试类分组
- TestConstruction - 构造和初始化
- TestFunctionality - 核心功能
- TestEdgeCases - 边界情况

### 4. pytest 风格断言
```python
assert result is not None
with pytest.raises(ValueError):
    some_function()
```

## 运行测试
```bash
pytest test/backtest/ -v
pytest test/backtest/ -m unit -v
pytest test/backtest/ --cov=ginkgo.backtest --cov-report=html
```
