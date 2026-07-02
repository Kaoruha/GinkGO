# ADR-005: 组件参数序列化对称

**Status:** Accepted
**Date:** 2026-06-13

## Context

组件参数（`MParam`）的写入方多样——API 写入、CLI 写入、测试直接写入——格式不统一：有的值是 `json.dumps("xxx")`（带引号），有的是原始字符串。若读取端不做对称反序列化，参数会带着引号或 JSON 外壳进入组件构造函数，引发隐蔽 bug。

## Decision

- **存储**：`MParam.value` 为 `String(255)`，统一存字符串（可能是原始字符串或 JSON 序列化后的字符串）。
- **读取**：所有读取点必须 `json.loads(value)` 并 **fallback 到默认值/原始字符串**：
  ```python
  value = json.loads(p.value) if p.value else <默认>
  ```
- **参数名不入库**：`MParam` 只存 `mapping_id / index / value`，参数名通过 `ComponentParameterExtractor` 按代码 AST 解析。
- **实例化**：~~组件构造优先 **kwargs 关键字传参，fallback 到 positional。~~ **订正（ADR-020, 2026-07-02）**：已改为纯位置 splat `component_class(*component_params)`，移除 kwargs 分支与打分启发式。
- **股票代码**：库内统一**大写**（如 `000001.SZ`），前端传入的小写在存储/查询时转大写。

## Rationale

- **写入多样性的现实**：无法强制所有写入方统一格式，因此在读取端做对称的"尝试反序列化 + fallback"，是最鲁棒的收敛点。
- **参数名靠 AST 而非存储**：参数名是组件源码的属性，存表会与代码漂移；从代码提取保证单一真相源。

## Consequences

- 任何新增的 `MParam.value` 读取点，必须照搬 `json.loads + fallback` 模式（参照 `portfolio_mapping_service.py` 现有实现），不能裸取 `p.value`。
- 修改组件构造函数签名时，`ComponentParameterExtractor` 的 AST 解析自动跟随，无需同步改表。
- **注意**：~~`--param` 索引 `0` 映射到组件 `name` 参数（见 issue #5955），这是已知的索引平移规则。~~ **订正（ADR-020, 2026-07-02）**：index0 = 构造器首参（通常 name），从 0 连续存；不再有「跳 name / 偏移 -1」约定。详见 ADR-020。
