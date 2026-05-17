import sys
from pathlib import Path

# Issue #3849: 统一管理 api/ 目录路径，避免各测试文件重复 sys.path.insert
api_dir = Path(__file__).parent.parent.parent / "api"
api_str = str(api_dir)
if api_str not in sys.path:
    sys.path.insert(0, api_str)
