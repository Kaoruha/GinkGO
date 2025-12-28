"""
Runtime analyzer for signal generation tracking.

This module provides:
- DataSourceAdapter: Interface for adapting different event types
- BarDataAdapter: Adapter for K-line (EventPriceUpdate) data
- TickDataAdapter: Adapter for Tick (EventTickUpdate) data
- AdapterFactory: Auto-select adapter by event type
- SignalTracer: Context manager for capturing cal() invocations
- RuntimeAnalyzer: Runtime inspection for strategy classes
"""

import uuid
from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ginkgo.libs import GLOG, time_logger
from ginkgo.trading.evaluation.core.evaluation_result import SignalTrace, SignalTraceReport
from ginkgo.trading.events import EventBase


class DataSourceAdapter(ABC):
    """
    Interface for adapting different event types for visualization and tracing.

    Each adapter knows how to:
    1. Extract visualization data from events
    2. Format signal information for display
    3. Provide data summary for reports
    """

    @abstractmethod
    def get_visualization_data(self, event: EventBase) -> Dict[str, Any]:
        """
        Extract data suitable for visualization from an event.

        Returns dict with keys like: timestamp, price, volume, indicators
        """
        pass

    @abstractmethod
    def format_signal_info(self, signal: Any, event: EventBase) -> Dict[str, Any]:
        """
        Format signal information with context from the event.

        Returns dict with keys like: price, ma_value, rsi_value, etc.
        """
        pass

    @abstractmethod
    def get_data_summary(self, events: List[EventBase]) -> Dict[str, Any]:
        """
        Get summary statistics for a list of events.

        Returns dict with keys like: count, start_time, end_time, price_range
        """
        pass

    @abstractmethod
    def supports_event_type(self, event: EventBase) -> bool:
        """Check if this adapter supports the given event type."""
        pass


class BarDataAdapter(DataSourceAdapter):
    """
    Adapter for K-line data (EventPriceUpdate).

    Extracts OHLCV data for candlestick charts and technical indicators.
    """

    def get_visualization_data(self, event: EventBase) -> Dict[str, Any]:
        """Extract OHLCV data from EventPriceUpdate."""
        data = {
            "timestamp": None,
            "code": None,
            "open": None,
            "high": None,
            "low": None,
            "close": None,
            "volume": None,
        }

        # Extract from event if it's a price update event
        if hasattr(event, "timestamp"):
            data["timestamp"] = event.timestamp
        if hasattr(event, "code"):
            data["code"] = event.code
        if hasattr(event, "bar"):
            bar = event.bar
            data["open"] = getattr(bar, "open", None)
            data["high"] = getattr(bar, "high", None)
            data["low"] = getattr(bar, "low", None)
            data["close"] = getattr(bar, "close", None)
            data["volume"] = getattr(bar, "volume", None)

        return data

    def format_signal_info(self, signal: Any, event: EventBase) -> Dict[str, Any]:
        """Format signal with K-line context."""
        info = {
            "signal_code": getattr(signal, "code", None),
            "signal_direction": str(getattr(signal, "direction", None)),
            "signal_reason": getattr(signal, "reason", None),
            "price": None,
            "volume": None,
        }

        viz_data = self.get_visualization_data(event)
        info["price"] = viz_data.get("close")
        info["volume"] = viz_data.get("volume")

        return info

    def get_data_summary(self, events: List[EventBase]) -> Dict[str, Any]:
        """Get summary statistics for K-line data."""
        if not events:
            return {"count": 0}

        prices = []
        volumes = []
        timestamps = []

        for event in events:
            viz_data = self.get_visualization_data(event)
            if viz_data.get("close"):
                prices.append(viz_data["close"])
            if viz_data.get("volume"):
                volumes.append(viz_data["volume"])
            if viz_data.get("timestamp"):
                timestamps.append(viz_data["timestamp"])

        summary = {
            "count": len(events),
            "start_time": min(timestamps) if timestamps else None,
            "end_time": max(timestamps) if timestamps else None,
        }

        if prices:
            summary["price_min"] = min(prices)
            summary["price_max"] = max(prices)
            summary["price_avg"] = sum(prices) / len(prices)

        if volumes:
            summary["volume_total"] = sum(volumes)
            summary["volume_avg"] = sum(volumes) / len(volumes)

        return summary

    def supports_event_type(self, event: EventBase) -> bool:
        """Check if event is a price update event."""
        return hasattr(event, "bar") or hasattr(event, "close")


