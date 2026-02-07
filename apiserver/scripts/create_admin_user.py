#!/usr/bin/env python3
"""
直接使用 SQL 创建默认管理员用户
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

def create_admin_user():
    """使用 SQL 创建 admin 用户"""
    print("创建默认管理员用户...")

    user_crud = container.user_crud()

    with user_crud.get_session() as session:
        # 检查是否已存在 admin 用户
        result = session.execute(text("SELECT uuid FROM users WHERE username = :username"), {"username": "admin"})
        if result.fetchone():
            print("  - admin 用户已存在，跳过创建")
            return True

        # 生成 UUID 和密码哈希
        user_uuid = uuid.uuid4().hex
        credential_uuid = uuid.uuid4().hex
        password_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        now = datetime.now()

        # 1. 创建 users 记录
        print("  - 创建 users 记录...")
        session.execute(text("""
            INSERT INTO users (
                uuid, name, username, display_name, email, description,
                user_type, is_active, source, meta, `desc`, create_at, update_at, is_del
            ) VALUES (
                :uuid, :name, :username, :display_name, :email, :description,
                :user_type, :is_active, :source, :meta, :desc, :create_at, :update_at, :is_del
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
            "meta": "{}",
            "desc": "System administrator",
            "create_at": now,
            "update_at": now,
            "is_del": False
        })

        # 2. 创建 user_credentials 记录
        print("  - 创建 user_credentials 记录...")
        session.execute(text("""
            INSERT INTO user_credentials (
                uuid, user_id, password_hash, is_admin, is_active,
                last_login_ip, create_at, update_at, is_del
            ) VALUES (
                :uuid, :user_id, :password_hash, :is_admin, :is_active,
                :last_login_ip, :create_at, :update_at, :is_del
            )
        """), {
            "uuid": credential_uuid,
            "user_id": user_uuid,
            "password_hash": password_hash,
            "is_admin": True,
            "is_active": True,
            "last_login_ip": "",
            "create_at": now,
            "update_at": now,
            "is_del": False
        })

        session.commit()

        print(f"  ✓ admin 用户创建成功 (UUID: {user_uuid[:8]}...)")
        print("  - 用户名: admin")
        print("  - 密码: admin123")
        print("  - 权限: 管理员")

    return True

if __name__ == "__main__":
    if create_admin_user():
        print("\n✓ 用户创建完成!")
        print("现在可以使用 admin/admin123 登录了")
    else:
        print("\n✗ 创建用户失败")
        sys.exit(1)
