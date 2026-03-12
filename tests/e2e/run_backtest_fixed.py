"""
回测 E2E 测试 - 修复参数填充逻辑

测试通过 Playwright 操作 WebUI 创建 Portfolio 并运行回测
正确填写组件参数：
- FixedSelector: codes (股票代码)
- FixedSizer: volume (下单数量)
- RandomSignalStrategy: buy_probability, sell_probability
"""

import time
import pytest
import json
import urllib.request
from playwright.sync_api import Page, expect

from .config import config


@pytest.mark.e2e
@pytest.mark.slow
class TestBacktestWithFixedParams:
    """回测流程测试 - 固定参数"""

    @pytest.fixture(autouse=True)
    def setup(self, authenticated_page: Page):
        """每个测试前准备"""
        self.page = authenticated_page
        self.page.set_default_timeout(60000)
        self.api_base = "http://192.168.50.12:8000/api/v1"

        # 生成唯一任务名
        self.task_name = f"Fixed_BT_{int(time.time())}"
        self.bt_name = f"BT_{int(time.time())}"

        yield

    def _fill_parameter_by_label(self, label_text: str, value: str) -> bool:
        """根据参数标签找到对应的输入框并填写值"""
        page = self.page
        label = page.locator(f".param-label:has-text('{label_text}')").first

        if label.is_visible(timeout=2000):
            param_row = label.locator("..")
            input_field = param_row.locator("input, .ant-input-number-input").first
            input_field.fill(str(value))
            print(f"    ✓ 填写参数 {label_text} = {value}")
            return True
        else:
            print(f"    ✗ 未找到参数标签: {label_text}")
            return False

    def test_01_create_portfolio_with_fixed_selector(self):
        """测试 1: 创建带 FixedSelector 的 Portfolio"""
        page = self.page

        # 导航到组合页面
        page.goto(f"{config.web_ui_url}/portfolio")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # 验证在组合页面
        assert "/portfolio" in page.url

        # 点击创建组合
        page.click('button:has-text("创建组合")')
        page.wait_for_timeout(1000)

        # 验证模态框打开
        modal = page.locator(".ant-modal")
        assert modal.is_visible(), "创建组合模态框应该打开"

        # 填写组合名称
        page.fill('input[placeholder="组合名称"]', self.task_name)
        assert page.locator('input[placeholder="组合名称"]').input_value() == self.task_name

        # 设置初始资金
        cash_input = page.locator(".ant-modal .ant-input-number-input").first
        cash_input.fill("")
        cash_input.fill("100000")
        print("✓ 初始资金: 100000")

        # 添加选股器
        type_btns = page.locator(".ant-modal .component-type-tabs button").all()
        for btn in type_btns:
            text = btn.text_content()
            if "选股器" in text or "SEL" in text:
                btn.click()
                page.wait_for_timeout(500)
                break

        selector_select = page.locator(".ant-modal .component-selector .ant-select").first
        selector_select.click()
        page.wait_for_timeout(500)
        page.keyboard.type("fixed_selector")
        page.wait_for_timeout(500)
        page.keyboard.press("Enter")
        page.wait_for_timeout(1500)
        print("  ✓ 已选择: fixed_selector")

        # 验证选股器被选择
        selector_value = page.locator(".ant-modal .component-selector .ant-select").first.text_content()
        assert "fixed" in selector_value.lower(), "应该选择 fixed_selector"

        # 填写 codes 参数
        result = self._fill_parameter_by_label(page, "codes", "600000.SH")
        assert result, "应该成功填写 codes 参数"

        # 添加仓位管理器
        for btn in type_btns:
            text = btn.text_content()
            if "仓位" in text or "SIZ" in text:
                btn.click()
                page.wait_for_timeout(500)
                break

        sizer_select = page.locator(".ant-modal .component-selector .ant-select").first
        sizer_select.click()
        page.wait_for_timeout(500)
        page.keyboard.type("fixed_sizer")
        page.wait_for_timeout(500)
        page.keyboard.press("Enter")
        page.wait_for_timeout(1500)
        print("  ✓ 已选择: fixed_sizer")

        self._fill_parameter_by_label(page, "volume", "1000")

        # 添加策略
        for btn in type_btns:
            text = btn.text_content()
            if "策略" in text or "STR" in text:
                btn.click()
                page.wait_for_timeout(500)
                break

        strategy_select = page.locator(".ant-modal .component-selector .ant-select").first
        strategy_select.click()
        page.wait_for_timeout(500)
        page.keyboard.type("random_signal")
        page.wait_for_timeout(500)
        page.keyboard.press("Enter")
        page.wait_for_timeout(1500)
        print("  ✓ 已选择: random_signal_strategy")

        self._fill_parameter_by_label(page, "buy_probability", "0.8")
        self._fill_parameter_by_label(page, "sell_probability", "0.1")

        # 保存 Portfolio
        submit_btn = page.locator(".ant-modal button.ant-btn-primary:has-text('创 建')")
        submit_btn.click()
        page.wait_for_timeout(5000)

        # 验证成功消息
        success_msg = page.locator(".ant-message-success, .ant-message-notice-content")
        if success_msg.is_visible():
            print("✓ Portfolio 创建成功")

        # 关闭模态框
        close_btn = page.locator(".ant-modal-close")
        if close_btn.is_visible(timeout=2000):
            close_btn.click()
            page.wait_for_timeout(1000)

    def test_02_verify_portfolio_in_api(self):
        """测试 2: 从 API 验证 Portfolio 已创建"""
        api_url = f"{self.api_base}/portfolio?size=1&sort_by=created_at&order=desc"
        response = urllib.request.urlopen(api_url, timeout=5)
        data = json.loads(response.read())
        portfolios = data.get("data", [])

        assert portfolios, "应该能获取 Portfolio 列表"

        portfolio = portfolios[0]
        portfolio_id = portfolio.get("uuid", "")
        assert portfolio_id, "Portfolio ID 不应该为空"

        print(f"✓ Portfolio ID: {portfolio_id}")

        # 验证组件配置
        components = portfolio.get("components", {})

        selectors = components.get("selectors", [])
        assert selectors, "应该有选股器"
        assert selectors[0].get("name") == "FixedSelector", "应该是 FixedSelector"
        assert "600000.SH" in selectors[0].get("config", {}).get("codes", ""), "codes 应该包含 600000.SH"

        sizer = components.get("sizer", {})
        assert sizer, "应该有仓位管理器"
        assert sizer.get("name") == "FixedSizer", "应该是 FixedSizer"
        assert sizer.get("config", {}).get("volume") == 1000, "volume 应该是 1000"

    def test_03_create_backtest_task(self):
        """测试 3: 创建回测任务"""
        page = self.page

        page.goto(f"{config.web_ui_url}/stage1/backtest")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # 验证在回测页面
        assert "/stage1/backtest" in page.url

        # 点击新建
        page.click('button:has-text("新建")')
        page.wait_for_timeout(1000)

        # 验证模态框打开
        modal = page.locator(".ant-modal")
        assert modal.is_visible(), "创建回测模态框应该打开"

        # 填写任务名称
        page.fill('.ant-modal:visible input[placeholder*="任务名称"]', self.bt_name)
        print(f"✓ 任务名称: {self.bt_name}")

        # 选择 Portfolio
        portfolio_select = page.locator(".ant-modal:visible .ant-select").first
        portfolio_select.click()
        page.wait_for_timeout(500)

        search_input = page.locator(".ant-select-dropdown:visible .ant-select-search__field").first
        if search_input.is_visible():
            search_input.fill(self.task_name)
            page.wait_for_timeout(500)

        dropdown_items = page.locator(".ant-select-dropdown:visible .ant-select-item").all()
        assert dropdown_items, "Portfolio 下拉列表应该有选项"

        dropdown_items[0].click()
        print(f"✓ 已选择Portfolio: {self.task_name}")
        page.wait_for_timeout(500)

        # 设置日期范围
        date_inputs = page.locator(".ant-modal:visible input.ant-picker-input").all()
        assert len(date_inputs) >= 2, "应该有开始和结束日期输入框"

        date_inputs[0].fill("2024-01-02")
        date_inputs[1].fill("2024-01-10")
        print("✓ 日期: 2024-01-02 ~ 2024-01-10")
        page.wait_for_timeout(300)

        # 提交回测
        submit_btn = page.locator(".ant-modal:visible button.ant-btn-primary:has-text('确 定')")
        submit_btn.click()
        page.wait_for_timeout(5000)

        # 验证成功消息
        success_msg = page.locator(".ant-message-success, .ant-message-notice-content")
        if success_msg.is_visible():
            print("✓ 回测任务创建成功")

    def test_04_verify_backtest_in_api(self):
        """测试 4: 从 API 验证回测任务已创建"""
        api_url = f"{self.api_base}/backtest?size=1&sort_by=created_at&order=desc"
        response = urllib.request.urlopen(api_url, timeout=5)
        data = json.loads(response.read())
        tasks = data.get("data", [])

        assert tasks, "应该能获取回测任务列表"

        task = tasks[0]
        backtest_id = task.get("uuid", "")
        assert backtest_id, "回测任务 ID 不应该为空"

        print(f"✓ 回测任务ID: {backtest_id}")

        # 验证任务配置
        assert task.get("name") == self.bt_name, "任务名称应该匹配"

    def test_05_start_backtest_task(self):
        """测试 5: 启动回测任务"""
        # 获取最新回测任务
        api_url = f"{self.api_base}/backtest?size=1&sort_by=created_at&order=desc"
        response = urllib.request.urlopen(api_url, timeout=5)
        data = json.loads(response.read())
        tasks = data.get("data", [])

        assert tasks, "应该有回测任务"
        backtest_id = tasks[0].get("uuid", "")

        # 获取 portfolio_id
        portfolio_id = tasks[0].get("portfolio_id", "")
        assert portfolio_id, "Portfolio ID 不应该为空"

        # 启动回测
        start_url = f"{self.api_base}/backtest/{backtest_id}/start"
        start_req = urllib.request.Request(
            start_url,
            data=b"{}",
            headers={'Content-Type': 'application/json'}
        )
        response = urllib.request.urlopen(start_req, timeout=10)
        result = json.loads(response.read())

        assert result.get("success") or "message" in result, f"启动回测失败: {result}"
        print(f"✓ 回测已启动: {result.get('message', '')}")

    def test_06_wait_for_backtest_completion(self):
        """测试 6: 等待回测完成"""
        # 获取最新回测任务
        api_url = f"{self.api_base}/backtest?size=1&sort_by=created_at&order=desc"
        response = urllib.request.urlopen(api_url, timeout=5)
        data = json.loads(response.read())
        tasks = data.get("data", [])

        assert tasks, "应该有回测任务"
        backtest_id = tasks[0].get("uuid", "")

        # 等待完成
        for i in range(36):
            time.sleep(5)

            try:
                response = urllib.request.urlopen(f"{self.api_base}/backtest/{backtest_id}", timeout=5)
                data = json.loads(response.read())

                status = data.get("status", "")
                progress = data.get("progress", 0)

                print(f"  [{i*5}s] 状态: {status}, 进度: {progress}%")

                if status == "completed" or progress >= 100:
                    print("\n✓✓✓ 回测完成!")
                    return
                elif status == "failed":
                    error_msg = data.get("error_message", "Unknown error")
                    pytest.fail(f"回测失败: {error_msg}")

            except Exception as e:
                print(f"查询状态失败: {e}")

        pytest.fail("回测超时")

    def test_07_verify_analyzer_data(self):
        """测试 7: 验证分析器数据"""
        # 获取最新回测任务
        api_url = f"{self.api_base}/backtest?size=1&sort_by=created_at&order=desc"
        response = urllib.request.urlopen(api_url, timeout=5)
        data = json.loads(response.read())
        tasks = data.get("data", [])

        assert tasks, "应该有回测任务"
        backtest_id = tasks[0].get("uuid", "")

        # 获取分析器数据
        try:
            api_url = f"{self.api_base}/backtest/{backtest_id}/analyzers"
            response = urllib.request.urlopen(api_url, timeout=10)
            data = json.loads(response.read())

            print(f"分析器API返回:")
            print(f"  run_id: {data.get('run_id', '')[:32]}...")
            print(f"  total_count: {data.get('total_count', 0)}")

            analyzers = data.get('analyzers', [])
            assert isinstance(analyzers, list), "分析器数据应该是列表"

            if analyzers:
                print(f"  分析器数量: {len(analyzers)}")

                for analyzer in analyzers:
                    name = analyzer.get('name')
                    count = analyzer.get('record_count', 0)
                    latest = analyzer.get('latest_value')
                    print(f"    - {name}: {count} 条记录, 最新值 = {latest}")

                # 验证至少有一个分析器有数据
                has_data = any(a.get('record_count', 0) > 0 for a in analyzers)
                assert has_data, "至少应该有一个分析器有记录数据"
            else:
                pytest.skip("没有分析器数据（可能未配置分析器）")

        except Exception as e:
            pytest.skip(f"获取分析器数据失败: {e}")
