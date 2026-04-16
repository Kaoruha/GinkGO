"""
登录功能 E2E 测试

覆盖：
- 页面元素渲染
- 表单验证（空字段）
- 登录成功/失败
- 密码显示切换
- 路由守卫（未登录跳转）
- 登出
- Token 存储
"""

import re

import pytest
from playwright.sync_api import Page, expect

from ..config import config

# ====== data-testid 选择器 ======
SEL = {
    "form": "[data-testid='login-form']",
    "username": "[data-testid='username-input']",
    "password": "[data-testid='password-input']",
    "username_error": "[data-testid='username-error']",
    "password_error": "[data-testid='password-error']",
    "toggle_pwd": "[data-testid='password-toggle']",
    "submit": "[data-testid='login-submit']",
    "toast": "[data-testid='toast']",
    "user_menu": "[data-testid='user-menu-btn']",
    "logout": "[data-testid='logout-btn']",
}


def _goto_login(page: Page):
    """导航到登录页并清除认证状态"""
    page.goto(f"{config.web_ui_url}/login")
    page.evaluate("localStorage.clear(); sessionStorage.clear();")
    page.reload(wait_until="networkidle")


@pytest.mark.e2e
class TestLoginPageRender:
    """登录页面渲染"""

    def test_page_elements_visible(self, page: Page):
        """所有表单元素可见"""
        _goto_login(page)

        expect(page.locator(SEL["form"])).to_be_visible()
        expect(page.locator(SEL["username"])).to_be_visible()
        expect(page.locator(SEL["password"])).to_be_visible()
        expect(page.locator(SEL["submit"])).to_be_visible()
        expect(page.locator(SEL["toggle_pwd"])).to_be_visible()

    def test_title_displays_ginkgo(self, page: Page):
        """页面标题包含 GINKGO"""
        _goto_login(page)

        expect(page.locator("h1")).to_contain_text("GINKGO")


@pytest.mark.e2e
class TestFormValidation:
    """客户端表单验证"""

    def test_empty_username_shows_error(self, page: Page):
        """空用户名提交后显示错误"""
        _goto_login(page)

        # 只填密码，用户名留空（默认为空），直接提交
        page.fill(SEL["password"], "somepass")
        page.click(SEL["submit"])

        expect(page.locator(SEL["username_error"])).to_be_visible()

    def test_empty_password_shows_error(self, page: Page):
        """空密码提交后显示错误"""
        _goto_login(page)

        page.fill(SEL["username"], "admin")
        page.click(SEL["submit"])

        expect(page.locator(SEL["password_error"])).to_be_visible()

    def test_both_empty_shows_both_errors(self, page: Page):
        """两个字段都为空时显示两个错误"""
        _goto_login(page)

        # 两个字段默认为空，直接提交
        page.click(SEL["submit"])

        expect(page.locator(SEL["username_error"])).to_be_visible()
        expect(page.locator(SEL["password_error"])).to_be_visible()


@pytest.mark.e2e
class TestLoginFlow:
    """登录流程"""

    def test_login_success(self, page: Page):
        """正确凭证登录成功，跳转到仪表盘"""
        _goto_login(page)

        page.fill(SEL["username"], config.test_username)
        page.fill(SEL["password"], config.test_password)
        page.click(SEL["submit"])

        page.wait_for_url("**/dashboard", timeout=10000)
        assert "/dashboard" in page.url

    def test_login_success_stores_token(self, page: Page):
        """登录成功后 localStorage 存入 access_token"""
        _goto_login(page)

        page.fill(SEL["username"], config.test_username)
        page.fill(SEL["password"], config.test_password)
        page.click(SEL["submit"])

        page.wait_for_url("**/dashboard", timeout=10000)

        token = page.evaluate("localStorage.getItem('access_token')")
        assert token is not None and len(token) > 0

    def test_login_failure_wrong_password(self, page: Page):
        """错误密码登录失败，显示错误 toast"""
        _goto_login(page)

        page.fill(SEL["username"], config.test_username)
        page.fill(SEL["password"], "wrongpassword")
        page.click(SEL["submit"])

        # 验证错误 toast 出现
        toast = page.locator(SEL["toast"])
        expect(toast).to_be_visible(timeout=5000)
        expect(toast).to_have_class(re.compile(r"error"))

        # 确认仍在登录页
        assert "/login" in page.url


@pytest.mark.e2e
class TestPasswordToggle:
    """密码显示/隐藏切换"""

    def test_password_hidden_by_default(self, page: Page):
        """密码输入框默认为 password 类型"""
        _goto_login(page)

        pwd_input = page.locator(SEL["password"])
        assert pwd_input.get_attribute("type") == "password"

    def test_click_toggle_shows_password(self, page: Page):
        """点击切换按钮后密码明文显示"""
        _goto_login(page)

        page.fill(SEL["password"], "testpass")
        page.click(SEL["toggle_pwd"])

        pwd_input = page.locator(SEL["password"])
        assert pwd_input.get_attribute("type") == "text"

    def test_double_toggle_restores_hidden(self, page: Page):
        """双击切换恢复隐藏状态"""
        _goto_login(page)

        page.fill(SEL["password"], "testpass")
        page.click(SEL["toggle_pwd"])
        page.click(SEL["toggle_pwd"])

        pwd_input = page.locator(SEL["password"])
        assert pwd_input.get_attribute("type") == "password"


@pytest.mark.e2e
class TestRouteGuard:
    """路由守卫"""

    def test_unauthenticated_redirect_to_login(self, page: Page):
        """未登录访问 dashboard 被重定向到 login"""
        # 先到登录页清除状态
        page.goto(f"{config.web_ui_url}/login")
        page.evaluate("localStorage.clear(); sessionStorage.clear();")

        # 再访问受保护页面
        page.goto(f"{config.web_ui_url}/dashboard")
        page.wait_for_load_state("networkidle")

        assert "/login" in page.url

    def test_redirect_preserves_original_path(self, page: Page):
        """重定向时保留原始路径在 redirect 参数中"""
        page.goto(f"{config.web_ui_url}/login")
        page.evaluate("localStorage.clear(); sessionStorage.clear();")

        page.goto(f"{config.web_ui_url}/portfolio")
        page.wait_for_load_state("networkidle")

        assert "/login" in page.url
        assert "redirect" in page.url


@pytest.mark.e2e
class TestLogout:
    """登出功能"""

    def test_logout_redirects_to_login(self, authenticated_page: Page):
        """登出后跳转到登录页"""
        page = authenticated_page
        # 确保在已认证页面（可能是 dashboard 或其他）
        assert "/login" not in page.url

        # 点击用户菜单
        page.click(SEL["user_menu"])

        # 点击登出
        logout_btn = page.locator(SEL["logout"])
        expect(logout_btn).to_be_visible(timeout=5000)
        logout_btn.click()

        # 验证跳转到登录页
        page.wait_for_url("**/login**", timeout=5000)
        assert "/login" in page.url

    def test_logout_clears_token(self, authenticated_page: Page):
        """登出后 localStorage 的 token 被清除"""
        page = authenticated_page

        page.click(SEL["user_menu"])
        page.locator(SEL["logout"]).click()
        page.wait_for_url("**/login**", timeout=5000)

        token = page.evaluate("localStorage.getItem('access_token')")
        assert token is None
