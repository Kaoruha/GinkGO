# Web UI 重构进度报告

## 总体目标
将 Ginkgo Web UI 从 Ant Design Vue 迁移到原生 HTML + Tailwind CSS

## 已完成页面（11个）

### 核心页面
1. ✅ **Dashboard** (`src/views/dashboard/Dashboard.vue`)
   - 移除 Ant Design 组件
   - E2E 测试通过

2. ✅ **数据概览** (`src/views/data/DataOverview.vue`)
   - 移除 a-card, a-button, a-row, a-col, a-statistic
   - E2E 测试通过

3. ✅ **数据同步** (`src/views/data/DataSync.vue`)
   - 移除 Ant Design 组件
   - E2E 测试通过

4. ✅ **K线数据** (`src/views/data/BarData.vue`)
   - 移除 a-select, a-range-picker, a-button, a-card, a-table, a-statistic
   - E2E 测试通过

5. ✅ **股票列表** (`src/views/data/StockList.vue`)
   - 移除 a-table, a-tag, a-drawer
   - E2E 测试通过

### 投资组合模块
6. ✅ **投资组合列表** (`src/views/portfolio/PortfolioList.vue`)
   - 移除 a-tag, a-input-search, a-button, a-radio-group, a-row, a-col, a-card, a-statistic, a-spin, a-empty, a-dropdown, a-menu, a-modal
   - E2E 测试通过（9个测试）

### 回测模块
7. ✅ **回测列表** (`src/views/stage1/BacktestList.vue`)
   - 移除 a-button, a-row, a-col, a-statistic, a-radio-group, a-input-search, a-table, a-progress, a-tooltip, a-space, a-modal, a-form, a-select, a-date-picker, a-spin, a-empty
   - E2E 测试通过（14个测试）

### 系统模块
8. ✅ **系统状态** (`src/views/system/SystemStatus.vue`)
   - 移除 a-switch, a-button, a-row, a-col, a-card, a-statistic, a-tag, a-table, a-empty
   - E2E 测试通过（13个测试）

9. ✅ **Worker 管理** (`src/views/system/WorkerManagement.vue`)
   - 占位页面重构

10. ✅ **告警中心** (`src/views/system/AlertCenter.vue`)
    - 占位页面重构

### 实盘模块
11. ✅ **实盘监控** (`src/views/stage4/LiveTrading.vue`)
    - 简单页面重构

## E2E 测试通过情况

| 测试文件 | 测试数量 | 状态 |
|---------|---------|------|
| login-page.test.js | 9 | ✅ 全部通过 |
| data-pages.test.js | 7 | ✅ 全部通过 |
| portfolio-list.test.js | 9 | ✅ 全部通过 |
| backtest-list.test.js | 14 | ✅ 全部通过 |
| system-status.test.js | 13 | ✅ 全部通过 |
| **总计** | **52** | **✅ 全部通过** |

## 剩余工作

### 待重构文件数量
- 约 67 个文件仍包含 Ant Design 组件

### 优先重构页面（建议顺序）
1. Stage 2/3 页面
   - WalkForward.vue
   - MonteCarlo.vue
   - Sensitivity.vue
   - PaperTrading.vue
   - PaperTradingOrders.vue

2. Stage 4 页面
   - LiveOrders.vue
   - LivePositions.vue

3. 组件管理页面
   - ComponentList.vue
   - ComponentDetail.vue
   - 各类组件编辑器

4. 优化和研究页面
   - 网格搜索、遗传算法、贝叶斯优化
   - IC分析、因子分层等研究页面

## 重构模式参考

### 按钮替换
```vue
<!-- 旧 -->
<a-button type="primary">确定</a-button>

<!-- 新 -->
<button class="btn-primary">确定</button>
```

### 表格替换
```vue
<!-- 旧 -->
<a-table :columns="columns" :dataSource="data" row-key="id" />

<!-- 新 -->
<table class="data-table">
  <thead>
    <tr>
      <th v-for="col in columns">{{ col.title }}</th>
    </tr>
  </thead>
  <tbody>
    <tr v-for="row in data" :key="row.id">
      <td v-for="col in columns">{{ row[col.dataIndex] }}</td>
    </tr>
  </tbody>
</table>
```

### 表单替换
```vue
<!-- 旧 -->
<a-form-item label="名称">
  <a-input v-model:value="form.name" />
</a-form-item>

<!-- 新 -->
<div class="form-item">
  <label class="form-label">名称</label>
  <input v-model="form.name" type="text" class="form-input" />
</div>
```

### 模态框替换
```vue
<!-- 旧 -->
<a-modal v-model:open="visible" title="标题">
  内容...
</a-modal>

<!-- 新 -->
<div v-if="visible" class="modal-overlay" @click.self="closeModal">
  <div class="modal-content">
    <div class="modal-header">
      <h3>标题</h3>
      <button @click="closeModal" class="btn-close">×</button>
    </div>
    <div class="modal-body">内容...</div>
  </div>
</div>
```

## 通用样式类

创建 `src/styles/common.css` 存放通用样式：
- `.btn-primary`, `.btn-secondary`, `.btn-danger`
- `.card`, `.card-header`, `.card-body`
- `.form-item`, `.form-label`, `.form-input`, `.form-select`
- `.data-table`, `.table-wrapper`
- `.modal-overlay`, `.modal-content`, `.modal-header`, `.modal-body`
- `.tag`, `.tag-blue`, `.tag-green`, `.tag-red`, `.tag-orange`
- `.stat-card`, `.stat-value`, `.stat-label`

## 最终步骤

当所有页面重构完成后：
1. 移除 Ant Design Vue 依赖
2. 移除 `src/main.ts` 中的 Ant Design 导入
3. 更新 `package.json`
4. 运行所有 E2E 测试验证

## 更新时间
2025-03-14
