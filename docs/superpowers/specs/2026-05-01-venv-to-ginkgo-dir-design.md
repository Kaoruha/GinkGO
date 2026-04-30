# 虚拟环境迁移至 ~/.ginkgo/.venv 设计

## 背景

当前 `install.py` 要求用户手动创建并激活虚拟环境后才能运行安装。venv 默认在项目根目录 `.venv`，与源码混在一起。目标是让安装流程自动在 `~/.ginkgo/.venv` 创建和管理虚拟环境，简化用户体验。

## 目标

- `install.py` 自动在 `~/.ginkgo/.venv` 创建 venv（无需手动前置步骤）
- 统一使用 uv，移除 pip 分支逻辑
- 多平台兼容（Linux / macOS / Windows）

## 改动范围

仅修改 `install.py`。

## env_check() 新流程

```
env_check():
├── uv 命令不存在 → 打印安装提示 → sys.exit()
├── 检测到活跃 venv
│   ├── 路径匹配 ~/.ginkgo/.venv → ✅ 返回路径
│   └── 路径不匹配 → ⚠️ 警告非标准路径，继续但不自动迁移
└── 无活跃 venv
    ├── ~/.ginkgo/.venv 已存在 → subprocess.run(["uv", "sync"]) 激活
    └── ~/.ginkgo/.venv 不存在 → uv venv ~/.ginkgo/.venv → uv sync
```

## 详细改动

### 1. env_check() 重写

```python
def get_venv_path():
    ginkgo_dir = os.environ.get("GINKGO_DIR", os.path.expanduser("~/.ginkgo"))
    return os.path.join(ginkgo_dir, ".venv")

def check_uv_available():
    try:
        subprocess.run(["uv", "--version"], check=True, capture_output=True)
        return True
    except FileNotFoundError:
        return False

def env_check():
    if not check_uv_available():
        print("uv is required. Install: curl -LsSf https://astral.sh/uv/install.sh | sh")
        sys.exit(1)

    venv_path = get_venv_path()
    active_env = os.environ.get("VIRTUAL_ENV") or os.environ.get("UV_ACTIVE_ENV")

    if active_env:
        if os.path.normpath(active_env) == os.path.normpath(venv_path):
            print(f"[OK] UV env: {venv_path}")
            return venv_path
        else:
            print(f"[WARN] Active env {active_env} != expected {venv_path}")
            return active_env

    # 无活跃 venv，确保 ~/.ginkgo/.venv 存在
    if not os.path.exists(os.path.join(venv_path, "pyvenv.cfg")):
        print(f"Creating venv at {venv_path}...")
        subprocess.run(["uv", "venv", venv_path], check=True)

    # 激活 venv（修改当前进程的 sys.path 和 os.environ）
    activate_venv(venv_path)
    return venv_path

def activate_venv(venv_path):
    """在当前进程中激活 venv（等价于 source activate）"""
    os.environ["VIRTUAL_ENV"] = venv_path
    os.environ["UV_ACTIVE_ENV"] = venv_path
    bin_dir = os.path.join(venv_path, "bin")
    os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
    # 更新 sys.path 让后续 import 使用新 venv 的 site-packages
    site_packages = os.path.join(venv_path, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages")
    if site_packages not in sys.path:
        sys.path.insert(0, site_packages)
```

### 2. install_ginkgo() 简化

移除 pip 分支，直接使用 uv：

```python
def install_ginkgo():
    venv_path = get_venv_path()
    env = os.environ.copy()
    env["UV_PROJECT_ENVIRONMENT"] = venv_path
    subprocess.run(["uv", "sync"], env=env, check=True)
    print("Ginkgo package installed successfully.")
```

### 3. install_dependencies() 简化

移除 pip 分支，统一用 uv sync（已在 install_ginkgo 中完成）。

### 4. is_uv_environment() / get_package_manager() 简化

直接返回 `"uv"`，不再需要复杂的检测逻辑。

### 5. create_entrypoint() 不变

已经通过 `which python` 获取路径，venv 迁移后自动正确。

## 迁移步骤（用户视角）

```bash
# 拉取更新
git pull

# 直接运行（无需预先激活 venv）
python install.py

# install.py 自动：
#   1. 检查 uv
#   2. 创建 ~/.ginkgo/.venv（如不存在）
#   3. uv sync 安装依赖
#   4. 更新 /usr/local/bin/ginkgo 入口
#
# 旧的项目根 .venv 可手动删除：
rm -rf .venv
```

## 不受影响的部分

- `pyproject.toml` — 无改动
- `config.py` / `GCONF` — 无改动
- `docker-compose.yml` — 容器不依赖本地 venv
- `main.py` — 入口脚本由 `create_entrypoint()` 生成，自动正确
- `uv.lock` — 锁文件不变

## 注意事项

- IDE 需要手动选择 `~/.ginkgo/.venv/bin/python` 作为 interpreter
- `uv run`/`uv add` 在项目外运行时需设 `UV_PROJECT_ENVIRONMENT`（可在 `install.py` 末尾提示用户）
- Windows 路径分隔符已通过 `os.path.join` 处理
