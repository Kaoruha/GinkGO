// MongoDB Initialization Script for Ginkgo
// 创建数据库和集合，初始化用户权限
//
// 数据库职责划分:
// - MySQL: 用户管理 (users, user_contacts, user_groups, user_group_mapping)
// - MongoDB: 文档存储 (ginkgo 数据库，集合隔离不同功能)

// 切换到 admin 数据库创建用户
db = db.getSibling('admin');

// 创建 ginkgo 应用用户（如果不存在）
try {
    db.createUser({
        user: 'ginkgoadm',
        pwd: 'ginkgomongo',
        roles: [
            { role: 'readWrite', db: 'ginkgo' }
        ]
    });
    print('User ginkgoadm created successfully');
} catch (e) {
    if (e.code === 51003) {
        print('User ginkgoadm already exists');
    } else {
        print('Error creating user: ' + e);
    }
}

// 切换到 ginkgo 数据库
db = db.getSibling('ginkgo');

// 通知记录集合（带 TTL 索引）
db.createCollection('notification_records');
db.notification_records.createIndex({ message_id: 1 });
db.notification_records.createIndex({ status: 1 });
db.notification_records.createIndex({ create_at: 1 }, { name: 'ttl_index', expireAfterSeconds: 604800 }); // 7天 = 7*24*3600 = 604800秒

print('MongoDB initialization completed successfully');
print('Database: ginkgo');
print('Collections created:');
print('  - notification_records with 7-day TTL');
print('Note: User data (users, user_contacts, user_groups) is stored in MySQL');
