"""
快速测试 - 只验证日期设置是否正确
"""

import pytest
import time
from playwright.sync_api import sync_playwright

WEB_UI_URL = "http://192.168.50.12:5173"
REMOTE_BROWSER = "http://192.168.50.10:9222"


@pytest.mark.e2e
def test_date_picker_only():
    """只测试日期选择器设置"""

    print("\n" + "=" * 60)
    print("日期选择器测试")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(REMOTE_BROWSER)
        contexts = browser.contexts
        context = contexts[0] if contexts else browser.new_context()
        pages = context.pages
        page = pages[0] if pages else context.new_page()

        try:
            # 导航到回测创建页
            page.goto(f"{WEB_UI_URL}/stage1/backtest/create", wait_until="domcontentloaded")
            time.sleep(2)

            print("\n📅 测试日期设置")

            def set_date_picker(page, label: str, date_value: str):
                """设置 Ant Design DatePicker"""
                # 找到包含 label 的表单项
                form_item = page.locator(f".ant-form-item:has-text('{label}')").first
                if form_item.count() == 0:
                    print(f"  ❌ 未找到 {label} 表单项")
                    return False

                # 找到 picker 组件
                picker = form_item.locator(".ant-picker").first
                if picker.count() == 0:
                    print(f"  ❌ 未找到 {label} picker")
                    return False

                # 点击 picker
                picker.click()
                time.sleep(0.5)

                # 填写日期
                picker_input = picker.locator("input").first
                picker_input.fill(date_value)
                time.sleep(0.3)

                # 按回车确认
                page.keyboard.press("Enter")
                time.sleep(0.5)

                return True

            # 设置开始日期
            if set_date_picker(page, "开始日期", "2024-01-01"):
                print(f"  ✅ 开始日期设置成功")

            # 设置结束日期
            if set_date_picker(page, "结束日期", "2025-12-31"):
                print(f"  ✅ 结束日期设置成功")

            time.sleep(1)

            # 验证 - 检查表单错误
            errors = page.locator(".ant-form-item-explain-error").all()
            print(f"\n表单验证错误数量: {len(errors)}")
            for err in errors:
                print(f"  - {err.text_content()}")

            # 截图
            page.screenshot(path="/tmp/date_picker_test.png", full_page=True)
            print("\n📸 截图已保存: /tmp/date_picker_test.png")

        finally:
            browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
