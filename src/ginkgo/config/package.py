# Upstream: 安装脚本和打包工具(setup.py/pip install 读取版本信息)
# Downstream: 无(纯元数据定义模块)
# Role: 配置管理包，提供配置文件读取、环境变量解析、配置验证、分层配置(环境变量→配置文件→默认值)等功能，定义GCONF全局配置实例



# 版本解析逻辑共享自 _version_core（见该文件头注释关于双模导入的约束）。
# 本文件必须能被 CLI 快速路径（main.py: sys.path.insert + import package）作为
# 顶层裸模块导入 —— 故不能写任何 `from ginkgo...`，只能 import 同目录 sibling。
try:
    from _version_core import resolve_version  # CLI 快速路径：顶层裸模块
except ImportError:
    from ._version_core import resolve_version  # 常规/setup_install：包内相对导入

PACKAGENAME = "ginkgo"
VERSION = resolve_version()
AUTHOR = "suny"
EMAIL = "sun159753@gmail.com"
DESC = "Python Backtesting library for trading research"
URL = "url://waf"
