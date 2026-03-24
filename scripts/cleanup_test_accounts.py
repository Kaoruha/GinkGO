#!/usr/bin/env python3
"""
清理测试账号脚本

删除测试用户创建的账号，避免数据库污染
"""

import sys
sys.path.insert(0, '/home/kaoru/Ginkgo')

from ginkgo.data.containers import container
from ginkgo.libs import GLOG

def cleanup_test_accounts():
    """清理测试账号"""
    crud = container.live_account_crud()

    # 查找测试用户的账号
    test_users = [
        'test-user-123',
        'integration-test-user',
        'test_user_001',
        'test-user-unique'
    ]

    total_deleted = 0

    for user_id in test_users:
        # 查找该用户的所有账号
        accounts = crud.find(filters={'user_id': user_id}, page=0, page_size=1000)

        if accounts:
            GLOG.INFO(f"用户 {user_id} 有 {len(accounts)} 个账号")

            for account in accounts:
                # 软删除
                try:
                    crud.remove({'uuid': account.uuid})
                    total_deleted += 1
                    GLOG.DEBUG(f"  已删除: {account.uuid} ({account.name})")
                except Exception as e:
                    GLOG.ERROR(f"  删除失败 {account.uuid}: {e}")

    GLOG.INFO(f"总计删除 {total_deleted} 个测试账号")
    return total_deleted

def show_statistics():
    """显示统计信息"""
    crud = container.live_account_crud()

    # 统计所有账号
    all_accounts = crud.find(filters={}, page=0, page_size=1000)

    from collections import Counter
    user_counts = Counter(acc.user_id for acc in all_accounts)
    env_counts = Counter(acc.environment for acc in all_accounts)

    print("\n=== 当前账号统计 ===")
    print(f"总账号数: {len(all_accounts)}")
    print(f"\n按用户分布:")
    for user_id, count in user_counts.most_common():
        print(f"  {user_id}: {count}")
    print(f"\n按环境分布:")
    for env, count in env_counts.most_common():
        print(f"  {env}: {count}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="清理测试账号")
    parser.add_argument("--dry-run", action="store_true", help="只显示统计，不删除")
    args = parser.parse_args()

    show_statistics()

    if args.dry_run:
        print("\n[模式] 只显示统计，不删除账号")
    else:
        print("\n[模式] 将删除所有测试账号")
        confirm = input("确认删除? (yes/NO): ")

        if confirm.lower() == 'yes':
            cleanup_test_accounts()
            print("\n清理完成！")
        else:
            print("已取消")
