# 虚拟环境迁移至 ~/.ginkgo/.venv 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 install.py 自动在 ~/.ginkgo/.venv 创建和管理虚拟环境，无需手动前置步骤。

**Architecture:** 仅修改 install.py，强制使用 uv，env_check() 四分支逻辑自动检测/创建/激活 venv。

**Tech Stack:** Python 3.12, uv

---

### Task 1: 添加辅助函数

**Files:**
- Modify: `install.py:59-93` (在 `env_check` 前插入新函数)

- [ ] **Step 1: 在 `docker_check()` 和 `env_check()` 之间插入三个新函数**

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


def activate_venv(venv_path):
    """在当前进程中激活 venv（等价于 source activate）"""
    os.environ["VIRTUAL_ENV"] = venv_path
    os.environ["UV_ACTIVE_ENV"] = venv_path
    bin_dir = os.path.join(venv_path, "bin")
    os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
    # Windows 兼容
    if os.name == "nt":
        bin_dir = os.path.join(venv_path, "Scripts")
        os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
    # 更新 sys.path 让后续 import 使用新 venv 的 site-packages
    for p in Path(venv_path).glob("lib/python*/site-packages"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
```

- [ ] **Step 2: 验证语法**

Run: `python -c "import ast; ast.parse(open('install.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add install.py
git commit -m "feat(install): add venv helper functions for ~/.ginkgo/.venv"
```

---

### Task 2: 重写 env_check()

**Files:**
- Modify: `install.py:59-93` (替换整个 `env_check` 函数)

- [ ] **Step 1: 替换 env_check() 为四分支逻辑**

```python
def env_check():
    venv_path = get_venv_path()

    # 分支 1: uv 不存在
    if not check_uv_available():
        print(f"[{red('ERROR')}] uv is required but not found.")
        print(f"  Install: {green('curl -LsSf https://astral.sh/uv/install.sh | sh')}")
        return None

    active_env = os.environ.get("VIRTUAL_ENV") or os.environ.get("UV_ACTIVE_ENV")

    # 分支 2: 已有活跃 venv，检查路径
    if active_env:
        if os.path.normpath(active_env) == os.path.normpath(venv_path):
            print(f"[{green('ACTIVE')}] UV env: {lightblue(venv_path)}")
            return venv_path
        else:
            print(f"[{lightyellow('WARN')}] Active env {lightblue(active_env)} != expected {lightblue(venv_path)}")
            return active_env

    # 分支 3 & 4: 无活跃 venv
    if not os.path.exists(os.path.join(venv_path, "pyvenv.cfg")):
        # 分支 4: 不存在，创建
        print(f"[{green('CREATE')}] Creating venv at {lightblue(venv_path)}...")
        subprocess.run(["uv", "venv", venv_path], check=True)
    else:
        # 分支 3: 已存在，复用
        print(f"[{green('REUSE')}] Found existing venv at {lightblue(venv_path)}")

    activate_venv(venv_path)
    return venv_path
```

- [ ] **Step 2: 验证语法**

Run: `python -c "import ast; ast.parse(open('install.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add install.py
git commit -m "feat(install): rewrite env_check with auto-create ~/.ginkgo/.venv"
```

---

### Task 3: 简化 install 相关函数

**Files:**
- Modify: `install.py:157-268` (替换 `is_uv_environment`, `get_package_manager`, `install_ginkgo`, `install_dependencies`)

- [ ] **Step 1: 简化 is_uv_environment() 和 get_package_manager()**

替换 `install.py:157-195` 的两个函数为：

```python
def is_uv_environment():
    return check_uv_available()


def get_package_manager():
    return "uv"
```

- [ ] **Step 2: 简化 install_ginkgo()**

替换 `install.py:198-227` 的 `install_ginkgo` 函数为：

```python
def install_ginkgo():
    venv_path = get_venv_path()
    env = os.environ.copy()
    env["UV_PROJECT_ENVIRONMENT"] = venv_path
    try:
        print(f"Installing Ginkgo package in development mode using uv...")
        subprocess.run(["uv", "sync"], env=env, check=True)
        print("Ginkgo package installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to install Ginkgo package: {e}")
        print("Trying uv lock + sync...")
        subprocess.run(["uv", "lock"], env=env)
        subprocess.run(["uv", "sync"], env=env)
```

- [ ] **Step 3: 简化 install_dependencies()**

替换 `install.py:229-268` 的 `install_dependencies` 函数为：

```python
def install_dependencies(path_pip):
    venv_path = get_venv_path()
    env = os.environ.copy()
    env["UV_PROJECT_ENVIRONMENT"] = venv_path
    print("Installing dependencies using UV...")
    try:
        subprocess.run(["uv", "sync"], env=env, check=True)
        print("Dependencies installation success via UV.")
    except Exception as e:
        print(f"Failed to install dependencies via UV: {e}")
        sys.exit(1)
```

- [ ] **Step 4: 验证语法**

Run: `python -c "import ast; ast.parse(open('install.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add install.py
git commit -m "refactor(install): simplify to uv-only, remove pip fallback"
```

---

### Task 4: 更新 main() 中的 venv 路径引用

**Files:**
- Modify: `install.py:616` (`path_log` 使用硬编码路径)
- Modify: `install.py:631-633` (`env is None` 检查)

- [ ] **Step 1: 更新 path_log 使用 GINKGO_DIR**

将 `install.py:616` 的：
```python
path_log = os.path.expanduser("~") + "/.ginkgo/logs"
```
改为：
```python
ginkgo_dir = os.environ.get("GINKGO_DIR", os.path.expanduser("~/.ginkgo"))
path_log = os.path.join(ginkgo_dir, "logs")
```

- [ ] **Step 2: env_check 不再返回 None 时 bye() 不会触发，但保留防御性检查**

`install.py:631-633` 已有的逻辑无需改动（`env is None` 时 bye 退出，新 env_check 只在 uv 缺失时返回 None）。

- [ ] **Step 3: 验证语法**

Run: `python -c "import ast; ast.parse(open('install.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add install.py
git commit -m "refactor(install): use GINKGO_DIR for log path"
```

---

### Task 5: 端到端验证

**Files:** 无文件改动

- [ ] **Step 1: 记录当前 ginkgo 入口脚本作为对比基准**

Run: `cat /usr/local/bin/ginkgo`

- [ ] **Step 2: 运行 install.py**

Run: `cd /home/kaoru/Ginkgo && python install.py -y`

预期行为：
1. `[CREATE]` 或 `[REUSE]` 提示 `~/.ginkgo/.venv`
2. `uv sync` 安装依赖
3. `create_entrypoint` 更新 `/usr/local/bin/ginkgo`

- [ ] **Step 3: 验证 ginkgo 命令**

Run: `ginkgo version`
Expected: `✨ ginkgo 0.8.1`

- [ ] **Step 4: 验证入口脚本指向新 venv**

Run: `cat /usr/local/bin/ginkgo | grep python`
Expected: `/home/kaoru/.ginkgo/.venv/bin/python`（不再是 `Ginkgo/.venv/bin/python`）

- [ ] **Step 5: 验证 ginkgo serve 正常**

Run: `ginkgo status`
Expected: 正常输出（不报 python 路径错误）

- [ ] **Step 6: 旧 venv 清理提示**

如果验证通过，手动清理旧 venv：
```bash
rm -rf /home/kaoru/Ginkgo/.venv
```

- [ ] **Step 7: 最终 Commit**

```bash
git add install.py
git commit -m "feat(install): auto-create venv at ~/.ginkgo/.venv, uv-only"
```
