-- 节点图配置表
CREATE TABLE IF NOT EXISTS node_graphs (
    uuid VARCHAR(64) PRIMARY KEY COMMENT '唯一标识符',
    name VARCHAR(255) NOT NULL COMMENT '配置名称',
    description TEXT COMMENT '配置描述',
    graph_data JSON NOT NULL COMMENT '节点图数据',
    user_uuid VARCHAR(64) NOT NULL COMMENT '所有者用户ID',
    version INT DEFAULT 1 COMMENT '版本号',
    parent_uuid VARCHAR(64) COMMENT '父版本UUID',
    is_template BOOLEAN DEFAULT FALSE COMMENT '是否为模板',
    is_public BOOLEAN DEFAULT FALSE COMMENT '是否公开共享',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_user_uuid (user_uuid),
    INDEX idx_is_template (is_template),
    INDEX idx_parent_uuid (parent_uuid),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='节点图配置表';

-- 节点图模板表
CREATE TABLE IF NOT EXISTS node_graph_templates (
    uuid VARCHAR(64) PRIMARY KEY COMMENT '唯一标识符',
    name VARCHAR(255) NOT NULL COMMENT '模板名称',
    description TEXT COMMENT '模板描述',
    category VARCHAR(100) COMMENT '分类',
    graph_data JSON NOT NULL COMMENT '预配置的节点图数据',
    is_system BOOLEAN DEFAULT FALSE COMMENT '是否系统模板',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_category (category),
    INDEX idx_is_system (is_system)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='节点图模板表';
