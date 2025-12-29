# Upstream: Data Layer
# Downstream: External APIs (Tushare, Yahoo, etc.)
# Role: TUI终端界面CLI实现仪表板/回测板/实盘板等6个面板类提供交互式终端用户界面支持交易系统功能和组件集成提供完整业务支持






from __future__ import annotations

from functools import partial
from textual import log
from typing import Any

from textual._on import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.timer import Timer
from textual.containers import Container, Grid, Horizontal, VerticalScroll
from textual.widgets import (
    Button,
    Collapsible,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    MarkdownViewer,
    OptionList,
    ProgressBar,
    RadioSet,
    RichLog,
    Static,
    Select,
    SelectionList,
    Switch,
    TabbedContent,
    TabPane,
    TextArea,
    Tree,
)
from textual.widgets._masked_input import MaskedInput
from textual.widgets._toggle_button import ToggleButton
from textual.widgets.option_list import Option
from textual.widgets.text_area import Selection

from ginkgo.data.containers import container

import asyncio
import datetime


class DashboardPanel(Container):
    def compose(self) -> None:
        yield TextArea("Welcome to Dashboard!")

class BacktestPanel(Container):
    def compose(self) -> None:
        # 使用 Horizontal 容器来布局左右部分
        with Horizontal(id="backtest_panel_layout"):
            # 左侧 Docker 区域
            with Container(id="backtest_left", classes="dock panel_left"):
                self.search_box = Input(placeholder="Search...", id="backtest_search_input", classes="border_container")
                self.search_box.border_title = "Search"
                yield self.search_box

                self.backtest_list = VerticalScroll(id="option_list", classes="scroll")
                self.backtest_list.border_title = "Backtest"
                with self.backtest_list:
                    self.option_list = OptionList("backtest Item 1", "backtesst Item 2", "backtest Item 3", id="dock_items")
                    yield self.option_list

            # 右侧 滚动内容
            self.content = VerticalScroll()
            with self.content:
                self.summary = Container(id="summary", classes="border_container")
                self.summary.border_title = "Summary"
                with self.summary:
                    yield Static("Summary")
                self.indicators = Container(id="indicators", classes="border_container")
                self.indicators.border_title="Indicators"
                with self.indicators:
                    yield Static("Indicator 1")

class LivePanel(Container):
    def compose(self) -> None:
        yield TextArea("Welcome to Live!")


