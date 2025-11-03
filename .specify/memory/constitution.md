<!--
Sync Impact Report:
Version change: none → 1.0.0
Modified principles: N/A (initial creation)
Added sections:
- Security & Compliance Principle (敏感文件安全检查)
- Architecture Excellence Principle (架构设计原则)
- Code Quality Principle (代码质量原则)
- Testing Excellence Principle (测试原则)
- Performance Excellence Principle (性能原则)
- Documentation Excellence Principle (文档原则)
Removed sections: N/A
Files Updated for Consistency:
✅ /home/kaoru/Ginkgo/.gitignore - 添加了全面的敏感文件保护规则
✅ 移除了版本控制中的敏感文件: src/ginkgo/config/secure.yml, src/ginkgo/config/secure.backup
Templates requiring updates: N/A (no templates exist yet)
Follow-up TODOs:
- 考虑创建pre-commit hooks来自动执行敏感文件扫描
- 考虑在CI/CD流水线中集成章程合规性检查
- 定期审查和更新敏感文件检测规则
-->

# Ginkgo 项目章程

## 基本信息

- **项目名称**: Ginkgo
- **章程版本**: 1.0.0
- **制定日期**: 2025-11-03
- **最后修订**: 2025-11-03
- **项目描述**: Python量化交易库，专注于事件驱动回测、多数据库支持和完整的风险管理系统

## 核心原则

### 1. 安全与合规原则 (Security & Compliance)

**敏感文件安全检查**: 所有代码提交前必须进行敏感文件检查，确保不包含API密钥、数据库凭证、交易配置或其他敏感信息。

**具体要求**:
- 严禁在代码库中提交任何形式的明文密码、API密钥或访问令牌
- 必须使用环境变量或配置文件管理敏感信息，且敏感配置文件必须添加到.gitignore
- 提交前运行自动化扫描工具检查潜在的敏感信息泄露
- 数据库连接字符串、第三方服务凭证等必须通过安全的配置管理系统加载
- 所有开发者必须定期审查和轮换访问凭证

**理由**: 作为量化交易系统，Ginkgo处理金融数据和交易执行，安全性至关重要。敏感信息泄露可能导致资产损失和合规风险。

### 2. 架构设计原则 (Architecture Excellence)

**事件驱动优先**: 所有交易功能必须基于事件驱动架构设计，遵循PriceUpdate → Strategy → Signal → Portfolio → Order → Fill的标准流程。

**依赖注入模式**: 必须使用统一的依赖注入容器，通过`from ginkgo import services`访问所有服务组件。

**职责分离**: 严格分离数据层、策略层、执行层、分析层和服务层的职责，避免跨层功能耦合。

### 3. 代码质量原则 (Code Quality)

**装饰器优化**: 必须使用`@time_logger`、`@retry`、`@cache_with_expiration`等装饰器进行性能优化和错误处理。

**类型安全**: 所有新代码必须提供类型注解，支持静态类型检查。

**命名规范**: 遵循既定的命名约定，如CRUD操作的add_/get_/update_/delete_前缀，模型继承MClickBase/MMysqlBase等。

### 4. 测试原则 (Testing Excellence)

**TDD流程**: 新功能开发必须遵循TDD流程，先写测试再实现功能。

**测试分类**: 按照unit、integration、database、network等标记进行测试分类，确保测试覆盖的完整性。

**测试隔离**: 数据库相关测试必须使用测试数据库，避免影响生产数据。

### 5. 性能原则 (Performance Excellence)

**批处理优先**: 数据操作必须使用批量方法(如add_bars)而非单条操作，确保高性能。

**缓存策略**: 合理使用多级缓存(Redis + Memory + Method级别)优化性能。

**懒加载**: 动态导入和懒加载机制必须用于优化启动时间。

### 6. 文档原则 (Documentation Excellence)

**中文优先**: 所有文档和注释必须使用中文，确保团队理解和维护的便利性。

**API文档**: 核心API必须提供详细的使用示例和参数说明。

**架构文档**: 重要组件必须有清晰的架构说明和设计理念文档。

## 治理结构

### 章程修订流程

1. **提案**: 任何项目成员都可以提出章程修订建议
2. **讨论**: 在团队中进行充分讨论，确保所有相关人员理解变更内容
3. **投票**: 采用多数同意原则进行表决
4. **实施**: 修订通过后更新版本号并通知所有相关人员

### 版本管理策略

- **主版本号(MAJOR)**: 向后不兼容的治理原则变更或核心原则重新定义
- **次版本号(MINOR)**: 新增原则或重大扩展现有指导原则
- **修订号(PATCH)**: 澄清说明、文字修正、非语义优化

### 合规审查

- 每季度审查章程执行情况
- 新成员加入时必须学习并确认理解章程内容
- 重要架构决策必须对照章程原则进行审查

## 执行机制

### 自动化检查

- CI/CD流水线必须集成敏感文件扫描
- 代码质量检查必须包含章程合规性验证
- 测试覆盖率必须达到设定的最低标准

### 问责机制

- 违反章程原则的代码提交必须被拒绝或要求修正
- 严重违反章程的行为将影响项目参与权限
- 优秀遵守章程的实践将被记录和推广

---

**此章程自2025年11月3日起生效，所有Ginkgo项目参与者必须严格遵守。**