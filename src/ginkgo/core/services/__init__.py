# Upstream: API Server (ginkgo serve api), CLI (ginkgo status)
# Downstream: system_service (系统状态/基础设施健康检查)
# Role: 核心服务层入口，导出系统状态与健康检查服务（MySQL/Redis/Kafka/ClickHouse）
