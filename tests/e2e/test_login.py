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
        import re

        page = authenticated_page

        # 确保在仪表盘
        assert "/dashboard" in page.url

        # 查找用户菜单 - 必须存在
        user_menu = page.locator(
            '[data-testid="user-menu"], .anticon-user, .user-menu, [class*="user"]'
        )
        expect(user_menu.first).to_be_visible(timeout=5000)
        user_menu.first.click()

        # 查找登出按钮 - 必须存在
        logout_btn = page.locator(
            'text=退出, text=登出, text=Logout, [data-testid="logout-btn"]'
        )
        expect(logout_btn.first).to_be_visible(timeout=5000)
        logout_btn.first.click()

        # 验证跳转到登录页
        expect(page).to_have_url(re.compile(r".*login.*"), timeout=5000)
