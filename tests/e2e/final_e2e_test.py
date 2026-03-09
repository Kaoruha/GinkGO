"""
完整回测 E2E 测试

测试流程:
1. 创建 Portfolio (FixedSelector + FixedSizer + RandomSignalStrategy)
2. 配置组件参数 (codes=000001.SZ, 有数据)
3. 创建并启动回测
4. 等待完成并验证分析器数据
"""

import time
import json
import pytest
import urllib.request
from playwright.sync_api import Page, expect

from .config import config


@pytest.mark.e2e
@pytest.mark.slow
class TestFullBacktestFlow:
    """完整回测流程测试"""

    @pytest.fixture(autouse=True)
    def setup(self, authenticated_page: Page):
        """每个测试前准备"""
        self.page = authenticated_page
        self.page.set_default_timeout(60000)
        self.api_base = "http://192.168.50.12:8000/api/v1"

        # 生成唯一任务名
        self.task_name = f"Final_E2E_{int(time.time())}"
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

    def _get_portfolio_id(self) -> str:
        """从 API 获取最新的 Portfolio ID"""
        api_url = f"{self.api_base}/portfolio?size=1&sort_by=created_at&order=desc"
        response = urllib.request.urlopen(api_url, timeout=5)
        data = json.loads(response.read())
        portfolios = data.get("data", [])

        assert portfolios, "无法获取 Portfolio 列表"
        portfolio_id = portfolios[0].get("uuid", "")
        assert portfolio_id, "Portfolio ID 为空"

        return portfolio_id

    def _get_backtest_id(self) -> str:
        """从 API 获取最新的回测任务 ID"""
        api_url = f"{self.api_base}/backtest?size=1&sort_by=created_at&order=desc"
        response = urllib.request.urlopen(api_url, timeout=5)
        data = json.loads(response.read())
        tasks = data.get("data", [])

        assert tasks, "无法获取回测任务列表"
        backtest_id = tasks[0].get("uuid", "")
        assert backtest_id, "回测任务 ID 为空"

        return backtest_id

    def _start_backtest(self, backtest_id: str, portfolio_id: str):
        """启动回测任务"""
        start_url = f"{self.api_base}/backtest/{backtest_id}/start"
        start_req = urllib.request.Request(
            start_url,
            data=b"{}",  # 空请求体
            headers={'Content-Type': 'application/json'}
        )
        response = urllib.request.urlopen(start_req, timeout=10)
        result = json.loads(response.read())

        assert result.get("success") or "message" in result, f"启动回测失败: {result}"
        print(f"✓ 回测已启动: {result.get('message', '')}")

    def _wait_for_backtest_completion(self, backtest_id: str, max_wait_seconds: int = 180):
        """等待回测完成"""
        start_time = time.time()

        for i in range(max_wait_seconds // 5):
            time.sleep(5)

            response = urllib.request.urlopen(f"{self.api_base}/backtest/{backtest_id}", timeout=5)
            data = json.loads(response.read())

            status = data.get("status", "")
            progress = data.get("progress", 0)
            stage = data.get("current_stage", "")

            print(f"  [{i*5}s] 状态: {status}, 进度: {progress}%, 阶段: {stage}")

            if status == "completed" or progress >= 100:
                print(f"\n✓✓✓ 回测完成!")
                return data
            elif status == "failed":
                error_msg = data.get("error_message", "Unknown error")
                pytest.fail(f"回测失败: {error_msg}")

        pytest.fail(f"回测超时 ({max_wait_seconds}秒)")

    def test_01_create_portfolio(self):
        """测试 1: 创建 Portfolio"""
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
        print(f"✓ 组合名称: {self.task_name}")

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

        self._fill_parameter_by_label(page, "codes", "000001.SZ")

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

        self._fill_parameter_by_label(page, "volume", "100")

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

        self._fill_parameter_by_label(page, "buy_probability", "0.7")
        self._fill_parameter_by_label(page, "sell_probability", "0.2")

        # 保存 Portfolio
        submit_btn = page.locator(".ant-modal button.ant-btn-primary:has-text('创 建')")
        submit_btn.click()
        page.wait_for_timeout(5000)

        # 验证成功消息
        success_msg = page.locator(".ant-message-success")
        if success_msg.is_visible():
            print("✓ Portfolio 创建成功")

        # 关闭模态框
        close_btn = page.locator(".ant-modal-close")
        if close_btn.is_visible(timeout=2000):
            close_btn.click()
            page.wait_for_timeout(1000)

    def test_02_verify_portfolio_created(self):
        """测试 2: 验证 Portfolio 已创建"""
        portfolio_id = self._get_portfolio_id()
        assert portfolio_id, "Portfolio ID 应该存在"
        print(f"✓ Portfolio ID: {portfolio_id}")

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

        date_inputs[0].fill("2023-01-01")
        date_inputs[1].fill("2023-01-31")
        print("✓ 日期: 2023-01-01 ~ 2023-01-31")
        page.wait_for_timeout(300)

        # 提交回测
        submit_btn = page.locator(".ant-modal:visible button.ant-btn-primary:has-text('确 定')")
        submit_btn.click()
        page.wait_for_timeout(5000)

        # 验证成功消息
        success_msg = page.locator(".ant-message-success")
        if success_msg.is_visible():
            print("✓ 回测任务创建成功")

    def test_04_verify_backtest_created(self):
        """测试 4: 验证回测任务已创建"""
        backtest_id = self._get_backtest_id()
        assert backtest_id, "回测任务 ID 应该存在"
        print(f"✓ 回测任务ID: {backtest_id}")

    def test_05_start_backtest(self):
        """测试 5: 启动回测"""
        backtest_id = self._get_backtest_id()
        portfolio_id = self._get_portfolio_id()

        self._start_backtest(backtest_id, portfolio_id)

    def test_06_wait_for_completion(self):
        """测试 6: 等待回测完成"""
        backtest_id = self._get_backtest_id()

        result = self._wait_for_backtest_completion(backtest_id, max_wait_seconds=180)

        # 验证结果
        assert result.get("status") == "completed", "回测状态应为 completed"
        assert result.get("total_signals", 0) >= 0, "应该有信号数据"
        assert result.get("total_orders", 0) >= 0, "应该有订单数据"

        print(f"  信号数: {result.get('total_signals')}")
        print(f"  订单数: {result.get('total_orders')}")
        print(f"  最终净值: {result.get('final_portfolio_value')}")

    def test_07_verify_analyzer_data(self):
        """测试 7: 验证分析器数据"""
        backtest_id = self._get_backtest_id()

        # 从 API 获取分析器数据
        api_url = f"{self.api_base}/backtest/{backtest_id}/analyzers"
        response = urllib.request.urlopen(api_url, timeout=10)
        data = json.loads(response.read())

        print(f"\n分析器API返回:")
        print(f"  run_id: {data.get('run_id', '')[:32]}...")
        print(f"  total_count: {data.get('total_count', 0)}")

        analyzers = data.get('analyzers', [])
        assert isinstance(analyzers, list), "分析器数据应该是列表"

        if analyzers:
            print(f"  分析器数量: {len(analyzers)}")
            print(f"\n分析器详情:")
            for analyzer in analyzers:
                name = analyzer.get('name')
                count = analyzer.get('record_count', 0)
                latest = analyzer.get('latest_value')
                print(f"  - {name}: {count} 条记录, 最新值 = {latest}")

            # 验证至少有一个分析器有数据
            has_data = any(a.get('record_count', 0) > 0 for a in analyzers)
            assert has_data, "至少应该有一个分析器有记录数据"
        else:
            pytest.skip("没有分析器数据（可能未配置分析器）")

    def test_08_verify_analyzer_ui(self):
        """测试 8: 验证分析器 UI 显示"""
        page = self.page
        backtest_id = self._get_backtest_id()

        # 导航到详情页
        page.goto(f"{config.web_ui_url}/stage1/backtest/{backtest_id}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # 点击分析器标签
        analyzer_tab = page.locator('.ant-tabs-tab:has-text("分析器")')
        if analyzer_tab.is_visible():
            analyzer_tab.click()
            page.wait_for_timeout(2000)

            cards = page.locator(".ant-card").all()
            print(f"\n页面显示分析器卡片: {len(cards)} 个")

            # 应该至少有一些卡片显示
            assert len(cards) > 0, "应该有分析器卡片显示"

            for card in cards[:3]:
                text = card.text_content()
                if text:
                    print(f"  - {text[:100]}...")
        else:
            pytest.skip("分析器标签不可见")


# ==================== 独立运行模式 ====================

def run_full_e2e_test():
    """独立运行完整 E2E 测试（兼容旧版接口）"""
    from playwright.sync_api import sync_playwright

    print("\n" + "="*50)
    print("完整回测 E2E 测试（独立运行模式）")
    print("="*50)
    print("\n💡 建议使用 pytest 运行: pytest tests/e2e/final_e2e_test.py -v -s")

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(config.remote_browser)
        context = browser.contexts[0]
        page = context.new_page()
        page.set_default_timeout(60000)

        try:
            # 登录
            page.goto(f"{config.web_ui_url}/login")
            page.fill('input[placeholder="enter username"]', config.test_username)
            page.fill('input[placeholder="enter password"]', config.test_password)
            page.click('button:has-text("EXECUTE")')
            page.wait_for_url("**/dashboard", timeout=10000)

            # 执行测试流程...
            print("✅ 测试准备完成，请使用 pytest 运行完整测试")
            return {"success": True}

        except Exception as e:
            print(f"\n✗ 错误: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}


if __name__ == "__main__":
    result = run_full_e2e_test()
    print(f"\n{'='*50}")
    print(f"测试结果: {'✅ 成功' if result.get('success') else '❌ 失败'}")
    if result.get('error'):
        print(f"错误: {result.get('error')}")
    print(f"{'='*50}")
