# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: Html Visualizer模块提供HTML可视化生成器生成HTML可视化报告支持Web展示功能支持交易系统功能和组件集成提供完整业务支持






"""
HTML-based Signal Visualizer for strategy validation.

Generates interactive HTML charts for signal tracing without external dependencies.
Uses pure HTML/CSS/JavaScript with embedded Chart.js CDN for rendering.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote


class HTMLSignalVisualizer:
    """
    Generate interactive HTML visualizations for signal traces.

    Creates standalone HTML files with embedded JavaScript for interactive charts.
    Uses Chart.js from CDN for rendering candlestick and signal charts.

    Attributes:
        template_dir: Directory containing HTML templates
    """

    def __init__(self, template_dir: Optional[Path] = None):
        """
        Initialize the HTML visualizer.

        Args:
            template_dir: Optional custom template directory
        """
        self.template_dir = template_dir

    def generate_signal_chart(
        self,
        bars: List[Any],
        signals: List[Any],
        output_path: str,
        title: str = "Strategy Signal Chart",
        width: int = 1200,
        height: int = 600,
    ) -> None:
        """
        Generate an interactive HTML candlestick chart with signal markers.

        Args:
            bars: List of bar data with OHLCV properties
            signals: List of Signal objects
            output_path: Path to output HTML file
            title: Chart title
            width: Chart width in pixels
            height: Chart height in pixels
        """
        # Prepare data for chart
        bar_data = self._prepare_bar_data(bars)
        signal_data = self._prepare_signal_data(signals)

        # Generate HTML
        html_content = self._generate_html_template(
            bar_data=bar_data,
            signal_data=signal_data,
            title=title,
            width=width,
            height=height,
        )

        # Write to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(html_content, encoding="utf-8")

    def generate_signal_chart_from_traces(
        self,
        bars: List[Any],
        traces: List[Any],
        output_path: str,
        title: str = "Strategy Signal Chart",
        width: int = 1200,
        height: int = 600,
    ) -> None:
        """
        Generate an interactive HTML candlestick chart with signal markers from SignalTrace objects.

        Uses trace timestamp (event time) instead of signal timestamp for proper K-line mapping.

        Args:
            bars: List of bar data with OHLCV properties
            traces: List of SignalTrace objects
            output_path: Path to output HTML file
            title: Chart title
            width: Chart width in pixels
            height: Chart height in pixels
        """
        # Prepare data for chart
        bar_data = self._prepare_bar_data(bars)
        signal_data = self._prepare_signal_data_from_traces(traces)

        # Generate HTML
        html_content = self._generate_html_template(
            bar_data=bar_data,
            signal_data=signal_data,
            title=title,
            width=width,
            height=height,
        )

        # Write to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(html_content, encoding="utf-8")

    def _prepare_bar_data(self, bars: List[Any]) -> List[Dict[str, Any]]:
        """
        Convert bar objects to chart data format.

        Args:
            bars: List of bar objects with OHLCV properties

        Returns:
            List of dictionaries with timestamp_iso, open, high, low, close, volume
        """
        bar_data = []
        for bar in bars:
            # Get OHLC values - skip bars with missing essential data
            open_val = getattr(bar, "open", None)
            high_val = getattr(bar, "high", None)
            low_val = getattr(bar, "low", None)
            close_val = getattr(bar, "close", None)
            volume_val = getattr(bar, "volume", None)
            timestamp = getattr(bar, "timestamp", None)

            # Skip bars with missing critical data
            if None in [open_val, high_val, low_val, close_val]:
                continue

            # Format timestamp for display and JSON serialization
            if timestamp:
                if hasattr(timestamp, "isoformat"):
                    timestamp_iso = timestamp.isoformat()
                else:
                    timestamp_iso = str(timestamp)
            else:
                continue  # Skip bars without timestamp

            # Convert Decimal to float for JSON serialization
            data_point = {
                "timestamp_iso": timestamp_iso,
                "open": float(open_val),
                "high": float(high_val),
                "low": float(low_val),
                "close": float(close_val),
                "volume": float(volume_val) if volume_val is not None else 0,
            }
            bar_data.append(data_point)
        return bar_data

    def _prepare_signal_data(self, signals: List[Any]) -> List[Dict[str, Any]]:
        """
        Convert signal objects to chart marker format.

        Args:
            signals: List of Signal objects

        Returns:
            List of dictionaries with timestamp_iso, direction, reason
        """
        signal_data = []
        for signal in signals:
            direction = str(getattr(signal, "direction", "UNKNOWN"))
            # Normalize direction enum
            if "." in direction:
                direction = direction.split(".")[-1]

            timestamp = getattr(signal, "timestamp", None)
            # Format timestamp for display and JSON serialization
            if timestamp:
                if hasattr(timestamp, "isoformat"):
                    timestamp_iso = timestamp.isoformat()
                else:
                    timestamp_iso = str(timestamp)
            else:
                timestamp_iso = None

            data_point = {
                "timestamp_iso": timestamp_iso,
                "code": getattr(signal, "code", None),
                "direction": direction,
                "reason": getattr(signal, "reason", ""),
            }
            signal_data.append(data_point)
        return signal_data

    def _prepare_signal_data_from_traces(self, traces: List[Any]) -> List[Dict[str, Any]]:
        """
        Convert SignalTrace objects to chart marker format using trace timestamp (event time).

        Args:
            traces: List of SignalTrace objects

        Returns:
            List of dictionaries with timestamp_iso (from trace/event), direction, reason
        """
        signal_data = []
        for trace in traces:
            signal = trace.signal
            direction = str(getattr(signal, "direction", "UNKNOWN"))
            # Normalize direction enum
            if "." in direction:
                direction = direction.split(".")[-1]

            # Use trace timestamp (event/K-line time) instead of signal timestamp
            timestamp = getattr(trace, "timestamp", None)
            if timestamp is None:
                # Try alternative attribute names
                timestamp = getattr(trace, "trace_timestamp", None)
            if timestamp is None:
                # Fall back to signal timestamp (execution time)
                timestamp = getattr(signal, "timestamp", None)

            if timestamp:
                if hasattr(timestamp, "isoformat"):
                    timestamp_iso = timestamp.isoformat()
                else:
                    timestamp_iso = str(timestamp)
            else:
                timestamp_iso = None

            data_point = {
                "timestamp_iso": timestamp_iso,
                "code": getattr(signal, "code", None),
                "direction": direction,
                "reason": getattr(signal, "reason", ""),
            }
            signal_data.append(data_point)
        return signal_data

    def _generate_html_template(
        self,
        bar_data: List[Dict[str, Any]],
        signal_data: List[Dict[str, Any]],
        title: str,
        width: int,
        height: int,
    ) -> str:
        """
        Generate complete HTML document with embedded chart.

        Layout: Left side K-line chart, Right side signal list.
        Features: Zoom, pan, synchronized charts, hover interactions.

        Args:
            bar_data: Prepared bar data
            signal_data: Prepared signal data
            title: Chart title
            width: Chart width
            height: Chart height

        Returns:
            Complete HTML document as string
        """
        # Escape title for HTML
        title_escaped = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title_escaped}</title>
    <script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1800px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 30px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 24px;
            margin-bottom: 10px;
        }}
        .stats {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 10px;
        }}
        .stat {{
            background: rgba(255,255,255,0.2);
            padding: 8px 20px;
            border-radius: 20px;
            font-size: 13px;
        }}
        .stat-value {{
            font-weight: bold;
            font-size: 16px;
        }}
        /* Main content area with split layout */
        .main-content {{
            display: grid;
            grid-template-columns: 1.4fr 1fr;
            gap: 0;
            height: calc(100vh - 160px);
            min-height: 600px;
        }}
        /* Left side - Charts */
        .chart-section {{
            padding: 20px;
            border-right: 1px solid #eee;
            overflow-y: auto;
        }}
        /* Chart controls */
        .chart-controls {{
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
            flex-wrap: wrap;
            align-items: center;
        }}
        .control-btn {{
            padding: 8px 16px;
            border: 1px solid #ddd;
            background: white;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        .control-btn:hover {{
            background: #f0f0f0;
            border-color: #bbb;
        }}
        .control-btn.primary {{
            background: #667eea;
            color: white;
            border-color: #667eea;
        }}
        .control-btn.primary:hover {{
            background: #5568d3;
        }}
        .window-control {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 0 15px;
            border-left: 1px solid #eee;
            border-right: 1px solid #eee;
        }}
        .window-control label {{
            font-size: 13px;
            color: #666;
        }}
        .window-control select {{
            padding: 6px 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 13px;
            cursor: pointer;
        }}
        .zoom-hint {{
            font-size: 12px;
            color: #999;
            margin-left: auto;
        }}
        .chart-wrapper {{
            position: relative;
            height: 300px;
            margin-bottom: 20px;
        }}
        /* Right side - Signal List */
        .signal-list-section {{
            padding: 20px;
            background: #f9f9f9;
            overflow-y: auto;
            max-height: calc(100vh - 160px);
        }}
        .signal-list-section h2 {{
            font-size: 18px;
            margin-bottom: 15px;
            color: #333;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }}
        .signal-list {{
            list-style: none;
        }}
        .signal-item {{
            background: white;
            border-radius: 8px;
            padding: 12px 15px;
            margin-bottom: 10px;
            border-left: 4px solid #ddd;
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid #e0e0e0;
            border-left-width: 4px;
        }}
        .signal-item:hover {{
            transform: translateX(5px);
            box-shadow: 0 3px 10px rgba(0,0,0,0.15);
            border-color: #667eea;
        }}
        .signal-item.active {{
            background: #e3f2fd;
            border-left-color: #2196F3;
        }}
        .signal-item.buy {{
            border-left-color: #00c853;
        }}
        .signal-item.buy:hover {{
            background: #e8f5e9;
        }}
        .signal-item.sell {{
            border-left-color: #ff1744;
        }}
        .signal-item.sell:hover {{
            background: #ffebee;
        }}
        .signal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}
        .signal-direction {{
            font-weight: bold;
            font-size: 14px;
            padding: 4px 12px;
            border-radius: 12px;
            display: inline-block;
        }}
        .signal-direction.buy {{
            background: #00c853;
            color: white;
        }}
        .signal-direction.sell {{
            background: #ff1744;
            color: white;
        }}
        .signal-time {{
            font-size: 12px;
            color: #999;
        }}
        .signal-reason {{
            font-size: 13px;
            color: #555;
            line-height: 1.4;
        }}
        .signal-info {{
            display: flex;
            gap: 15px;
            margin-top: 8px;
            font-size: 12px;
            color: #666;
        }}
        .footer {{
            text-align: center;
            padding: 15px;
            color: #999;
            font-size: 12px;
            border-top: 1px solid #eee;
            background: #f5f5f5;
        }}
        /* Scrollbar styling */
        .signal-list-section::-webkit-scrollbar {{
            width: 8px;
        }}
        .signal-list-section::-webkit-scrollbar-track {{
            background: #f1f1f1;
        }}
        .signal-list-section::-webkit-scrollbar-thumb {{
            background: #888;
            border-radius: 4px;
        }}
        .signal-list-section::-webkit-scrollbar-thumb:hover {{
            background: #555;
        }}
        /* Responsive */
        @media (max-width: 1200px) {{
            .main-content {{
                grid-template-columns: 1fr;
                height: auto;
            }}
            .chart-section {{
                border-right: none;
                border-bottom: 1px solid #eee;
            }}
            .signal-list-section {{
                max-height: 400px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📈 {title_escaped}</h1>
            <div class="stats">
                <div class="stat">
                    <span>总信号: </span>
                    <span class="stat-value">{len(signal_data)}</span>
                </div>
                <div class="stat">
                    <span>买入: </span>
                    <span class="stat-value">{sum(1 for s in signal_data if s['direction'] in ['LONG', 'BUY'])}</span>
                </div>
                <div class="stat">
                    <span>卖出: </span>
                    <span class="stat-value">{sum(1 for s in signal_data if s['direction'] in ['SHORT', 'SELL'])}</span>
                </div>
            </div>
        </div>

        <div class="main-content">
            <!-- Left: Charts -->
            <div class="chart-section">
                <!-- Chart Controls -->
                <div class="chart-controls">
                    <button class="control-btn primary" id="resetZoom">
                        🔄 重置缩放
                    </button>
                    <button class="control-btn" id="zoomIn">
                        🔍+ 放大
                    </button>
                    <button class="control-btn" id="zoomOut">
                        🔍- 缩小
                    </button>
                    <div class="window-control">
                        <label>窗口大小:</label>
                        <select id="windowSize">
                            <option value="20">20 天</option>
                            <option value="30">30 天</option>
                            <option value="60" selected>60 天</option>
                            <option value="90">90 天</option>
                            <option value="120">120 天</option>
                            <option value="all">全部</option>
                        </select>
                    </div>
                    <span class="zoom-hint">💡 滚轮缩放 | 拖拽平移</span>
                </div>
                <div class="chart-wrapper">
                    <div id="priceChart" style="width: 100%; height: 100%;"></div>
                </div>
                <div class="chart-wrapper">
                    <div id="volumeChart" style="width: 100%; height: 100%;"></div>
                </div>
            </div>

            <!-- Right: Signal List -->
            <div class="signal-list-section">
                <h2>📋 信号列表 ({len(signal_data)} 条)</h2>
                <ul class="signal-list" id="signalList">
                    {self._generate_signal_list_items(signal_data)}
                </ul>
            </div>
        </div>

        <div class="footer">
            Generated by Ginkgo Strategy Validation | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>

    <script>
        // ============================================
        // Lightweight Charts K线可视化
        // ============================================
        console.log('=== Lightweight Charts K线可视化 ===');
        console.log('Lightweight Charts 版本:', LightweightCharts ? '已加载 ✅' : '未加载 ❌');

        // Chart data
        const barData = {json.dumps(bar_data)};
        const signalData = {json.dumps(signal_data)};

        console.log('K线数据:', barData.length, '条');
        console.log('信号数据:', signalData.length, '条');

        // Convert data for Lightweight Charts
        // Lightweight Charts expects: {{ time: string/number, open: number, high: number, low: number, close: number, value: number }}
        const candlestickData = barData.map(d => ({{
            time: d.timestamp_iso,
            open: d.open,
            high: d.high,
            low: d.low,
            close: d.close
        }}));

        const volumeData = barData.map(d => ({{
            time: d.timestamp_iso,
            value: d.volume,
            color: d.close >= d.open ? 'rgba(38, 166, 154, 0.5)' : 'rgba(239, 83, 80, 0.5)'
        }}));

        // Map signals to markers
        const markers = [];
        signalData.forEach((signal, idx) => {{
            let signalDate = null;
            if (signal.reason) {{
                const match = signal.reason.match(/(\\d{{4}}-\\d{{2}}-\\d{{2}})/);
                if (match) signalDate = match[1];
            }}
            if (!signalDate && signal.timestamp_iso) {{
                const match = signal.timestamp_iso.match(/(\\d{{4}}-\\d{{2}}-\\d{{2}})/);
                if (match) signalDate = match[1];
            }}
            if (!signalDate) return;

            const bar = barData.find(b => b.timestamp_iso.startsWith(signalDate));
            if (bar) {{
                const isBuy = signal.direction === 'LONG' || signal.direction === 'BUY';
                markers.push({{
                    time: bar.timestamp_iso,
                    position: isBuy ? 'belowBar' : 'aboveBar',
                    color: isBuy ? '#00c853' : '#ff1744',
                    shape: isBuy ? 'arrowUp' : 'arrowDown',
                    text: isBuy ? '买入' : '卖出'
                }});
            }}
        }});

        console.log('转换后的K线数据:', candlestickData.length, '条');
        console.log('成交量数据:', volumeData.length, '条');
        console.log('信号标记:', markers.length, '个');

        // Create chart
        const chartElement = document.getElementById('priceChart');
        const volumeElement = document.getElementById('volumeChart');

        // Chart options
        const chartOptions = {{
            width: chartElement.clientWidth,
            height: 300,
            layout: {{
                background: {{ type: 'solid', color: '#ffffff' }},
                textColor: '#333',
            }},
            grid: {{
                vertLines: {{ color: '#e1e1e1' }},
                horzLines: {{ color: '#e1e1e1' }},
            }},
            timeScale: {{
                borderColor: '#cccccc',
                timeVisible: true,
                secondsVisible: false,
            }},
            rightPriceScale: {{
                borderColor: '#cccccc',
            }},
            crosshair: {{
                mode: LightweightCharts.CrosshairMode.Normal,
            }},
            // Hide any overlay UI elements
            handleScroll: {{
                mouseWheel: true,
                pressed: true,
                verticalTouchDrag: true,
            }},
            handleScale: {{
                axisPressedMouseMove: true,
            }},
        }};

        // Create candlestick series
        const chart = LightweightCharts.createChart(chartElement, chartOptions);
        const candlestickSeries = chart.addCandlestickSeries({{
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderUpColor: '#26a69a',
            borderDownColor: '#ef5350',
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
        }});

        // Add markers
        candlestickSeries.setMarkers(markers);

        // Set data
        candlestickSeries.setData(candlestickData);

        // Create volume chart
        const volumeChart = LightweightCharts.createChart(volumeElement, {{
            ...chartOptions,
            height: 100
        }});
        const volumeSeries = volumeChart.addHistogramSeries({{
            color: '#26a69a',
            priceFormat: {{
                type: 'volume',
            }},
            priceScaleId: '',
        }});
        volumeSeries.setData(volumeData);

        // Sync time scales
        chart.timeScale().subscribeVisibleLogicalRangeChange(range => {{
            volumeChart.timeScale().setVisibleLogicalRange(range);
        }});

        volumeChart.timeScale().subscribeVisibleLogicalRangeChange(range => {{
            chart.timeScale().setVisibleLogicalRange(range);
        }});

        // Fit content
        chart.timeScale().fitContent();
        volumeChart.timeScale().fitContent();

        console.log('✅ K线图表创建成功');
        console.log('K线数据已设置，数量:', candlestickData.length);
        console.log('成交量数据已设置，数量:', volumeData.length);
        console.log('信号标记已设置，数量:', markers.length);
        console.log('=====================================');

        // Store original markers for highlighting
        let originalMarkers = [...markers];
        let currentHighlightTime = null;

        // Function to update chart with highlighted signal
        const highlightSignal = (signalTime) => {{
            // Remove previous highlight if exists
            if (currentHighlightTime) {{
                candlestickSeries.setMarkers(originalMarkers);
            }}

            // Find and highlight the clicked signal
            const signalIndex = originalMarkers.findIndex(m => m.time === signalTime);
            if (signalIndex !== -1) {{
                const highlightedMarkers = [...originalMarkers];
                const originalMarker = highlightedMarkers[signalIndex];
                highlightedMarkers[signalIndex] = {{
                    ...originalMarker,
                    size: 2.5,  // Larger size to make it stand out
                    color: '#2196F3',  // Blue color for highlighted signal
                    text: originalMarker.text  // Keep original text (买入/卖出)
                }};
                candlestickSeries.setMarkers(highlightedMarkers);
                currentHighlightTime = signalTime;
            }}
        }};

        // Function to clear highlight
        const clearHighlight = () => {{
            if (currentHighlightTime) {{
                candlestickSeries.setMarkers(originalMarkers);
                currentHighlightTime = null;
                // Also remove active class from all signal items
                document.querySelectorAll('.signal-item').forEach(i => i.classList.remove('active'));
            }}
        }};

        // Click on chart background to clear highlight
        chart.subscribeClick((param) => {{
            if (!param.time || !param.point) {{
                // Clicked on empty space
                clearHighlight();
            }}
        }});

        // Resize handler
        window.addEventListener('resize', () => {{
            chart.applyOptions({{ width: chartElement.clientWidth }});
            volumeChart.applyOptions({{ width: volumeElement.clientWidth }});
        }});

        // Control buttons
        document.getElementById('resetZoom').addEventListener('click', () => {{
            chart.timeScale().fitContent();
            volumeChart.timeScale().fitContent();
        }});

        document.getElementById('zoomIn').addEventListener('click', () => {{
            chart.timeScale().zoomIn();
            volumeChart.timeScale().zoomIn();
        }});

        document.getElementById('zoomOut').addEventListener('click', () => {{
            chart.timeScale().zoomOut();
            volumeChart.timeScale().zoomOut();
        }});

        // Window size control
        document.getElementById('windowSize').addEventListener('change', (e) => {{
            const value = e.target.value;
            if (value === 'all') {{
                chart.timeScale().fitContent();
                volumeChart.timeScale().fitContent();
            }} else {{
                const days = parseInt(value);
                const totalBars = barData.length;
                if (totalBars > 0) {{
                    const endIndex = totalBars - 1;
                    const startIndex = Math.max(0, endIndex - days);
                    const startTime = barData[startIndex].timestamp_iso;
                    const endTime = barData[endIndex].timestamp_iso;

                    chart.timeScale().setVisibleRange({{
                        from: new Date(startTime),
                        to: new Date(endTime)
                    }});
                }}
            }}
        }});

        // Signal list click interactions (click only, no hover)
        const signalListItems = document.querySelectorAll('.signal-item');
        signalListItems.forEach((item, idx) => {{
            item.addEventListener('click', function() {{
                // Remove active from all items
                signalListItems.forEach(i => i.classList.remove('active'));
                // Add active to clicked item
                item.classList.add('active');

                const signal = signalData[idx];
                let signalDate = null;
                if (signal.reason) {{
                    const match = signal.reason.match(/(\\d{{4}}-\\d{{2}}-\\d{{2}})/);
                    if (match) signalDate = match[1];
                }}
                if (!signalDate && signal.timestamp_iso) {{
                    const match = signal.timestamp_iso.match(/(\\d{{4}}-\\d{{2}}-\\d{{2}})/);
                    if (match) signalDate = match[1];
                }}
                if (!signalDate) return;

                // Find the bar and scroll to it
                const bar = barData.find(b => b.timestamp_iso.startsWith(signalDate));
                if (bar) {{
                    console.log('跳转到信号:', signalDate, '时间戳:', bar.timestamp_iso);

                    // Highlight the clicked signal on the chart
                    highlightSignal(bar.timestamp_iso);

                    // Find the index of this bar in the data
                    const barIndex = barData.findIndex(b => b.timestamp_iso === bar.timestamp_iso);

                    // Show more context - 30 days before and after the signal
                    const dayBefore = 30;
                    const dayAfter = 30;
                    const startIndex = Math.max(0, barIndex - dayBefore);
                    const endIndex = Math.min(barData.length - 1, barIndex + dayAfter);

                    const startTime = new Date(barData[startIndex].timestamp_iso).getTime();
                    const endTime = new Date(barData[endIndex].timestamp_iso).getTime();

                    console.log('使用数据索引:', {{ startIndex, endIndex, barIndex }});
                    console.log('时间范围:', {{
                        from: new Date(startTime).toISOString().split('T')[0],
                        to: new Date(endTime).toISOString().split('T')[0]
                    }});

                    // Use setVisibleRange with timestamp numbers
                    const timeScale = chart.timeScale();
                    timeScale.setVisibleRange({{
                        from: startTime / 1000,  // Convert to seconds for Lightweight Charts
                        to: endTime / 1000
                    }});

                    console.log('跳转完成');
                }}
            }});
        }});
    </script>
</body>
</html>"""
        return html

    def _generate_signal_list_items(self, signal_data: List[Dict[str, Any]]) -> str:
        """
        Generate HTML list items for signals.

        Args:
            signal_data: Prepared signal data

        Returns:
            HTML string with list items
        """
        items = []
        for i, signal in enumerate(signal_data):
            direction_class = "buy" if signal["direction"] in ["LONG", "BUY"] else "sell"
            direction_display = "买入" if signal["direction"] in ["LONG", "BUY"] else "卖出"
            direction_emoji = "🟢" if direction_class == "buy" else "🔴"

            # Format timestamp for display
            timestamp_str = signal.get("timestamp_iso", "N/A")
            if timestamp_str and "T" in timestamp_str:
                timestamp_str = timestamp_str.split("T")[0] + " " + timestamp_str.split("T")[1].split(".")[0][:8]

            # Format reason
            reason = signal.get("reason", "N/A")[:80]
            if len(signal.get("reason", "")) > 80:
                reason += "..."

            item = f"""<li class="signal-item {direction_class}" data-index="{i}">
                <div class="signal-header">
                    <span class="signal-direction {direction_class}">{direction_emoji} {direction_display}</span>
                    <span class="signal-time">#{i+1} • {timestamp_str}</span>
                </div>
                <div class="signal-reason">{reason}</div>
                <div class="signal-info">
                    <span>代码: {signal.get('code', 'N/A')}</span>
                </div>
            </li>"""
            items.append(item)
        return "\n".join(items)

    def generate_summary_report(
        self,
        report: Any,
        output_path: str,
        title: str = "Strategy Validation Report",
    ) -> None:
        """
        Generate an HTML summary report for signal tracing.

        Args:
            report: SignalTraceReport object
            output_path: Path to output HTML file
            title: Report title
        """
        # Extract data from report
        traces = getattr(report, "traces", [])

        # Prepare trace data for display
        trace_data = []
        for trace in traces:
            signal = trace.signal
            direction = str(getattr(signal, "direction", "UNKNOWN"))
            if "." in direction:
                direction = direction.split(".")[-1]

            trace_item = {
                "timestamp": getattr(trace, "timestamp", None),
                "code": getattr(signal, "code", None),
                "direction": direction,
                "reason": getattr(signal, "reason", ""),
                "input_context": getattr(trace, "input_context", {}),
            }
            trace_data.append(trace_item)

        # Generate HTML
        html_content = self._generate_summary_html(
            trace_data=trace_data,
            title=title,
            strategy_name=getattr(report, "strategy_name", "Unknown"),
            strategy_file=getattr(report, "strategy_file", "Unknown"),
            total_count=getattr(report, "signal_count", len(traces)),
            buy_count=getattr(report, "buy_count", 0),
            sell_count=getattr(report, "sell_count", 0),
        )

        # Write to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(html_content, encoding="utf-8")

    def _generate_summary_html(
        self,
        trace_data: List[Dict[str, Any]],
        title: str,
        strategy_name: str,
        strategy_file: str,
        total_count: int,
        buy_count: int,
        sell_count: int,
    ) -> str:
        """Generate HTML summary report."""
        title_escaped = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        rows = []
        for i, trace in enumerate(trace_data, 1):
            direction_class = "signal-buy" if trace["direction"] in ["LONG", "BUY"] else "signal-sell"
            direction_display = "买入" if trace["direction"] in ["LONG", "BUY"] else "卖出"

            # Format timestamp
            timestamp_str = str(trace.get("timestamp", "N/A"))
            if "T" in timestamp_str:
                timestamp_str = timestamp_str.split("T")[0] + " " + timestamp_str.split("T")[1].split(".")[0][:8]

            # Format context
            context = trace.get("input_context", {})
            context_str = ", ".join([f"{k}={v}" for k, v in context.items() if v is not None and k != "timestamp"])

            row = f"""<tr>
                <td>{i}</td>
                <td>{timestamp_str}</td>
                <td>{trace.get('code', 'N/A')}</td>
                <td class="{direction_class}">{direction_display}</td>
                <td>{trace.get('reason', 'N/A')[:80]}</td>
                <td style="font-size: 12px; color: #666;">{context_str[:100]}</td>
            </tr>"""
            rows.append(row)

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title_escaped}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{ font-size: 28px; margin-bottom: 10px; }}
        .header p {{ opacity: 0.9; }}
        .stats {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 20px;
        }}
        .stat {{
            background: rgba(255,255,255,0.2);
            padding: 15px 25px;
            border-radius: 20px;
        }}
        .stat-label {{ font-size: 14px; opacity: 0.9; }}
        .stat-value {{ font-size: 24px; font-weight: bold; }}
        .content {{ padding: 30px; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}
        th {{
            background: #f5f5f5;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #ddd;
        }}
        td {{ padding: 10px 12px; border-bottom: 1px solid #eee; }}
        tr:hover {{ background: #f9f9f9; }}
        .signal-buy {{ color: #00c853; font-weight: bold; }}
        .signal-sell {{ color: #ff1744; font-weight: bold; }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #999;
            font-size: 12px;
            border-top: 1px solid #eee;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 {title_escaped}</h1>
            <p>策略: {strategy_name}</p>
            <p>文件: {strategy_file}</p>
            <div class="stats">
                <div class="stat">
                    <div class="stat-label">总信号</div>
                    <div class="stat-value">{total_count}</div>
                </div>
                <div class="stat">
                    <div class="stat-label">买入</div>
                    <div class="stat-value">{buy_count}</div>
                </div>
                <div class="stat">
                    <div class="stat-label">卖出</div>
                    <div class="stat-value">{sell_count}</div>
                </div>
            </div>
        </div>

        <div class="content">
            <table>
                <thead>
                    <tr>
                        <th>序号</th>
                        <th>时间</th>
                        <th>代码</th>
                        <th>方向</th>
                        <th>理由</th>
                        <th>上下文</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>

        <div class="footer">
            Generated by Ginkgo Strategy Validation | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>"""
        return html
