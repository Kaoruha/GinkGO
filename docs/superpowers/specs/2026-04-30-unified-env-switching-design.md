# 统一环境切换机制设计

## 问题

当前环境切换机制不一致：
- 本地服务通过 `ginkgo system config set --debug on/off` 切换（GCONF 端口 hack）
- Docker 服务在 compose 中硬编码数据库地址（各自写死）
- Vector 硬编码 `clickhouse-master`

导致：
1. Docker 服务无法跟随 debug 模式切换环境
2. Vector 始终写 clickhouse-master，与 debug 模式下的应用查询（clickhouse-test）不一致
3. compose 中硬编码地址，新增服务时需要手动指定正确的数据库

## 目标

`ginkgo system config set --debug on/off` 一条命令控制所有服务（本地 + Docker + Vector）的数据库指向。

## 设计

### 1. compose 固定项目名

在 `docker-compose.yml` 顶层添加 `name: ginkgo`，替代当前的 `x-project-name`（Docker 不读后者）。

效果：无论从哪个目录启动 compose，项目名、网络名、容器名始终一致（`ginkgo_default` 网络）。

### 2. compose 变量化

将所有硬编码的数据库地址改为引用 `.env` 变量：

```yaml
services:
  notify-worker:
    GINKGO_CLICKHOUSE_HOST: ${CLICKHOUSE_HOST}
    GINKGO_MYSQL_HOST: ${MYSQL_HOST}
    GINKGO_MONGODB_HOST: ${MONGODB_HOST}

  vector:
    CLICKHOUSE_HOST: ${CLICKHOUSE_HOST}
    # vector.toml endpoint 引用 ${CLICKHOUSE_HOST}
```

每个变量提供默认值指向 test 环境（安全默认）：

```yaml
GINKGO_CLICKHOUSE_HOST: ${CLICKHOUSE_HOST:-clickhouse-test}
```

### 3. .env 文件

在 compose 文件同目录下维护 `.env` 文件，定义当前环境的数据库地址：

```env
# .env - 由 CLI 自动管理，不要手动编辑
CLICKHOUSE_HOST=clickhouse-test
MYSQL_HOST=mysql-test
MONGODB_HOST=mongo-master
```

初始创建时根据当前 debug 设置生成对应值。

### 4. Vector endpoint 变量化

`vector.toml` 的 ClickHouse endpoint 改为环境变量引用：

```toml
[sinks.clickhouse_backtest]
endpoint = "http://${CLICKHOUSE_HOST}:8123"
```

### 5. CLI 增强

`ginkgo system config set --debug on/off` 增加以下行为：

1. 更新 `config.yml`（已有）
2. 读取 `config.yml` 中的 `compose_file` 路径
3. 更新 compose 文件同目录下的 `.env` 文件：
   - debug=on → `CLICKHOUSE_HOST=clickhouse-test`, `MYSQL_HOST=mysql-test`
   - debug=off → `CLICKHOUSE_HOST=clickhouse-master`, `MYSQL_HOST=mysql-master`
4. 执行 `docker compose -f <path> up -d`（仅重建有变化的容器）

### 6. compose 文件移到项目根目录

将 `.conf/docker-compose.yml` 移到项目根目录 `docker-compose.yml`，符合 Docker 标准约定。

好处：
- CLI 定位简单：`working_directory + "/docker-compose.yml"`
- 无需 `-f` 参数，直接 `docker compose up -d`
- `.env` 文件也在项目根目录，compose 自动读取

需同步更新 compose 内的相对路径：

**`./` 开头（同目录 → 加 `.conf/` 前缀）：**

| 原路径 | 新路径 |
|---|---|
| `./redis.conf` | `.conf/redis.conf` |
| `./clickhouse_users.xml` | `.conf/clickhouse_users.xml` |
| `./clickhouse_log_config.xml` | `.conf/clickhouse_log_config.xml` |
| `./mongo_entrypoint` | `.conf/mongo_entrypoint` |
| `./mysql_entrypoint` | `.conf/mysql_entrypoint` |

**`../` 开头（上级目录 → 去掉 `../`）：**

| 原路径 | 新路径 |
|---|---|
| `../deploy/vector/vector.toml` | `.conf/vector.toml` |
| `../.conf/grafana-provisioning` | `.conf/grafana-provisioning` |
| `../.db/xxx` | `.db/xxx` |
| `../.logs/xxx` | `.logs/xxx` |

**绝对路径不变**：`/home/kaoru/.ginkgo/logs`、`${HOME}/.ginkgo/task_timer.yml` 等。

新用户安装时 `working_directory` 自动设置；无 Docker 环境时 `docker compose up -d` 静默失败，不影响其他功能。

### 7. debug 模式与数据库映射

| debug | ClickHouse | MySQL | MongoDB |
|---|---|---|---|
| on | clickhouse-test | mysql-test | mongo-master |
| off | clickhouse-master | mysql-master | mongo-master |

MongoDB 只有一个实例，不需要切换。Redis 和 Kafka 同理。

## 不改的东西

- GCONF 的 debug 模式端口 hack（本地服务继续使用）
- 本地服务的切换逻辑不变
- Docker 容器内部逻辑不变
- 不新增基础设施组件

## 顺手修复

### 8. .env 合并

`.conf/.env` 已存在（含密码 + 服务主机变量）。compose 移到根目录后，将 `.conf/.env` 移到项目根目录，compose 自动读取。同时将 `.conf/.env.example` 移到根目录，并补齐缺失的变量（GINKGO_* 主机、GINKGO_LOG_PATH、Grafana 等）。

### 9. config_cli.py 死代码清理

`config_cli.py:292` 引用不存在的 `docker-compose.worker.yml`，清理该段代码。

### 10. nginx.conf 硬编码 IP

`nginx.conf` 中 `192.168.50.10:8000` 硬编码两处（`/api` 和 `/stream`），改为引用环境变量 `${API_HOST}:${API_PORT}`。

## 实现范围

1. `docker-compose.yml`：从 `.conf/` 移到项目根目录，添加 `name: ginkgo`，变量化数据库地址，更新所有相对路径
2. `.env` + `.env.example`：从 `.conf/` 移到项目根目录，补齐变量
3. `deploy/vector/vector.toml`：移到 `.conf/vector.toml`，endpoint 变量化，删除空的 `deploy/` 目录
4. `install.py:619`：更新 compose 文件路径引用
5. `src/ginkgo/client/config_cli.py`：更新路径引用 + 清理死代码
6. `src/ginkgo/libs/core/config.py`：新增 compose 文件路径推导（基于 working_directory）
7. `src/ginkgo/client/system_cli.py`：CLI 增强自动更新 .env + docker compose up
8. `.conf/nginx.conf`：硬编码 IP 改为环境变量
