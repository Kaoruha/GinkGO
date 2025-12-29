# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: Json Reporter模块提供JSONReporter JSON报告器生成JSON格式报告支持数据导出功能支持回测评估和代码验证






"""
JSON reporter for evaluation results.

Generates machine-readable JSON output for evaluation results.
"""

import json
from io import StringIO
from typing import Any, Optional, TextIO

from ginkgo.trading.evaluation.core.evaluation_result import EvaluationResult, SignalTraceReport
from ginkgo.trading.evaluation.reporters.base_reporter import BaseReporter, FileOutputReporter


class JsonReporter(FileOutputReporter):
    """
    Reporter that generates JSON format output.

    Attributes:
        format_name: "json"
        file_extension: "json"
        indent: Indentation level for pretty-printing (default: 2)
    """

    format_name = "json"
    file_extension = "json"

    def __init__(self, indent: int = 2, ensure_ascii: bool = False):
        """
        Initialize the JSON reporter.

        Args:
            indent: Indentation level for pretty-printing (None for compact)
            ensure_ascii: Whether to escape non-ASCII characters
        """
        super().__init__(indent=indent)
        self.ensure_ascii = ensure_ascii

    def generate(
        self,
        result: EvaluationResult,
        output: Optional[TextIO] = None,
        show_context: bool = False,
    ) -> str:
        """
        Generate a JSON report from the evaluation result.

        Args:
            result: The evaluation result to report
            output: Optional file-like object to write to
            show_context: Whether to include code context in issues (ignored for JSON, context always included)

        Returns:
            Formatted report as JSON string
        """
        # Build the report structure
        report_data = self._build_report(result)

        # Convert to JSON
        json_content = json.dumps(
            report_data,
            indent=self.indent,
            ensure_ascii=self.ensure_ascii,
            default=self._json_serializer,
        )

        # Write to output if provided
        if output:
            output.write(json_content)

        return json_content

    def _build_report(self, result: EvaluationResult) -> dict[str, Any]:
        """Build the report data structure."""
        return {
            "format": "json",
            "version": "1.0",
            "result": result.to_dict(),
        }

    def generate_signal_trace_report(
        self,
        trace_report: SignalTraceReport,
        output: Optional[TextIO] = None,
    ) -> str:
        """
        Generate a signal trace report in JSON format.

        Args:
            trace_report: The signal trace report
            output: Optional file-like object to write to

        Returns:
            Formatted trace report as JSON string
        """
        # Build the report structure
        report_data = {
            "format": "json",
            "version": "1.0",
            "report_type": "signal_trace",
            "trace_report": trace_report.to_dict(),
        }

        # Convert to JSON
        json_content = json.dumps(
            report_data,
            indent=self.indent,
            ensure_ascii=self.ensure_ascii,
            default=self._json_serializer,
        )

        if output:
            output.write(json_content)

        return json_content

    def _json_serializer(self, obj: Any) -> Any:
        """
        Custom JSON serializer for non-serializable objects.

        Args:
            obj: Object to serialize

        Returns:
            JSON-serializable representation
        """
        # Handle Path objects
        if hasattr(obj, "__fspath__"):
            return str(obj)

        # Handle datetime objects
        if hasattr(obj, "isoformat"):
            return obj.isoformat()

        # Handle enum objects
        if hasattr(obj, "value"):
            return obj.value

        # Handle objects with to_dict method
        if hasattr(obj, "to_dict"):
            return obj.to_dict()

        # Handle objects with __dict__
        if hasattr(obj, "__dict__"):
            return obj.__dict__

        # Default: convert to string
        return str(obj)
