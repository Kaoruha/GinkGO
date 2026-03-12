# E2E 测试 - Python Playwright

回测列表与详情功能的端到端测试，使用 Python + Playwright 实现。

## 核心原则

1. **每步操作都有明确的断言验证**
2. **页面有错误 = 测试立即失败**
3. **先检查页面健康，再验证功能**

## 环境要求

```bash
# 安装 Playwright Python
pip install pytest-playwright

# 安装浏览器
playwright install chromium
```

## 环境变量

```bash
# 远程浏览器地址（使用 CDP 连接）
export REMOTE_BROWSER="http://192.168.50.10:9222"

# Web UI 地址
export WEB_UI_URL="http://192.168.50.12:5173"
```

## 运行测试

### 运行所有测试

```bash
cd /home/kaoru/Ginkgo/web-ui
pytest tests/e2e/test_backtest_list.py -v
pytest tests/e2e/test_backtest_operations.py -v
```

### 运行特定测试

```bash
# 只测试页面健康
pytest tests/e2e/test_backtest_list.py::test_page_must_load_healthy -v

# 只测试状态标签
pytest tests/e2e/test_backtest_list.py::test_should_display_six_status_tags -v
```

### 查看详细输出

```bash
pytest tests/e2e/test_backtest_list.py -v -s
```

### 生成测试报告

```bash
pytest tests/e2e/ --html=report.html --self-contained-html
```

## 测试文件结构

```
tests/e2e/
├── conftest.py                      # Pytest 配置和固定装置
├── test_backtest_list.py           # 回测列表页测试
└── test_backtest_operations.py     # 回测操作测试
```

## 测试覆盖

### test_backtest_list.py

| 测试 ID | 测试名称 | 验证内容 |
|---------|----------|----------|
| TEST_001 | 页面健康加载 | 无错误、正确标题 |
| TEST_002 | 页面结构显示 | 容器、头部、标题 |
| TEST_003 | 六态筛选按钮 | 所有状态筛选可见 |
| TEST_004 | 统计卡片 | 总任务数、已完成、运行中、失败 |
| TEST_005 | 任务选择 | 复选框、批量操作栏 |
| TEST_006 | 全选功能 | 全选复选框 |
| TEST_007 | 取消选择 | 取消选择按钮 |
| TEST_008 | 六态标签 | 中文状态标签 |
| TEST_009 | 批量操作按钮 | 启动、停止、取消 |
| TEST_010 | 动态按钮状态 | 根据选中任务变化 |
| TEST_011 | 详情页导航 | 查看详情链接 |
| TEST_012 | 详情页操作按钮 | 根据状态显示按钮 |
| TEST_013 | 手动刷新 | 操作按钮 |
| TEST_014 | 权限控制 | 无权限提示 |

### test_backtest_operations.py

| 测试 ID | 测试名称 | 验证内容 |
|---------|----------|----------|
| TEST_OP_001 | 启动已完成任务 | 启动按钮、消息提示 |
| TEST_OP_002 | 待调度不显示启动 | 符合状态机设计 |
| TEST_OP_003 | 停止进行中任务 | 停止按钮、成功提示 |
| TEST_OP_004 | 取消待调度任务 | 取消按钮、成功提示 |
| TEST_OP_005 | 取消排队中任务 | 取消按钮存在 |
| TEST_OP_006 | 批量启动 | 仅对可启动任务有效 |
| TEST_OP_007 | 批量取消 | 仅对可取消任务有效 |
| TEST_OP_008 | 状态更新 | 操作后状态正确 |
| TEST_OP_009 | 状态转换 | 操作触发状态变化 |

## 断言模式

每个测试都遵循以下模式：

```python
def test_example(healthy_page: Page):
    """
    测试 ID: TEST_XXX
    验证：测试描述

    步骤：
        1. 第一步操作
        2. 第二步操作
        3. 验证结果

    断言：
        - 断言1说明
        - 断言2说明
    """
    # 执行操作
    element = healthy_page.locator("selector")
    element.click()
    print("✓ 操作完成")

    # 明确断言
    expect(element).to_be_visible()
    assert "expected_text" in element.text_content()
    print("✓ 断言通过")
```

## 页面健康检查

所有测试都通过 `healthy_page` fixture 自动进行页面健康检查：

1. **标题检查**：不包含 404/500/Error
2. **控制台错误**：无 JavaScript 错误
3. **页面错误**：无运行时错误
4. **网络错误**：无关键请求失败
5. **页面结构**：不显示错误信息

## 故障排除

### 测试跳过

如果测试被跳过（SKIPPED），通常是：
- 表格没有数据
- 没有特定状态的任务

### 测试失败

如果测试失败，检查：
1. 远程浏览器是否运行
2. Web UI 是否可访问
3. 页面是否有 JavaScript 错误

### 调试模式

```bash
# 启用调试模式（显示浏览器）
pytest tests/e2e/test_backtest_list.py -v --headed

# 暂停执行（交互式调试）
pytest tests/e2e/test_backtest_list.py -v --pdb
```
