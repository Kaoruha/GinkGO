# 拆分 BaseCRUD 超长文件设计

**Issue:** #3833
**日期:** 2026-05-17
**状态:** Draft

## 问题

`data/crud/base_crud.py` 有 2308 行、65 个方法（CRUDResult 12 + BaseCRUD 53），混合了 7 种职责：核心 CRUD、验证、类型转换/枚举、过滤解析、ClickHouse 特殊处理、流式查询、流式检查点/监控。

38 个子类全部直接继承 `BaseCRUD`，任何子类改动都需要加载整个基类。

## 方案

Mixin 平铺 + 向后兼容。BaseCRUD 作为组合入口，子类零改动。

### 文件结构

```
data/crud/
  base_crud.py                    # CoreCRUD + CRUDResult + BaseCRUD 组合入口 ~500 行
  mixins/
    __init__.py                   # 导出所有 Mixin
    conversion_mixin.py           # 类型/枚举转换 ~400 行
    validation_mixin.py           # 验证 + ClickHouse 特殊处理 ~200 行
    streaming_mixin.py            # 流式查询/checkpoint/监控 ~900 行
```

### CoreCRUD（base_crud.py 内部）

保留在 `base_crud.py` 的内容：

- `CRUDResult` 类（165 行，和 CRUD 操作紧密关联）
- `CoreCRUD` 类：
  - `__init__`, `__init_subclass__` — 初始化和子类注册
  - `_get_connection`, `get_session` — 连接管理
  - 公开模板方法：`add`, `add_batch`, `create`, `find`, `remove`, `modify`, `replace`, `count`, `exists`, `soft_remove`
  - Hook 实现：`_do_add`, `_do_add_batch`, `_do_find`, `_do_remove`, `_do_modify`, `_do_count`, `_do_exists`, `_do_soft_remove`
  - `_parse_filters` — 过滤器构建（和 `_do_find` 紧密耦合）
- `BaseCRUD` 组合入口类

### ConversionMixin（mixins/conversion_mixin.py）

- `_create_from_params`
- `_convert_input_batch`, `_convert_input_item`
- `_convert_output_items`
- `_get_enum_mappings`, `_safe_enum_convert`, `_convert_enum_values`, `_normalize_single_enum_value`
- `_validate_item_enum_fields`
- `_process_dataframe_output`
- `_convert_to_business_objects`, `_convert_models_to_business_objects`, `_convert_models_to_dataframe`

### ValidationMixin（mixins/validation_mixin.py）

- `CLICKHOUSE_STRING_FIELDS` 类属性
- `_validate_before_database`
- `_get_field_config`, `_get_database_required_config`
- `_get_mysql_required_config`, `_get_clickhouse_required_config`
- `_clean_clickhouse_strings`

### StreamingMixin（mixins/streaming_mixin.py）

- `_initialize_streaming`, `_get_streaming_engine`, `_build_streaming_query`
- `stream_find`, `stream_find_with_progress`, `stream_find_resumable`
- `is_streaming_enabled`, `enable_streaming`, `disable_streaming`
- `get_streaming_metrics`
- `_fallback_to_traditional_query`
- `stream_find_with_detailed_progress`
- `get_checkpoint_status`, `list_checkpoints`, `delete_checkpoint`
- `_adjust_filters_for_resume`, `_save_checkpoint_progress`, `_estimate_total_records`
- `stream_find_with_monitoring`
- `get_streaming_session_metrics`
- `get_memory_statistics`, `optimize_streaming_resources`
- `enable_memory_monitoring`, `disable_memory_monitoring`

注：`stream_find_resumable` 在原文件中定义了两次（第 2 次覆盖第 1 次），迁移时只保留第 2 次定义。

### 组合方式

```python
class BaseCRUD(CoreCRUD, ConversionMixin, ValidationMixin, StreamingMixin, Generic[T], ABC):
    """CRUD 基类，通过 Mixin 组合所有能力。子类继承此类即可获得全部功能。"""
    pass
```

MRO: `BaseCRUD → CoreCRUD → ConversionMixin → ValidationMixin → StreamingMixin → Generic → ABC`

各 Mixin 方法名不冲突，MRO 安全。

### Mixin 间依赖

- `ConversionMixin` — 无外部依赖，纯类型转换
- `ValidationMixin` — 无外部依赖，纯验证逻辑
- `StreamingMixin` — 调用 `self.find()`, `self.count()`（CoreCRUD 方法），通过 Mixin 组合自动获得
- `CoreCRUD` — 调用 `self._convert_input_item()`（ConversionMixin）、`self._validate_before_database()`（ValidationMixin），通过 Mixin 组合自动获得

### 向后兼容保证

- 38 个子类（如 `BarCRUD(BaseCRUD[MBar])`）**零改动**
- `__init__.py` 的懒加载注册表**零改动**
- 公开 API（所有方法签名）**零改动**
- `@restrict_crud_access` 装饰器保留在 `CoreCRUD` 上
- `ModelCRUDMapping` 注册保留在 `CoreCRUD.__init_subclass__` 中

### 测试策略

1. 迁移前运行 `tests/unit/data/crud/` 全部测试，确认绿色基线
2. 迁移后重新运行，确认全部通过
3. 额外验证：`isinstance(BarCRUD(), BaseCRUD)` 为 True
4. 额外验证：MRO 顺序正确

### 实施步骤

1. 创建 `mixins/` 目录和 `__init__.py`
2. 提取 `ConversionMixin` — 从 base_crud.py 剪切相关方法到 `conversion_mixin.py`
3. 提取 `ValidationMixin` — 同上
4. 提取 `StreamingMixin` — 同上
5. 重构 `base_crud.py` — 保留 CoreCRUD + CRUDResult + BaseCRUD 组合入口
6. 运行测试验证
7. 更新 `__init__.py` 如有需要
8. 提交并关联 #3833

## 不做的事

- 不拆分 `CRUDResult`（只有 165 行，和 CRUD 操作紧密关联）
- 不改变任何公开方法签名
- 不改变子类的继承方式
- 不引入新的抽象层或接口
