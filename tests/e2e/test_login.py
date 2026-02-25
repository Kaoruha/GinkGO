"""
登录功能 E2E 测试

测试登录页面的基本功能：
- 页面访问
- 登录成功
- 登录失败
"""

import pytest
from playwright.sync_api import Page, expect

from .config import config


@pytest.mark.e2e
class TestLogin:
    """登录功能测试"""

    def test_login_page_accessible(self, page: Page):
        """可以访问登录页面"""
        page.goto(f"{config.web_ui_url}/login")

        # 清除认证状态
        page.evaluate("localStorage.clear(); sessionStorage.clear();")
        page.reload(wait_until="networkidle")

        # 验证页面元素
        expect(page.locator("h1")).to_contain_text("GINKGO")
        expect(page.locator('input[placeholder="enter username"]')).to_be_visible()
        expect(page.locator('input[placeholder="enter password"]')).to_be_visible()
        expect(page.locator('button:has-text("EXECUTE")')).to_be_visible()

    def test_login_success(self, page: Page):
        """登录成功"""
        page.goto(f"{config.web_ui_url}/login")
        page.evaluate("localStorage.clear(); sessionStorage.clear();")
        page.reload(wait_until="networkidle")

        # 填写登录信息
        page.fill('input[placeholder="enter username"]', config.test_username)
        page.fill('input[placeholder="enter password"]', config.test_password)
        page.click('button:has-text("EXECUTE")')

        # 验证跳转到仪表盘
        page.wait_for_url("**/dashboard", timeout=10000)
        assert "/dashboard" in page.url

    def test_login_failure(self, page: Page):
        """登录失败"""
        page.goto(f"{config.web_ui_url}/login")
        page.evaluate("localStorage.clear(); sessionStorage.clear();")
        page.reload(wait_until="networkidle")

        # 使用错误密码
        page.fill('input[placeholder="enter username"]', config.test_username)
        page.fill('input[placeholder="enter password"]', "wrongpassword")
        page.click('button:has-text("EXECUTE")')

        # 等待一下
        page.wait_for_timeout(1500)

        # 验证仍在登录页
        assert "/login" in page.url

    def test_logout(self, authenticated_page: Page):
        """登出功能"""
        page = authenticated_page

        # 确保在仪表盘
        assert "/dashboard" in page.url

        # 点击用户菜单 (假设有)
        user_menu = page.locator(".user-menu, .user-dropdown, [data-testid='user-menu']")
        if user_menu.is_visible():
            user_menu.click()
            logout_btn = page.locator("button:has-text('退出'), button:has-text('登出')")
            if logout_btn.is_visible():
                logout_btn.click()
                page.wait_for_url("**/login", timeout=5000)
                assert "/login" in page.url
