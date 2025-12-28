"""
Evaluation result entities.

This module defines the result entities returned by evaluators:
- EvaluationIssue: Individual issue found during evaluation
- EvaluationResult: Complete evaluation result with all issues and summary
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ginkgo.trading.evaluation.core.enums import EvaluationLevel, EvaluationSeverity


@dataclass
class EvaluationIssue:
    """
    A single issue found during component evaluation.

    Attributes:
        severity: The severity level of this issue
        code: Unique code identifying the issue type (e.g., "MISSING_CAL_METHOD")
        message: Human-readable description of the issue
        suggestion: Suggested fix or explanation (optional)
        file_path: Path to the file where the issue was found
        line: Line number where the issue occurs (optional)
        column: Column number where the issue occurs (optional)
        context: Additional context information (e.g., code snippet)
        rule_id: ID of the rule that detected this issue
    """

    severity: EvaluationSeverity
    code: str
    message: str
    suggestion: Optional[str] = None
    file_path: Optional[Path] = None
    line: Optional[int] = None
    column: Optional[int] = None
    context: Optional[str] = None
    rule_id: Optional[str] = None

    def __str__(self) -> str:
        """Format issue for display."""
        location = ""
        if self.file_path:
            location = str(self.file_path)
            if self.line is not None:
                location += f":{self.line}"
                if self.column is not None:
                    location += f":{self.column}"

        severity_symbol = {
            EvaluationSeverity.ERROR: "✗",
            EvaluationSeverity.WARNING: "⚠",
            EvaluationSeverity.INFO: "ℹ",
        }[self.severity]

        result = f"{severity_symbol} {self.code}: {self.message}"
        if location:
            result = f"{location}: {result}"
        if self.suggestion:
            result += f"\n  Suggestion: {self.suggestion}"
        return result

    def to_dict(self) -> Dict[str, Any]:
        """Convert issue to dictionary representation."""
        return {
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
            "suggestion": self.suggestion,
            "file_path": str(self.file_path) if self.file_path else None,
            "line": self.line,
            "column": self.column,
            "context": self.context,
            "rule_id": self.rule_id,
        }


@dataclass
class EvaluationResult:
    """
    Complete evaluation result for a component.

    This class aggregates all issues found during evaluation and provides
    summary statistics and pass/fail determination.

    Attributes:
        file_path: Path to the evaluated file
        component_type: Type of component evaluated
        level: Evaluation level used
        issues: List of all issues found
        duration_seconds: Time taken for evaluation (optional)
        metadata: Additional metadata about the evaluation
    """

    file_path: Path
    component_type: str
    level: EvaluationLevel
    issues: List[EvaluationIssue] = field(default_factory=list)
    duration_seconds: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def errors(self) -> List[EvaluationIssue]:
        """Get all ERROR-level issues."""
        return [i for i in self.issues if i.severity == EvaluationSeverity.ERROR]

    @property
    def warnings(self) -> List[EvaluationIssue]:
        """Get all WARNING-level issues."""
        return [i for i in self.issues if i.severity == EvaluationSeverity.WARNING]

    @property
    def infos(self) -> List[EvaluationIssue]:
        """Get all INFO-level issues."""
        return [i for i in self.issues if i.severity == EvaluationSeverity.INFO]

    @property
    def passed(self) -> bool:
        """
        Check if evaluation passed.

        Evaluation passes if there are no ERROR-level issues.
        """
        return len(self.errors) == 0

    @property
    def total_count(self) -> int:
        """Total number of issues."""
        return len(self.issues)

    @property
    def error_count(self) -> int:
        """Number of ERROR-level issues."""
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        """Number of WARNING-level issues."""
        return len(self.warnings)

    @property
    def info_count(self) -> int:
        """Number of INFO-level issues."""
        return len(self.infos)

    def add_issue(self, issue: EvaluationIssue) -> None:
        """
        Add an issue to the result.

        Args:
            issue: The issue to add
        """
        self.issues.append(issue)

    def merge(self, other: "EvaluationResult") -> None:
        """
        Merge another result into this one.

        Args:
            other: Another evaluation result to merge
        """
        self.issues.extend(other.issues)
        if other.duration_seconds:
            if self.duration_seconds is None:
                self.duration_seconds = other.duration_seconds
            else:
                self.duration_seconds += other.duration_seconds

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            "file_path": str(self.file_path),
            "component_type": self.component_type,
            "level": self.level.value,
            "passed": self.passed,
            "summary": {
                "total": self.total_count,
                "errors": self.error_count,
                "warnings": self.warning_count,
                "infos": self.info_count,
            },
            "issues": [issue.to_dict() for issue in self.issues],
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata,
        }

    def get_status_symbol(self) -> str:
        """Get status symbol for display."""
        return "✅ PASSED" if self.passed else "❌ FAILED"

    def __str__(self) -> str:
        """Format result for display."""
        result = [
            f"File: {self.file_path}",
            f"Component: {self.component_type}",
            f"Level: {self.level.value.upper()}",
            f"Result: {self.get_status_symbol()}",
        ]

        if self.duration_seconds:
            result.append(f"Duration: {self.duration_seconds:.2f}s")

        if self.issues:
            result.append("\nIssues:")
            for severity in [EvaluationSeverity.ERROR, EvaluationSeverity.WARNING, EvaluationSeverity.INFO]:
                severity_issues = [i for i in self.issues if i.severity == severity]
                if severity_issues:
                    result.append(f"\n{severity.value.upper()}s:")
                    for issue in severity_issues:
                        result.append(f"  {str(issue)}")
        else:
            result.append("\nNo issues found.")

        return "\n".join(result)


@dataclass
class SignalTrace:
    """
    A single signal generation trace captured during runtime.

    Records the input event and output signal for a single cal() invocation.

    Attributes:
        trace_id: Unique identifier for this trace
        timestamp: When the signal was generated
        input_context: Event data that triggered the signal (price, indicators, etc.)
        signal: The Signal object that was generated
        signal_info: Formatted information about the signal
        strategy_state: Strategy internal state at time of generation (optional)
    """

    trace_id: str
    timestamp: datetime
    input_context: Dict[str, Any]
    signal: Any  # Signal object
    signal_info: Dict[str, Any]
    strategy_state: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary representation."""
        return {
            "trace_id": self.trace_id,
            "timestamp": self.timestamp.isoformat(),
            "input_context": self.input_context,
            "signal": {
                "code": getattr(self.signal, "code", None),
                "direction": str(getattr(self.signal, "direction", None)),
                "reason": getattr(self.signal, "reason", None),
                "timestamp": str(getattr(self.signal, "timestamp", None)),
            },
            "signal_info": self.signal_info,
            "strategy_state": self.strategy_state,
        }


