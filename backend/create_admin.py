#!/usr/bin/env python3
"""
创建管理员用户的脚本
"""
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db, User, Role, Permission

def create_admin_user():
    """创建或更新管理员用户"""
    app = create_app('development')
    
    with app.app_context():
        # 首先确保角色存在
        print("初始化角色...")
        Role.insert_roles()
        
        # 获取管理员角色
        admin_role = Role.query.filter_by(name='Administrator').first()
        if not admin_role:
            print("错误：管理员角色不存在")
            return False
        
        # 检查是否已有admin用户
        admin_user = User.query.filter_by(username='admin').first()
        
        if admin_user:
            print(f"找到现有admin用户: {admin_user.email}")
            # 更新为管理员角色
            admin_user.role = admin_role
            print("已将admin用户设置为管理员")
        else:
            # 创建新的admin用户
            print("创建新的admin用户...")
            admin_user = User(
                email='admin@example.com',
                username='admin',
                name='系统管理员',
                password='admin123',  # 默认密码，建议首次登录后修改
                role=admin_role
            )
            db.session.add(admin_user)
            print("已创建admin用户")
        
        # 提交更改
        db.session.commit()
        
        # 验证管理员权限
        print(f"验证管理员权限: {admin_user.is_administrator()}")
        print(f"用户角色: {admin_user.role.name}")
        print(f"角色权限: {admin_user.role.permissions}")
        
        print("\n管理员用户信息:")
        print(f"用户名: {admin_user.username}")
        print(f"邮箱: {admin_user.email}")
        print(f"密码: admin123 (请首次登录后修改)")
        print(f"是否管理员: {admin_user.is_administrator()}")
        
        return True

def list_all_users():
    """列出所有用户及其角色"""
    app = create_app('development')
    
    with app.app_context():
        users = User.query.all()
        print("\n所有用户列表:")
        print("-" * 60)
        for user in users:
            role_name = user.role.name if user.role else 'No Role'
            is_admin = user.is_administrator()
            print(f"ID: {user.id:3d} | 用户名: {user.username:15s} | 邮箱: {user.email:25s} | 角色: {role_name:15s} | 管理员: {is_admin}")

def set_user_as_admin(username):
    """将指定用户设置为管理员"""
    app = create_app('development')
    
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"错误：用户 '{username}' 不存在")
            return False
        
        admin_role = Role.query.filter_by(name='Administrator').first()
        if not admin_role:
            print("错误：管理员角色不存在，正在创建...")
            Role.insert_roles()
            admin_role = Role.query.filter_by(name='Administrator').first()
        
        user.role = admin_role
        db.session.commit()
        
        print(f"已将用户 '{username}' 设置为管理员")
        print(f"验证管理员权限: {user.is_administrator()}")
        return True

if __name__ == '__main__':
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'create':
            create_admin_user()
        elif command == 'list':
            list_all_users()
        elif command == 'set' and len(sys.argv) > 2:
            username = sys.argv[2]
            set_user_as_admin(username)
        else:
            print("用法:")
            print("  python create_admin.py create     # 创建admin用户")
            print("  python create_admin.py list       # 列出所有用户")
            print("  python create_admin.py set <用户名> # 将指定用户设置为管理员")
    else:
        print("选择操作:")
        print("1. 创建admin用户")
        print("2. 列出所有用户")
        print("3. 设置用户为管理员")
        
        choice = input("请输入选择 (1-3): ").strip()
        
        if choice == '1':
            create_admin_user()
        elif choice == '2':
            list_all_users()
        elif choice == '3':
            username = input("请输入用户名: ").strip()
            if username:
                set_user_as_admin(username)
            else:
                print("用户名不能为空")
        else:
            print("无效选择") 