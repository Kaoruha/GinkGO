# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: Markdown Reporter模块提供Markdown报告器生成报告支持文档生成功能支持回测评估和代码验证






"""
Markdown reporter for evaluation results.

Generates Markdown format output for evaluation results,
suitable for documentation and GitHub/GitLab display.
"""

from typing import Optional, TextIO

from ginkgo.trading.evaluation.core.enums import EvaluationSeverity
from ginkgo.trading.evaluation.core.evaluation_result import EvaluationResult, EvaluationIssue, SignalTraceReport
from ginkgo.trading.evaluation.reporters.base_reporter import BaseReporter, FileOutputReporter


class MarkdownReporter(FileOutputReporter):
    """
    Reporter that generates Markdown format output.

    Attributes:
        format_name: "markdown"
        file_extension: "md"
    """

    format_name = "markdown"
    file_extension = "md"

    def __init__(self, indent: Optional[int] = None):
        """
        Initialize the Markdown reporter.

        Args:
            indent: Ignored for Markdown (kept for compatibility)
        """
        super().__init__(indent=indent)

    def generate(
        self,
        result: EvaluationResult,
        output: Optional[TextIO] = None,
        show_context: bool = False,
    ) -> str:
        """
        Generate a Markdown report from the evaluation result.

        Args:
            result: The evaluation result to report
            output: Optional file-like object to write to
            show_context: Whether to include code context in issues

        Returns:
            Formatted report as Markdown string
        """
        lines = []

        # Header
        status_emoji = "✅" if result.passed else "❌"
        lines.append(f"# {status_emoji} Strategy Validation Report\n")
        lines.append(f"**File:** `{result.file_path}`\n")
        lines.append(f"**Component:** {result.component_type}\n")
        lines.append(f"**Level:** `{result.level.value.upper()}`\n")
        lines.append(f"**Status:** **{'PASSED' if result.passed else 'FAILED'}**\n")

        if result.duration_seconds:
            lines.append(f"**Duration:** {result.duration_seconds:.2f}s\n")

        # Summary
        lines.append("## Summary\n")
        lines.append("| Metric | Count |")
        lines.append("|--------|-------|")
        lines.append(f"| **Total Issues** | {result.total_count} |")
        lines.append(f"| **Errors** | {result.error_count} |")
        lines.append(f"| **Warnings** | {result.warning_count} |")
        lines.append(f"| **Info** | {result.info_count} |\n")

        # Issues
        if result.issues:
            lines.append("## Issues\n")

            for severity in [EvaluationSeverity.ERROR, EvaluationSeverity.WARNING, EvaluationSeverity.INFO]:
                severity_issues = [i for i in result.issues if i.severity == severity]

                if severity_issues:
                    lines.extend(self._format_issue_group(severity, severity_issues, show_context))
        else:
            lines.append("## ✅ No Issues Found\n")

        # Join lines
        report_content = "\n".join(lines)

        # Write to output if provided
        if output:
            output.write(report_content)

        return report_content

    def _format_issue_group(
        self,
        severity: EvaluationSeverity,
        issues: list[EvaluationIssue],
        show_context: bool,
    ) -> list[str]:
        """Format a group of issues with the same severity."""
        lines = []

        severity_icon = {
            EvaluationSeverity.ERROR: "✗",
            EvaluationSeverity.WARNING: "⚠",
            EvaluationSeverity.INFO: "ℹ",
        }[severity]

        lines.append(f"### {severity_icon} {severity.value.upper()}s\n")

        for i, issue in enumerate(issues, 1):
            lines.append(f"#### {i}. `{issue.code}`\n")

            # Location
            if issue.file_path:
                location = str(issue.file_path)
                if issue.line is not None:
                    location += f":{issue.line}"
                    if issue.column is not None:
                        location += f":{issue.column}"
                lines.append(f"**Location:** `{location}`\n")

            # Message
            lines.append(f"**Message:** {issue.message}\n")

            # Suggestion
            if issue.suggestion:
                lines.append(f"**Suggestion:** 💡 {issue.suggestion}\n")

            # Context
            if show_context and issue.context:
                lines.append("**Context:**\n")
                lines.append("```python")
                for line in issue.context.splitlines()[:10]:  # Limit to 10 lines
                    lines.append(line)
                lines.append("```\n")

            lines.append("---\n")

        return lines

    def generate_signal_trace_report(
        self,
        trace_report: SignalTraceReport,
        output: Optional[TextIO] = None,
    ) -> str:
        """
        Generate a signal trace report in Markdown format.

        Args:
            trace_report: The signal trace report
            output: Optional file-like object to write to

        Returns:
            Formatted trace report as Markdown string
        """
        lines = []

        # Header
        lines.append("# 📊 Signal Trace Report\n")
        lines.append(f"**Strategy:** {trace_report.strategy_name}\n")
        lines.append(f"**File:** `{trace_report.strategy_file}`\n")

        # Summary
        lines.append("## Summary\n")
        lines.append("| Metric | Count |")
        lines.append("|--------|-------|")
        lines.append(f"| **Total Signals** | {trace_report.signal_count} |")
        lines.append(f"| **Buy Signals (LONG)** | {trace_report.buy_count} |")
        lines.append(f"| **Sell Signals (SHORT)** | {trace_report.sell_count} |")

        if trace_report.duration_seconds:
            lines.append(f"| **Duration** | {trace_report.duration_seconds:.2f}s |")

        lines.append("")

        # Signal list
        if trace_report.traces:
            lines.append("## Signals\n")
            lines.append("| # | Timestamp | Code | Direction | Reason |")
            lines.append("|---|-----------|------|-----------|--------|")

            for i, trace in enumerate(trace_report.traces[:100], 1):  # Limit to 100 signals
                signal = trace.signal

                # Format direction
                direction = str(getattr(signal, "direction", "N/A"))
                if "." in direction:
                    direction = direction.split(".")[-1]

                # Add emoji for direction
                direction_emoji = "📈" if "LONG" in direction or "BUY" in direction else "📉"

                # Format timestamp
                timestamp_str = trace.timestamp.strftime("%Y-%m-%d %H:%M:%S")

                # Get signal info
                code = getattr(signal, "code", "N/A")
                reason = getattr(signal, "reason", "")[:50]  # Limit reason length
                # Escape pipes in reason
                reason = reason.replace("|", "\\|")

                lines.append(f"| {i} | {timestamp_str} | {code} | {direction_emoji} {direction} | {reason} |")

            if len(trace_report.traces) > 100:
                lines.append(f"\n*... and {len(trace_report.traces) - 100} more signals*")

        report_content = "\n".join(lines)

        if output:
            output.write(report_content)

        return report_content
