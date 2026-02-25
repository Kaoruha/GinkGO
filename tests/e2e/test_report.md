# E2E测试参数填写问题修复报告

## 问题描述
用户反馈："param填写在的名称" - 参数名称被错误填写

## 根本原因
Playwright测试中使用过于简化的选择器来定位参数输入框：
```python
# 错误的方式 - 只取第一个输入框
param_input = page.locator(".ant-modal .ant-input").first
param_input.fill("600000.SH")
```

这会导致：
- 可能填写到错误的输入框
- 无法区分不同参数的输入框
- 参数值填写到错误的字段

## 修复方案
创建了 `fill_parameter_by_label()` 函数，根据参数标签精确定位输入框：

```python
def fill_parameter_by_label(page, label_text, value):
    """根据参数标签找到对应的输入框并填写值"""
    label = page.locator(f".param-label:has-text('{label_text}')").first
    if label.is_visible(timeout=2000):
        param_row = label.locator("..")
        input_field = param_row.locator("input, .ant-input-number-input").first
        input_field.fill(str(value))
        return True
    return False
```

## 修复结果
✅ 参数现在正确填写：
- FixedSelector: `codes = 600000.SH`
- FixedSizer: `volume = 1000`
- RandomSignalStrategy: `buy_probability = 0.8`, `sell_probability = 0.1`

✅ Portfolio创建成功，API验证配置正确保存：
```json
{
  "selectors": [{"config": {"name": "FixedSelector", "codes": "600000.SH"}}],
  "sizer": {"config": {"volume": 1000, "name": "FixedSizer"}},
  "strategies": [{"config": {
    "buy_probability": 0.8,
    "sell_probability": 0.1,
    "name": "RandomSignalStrategy"
  }}]
}
```

## 后续问题
回测失败是因为**数据库没有市场数据**（空的stockinfo和bar表）。

解决方法：
```bash
# 同步股票信息
ginkgo data update --stockinfo

# 同步K线数据
ginkgo data update day --code 000001.SZ
```

## 相关文件
- `tests/e2e/run_backtest_fixed.py` - 修复后的E2E测试
- `web-ui/src/views/portfolio/PortfolioFormEditor.vue` - Portfolio表单组件
- `src/ginkgo/data/services/component_parameter_extractor.py` - 参数提取服务
