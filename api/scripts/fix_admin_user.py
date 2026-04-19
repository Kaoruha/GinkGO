#!/usr/bin/env python3
"""
修复 admin 用户并创建凭证
"""

import sys
import bcrypt
from pathlib import Path
import uuid
from datetime import datetime

# 添加项目路径
ginkgo_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(ginkgo_path))

from ginkgo.data.containers import container
from sqlalchemy import text

def fix_admin_user():
    """修复 admin 用户"""
    print("修复 admin 用户...")

    user_crud = container.user_crud()

    with user_crud.get_session() as session:
        # 查找名为 admin 的用户
        result = session.execute(text("SELECT uuid FROM users WHERE name = :name"), {"name": "admin"})
        row = result.fetchone()

        if row:
            # 找到了名为 admin 的用户，更新 username
            user_uuid = row[0]
            print(f"  - 找到 admin 用户 (UUID: {user_uuid[:8]}...)")
            session.execute(text("""
                UPDATE users
                SET username = 'admin', display_name = 'Administrator', email = 'admin@ginkgo.local'
                WHERE uuid = :uuid
            """), {"uuid": user_uuid})
            session.commit()
            print(f"  ✓ 用户信息已更新")
            return user_uuid
        else:
            # 创建新的 admin 用户
            print("  - 创建新的 admin 用户...")
            user_uuid = uuid.uuid4().hex
            now = datetime.now()

            session.execute(text("""
                INSERT INTO users (
                    uuid, name, username, display_name, email, description,
                    user_type, is_active, source, is_del, create_at, update_at
                ) VALUES (
                    :uuid, :name, :username, :display_name, :email, :description,
                    :user_type, :is_active, :source, :is_del, :create_at, :update_at
                )
            """), {
                "uuid": user_uuid,
                "name": "admin",
                "username": "admin",
                "display_name": "Administrator",
                "email": "admin@ginkgo.local",
                "description": "系统管理员账户",
                "user_type": 1,  # PERSON
                "is_active": True,
                "source": 0,  # OTHER
                "create_at": now,
                "update_at": now
            })
            session.commit()
            print(f"  ✓ admin 用户创建成功 (UUID: {user_uuid[:8]}...)")
            return user_uuid

def create_admin_credential(user_uuid: str):
    """创建 admin 凭证"""
    print("\n创建 admin 凭证...")

    user_crud = container.user_crud()

    with user_crud.get_session() as session:
        # 检查是否已存在凭证
        result = session.execute(text("SELECT uuid FROM user_credentials WHERE user_id = :user_id"), {"user_id": user_uuid})
        row = result.fetchone()

        password_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        now = datetime.now()

        if row:
            # 更新现有凭证
            print("  - 更新现有凭证...")
            session.execute(text("""
                UPDATE user_credentials
                SET password_hash = :password_hash, is_admin = 1, is_active = 1, update_at = :update_at
                WHERE user_id = :user_id
            """), {
                "password_hash": password_hash,
                "user_id": user_uuid,
                "update_at": now
            })
        else:
            # 创建新凭证
            print("  - 创建新凭证...")
            credential_uuid = uuid.uuid4().hex
            session.execute(text("""
                INSERT INTO user_credentials (
                    uuid, user_id, password_hash, is_admin, is_active,
                    create_at, update_at
                ) VALUES (
                    :uuid, :user_id, :password_hash, :is_admin, :is_active,
                    :create_at, :update_at
                )
            """), {
                "uuid": credential_uuid,
                "user_id": user_uuid,
                "password_hash": password_hash,
                "is_admin": True,
                "is_active": True,
                "create_at": now,
                "update_at": now
            })

        session.commit()
        print(f"  ✓ admin 凭证设置成功")

if __name__ == "__main__":
    # 1. 修复 admin 用户
    user_uuid = fix_admin_user()
    if not user_uuid:
        print("\n✗ 修复用户失败")
        sys.exit(1)

    # 2. 创建/更新 admin 凭证
    create_admin_credential(user_uuid)

    print("\n✓ 所有设置完成!")
    print("  - 用户名: admin")
    print("  - 密码: admin123")
    print("  - 权限: 管理员")
    print("\n现在可以使用 admin/admin123 登录了")
