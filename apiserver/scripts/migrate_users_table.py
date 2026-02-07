#!/usr/bin/env python3
"""
迁移 users 表结构
- 添加 username 列 (从 name 复制数据)
- 添加 display_name 列 (从 name 复制数据)
- 添加 email 列
"""

import sys
from pathlib import Path

# 添加项目路径
ginkgo_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(ginkgo_path))

from ginkgo.data.containers import container
from sqlalchemy import text

def migrate_users_table():
    """迁移 users 表结构"""
    print("开始迁移 users 表...")

    user_crud = container.user_crud()

    with user_crud.get_session() as session:
        # 1. 添加 username 列 (从 name 复制数据)
        print("1. 添加 username 列...")
        try:
            # 先添加不唯一的列
            session.execute(text("""
                ALTER TABLE users
                ADD COLUMN username VARCHAR(64) AFTER uuid
            """))
            session.commit()

            # 复制 name 到 username，使用 UUID 处理重复
            session.execute(text("""
                UPDATE users SET username = CONCAT(name, '_', uuid) WHERE username IS NULL OR username = ''
            """))
            session.commit()

            # 设置唯一约束
            session.execute(text("""
                ALTER TABLE users
                ADD UNIQUE KEY idx_username (username)
            """))
            session.commit()
            print("   ✓ username 列添加成功")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("   - username 列已存在，跳过")
                session.rollback()
            else:
                print(f"   ✗ 添加 username 列失败: {e}")
                session.rollback()
                return False

        # 2. 添加 display_name 列 (从 name 复制数据)
        print("2. 添加 display_name 列...")
        try:
            session.execute(text("""
                ALTER TABLE users
                ADD COLUMN display_name VARCHAR(128) AFTER username
            """))
            # 复制 name 到 display_name
            session.execute(text("""
                UPDATE users SET display_name = name WHERE display_name IS NULL
            """))
            session.commit()
            print("   ✓ display_name 列添加成功")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("   - display_name 列已存在，跳过")
                session.rollback()
            else:
                print(f"   ✗ 添加 display_name 列失败: {e}")
                session.rollback()
                return False

        # 3. 添加 email 列
        print("3. 添加 email 列...")
        try:
            session.execute(text("""
                ALTER TABLE users
                ADD COLUMN email VARCHAR(128) DEFAULT '' AFTER display_name
            """))
            session.commit()
            print("   ✓ email 列添加成功")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("   - email 列已存在，跳过")
                session.rollback()
            else:
                print(f"   ✗ 添加 email 列失败: {e}")
                session.rollback()
                return False

        # 4. 验证表结构
        print("\n验证迁移后的表结构:")
        result = session.execute(text("DESCRIBE users"))
        for row in result.fetchall():
            print(f"  {row[0]}: {row[1]}")

    print("\n✓ users 表迁移完成!")
    return True

def create_admin_user():
    """创建默认管理员用户"""
    print("\n创建默认管理员用户...")

    from ginkgo.data.models import MUser, MUserCredential
    from ginkgo.enums import SOURCE_TYPES, USER_TYPES
    import bcrypt

    user_crud = container.user_crud()
    credential_crud = container.user_credential_crud()

    # 检查是否已存在 admin 用户
    users = user_crud.find(filters={"username": "admin"}, as_dataframe=False)

    if users:
        print("  - admin 用户已存在，跳过创建")
        return True

    # 创建 admin 用户
    print("  - 创建 admin 用户...")

    # 1. 创建 MUser (使用 kwargs 设置 name 字段以兼容旧表结构)
    user = MUser(
        username="admin",
        display_name="Administrator",
        email="admin@ginkgo.local",
        description="系统管理员账户",
        user_type=USER_TYPES.PERSON,
        is_active=True,
        source=SOURCE_TYPES.OTHER,
        name="admin"  # 兼容旧的 name 列 (NOT NULL)
    )

    created_user = user_crud.add(user)

    if not created_user:
        print("  ✗ 创建 admin 用户失败")
        return False

    # 2. 创建 MUserCredential
    password_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    credential = MUserCredential(
        user_id=created_user.uuid,
        password_hash=password_hash,
        is_active=True,
        is_admin=True
    )

    created_credential = credential_crud.add(credential)

    if not created_credential:
        print("  ✗ 创建 admin 凭证失败")
        # 删除已创建的 user
        user_crud.delete(filters={"uuid": created_user.uuid})
        return False

    print(f"  ✓ admin 用户创建成功 (UUID: {created_user.uuid[:8]}...)")
    print("  - 用户名: admin")
    print("  - 密码: admin123")
    print("  - 权限: 管理员")

    return True

if __name__ == "__main__":
    # 1. 迁移表结构
    if not migrate_users_table():
        print("\n迁移失败，退出")
        sys.exit(1)

    # 2. 创建 admin 用户
    if not create_admin_user():
        print("\n创建用户失败，退出")
        sys.exit(1)

    print("\n✓ 所有迁移完成!")
    print("现在可以使用 admin/admin123 登录了")
