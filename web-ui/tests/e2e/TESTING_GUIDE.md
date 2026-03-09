# E2E 测试质量指南

## 问题：为什么"假性通过"的测试是危险的？

### 真实案例
当页面有 500 错误或模板编译错误时：
- ❌ **旧测试**：仍然显示"通过"（只检查文字存在）
- ✅ **新测试**：正确检测错误并失败

### 旧测试的问题
```javascript
// ❌ 危险的测试 - 页面崩溃也会通过
test('应显示回测列表', async () => {
  await page.goto('/backtest')
  const bodyText = await page.locator('body').textContent()
  expect(bodyText).toContain('回测')  // 导航栏的文字仍在，测试通过！
})
```

### 新测试的改进
```javascript
// ✅ 健康的测试 - 检测页面错误
test('回测列表页健康检查', async () => {
  const errors = []

  page.on('console', msg => {
    if (msg.type() === 'error') errors.push(msg.text())
  })

  page.on('pageerror', error => {
    errors.push(error.message)
  })

  await page.goto('/backtest')
  await page.waitForTimeout(3000)  // 等待异步错误浮现

  // 断言：不能有任何错误
  if (errors.length > 0) {
    throw new Error(`发现错误: ${errors.join('\n')}`)
  }

  // 断言：关键元素必须存在且可见
  await expect(page.locator('.page-container')).toBeVisible()
  await expect(page.locator('.ant-table')).toBeVisible()
})
```

## 测试层级

### 1. 健康检查测试 (Health Check)
**文件**: `tests/e2e/health-check.test.js`

**目的**: 快速验证页面是否正常加载，没有编译或运行时错误

**检查项**:
- ✅ 没有 JavaScript 控制台错误
- ✅ 没有页面错误 (pageerror)
- ✅ 没有 HTTP 请求失败 (500, 404)
- ✅ 关键元素存在且可见
- ✅ 页面标题不是错误页面

**运行频率**: 每次代码变更后

### 2. 功能测试 (Functional Tests)
**文件**: `tests/e2e/backtest-list.test.js`

**目的**: 验证特定功能是否正常工作

**检查项**:
- ✅ 使用 `assertNoPageErrors()` 和 `assertPageNotError()`
- ✅ 验证用户交互流程
- ✅ 检查数据正确显示

## 关键原则

### 1. 错误监听是必须的
```javascript
// 始终监听控制台错误
page.on('console', msg => {
  if (msg.type() === 'error') {
    errors.push(msg.text())
  }
})

page.on('pageerror', error => {
  errors.push(error.message)
})
```

### 2. 等待足够的时间
```javascript
// ❌ 不好 - 太快，错误还没出现
await page.goto(url)
await page.waitForTimeout(100)

// ✅ 好 - 给足够时间让错误浮现
await page.goto(url)
await page.waitForTimeout(3000)
```

### 3. 验证元素真正存在
```javascript
// ❌ 不好 - count >= 0 永远通过
expect(await page.locator('.table').count()).toBeGreaterThanOrEqual(0)

// ✅ 好 - 验证元素真的可见
await expect(page.locator('.table')).toBeVisible()
```

### 4. 不要只检查文字
```javascript
// ❌ 危险 - 导航栏文字仍在就通过
expect(bodyText).toContain('回测')

// ✅ 好 - 验证实际内容
await expect(page.locator('.backtest-list')).toBeVisible()
await expect(page.locator('.ant-table')).toBeVisible()
```

## 快速验证命令

```bash
# 运行健康检查（快速验证页面状态）
WEB_UI_URL=http://192.168.50.12:5173 npx playwright test tests/e2e/health-check.test.js

# 运行完整测试套件
WEB_UI_URL=http://192.168.50.12:5173 npx playwright test tests/e2e/backtest-list.test.js

# 调试模式（打开浏览器）
npx playwright test --debug --project=chromium
```

## 故障排查

### 测试通过但页面显示错误

1. **检查控制台日志** - 是否有 JavaScript 错误被忽略
2. **增加等待时间** - 异步错误可能需要更长时间浮现
3. **验证元素可见性** - 使用 `toBeVisible()` 而不是 `toBe(0)`

### 页面 500 错误但测试不报错

检查测试是否包含：
```javascript
page.on('pageerror', error => {
  errors.push(error.message)
})
```

### Vite 编译错误但测试通过

原因：Vite 返回错误页面，但测试没有检查页面内容

解决：在 `assertPageNotError()` 中添加检查
```javascript
if (title.includes('500') || bodyText.includes('Internal Server Error')) {
  throw new Error('页面编译失败')
}
```