class TickDataAdapter(DataSourceAdapter):
    """
    Adapter for Tick data (EventTickUpdate).

    Extracts price/volume ticks for tick-by-tick visualization.
    """

    def get_visualization_data(self, event: EventBase) -> Dict[str, Any]:
        """Extract tick data from EventTickUpdate."""
        data = {
            "timestamp": None,
            "code": None,
            "price": None,
            "volume": None,
            "bid_price": None,
            "ask_price": None,
        }

        if hasattr(event, "timestamp"):
            data["timestamp"] = event.timestamp
        if hasattr(event, "code"):
            data["code"] = event.code
        if hasattr(event, "price"):
            data["price"] = event.price
        if hasattr(event, "volume"):
            data["volume"] = event.volume
        if hasattr(event, "bid_price"):
            data["bid_price"] = event.bid_price
        if hasattr(event, "ask_price"):
            data["ask_price"] = event.ask_price

        return data

    def format_signal_info(self, signal: Any, event: EventBase) -> Dict[str, Any]:
        """Format signal with tick context."""
        info = {
            "signal_code": getattr(signal, "code", None),
            "signal_direction": str(getattr(signal, "direction", None)),
            "signal_reason": getattr(signal, "reason", None),
            "price": None,
            "volume": None,
        }

        viz_data = self.get_visualization_data(event)
        info["price"] = viz_data.get("price")
        info["volume"] = viz_data.get("volume")

        return info

    def get_data_summary(self, events: List[EventBase]) -> Dict[str, Any]:
        """Get summary statistics for tick data."""
        if not events:
            return {"count": 0}

        prices = []
        volumes = []
        timestamps = []

        for event in events:
            viz_data = self.get_visualization_data(event)
            if viz_data.get("price"):
                prices.append(viz_data["price"])
            if viz_data.get("volume"):
                volumes.append(viz_data["volume"])
            if viz_data.get("timestamp"):
                timestamps.append(viz_data["timestamp"])

        summary = {
            "count": len(events),
            "start_time": min(timestamps) if timestamps else None,
            "end_time": max(timestamps) if timestamps else None,
        }

        if prices:
            summary["price_min"] = min(prices)
            summary["price_max"] = max(prices)
            summary["price_avg"] = sum(prices) / len(prices)

        if volumes:
            summary["volume_total"] = sum(volumes)

        return summary

    def supports_event_type(self, event: EventBase) -> bool:
        """Check if event is a tick update event."""
        return hasattr(event, "price") and not hasattr(event, "bar")


class AdapterFactory:
    """
    Factory for auto-selecting the appropriate adapter based on event type.
    """

    _adapters: List[DataSourceAdapter] = [
        BarDataAdapter(),
        TickDataAdapter(),
    ]

    @classmethod
    def get_adapter(cls, event: EventBase) -> Optional[DataSourceAdapter]:
        """
        Get the appropriate adapter for the given event type.

        Args:
            event: The event to find an adapter for

        Returns:
            The first adapter that supports this event type, or None
        """
        for adapter in cls._adapters:
            if adapter.supports_event_type(event):
                return adapter
        return None

    @classmethod
    def register_adapter(cls, adapter: DataSourceAdapter) -> None:
        """
        Register a new adapter.

        Args:
            adapter: The adapter to register
        """
        cls._adapters.insert(0, adapter)  # New adapters have priority


@contextmanager
def signal_tracer(strategy: Any, strategy_file: str):
    """
    Context manager for tracing signal generation during strategy execution.

    Usage:
        with signal_tracer(strategy, strategy_file) as tracer:
            result = strategy.cal(portfolio_info, event)
            # tracer automatically captures signals in result

    Args:
        strategy: The strategy instance to trace
        strategy_file: Path to the strategy file

    Yields:
        SignalTracer instance for accessing trace data
    """
    tracer_instance = SignalTracer(strategy, strategy_file)
    try:
        yield tracer_instance
    finally:
        tracer_instance.finalize()


