# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: 实现 BaseReporter、FileOutputReporter 等类的核心功能，封装相关业务逻辑






"""
Base reporter abstract class for evaluation result reporting.

All reporters must inherit from BaseReporter and implement the required methods.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, TextIO

from ginkgo.trading.evaluation.core.evaluation_result import EvaluationResult, SignalTraceReport


class BaseReporter(ABC):
    """
    Abstract base class for all evaluation result reporters.

    Each reporter is responsible for formatting and outputting
    evaluation results in a specific format (text, JSON, Markdown, etc.).

    Attributes:
        format_name: Human-readable name for this output format
        file_extension: Default file extension for this format
    """

    format_name: str = ""
    file_extension: str = ""

    @abstractmethod
    def generate(
        self,
        result: EvaluationResult,
        output: Optional[TextIO] = None,
        show_context: bool = False,
    ) -> str:
        """
        Generate a report from the evaluation result.

        Args:
            result: The evaluation result to report
            output: Optional file-like object to write to
            show_context: Whether to include code context in issues

        Returns:
            Formatted report as string
        """
        pass

    def generate_to_file(
        self,
        result: EvaluationResult,
        output_path: Path,
        show_context: bool = False,
    ) -> None:
        """
        Generate a report and write it to a file.

        Args:
            result: The evaluation result to report
            output_path: Path to the output file
            show_context: Whether to include code context in issues
        """
        report_content = self.generate(result, show_context=show_context)

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_content)

    def generate_signal_trace_report(
        self,
        trace_report: SignalTraceReport,
        output: Optional[TextIO] = None,
    ) -> str:
        """
        Generate a signal tracing report.

        Args:
            trace_report: The signal trace report to format
            output: Optional file-like object to write to

        Returns:
            Formatted trace report as string
        """
        # Default implementation - can be overridden by subclasses
        report = self._format_trace_report(trace_report)

        if output:
            output.write(report)

        return report

    def _format_trace_report(self, trace_report: SignalTraceReport) -> str:
        """
        Format a signal trace report.

        Args:
            trace_report: The signal trace report to format

        Returns:
            Formatted trace report as string
        """
        # Default simple text format
        lines = [
            f"Signal Trace Report: {trace_report.strategy_name}",
            f"File: {trace_report.strategy_file}",
            "",
            "Summary:",
            f"  Total Signals: {trace_report.signal_count}",
            f"  Buy Signals: {trace_report.buy_count}",
            f"  Sell Signals: {trace_report.sell_count}",
        ]

        if trace_report.duration_seconds:
            lines.append(f"  Duration: {trace_report.duration_seconds:.2f}s")

        if trace_report.traces:
            lines.append("")
            lines.append("Signals:")
            for i, trace in enumerate(trace_report.traces, 1):
                signal = trace.signal
                direction = str(getattr(signal, "direction", "N/A"))
                if "." in direction:
                    direction = direction.split(".")[-1]

                lines.append(
                    f"  {i}. [{trace.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] "
                    f"{getattr(signal, 'code', 'N/A')} - "
                    f"{direction} - "
                    f"{getattr(signal, 'reason', 'N/A')}"
                )

        return "\n".join(lines)

    def __repr__(self) -> str:
        """String representation of the reporter."""
        return f"{self.__class__.__name__}(format={self.format_name})"


class FileOutputReporter(BaseReporter):
    """
    Base class for reporters that support file output.

    Provides common functionality for file-based reporters.
    """

    def __init__(self, indent: Optional[int] = None):
        """
        Initialize the file output reporter.

        Args:
            indent: Optional indentation level for pretty-printing
        """
        self.indent = indent

    def _ensure_output_dir(self, output_path: Path) -> None:
        """
        Ensure the output directory exists.

        Args:
            output_path: Path to the output file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