class DataPanel(Container):
    def compose(self) -> ComposeResult:
        """Compose the layout of DataPanel."""
        # 使用 Horizontal 容器来布局左右部分
        with Horizontal(id="data_panel_layout"):
            # 左侧 Docker 区域
            with Container(id="backtest_left", classes="dock panel_left"):
                self.search_box = Input(placeholder="Search...", id="search_input", classes="border_container")
                self.search_box.border_title = "Search"
                yield self.search_box

                self.code_list = VerticalScroll(id="option_list", classes="scroll")
                self.code_list.border_title = "Code"
                with self.code_list:
                    self.option_list = OptionList("Dock Item 1", "Dock Item 2", "Dock Item 3", id="dock_items")
                    yield self.option_list
            # 右侧 滚动内容
            self.content = VerticalScroll()
            with self.content:
                self.summary = Container(id="stock_summary", classes="border_container")
                self.summary.border_title = "Code Info"
                with self.summary:
                    yield Static("Item 11", classes="item")
                    yield Static("Item 22", classes="item")
                    yield Static("Item 33", classes="item")
                    yield Static("Item 44", classes="item")
                    yield Static("Item 55", classes="item")
                    yield Static("Item 66", classes="item")
                self.charts = Container(id="indicators", classes="border_container")
                self.charts.border_title="Candle"
                with self.charts:
                    yield Static("Indicator 1")


    async def on_show(self) -> None:
        """
        当组件加载时执行一些逻辑并存储变量。
        """
        # 在这里执行加载时的逻辑 - 使用新的Service API
        stockinfo_service = container.stockinfo_service()
        get_result = stockinfo_service.get()

        if get_result.success:
            stockinfo_data = get_result.data
            import pandas as pd

            # 处理ModelList和其他数据格式
            try:
                if hasattr(stockinfo_data, 'to_dataframe'):  # ModelList有此方法
                    self.stockinfos = stockinfo_data.to_dataframe()
                elif isinstance(stockinfo_data, pd.DataFrame):
                    self.stockinfos = stockinfo_data
                else:
                    self.stockinfos = pd.DataFrame(stockinfo_data)
            except Exception as e:
                # TUI中静默处理错误，使用空DataFrame
                self.stockinfos = pd.DataFrame(columns=['code', 'code_name', 'industry'])
        else:
            # 如果获取失败，使用空的DataFrame
            import pandas as pd
            self.stockinfos = pd.DataFrame(columns=['code', 'code_name', 'industry'])
        self.debounce_timer= None  # 防抖计时器
        self.input_filter = ""

    async def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input value changes."""
        self.input_filter = event.value  # 获取输入框的当前值
        self.option_list.clear_options()
        self.option_list.add_options(["Loading..."])

        if self.debounce_timer is not None and not self.debounce_timer._task.done():
            print("Timer reset: ", self.debounce_timer._task.done())
            self.debounce_timer.reset()
        else:
            self.debounce_timer = self.set_timer(.5, self._filter_and_update_options)

    async def _filter_and_update_options(self) -> None:
        """异步执行过滤逻辑并更新选项列表。"""
        try:
            # 将同步阻塞操作放到线程池中执行
            filtered_df = await asyncio.to_thread(
                self._sync_filter_data, self.input_filter  # 假设 _sync_filter_data 是同步方法
            )
            # 生成显示内容
            new_df = filtered_df.copy()
            new_df['code_with_name'] = " "+new_df['code'] + "   " + new_df['code_name']
            res = [Option(prompt=r['code_with_name'],id=r['code']) for i,r in new_df.iterrows()]
            # 在主线程中更新选项列表
            def update_ui():
                self.option_list.clear_options()
                if res:
                    self.option_list.add_options(res)
                else:
                    self.option_list.add_options(["No results found"])
            # 如果不在主线程中，使用 call_soon_threadsafe 更新 UI
            if not self.is_running_in_main_thread():
                asyncio.get_event_loop().call_soon_threadsafe(update_ui)
            else:
                update_ui()
        except Exception as e:
            log(f"Error filtering data: {e}")
            def show_error():
                self.option_list.clear_options()
                self.option_list.add_options(["Error loading data"])
            # 如果不在主线程中，使用 call_soon_threadsafe 更新 UI
            if not self.is_running_in_main_thread():
                asyncio.get_event_loop().call_soon_threadsafe(show_error)
            else:
                show_error()

    def _sync_filter_data(self, input_value: str):
        """同步的过滤逻辑。"""
        # 这里是同步阻塞操作（例如 Pandas 数据处理）
        log(f"Try filter : {input_value}")
        filtered_df = self.stockinfos[
            self.stockinfos['code'].str.contains(input_value, case=False, na=False) |
            self.stockinfos['code_name'].str.contains(input_value, case=False, na=False)
        ]
        return filtered_df

    def is_running_in_main_thread(self) -> bool:
        """检查当前是否在主线程中运行。"""
        import threading
        return threading.current_thread() is threading.main_thread()

    def deal_keyinput(self, event: events.Key) -> None:
        if event.key == "up":
            self.option_list.action_cursor_up()
        elif event.key == "down":
            self.option_list.action_cursor_down()
            selected_index = self.option_list.highlighted
            print(self.option_list.get_option_at_index(selected_index).prompt)
            print(self.option_list.get_option_at_index(selected_index).id)
        elif event.key == "pageup":
            pass
        elif event.key == "pagedown":
            pass
        elif event.key == "escape":
            self.search_box.blur()
            log("ESC Pressed.")
        elif event.key == "enter":
            self.search_box.focus()

class DevelopPanel(OptionList):
    def on_mount(self) -> None:
        self.add_options(['13','2'])

class GinkgoApp(App[None]):

    CSS = """
    OptionList{
        scrollbar-size: 1 1;
    }
    .item{
        width: 10;
    }
    .panel_left{
        height: auto;
        width: 28;
    }
    .border_container {
        border: round $border;
        background: transparent;
        padding-left: 1;
        padding-right: 1;
    }
    #stock_summary {
        height: 8;
        scrollbar-size: 1 1;
    }
    #option_list {
        scrollbar-size: 1 1;
        border: round $border;
    }
    Input {
        height: 3;
    }
    #search_input {
        & OptionList {
            background: transparent;
            padding: 0;
            border: none;
        }
    }
    TextArea {
        height: 8;
        scrollbar-gutter: stable;
    }
    DataTable {
        height: 8;
    }
    ColorSample {
        width: 1fr;
        color: $text;
        padding: 0 1;
        &.hover-surface {
            &:hover {
                background: $surface;
            }
        }
        &.primary {
            background: $primary;
        }
        &.secondary {
            background: $secondary;
        }
        &.accent {
            background: $accent;
        }
        &.warning {
            background: $warning;
        }
        &.error {
            background: $error;
        }
        &.success {
            background: $success;
        }
        &.foreground, &.background {
            color: $foreground;
            background: $background;
        }
        &.surface {
            background: $surface;
        }
        &.panel {
            background: $panel;
        }
        &.text-primary {
            color: $text-primary;
        }
        &.text-secondary {
            color: $text-secondary;
        }
        &.text-success {
            color: $text-success;
        }
        &.text-warning {
            color: $text-warning;
        }
        &.text-error {
            color: $text-error;
        }
        &.text-accent {
            color: $text-accent;
        }
        &.text-muted {
            color: $text-muted;
        }
        &.text-disabled {
            color: $text-disabled;
        }
        &.primary-muted {
            color: $text-primary;
            background: $primary-muted;
        }
        &.secondary-muted {
            color: $text-secondary;
            background: $secondary-muted;
        }
        &.accent-muted {
            color: $text-accent;
            background: $accent-muted;
        }
        &.warning-muted {
            color: $text-warning;
            background: $warning-muted;
        }
        &.error-muted {
            color: $text-error;
            background: $error-muted;
        }
        &.success-muted {
            color: $text-success;
            background: $success-muted;
        }
    }
    ListView { 
        height: auto;

    }
    Tree {
        height: 5;
    }
    MarkdownViewer {
        height: 8;
    }
    LoadingIndicator {
        height: 3;
    }
    RichLog {
        height: 4;
    }
    TabbedContent {
        width: auto;
    }
    #label-variants {
        & > Label {
            padding: 0 1;
            margin-right: 1;
        }
    }

    #palette {
        height: auto;
        grid-size: 3;
        border-bottom: solid $border;
    }
    #widget-list {
        & > OptionList {
            height: 6;
        }
        & > RadioSet {
            height: 6;
        }
    }
    #widget-list {
    }
    #widget-list > * {
        margin: 1 2;
    }
    .panel {
        background: $panel;
    }
    .no-border {
        border: none;
    }
    #menu {
        height: auto;
        width: auto;
        border: round $border;

        & OptionList {
            background: transparent;
            padding: 0;
            border: none;
        }
    }
    """

    BINDINGS = [
        # Binding(
        #     "ctrl+o",
        #     "widget_search",
        #     "Widget search",
        #     tooltip="Search for a widget",
        # ),
        Binding(
            "ctrl+a",
            "dashboard_tab_switch",
            "Dashboard",
            tooltip="Dashboard",
        ),
        Binding(
            "ctrl+l",
            "live_tab_switch",
            "Live",
            tooltip="Live",
        ),
        Binding(
            "ctrl+b",
            "backtest_tab_switch",
            "Backtest",
            tooltip="Backtest",
        ),
        Binding(
            "ctrl+d",
            "data_tab_switch",
            "Data",
            tooltip="Data",
        ),
        Binding(
            "ctrl+v",
            "develop_tab_switch",
            "Develop",
            tooltip="Dev",
        ),
    ]


    def action_dashboard_tab_switch(self) ->None:
        self.main_menu.active = "dashboard_tabpanel"

    def action_live_tab_switch(self) ->None:
        self.main_menu.active = "live_tabpanel"

    def action_backtest_tab_switch(self) ->None:
        self.main_menu.active = "backtest_tabpanel"

    def action_data_tab_switch(self) ->None:
        self.main_menu.active = "data_tabpanel"

    def action_develop_tab_switch(self) ->None:
        self.main_menu.active = "develop_tabpanel"

    def action_widget_search(self) -> None:
        self.search_commands(
            [
                (
                    widget.__class__.__name__,
                    (
                        partial(self.set_focus, widget)
                        if widget.can_focus
                        else lambda: None
                    ),
                    f"Focus on {widget.__class__.__name__}",
                )
                for widget in self.query("#widget-list > *")
            ],
            placeholder="Search for a widget...",
        )

    def compose(self) -> ComposeResult:
        self.title = "Ginkgo"
        self.main_menu = TabbedContent()
        with Container(id="menu") as container:
            container.border_title = "Ginkgo"
            with self.main_menu as menu:
                with TabPane(title="D[underline cyan]a[/]shboard", id="dashboard_tabpanel"):
                    yield DashboardPanel(id="dashboard_panel")
                with TabPane(title="[underline cyan]L[/]ive", id="live_tabpanel"):
                    yield LivePanel(id="live_panel")
                with TabPane(title="[underline cyan]B[/]acktest", id="backtest_tabpanel"):
                    yield BacktestPanel(id="backtest_tabpanel")
                with TabPane(title="[underline cyan]D[/]ata", id="data_tabpanel"):
                    self.data_panel = DataPanel(id="data_panel")
                    yield self.data_panel
                with TabPane(title="De[underline cyan]v[/]elop", id="develop_tabpanel"):
                    self.dev_panel = DevelopPanel(id="dev_panel")
                    yield self.dev_panel
        yield Footer()

    async def on_key(self, event: events.Key) -> None:
        """Handle key press events for navigation."""
        if self.main_menu.active == "data_tabpanel":
            self.data_panel.deal_keyinput(event)


if __name__ == "__main__":
    GinkgoApp().run()
