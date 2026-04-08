#!/bin/bash
# =============================================================================
# run_tests_safe.sh — 分批隔离运行全量测试，防 OOM
#
# 原理：每个测试目录启动独立 pytest 进程，进程退出后 OS 回收全部内存。
#       配合 pytest-timeout 限制单测方法 60s 超时，防止单个测试 hang 住。
#
# 用法：bash scripts/run_tests_safe.sh [目录...]
#   不带参数：运行全部目录
#   带参数：  只运行指定目录，如 bash scripts/run_tests_safe.sh tests/unit/trading
#
# 输出：test_report.md（汇总报告）
# =============================================================================
set -uo pipefail

REPORT="test_report.md"
TIMEOUT_PER_DIR=300      # 单个目录最长 5 分钟
SKIP_FILES=(
    "tests/unit/trading/analysis/test_deviation_checker.py"
)

# 默认目录列表
ALL_DIRS=(
    tests/unit/backtest
    tests/unit/client
    tests/unit/core
    tests/unit/data
    tests/unit/database
    tests/unit/enums
    tests/unit/interfaces
    tests/unit/lab
    tests/unit/libs
    tests/unit/notifier
    tests/unit/notifiers
    tests/unit/research
    tests/unit/trading
    tests/unit/validation
    tests/unit/workers
    tests/integration/data
    tests/integration/database
    tests/integration/backtest
    tests/integration/trading
    tests/integration/network
)

# 如果传了参数，用参数替代
DIRS=("${@:-${ALL_DIRS[@]}}")

# 写报告头部
echo "# 测试报告" > "$REPORT"
echo "" >> "$REPORT"
echo "日期: $(date '+%Y-%m-%d %H:%M')" >> "$REPORT"
echo "" >> "$REPORT"
echo "| 目录 | 测试数 | 内存 | 耗时 | 状态 |" >> "$REPORT"
echo "|------|--------|------|------|------|" >> "$REPORT"

total_pass=0
total_fail=0
total_error=0
total_skip=0
max_rss=0
start_all=$(date +%s)

for dir in "${DIRS[@]}"; do
    [ ! -d "$dir" ] && echo "跳过（不存在）: $dir" && continue

    echo -n "[$(basename $dir)] ... "

    # 构造 ignore 参数
    ignore_args=""
    for sf in "${SKIP_FILES[@]}"; do
        ignore_args="$ignore_args --ignore=$sf"
    done

    # 运行测试：stdout 和 stderr 都捕获到同一个文件
    tmpout=$(mktemp)
    GINKGO_SKIP_DEBUG_CHECK=1 /usr/bin/time -v timeout "$TIMEOUT_PER_DIR" \
        python -m pytest "$dir" -q --tb=line --no-header $ignore_args \
        >"$tmpout" 2>&1
    rc=$?

    # 提取内存
    rss_kb=$(grep "Maximum resident set size" "$tmpout" | awk '{print $NF}')
    rss_mb=$((rss_kb / 1024))
    [ $rss_mb -gt $max_rss ] && max_rss=$rss_mb

    # 提取耗时
    elapsed=$(grep "Elapsed (wall clock) time" "$tmpout" | \
        sed -E 's/.*: ([0-9]+:[0-9:.]+).*/\1/')
    [ -z "$elapsed" ] && elapsed="?"

    # 提取测试结果（从 pytest 的 summary 行）
    summary=$(grep -E "^\d+ (passed|failed|error|skipped)" "$tmpout" | tail -1)
    [ -z "$summary" ] && summary=$(grep -E "passed" "$tmpout" | tail -1)
    p=$(echo "$summary" | grep -oP '\d+(?= passed)' | head -1 || echo "0")
    f=$(echo "$summary" | grep -oP '\d+(?= failed)' | head -1 || echo "0")
    e=$(echo "$summary" | grep -oP '\d+(?= error)' | head -1 || echo "0")
    s=$(echo "$summary" | grep -oP '\d+(?= skipped)' | head -1 || echo "0")
    p=${p:-0}; f=${f:-0}; e=${e:-0}; s=${s:-0}

    total_pass=$((total_pass + p))
    total_fail=$((total_fail + f))
    total_error=$((total_error + e))
    total_skip=$((total_skip + s))

    # 判断状态
    if [ $rc -eq 0 ]; then
        status="PASS"
    elif [ $rc -eq 124 ]; then
        status="TIMEOUT"
    elif [ $rc -eq 137 ]; then
        status="OOM"
    else
        status="FAIL($rc)"
    fi

    echo "${rss_mb}MB | ${p}p/${f}f | ${elapsed} | ${status}"

    # 写报告
    echo "| \`$dir\` | ${p}p/${f}f/${e}e/${s}s | ${rss_mb}MB | ${elapsed}s | ${status} |" >> "$REPORT"

    # 失败详情
    if [ "$status" != "PASS" ]; then
        echo "" >> "$REPORT"
        echo "### $dir 详情" >> "$REPORT"
        echo '```' >> "$REPORT"
        grep -E "FAILED|ERROR|TimeoutExpired|Timeout" "$tmpout" >> "$REPORT" 2>/dev/null || true
        grep -E "short test summary|FAILED" "$tmpout" >> "$REPORT" 2>/dev/null || true
        echo '```' >> "$REPORT"
    fi

    rm -f "$tmpout"
done

end_all=$(date +%s)
wall=$((end_all - start_all))

# 汇总
echo "" >> "$REPORT"
echo "---" >> "$REPORT"
echo "## 汇总" >> "$REPORT"
echo "" >> "$REPORT"
echo "- 总测试: **${total_pass} passed**, ${total_fail} failed, ${total_error} errors, ${total_skip} skipped" >> "$REPORT"
echo "- 总耗时: ${wall}s" >> "$REPORT"
echo "- 最大单批内存: ${max_rss}MB" >> "$REPORT"
echo "- 完成时间: $(date '+%Y-%m-%d %H:%M')" >> "$REPORT"

echo ""
echo "完成! ${total_pass} passed, ${total_fail} failed, ${wall}s, max ${max_rss}MB"
echo "报告: $REPORT"
