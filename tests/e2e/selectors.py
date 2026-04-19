"""
CSS 选择器常量

集中管理 E2E 测试中使用的 CSS 选择器。
优先使用 data-testid，其次使用语义化 CSS 类名。
"""

# 表格
TABLE = "table.data-table"
TABLE_ROW = "table.data-table tbody tr"
TABLE_CELL = "table.data-table td"

# 表单元素
MODAL = ".modal, .modal-content"
MODAL_CONFIRM = ".modal-overlay"
SELECT = ".form-select"
SELECT_DROPDOWN = "select option"
SELECT_ITEM = "select option"
INPUT = ".form-input"
INPUT_NUMBER = "input[type='number'].form-input"
DATE_PICKER = "input[type='date']"

# 按钮
BTN = ".btn, .btn-primary, .btn-secondary"
BTN_PRIMARY = ".btn-primary"
BTN_DANGER = ".btn-danger"
BTN_LINK = ".btn-link, .link-button"

# 导航
MENU = ".menu"
MENU_ITEM = ".menu-item"
TABS = ""  # 无 tabs 组件，使用路由导航
TAB_PANE = ""

# 表单
FORM_ITEM = ".form-group"

# 反馈
MESSAGE = ".toast, .ant-message"
NOTIFICATION = ".notification"
SPIN = ".spinner"
DRAWER = ".drawer"
POPUP = ".popover"

# 标签和徽章
TAG = ".tag"
BADGE = ".badge"
SWITCH = ".switch-input"
CHECKBOX = "input[type='checkbox']"
RADIO = "input[type='radio']"
DROPDOWN = ".dropdown-menu"
BREADCRUMB = ".breadcrumb"

# 卡片和统计
PAGINATION = ".pagination"
CARD = ".card"
COLLAPSE = ".collapse"
PROGRESS = ".progress-fill"
RESULT = ".result"
EMPTY = ".empty-state"
STAT_CARD = ".stat-card"

# 通用
CLOSE_BTN = ".modal-close, [aria-label='Close']"
SUBMIT_BTN = "button[type='submit'], .btn-primary"
CANCEL_BTN = ".btn-secondary"
