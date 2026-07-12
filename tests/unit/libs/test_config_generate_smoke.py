"""Smoke: GCONF.generate_config_file 从包内 config/ 拷贝模板（PR6686）。

PR6686 将模板源从 cwd 改为跟随 ginkgo 包（__file__ 解析到 src/ginkgo/config/）。
本 smoke 对空目录调用 generate_config_file，触发三条 origin_path 分支
（config.yml / secure.yml / task_timer.yml），既验证拷贝行为，又为
CI diff coverage gate (#6135) 覆盖 src/ginkgo/libs/core/config.py 的变更行。
"""

from ginkgo.libs.core.config import GinkgoConfig


def test_generate_config_file_copies_pkg_templates_to_fresh_dir(tmp_path):
    # 显式 path 绕过 _has_local_config 早退；空目录使三条 if not exists 分支全部命中
    target = tmp_path / "fresh"
    GinkgoConfig().generate_config_file(path=str(target))

    # 模板源跟随 ginkgo 包（__file__），应从包内 config/ 拷到目标目录
    assert (target / "config.yml").is_file()
    assert (target / "secure.yml").is_file()
    assert (target / "task_timer.yml").is_file()