@dataclass
class SignalTraceReport:
    """
    Complete signal tracing report for a strategy.

    Aggregates all SignalTrace records and provides summary statistics.

    Attributes:
        strategy_name: Name of the strategy being traced
        strategy_file: Path to the strategy file
        traces: List of all signal traces captured
        start_time: When tracing started
        end_time: When tracing ended
        metadata: Additional metadata about the tracing session
    """

    strategy_name: str
    strategy_file: Path
    traces: List[SignalTrace] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def signal_count(self) -> int:
        """Total number of signals generated."""
        return len(self.traces)

    @property
    def buy_count(self) -> int:
        """Number of LONG (buy) signals."""
        count = 0
        for trace in self.traces:
            direction = str(getattr(trace.signal, "direction", ""))
            if "LONG" in direction or "BUY" in direction:
                count += 1
        return count

    @property
    def sell_count(self) -> int:
        """Number of SHORT (sell) signals."""
        count = 0
        for trace in self.traces:
            direction = str(getattr(trace.signal, "direction", ""))
            if "SHORT" in direction or "SELL" in direction:
                count += 1
        return count

    @property
    def duration_seconds(self) -> Optional[float]:
        """Duration of the tracing session."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def add_trace(self, trace: SignalTrace) -> None:
        """Add a signal trace to the report."""
        self.traces.append(trace)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary representation."""
        return {
            "strategy_name": self.strategy_name,
            "strategy_file": str(self.strategy_file),
            "summary": {
                "signal_count": self.signal_count,
                "buy_count": self.buy_count,
                "sell_count": self.sell_count,
                "duration_seconds": self.duration_seconds,
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "end_time": self.end_time.isoformat() if self.end_time else None,
            },
            "traces": [trace.to_dict() for trace in self.traces],
            "metadata": self.metadata,
        }

    def to_csv_rows(self) -> List[Dict[str, Any]]:
        """Convert traces to CSV-friendly row format."""
        rows = []
        for trace in self.traces:
            row = {
                "timestamp": trace.timestamp.isoformat(),
                "code": getattr(trace.signal, "code", None),
                "direction": str(getattr(trace.signal, "direction", None)),
                "reason": getattr(trace.signal, "reason", None),
                "input_context": str(trace.input_context),
            }
            rows.append(row)
        return rows

    def __str__(self) -> str:
        """Format report for display."""
        result = [
            f"Strategy: {self.strategy_name}",
            f"File: {self.strategy_file}",
            f"\nSummary:",
            f"  Total Signals: {self.signal_count}",
            f"  Buy Signals: {self.buy_count}",
            f"  Sell Signals: {self.sell_count}",
        ]
        if self.duration_seconds:
            result.append(f"  Duration: {self.duration_seconds:.2f}s")

        if self.traces:
            result.append(f"\nSignals (showing first {min(20, len(self.traces))}):")
            for i, trace in enumerate(self.traces[:20], 1):
                signal = trace.signal
                # Format direction to show only the enum name (e.g., "LONG" instead of "DIRECTION_TYPES.LONG")
                direction = str(getattr(signal, 'direction', 'N/A'))
                if '.' in direction:
                    direction = direction.split('.')[-1]
                result.append(
                    f"  {i}. [{trace.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] "
                    f"{getattr(signal, 'code', 'N/A')} - "
                    f"{direction} - "
                    f"{getattr(signal, 'reason', 'N/A')[:50]}"
                )
            if len(self.traces) > 20:
                result.append(f"  ... and {len(self.traces) - 20} more")

        return "\n".join(result)
