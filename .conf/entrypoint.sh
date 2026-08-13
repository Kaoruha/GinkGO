#!/bin/sh
set -e

# #6651 根治: ginkgo-logs named volume 首次由历史 root worker 写成 root:root,
# ginkgo(10001)无写权限致 GLOG 初始化 PermissionError(GLOG 在 import 时打开
# /var/log/ginkgo/ginkgo.log,早于任何业务代码,直接 crashloop)。
#
# Dockerfile 内 chown /var/log/ginkgo 对 named volume 无效(volume 挂载覆盖镜像层),
# 故容器以 root 入口在此幂等修正属主,再 gosu 降权到 ginkgo 执行主进程。
# 模式参考官方 postgres/mysql/redis 镜像。down -v 重建 volume 也不怕。
chown -R 10001:10001 /var/log/ginkgo 2>/dev/null || true

exec gosu ginkgo "$@"
