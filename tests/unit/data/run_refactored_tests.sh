#!/bin/bash
# 数据模型和驱动重构测试运行脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Ginkgo 数据测试套件${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查虚拟环境
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}警告: 未检测到虚拟环境${NC}"
    echo -e "${YELLOW}建议先激活虚拟环境: source venv/bin/activate${NC}"
fi

# 检查pytest
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}错误: pytest 未安装${NC}"
    echo "安装命令: pip install pytest pytest-cov"
    exit 1
fi

# 默认参数
TEST_TYPE="unit"
COVERAGE=false
VERBOSE=false
PARALLEL=false

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--unit)
            TEST_TYPE="unit"
            shift
            ;;
        -i|--integration)
            TEST_TYPE="integration"
            shift
            ;;
        -a|--all)
            TEST_TYPE="all"
            shift
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -p|--parallel)
            PARALLEL=true
            shift
            ;;
        -h|--help)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  -u, --unit          运行单元测试(默认)"
            echo "  -i, --integration    运行集成测试"
            echo "  -a, --all           运行所有测试"
            echo "  -c, --coverage      生成覆盖率报告"
            echo "  -v, --verbose      详细输出"
            echo "  -p, --parallel      并行运行测试"
            echo "  -h, --help          显示此帮助信息"
            exit 0
            ;;
        *)
            echo -e "${RED}未知选项: $1${NC}"
            echo "使用 -h 查看帮助"
            exit 1
            ;;
    esac
done

# 构建pytest命令
PYTEST_CMD="pytest"

# 添加详细输出
if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
else
    PYTEST_CMD="$PYTEST_CMD -q"
fi

# 添加并行支持
if [ "$PARALLEL" = true ]; then
    if command -v pytest-xdist &> /dev/null; then
        PYTEST_CMD="$PYTEST_CMD -n auto"
        echo -e "${GREEN}启用并行测试${NC}"
    else
        echo -e "${YELLOW}pytest-xdist未安装，将串行运行${NC}"
    fi
fi

# 添加覆盖率
if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=src/ginkgo/data --cov-report=html --cov-report=term"
    echo -e "${GREEN}启用覆盖率报告${NC}"
fi

# 运行测试
run_tests() {
    local test_dir=$1
    local marker=$2

    echo ""
    echo -e "${GREEN}运行 $test_dir 测试...${NC}"

    if [ "$marker" = "all" ]; then
        eval "$PYTEST_CMD $test_dir"
    else
        eval "$PYTEST_CMD $test_dir -m $marker"
    fi
}

# 根据测试类型运行
case $TEST_TYPE in
    unit)
        echo -e "${GREEN}运行单元测试(无数据库依赖)${NC}"
        run_tests "test/data/models/" "unit"
        run_tests "test/data/drivers/" "unit"
        ;;
    integration)
        echo -e "${YELLOW}运行集成测试(需要数据库连接)${NC}"
        echo -e "${YELLOW}确保已开启调试模式: ginkgo system config set --debug on${NC}"
        run_tests "test/data/models/" "integration"
        run_tests "test/data/drivers/" "integration"
        ;;
    all)
        echo -e "${GREEN}运行所有测试${NC}"
        run_tests "test/data/models/" "all"
        run_tests "test/data/drivers/" "all"
        ;;
esac

# 检查结果
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}测试通过! ✓${NC}"
    echo -e "${GREEN}========================================${NC}"

    if [ "$COVERAGE" = true ]; then
        echo ""
        echo -e "${GREEN}覆盖率报告: htmlcov/index.html${NC}"
    fi
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}测试失败! ✗${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi
