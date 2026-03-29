# TDD测试工作流 Makefile
# 简化TDD开发流程的常用命令

PYTHON = python3
PYTEST = $(PYTHON) -m pytest
TEST_DIR = .
SRC_DIR = ../src/ginkgo
TDD_HELPER = tools/tdd_helper.py

# 颜色输出
RED = \033[0;31m
GREEN = \033[0;32m
YELLOW = \033[1;33m
BLUE = \033[0;34m
NC = \033[0m # No Color

.PHONY: help install test tdd-red tdd-green tdd-refactor coverage clean

# 默认目标
help:
	@echo "$(BLUE)Ginkgo TDD测试工作流$(NC)"
	@echo ""
	@echo "$(GREEN)TDD开发流程:$(NC)"
	@echo "  tdd-red MODULE=order    $(YELLOW)# Red阶段：编写失败测试$(NC)"
	@echo "  tdd-green              $(YELLOW)# Green阶段：实现代码$(NC)"
	@echo "  tdd-refactor           $(YELLOW)# Refactor阶段：重构优化$(NC)"
	@echo ""
	@echo "$(GREEN)测试命令:$(NC)"
	@echo "  test                   $(YELLOW)# 运行所有测试$(NC)"
	@echo "  test-tdd               $(YELLOW)# 只运行TDD测试$(NC)"
	@echo "  test-integration       $(YELLOW)# 只运行集成测试$(NC)"
	@echo "  test-unit              $(YELLOW)# 只运行单元测试$(NC)"
	@echo "  test-fast              $(YELLOW)# 快速测试（跳过慢测试）$(NC)"
	@echo ""
	@echo "$(GREEN)质量检查:$(NC)"
	@echo "  coverage               $(YELLOW)# 生成覆盖率报告$(NC)"
	@echo "  analyze-mock           $(YELLOW)# 分析Mock使用情况$(NC)"
	@echo "  metrics                $(YELLOW)# 收集TDD度量$(NC)"
	@echo "  quality                $(YELLOW)# 代码质量检查$(NC)"
	@echo ""
	@echo "$(GREEN)环境管理:$(NC)"
	@echo "  install                $(YELLOW)# 安装测试依赖$(NC)"
	@echo "  clean                  $(YELLOW)# 清理测试文件$(NC)"

# 安装依赖
install:
	@echo "$(GREEN)安装测试依赖...$(NC)"
	pip install pytest pytest-cov pytest-mock pytest-xdist
	pip install coverage[toml]
	@echo "$(GREEN)依赖安装完成$(NC)"

# TDD Red阶段
tdd-red:
	@if [ -z "$(MODULE)" ]; then \
		echo "$(RED)错误：请指定MODULE参数$(NC)"; \
		echo "使用方法: make tdd-red MODULE=order"; \
		echo "跳过建议: make tdd-red MODULE=order NO_SUGGESTIONS=1"; \
		exit 1; \
	fi
	@echo "$(RED)🔴 TDD Red阶段：模块 $(MODULE)$(NC)"
	@if [ "$(NO_SUGGESTIONS)" = "1" ]; then \
		$(PYTHON) $(TDD_HELPER) --mode red --module $(MODULE) --no-suggestions; \
	else \
		$(PYTHON) $(TDD_HELPER) --mode red --module $(MODULE); \
	fi

# TDD Green阶段
tdd-green:
	@echo "$(GREEN)🟢 TDD Green阶段$(NC)"
	$(PYTHON) $(TDD_HELPER) --mode green --run-tests

# TDD Refactor阶段
tdd-refactor:
	@echo "$(BLUE)🔄 TDD Refactor阶段$(NC)"
	$(PYTHON) $(TDD_HELPER) --mode refactor

# 运行所有测试
test:
	@echo "$(GREEN)运行所有测试...$(NC)"
	$(PYTEST) $(TEST_DIR) -v

# 只运行TDD测试
test-tdd:
	@echo "$(GREEN)运行TDD测试...$(NC)"
	$(PYTEST) $(TEST_DIR) -m tdd -v

# 只运行集成测试
test-integration:
	@echo "$(GREEN)运行集成测试...$(NC)"
	$(PYTEST) $(TEST_DIR) -m integration -v

# 只运行单元测试
test-unit:
	@echo "$(GREEN)运行单元测试...$(NC)"
	$(PYTEST) $(TEST_DIR) -m "unit and not slow" -v

# 快速测试（跳过慢测试）
test-fast:
	@echo "$(GREEN)运行快速测试...$(NC)"
	$(PYTEST) $(TEST_DIR) -m "not slow" -v --maxfail=3

# 风控相关测试
test-risk:
	@echo "$(GREEN)运行风控系统测试...$(NC)"
	$(PYTEST) $(TEST_DIR) -m risk_management -v

# 金融精度测试
test-financial:
	@echo "$(GREEN)运行金融精度测试...$(NC)"
	$(PYTEST) $(TEST_DIR) -m financial -v

# 生成覆盖率报告
coverage:
	@echo "$(GREEN)生成覆盖率报告...$(NC)"
	$(PYTHON) $(TDD_HELPER) --coverage-report
	@echo "$(GREEN)覆盖率报告: test_v2/htmlcov/index.html$(NC)"

# 分析Mock使用
analyze-mock:
	@echo "$(YELLOW)分析Mock使用情况...$(NC)"
	$(PYTHON) $(TDD_HELPER) --analyze-mock

# 收集TDD度量
metrics:
	@echo "$(BLUE)收集TDD度量数据...$(NC)"
	$(PYTHON) $(TDD_HELPER) --collect-metrics

# 代码质量检查
quality:
	@echo "$(BLUE)运行代码质量检查...$(NC)"
	@echo "检查代码格式..."
	-flake8 $(SRC_DIR) --max-line-length=100 --ignore=E203,W503
	@echo "检查导入排序..."
	-isort --check-only $(SRC_DIR)
	@echo "检查代码风格..."
	-black --check $(SRC_DIR)

# 格式化代码
format:
	@echo "$(GREEN)格式化代码...$(NC)"
	black $(SRC_DIR)
	isort $(SRC_DIR)

# 性能测试
test-performance:
	@echo "$(YELLOW)运行性能测试...$(NC)"
	$(PYTEST) $(TEST_DIR) -m "performance or slow" -v

# 冒烟测试（快速验证核心功能）
test-smoke:
	@echo "$(GREEN)运行冒烟测试...$(NC)"
	$(PYTEST) $(TEST_DIR) -m smoke -v --maxfail=1

# 调试模式运行测试
test-debug:
	@echo "$(YELLOW)调试模式运行测试...$(NC)"
	$(PYTEST) $(TEST_DIR) -v --tb=long --capture=no

# 并行测试（需要pytest-xdist）
test-parallel:
	@echo "$(GREEN)并行运行测试...$(NC)"
	$(PYTEST) $(TEST_DIR) -n auto -v

# 清理文件
clean:
	@echo "$(YELLOW)清理测试文件...$(NC)"
	find $(TEST_DIR) -name "*.pyc" -delete
	find $(TEST_DIR) -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	rm -rf $(TEST_DIR)/htmlcov
	rm -rf $(TEST_DIR)/.pytest_cache
	rm -rf $(TEST_DIR)/.coverage
	rm -f $(TEST_DIR)/tdd_metrics.json
	@echo "$(GREEN)清理完成$(NC)"

# 验证测试环境
check-env:
	@echo "$(BLUE)检查测试环境...$(NC)"
	@echo "Python版本: $(shell $(PYTHON) --version)"
	@echo "Pytest版本: $(shell $(PYTEST) --version)"
	@$(PYTHON) -c "import ginkgo; print('✅ Ginkgo可导入')" 2>/dev/null || echo "❌ Ginkgo不可导入"
	@echo "测试文件数量: $(shell find $(TEST_DIR) -name 'test_*.py' | wc -l)"

# 生成测试报告
report:
	@echo "$(BLUE)生成测试报告...$(NC)"
	$(PYTEST) $(TEST_DIR) --html=test_v2/report.html --self-contained-html

# 监视模式（自动重新运行测试）
watch:
	@echo "$(YELLOW)监视模式：文件变化时自动运行测试$(NC)"
	@echo "需要安装: pip install pytest-watch"
	ptw $(TEST_DIR) -- -v

# 示例用法说明
example:
	@echo "$(BLUE)TDD开发示例流程:$(NC)"
	@echo ""
	@echo "$(YELLOW)1. 开始开发新功能（订单管理）:$(NC)"
	@echo "   make tdd-red MODULE=order"
	@echo ""
	@echo "$(YELLOW)2. 实现代码使测试通过:$(NC)"
	@echo "   # 编写 src/ginkgo/trading/entities/order.py"
	@echo "   make tdd-green"
	@echo ""
	@echo "$(YELLOW)3. 重构代码:$(NC)"
	@echo "   # 优化代码结构"
	@echo "   make tdd-refactor"
	@echo ""
	@echo "$(YELLOW)4. 检查质量:$(NC)"
	@echo "   make coverage"
	@echo "   make analyze-mock"
	@echo "   make quality"