class SignalTracer:
    """
    Runtime signal generation tracer.

    Wraps a strategy's cal() method to capture:
    - Input events and their context
    - Generated signals and their properties
    - Strategy state at generation time
    """

    def __init__(self, strategy: Any, strategy_file: str):
        """
        Initialize the signal tracer.

        Args:
            strategy: The strategy instance to trace
            strategy_file: Path to the strategy file
        """
        self.strategy = strategy
        self.strategy_file = strategy_file
        self.strategy_name = getattr(strategy, "name", strategy.__class__.__name__)
        self.report = SignalTraceReport(
            strategy_name=self.strategy_name,
            strategy_file=strategy_file,
            start_time=datetime.now(),
        )
        self._original_cal = None
        self._adapter = None

    @time_logger
    def _trace_wrapper(self, portfolio_info: Dict, event: EventBase) -> List:
        """
        Wrapper for cal() method that captures signal generation.

        Args:
            portfolio_info: Portfolio information dict
            event: The event triggering cal()

        Returns:
            Original result from cal()
        """
        # Get adapter for this event type
        if self._adapter is None:
            self._adapter = AdapterFactory.get_adapter(event)

        # Call original cal()
        result = self._original_cal(portfolio_info, event)

        # Capture signals
        signals = result if isinstance(result, list) else []
        for signal in signals:
            # Build input context
            input_context = {
                "event_type": event.__class__.__name__,
                "timestamp": str(getattr(event, "timestamp", None)),
            }

            if self._adapter:
                viz_data = self._adapter.get_visualization_data(event)
                input_context.update(viz_data)

            # Build signal info
            signal_info = {
                "code": getattr(signal, "code", None),
                "direction": str(getattr(signal, "direction", None)),
                "reason": getattr(signal, "reason", None),
            }

            if self._adapter:
                signal_info.update(self._adapter.format_signal_info(signal, event))

            # Create trace record - use event business_timestamp (K-line time) for proper chart mapping
            # EventPriceUpdate has both timestamp (creation time) and business_timestamp (K-line time)
            event_timestamp = getattr(event, "business_timestamp", None)
            if event_timestamp is None:
                # Fallback to regular timestamp for event types without business_timestamp
                event_timestamp = getattr(event, "timestamp", None)
            trace_timestamp = event_timestamp if event_timestamp else datetime.now()

            trace = SignalTrace(
                trace_id=str(uuid.uuid4()),
                timestamp=trace_timestamp,
                input_context=input_context,
                signal=signal,
                signal_info=signal_info,
                strategy_state=None,  # Could add strategy state inspection here
            )
            self.report.add_trace(trace)

        return result

    @time_logger
    def start_tracing(self) -> None:
        """Start tracing by wrapping the strategy's cal() method."""
        if hasattr(self.strategy, "cal"):
            self._original_cal = self.strategy.cal
            self.strategy.cal = self._trace_wrapper

    @time_logger
    def stop_tracing(self) -> None:
        """Stop tracing by restoring the original cal() method."""
        if self._original_cal and hasattr(self.strategy, "cal"):
            self.strategy.cal = self._original_cal
            self._original_cal = None

    @time_logger
    def finalize(self) -> None:
        """Finalize tracing and set end time."""
        self.stop_tracing()
        self.report.end_time = datetime.now()

    @time_logger
    def get_report(self) -> SignalTraceReport:
        """Get the signal trace report."""
        return self.report

    def __enter__(self) -> "SignalTracer":
        """Context manager entry."""
        self.start_tracing()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.finalize()


