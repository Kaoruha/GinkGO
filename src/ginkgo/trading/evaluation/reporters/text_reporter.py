"""
Text reporter for evaluation results using Rich formatting.

Generates beautiful, colorized console output for evaluation results.
"""

from io import StringIO
from typing import Optional, TextIO

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ginkgo.trading.evaluation.core.enums import EvaluationSeverity
from ginkgo.trading.evaluation.core.evaluation_result import EvaluationResult, EvaluationIssue, SignalTraceReport
from ginkgo.trading.evaluation.reporters.base_reporter import BaseReporter


class TextReporter(BaseReporter):
    """
    Reporter that generates Rich-formatted text output.

    Attributes:
        format_name: "text"
        file_extension: "txt"
        console: Rich console instance for output
    """

    format_name = "text"
    file_extension = "txt"

    def __init__(self, use_colors: bool = True, width: Optional[int] = None):
        """
        Initialize the text reporter.

        Args:
            use_colors: Whether to use colors in output
            width: Optional width for output
        """
        super().__init__()
        self.use_colors = use_colors
        self.console = Console(width=width, force_terminal=use_colors)

    def generate(
        self,
        result: EvaluationResult,
        output: Optional[TextIO] = None,
        show_context: bool = False,
    ) -> str:
        """
        Generate a text report from the evaluation result.

        Args:
            result: The evaluation result to report
            output: Optional file-like object to write to
            show_context: Whether to include code context in issues

        Returns:
            Formatted report as string
        """
        # Generate simple text format (without Rich formatting issues)
        report_lines = self._generate_simple_report(result, show_context)
        report_content = "\n".join(report_lines)

        # Write to output if provided
        if output:
            output.write(report_content)

        return report_content

    def _generate_simple_report(
        self,
        result: EvaluationResult,
        show_context: bool,
    ) -> list[str]:
        """Generate simple text report without Rich formatting."""
        lines = []

        # Header box
        lines.append("╭─" + "─" * 58 + "─╮")
        lines.append("│" + " " * 15 + "Strategy Validation Report" + " " * 19 + "│")
        lines.append("╰─" + "─" * 58 + "─╯")
        lines.append("")

        # Basic info
        status_icon = "✅" if result.passed else "❌"
        status_text = "PASSED" if result.passed else "FAILED"

        # Handle both Path and str types
        file_path_str = str(result.file_path) if result.file_path else "Unknown"
        component_str = result.component_type.value if hasattr(result.component_type, 'value') else str(result.component_type)
        level_str = result.level.value.upper() if hasattr(result.level, 'value') else str(result.level).upper()

        lines.append(f"File: {file_path_str}")
        lines.append(f"Component: {component_str}")
        lines.append(f"Level: {level_str}")
        lines.append(f"Result: {status_icon} {status_text}")
        lines.append("")

        # Duration
        if result.duration_seconds:
            lines.append(f"Duration: {result.duration_seconds:.2f}s")
            lines.append("")

        # Summary
        lines.append("Summary:")
        lines.append(f"  Total Issues: {result.total_count}")
        lines.append(f"  Errors: {result.error_count}")
        lines.append(f"  Warnings: {result.warning_count}")
        lines.append(f"  Info: {result.info_count}")
        lines.append("")

        # Issues by severity
        for severity in [EvaluationSeverity.ERROR, EvaluationSeverity.WARNING, EvaluationSeverity.INFO]:
            severity_issues = [i for i in result.issues if i.severity == severity]
            if severity_issues:
                lines.extend(self._format_issue_group(severity, severity_issues, show_context))

        return lines

    def _format_issue_group(
        self,
        severity: EvaluationSeverity,
        issues: list[EvaluationIssue],
        show_context: bool,
    ) -> list[str]:
        """Format a group of issues as simple text."""
        lines = []

        severity_labels = {
            EvaluationSeverity.ERROR: ("✗ ERRORS", "red"),
            EvaluationSeverity.WARNING: ("⚠ WARNINGS", "yellow"),
            EvaluationSeverity.INFO: ("ℹ INFO", "blue"),
        }

        label, _ = severity_labels[severity]
        lines.append(f"{label}:")
        lines.append("")

        for i, issue in enumerate(issues, 1):
            # Location
            location = ""
            if issue.file_path:
                location = str(issue.file_path)
                if issue.line is not None:
                    location += f":{issue.line}"
            lines.append(f"  {i}. {issue.code}")
            if location:
                lines.append(f"     {location}")

            # Message
            lines.append(f"     {issue.message}")

            # Suggestion
            if issue.suggestion:
                lines.append(f"     💡 {issue.suggestion}")

            # Context
            if show_context and issue.context:
                lines.append("     Context:")
                for ctx_line in issue.context.splitlines()[:5]:
                    lines.append(f"       {ctx_line}")

            lines.append("")

        return lines

    def _generate_report(
        self,
        console: Console,
        result: EvaluationResult,
        show_context: bool,
    ) -> None:
        """Generate the actual report content."""
        # Header panel
        status_text = "✅ PASSED" if result.passed else "❌ FAILED"
        status_style = "green" if result.passed else "red"

        console.print(
            Panel(
                f"[bold white]{status_text}[/bold white]\n\n"
                f"File: {result.file_path}\n"
                f"Component: {result.component_type}\n"
                f"Level: {result.level.value.upper()}",
                title="[bold]Strategy Validation Report[/bold]",
                border_style=status_style,
            )
        )

        # Duration if available
        if result.duration_seconds:
            console.print(f"\n[dim]Duration: {result.duration_seconds:.2f}s[/dim]")

        # Summary table
        self._print_summary(console, result)

        # Issues by severity
        if result.issues:
            self._print_issues(console, result, show_context)
        else:
            console.print("\n[green]No issues found.[/green]")

    def _print_summary(self, console: Console, result: EvaluationResult) -> None:
        """Print summary statistics table."""
        table = Table(show_header=True, header_style="bold magenta", title="Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", justify="right")

        table.add_row("Total Issues", str(result.total_count))
        table.add_row("Errors", f"[red]{result.error_count}[/red]")
        table.add_row("Warnings", f"[yellow]{result.warning_count}[/yellow]")
        table.add_row("Info", f"[blue]{result.info_count}[/blue]")

        console.print("\n")
        console.print(table)

    def _print_issues(
        self,
        console: Console,
        result: EvaluationResult,
        show_context: bool,
    ) -> None:
        """Print issues grouped by severity."""
        for severity in [EvaluationSeverity.ERROR, EvaluationSeverity.WARNING, EvaluationSeverity.INFO]:
            severity_issues = [i for i in result.issues if i.severity == severity]

            if severity_issues:
                self._print_issue_group(console, severity, severity_issues, show_context)

    def _print_issue_group(
        self,
        console: Console,
        severity: EvaluationSeverity,
        issues: list[EvaluationIssue],
        show_context: bool,
    ) -> None:
        """Print a group of issues with the same severity."""
        severity_style = {
            EvaluationSeverity.ERROR: "red",
            EvaluationSeverity.WARNING: "yellow",
            EvaluationSeverity.INFO: "blue",
        }[severity]

        severity_icon = {
            EvaluationSeverity.ERROR: "✗",
            EvaluationSeverity.WARNING: "⚠",
            EvaluationSeverity.INFO: "ℹ",
        }[severity]

        console.print(f"\n[{severity_style}]{severity_icon} {severity.value.upper()}s[/{severity_style}]")

        for i, issue in enumerate(issues, 1):
            # Location
            location = ""
            if issue.file_path:
                location = str(issue.file_path)
                if issue.line is not None:
                    location += f":{issue.line}"
                    if issue.column is not None:
                        location += f":{issue.column}"

            # Issue header
            console.print(f"\n  [{severity_style}]{i}. {issue.code}[/{severity_style}]")

            if location:
                console.print(f"     [dim]{location}[/dim]")

            # Message
            console.print(f"     {issue.message}")

            # Suggestion
            if issue.suggestion:
                console.print(f"     [dim]💡 {issue.suggestion}[/dim]")

            # Context (code snippet)
            if show_context and issue.context:
                console.print(f"\n     [dim]Context:[/dim]")
                for line in issue.context.splitlines()[:5]:  # Limit to 5 lines
                    console.print(f"     {line}")

    def generate_signal_trace_report(
        self,
        trace_report: SignalTraceReport,
        output: Optional[TextIO] = None,
    ) -> str:
        """
        Generate a signal trace report.

        Args:
            trace_report: The signal trace report
            output: Optional file-like object to write to

        Returns:
            Formatted trace report as string
        """
        # Capture output
        string_output = StringIO()
        console = Console(file=string_output, force_terminal=self.use_colors)

        # Header
        console.print(
            Panel(
                f"[bold white]Signal Trace Report[/bold white]\n\n"
                f"Strategy: {trace_report.strategy_name}\n"
                f"File: {trace_report.strategy_file}",
                title="[bold]Signal Tracing[/bold]",
                border_style="cyan",
            )
        )

        # Summary table
        table = Table(show_header=True, header_style="bold magenta", title="Signal Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", justify="right")

        table.add_row("Total Signals", str(trace_report.signal_count))
        table.add_row("Buy Signals (LONG)", f"[green]{trace_report.buy_count}[/green]")
        table.add_row("Sell Signals (SHORT)", f"[red]{trace_report.sell_count}[/red]")

        if trace_report.duration_seconds:
            table.add_row("Duration", f"{trace_report.duration_seconds:.2f}s")

        console.print("\n")
        console.print(table)

        # Signal list
        if trace_report.traces:
            console.print(f"\n[bold]Signals:[/bold]")

            for i, trace in enumerate(trace_report.traces[:50], 1):  # Limit to 50 signals
                signal = trace.signal

                # Format direction
                direction = str(getattr(signal, "direction", "N/A"))
                if "." in direction:
                    direction = direction.split(".")[-1]

                # Color by direction
                direction_style = "green" if "LONG" in direction or "BUY" in direction else "red"

                # Format timestamp
                timestamp_str = trace.timestamp.strftime("%Y-%m-%d %H:%M:%S")

                # Get signal info
                code = getattr(signal, "code", "N/A")
                reason = getattr(signal, "reason", "")[:60]

                console.print(
                    f"\n  [cyan]{i}.[/cyan] [{timestamp_str}] {code} - "
                    f"[{direction_style}]{direction}[/{direction_style}] - "
                    f"{reason}"
                )

            if len(trace_report.traces) > 50:
                console.print(f"\n  [dim]... and {len(trace_report.traces) - 50} more signals[/dim]")

        report_content = string_output.getvalue()

        if output:
            output.write(report_content)

        return report_content