class RuntimeAnalyzer:
    """
    Runtime analyzer for inspecting strategy classes at runtime.

    This analyzer can:
    - Safely instantiate strategy classes
    - Inspect class attributes and methods
    - Check for required attributes (data_feeder, time_provider)
    - Validate method signatures at runtime
    """

    def __init__(self):
        """Initialize the runtime analyzer."""
        from ginkgo.libs import GLOG
        self.GLOG = GLOG

    @time_logger
    def analyze_class(
        self,
        strategy_class: type,
        file_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a strategy class at runtime.

        Args:
            strategy_class: The strategy class to analyze
            file_path: Optional path to the source file

        Returns:
            Dictionary with analysis results including:
            - class_name: Name of the class
            - base_classes: List of base class names
            - has_data_feeder: Whether data_feeder is bound
            - has_time_provider: Whether time_provider is set
            - methods: List of method names
            - attributes: Dict of class attributes
            - instantiation_success: Whether class can be instantiated
            - instantiation_error: Error if instantiation failed
        """
        result = {
            "class_name": strategy_class.__name__,
            "base_classes": self._get_base_classes(strategy_class),
            "has_data_feeder": False,
            "has_time_provider": False,
            "methods": [],
            "attributes": {},
            "instantiation_success": False,
            "instantiation_error": None,
        }

        # Get methods
        result["methods"] = self._get_methods(strategy_class)

        # Get class attributes
        result["attributes"] = self._get_attributes(strategy_class)

        # Try to instantiate
        try:
            instance = self._safe_instantiate(strategy_class)
            result["instantiation_success"] = True

            # Check for data_feeder and time_provider
            if hasattr(instance, "_data_feeder") and instance._data_feeder is not None:
                result["has_data_feeder"] = True
            if hasattr(instance, "_time_provider") and instance._time_provider is not None:
                result["has_time_provider"] = True

        except Exception as e:
            result["instantiation_error"] = str(e)
            self.GLOG.WARN(f"Failed to instantiate {strategy_class.__name__}: {e}")

        return result

    def _get_base_classes(self, cls: type) -> List[str]:
        """Get base class names."""
        bases = []
        for base in cls.__bases__:
            bases.append(base.__name__)
        return bases

    def _get_methods(self, cls: type) -> List[str]:
        """Get public method names."""
        methods = []
        for name in dir(cls):
            if not name.startswith("_") and callable(getattr(cls, name)):
                methods.append(name)
        return methods

    def _get_attributes(self, cls: type) -> Dict[str, Any]:
        """Get class attributes."""
        attributes = {}
        for name in dir(cls):
            if not name.startswith("__"):
                try:
                    attr = getattr(cls, name, None)
                    if not callable(attr):
                        attributes[name] = str(type(attr))
                except Exception:
                    pass
        return attributes

    @time_logger
    def _safe_instantiate(self, strategy_class: type):
        """
        Safely instantiate a strategy class.

        Args:
            strategy_class: The strategy class to instantiate

        Returns:
            Instance of the strategy class

        Raises:
            Exception: If instantiation fails
        """
        # Try basic instantiation with name
        try:
            return strategy_class(name="runtime_test")
        except Exception as e:
            self.GLOG.DEBUG(f"Basic instantiation failed: {e}")

        # Try with minimal parameters
        try:
            import inspect
            sig = inspect.signature(strategy_class.__init__)
            params = {}

            # Fill in required parameters
            for param_name, param in sig.parameters.items():
                if param_name == "self":
                    continue
                if param.default == param.empty:
                    # Required parameter
                    if "name" in param_name:
                        params[param_name] = f"test_{param_name}"
                    elif "code" in param_name:
                        params[param_name] = "000001.SZ"

            return strategy_class(**params)

        except Exception as e:
            raise Exception(f"Cannot instantiate {strategy_class.__name__}: {e}")

    @time_logger
    def check_method_signature(
        self,
        strategy_class: type,
        method_name: str = "cal",
    ) -> Dict[str, Any]:
        """
        Check method signature at runtime.

        Args:
            strategy_class: The strategy class
            method_name: Name of the method to check (default: "cal")

        Returns:
            Dictionary with signature information
        """
        import inspect

        result = {
            "method_name": method_name,
            "exists": False,
            "signature": None,
            "parameters": [],
            "return_annotation": None,
        }

        if not hasattr(strategy_class, method_name):
            return result

        method = getattr(strategy_class, method_name)
        result["exists"] = True

        try:
            sig = inspect.signature(method)
            result["signature"] = str(sig)

            for param_name, param in sig.parameters.items():
                param_info = {
                    "name": param_name,
                    "annotation": str(param.annotation) if param.annotation != param.empty else None,
                    "default": str(param.default) if param.default != param.empty else None,
                }
                result["parameters"].append(param_info)

            result["return_annotation"] = str(sig.return_annotation) if sig.return_annotation != sig.empty else None

        except Exception as e:
            self.GLOG.WARN(f"Failed to inspect {method_name}: {e}")

        return result
