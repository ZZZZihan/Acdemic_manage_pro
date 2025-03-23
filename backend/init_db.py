from app import create_app
from app.models import db
from app.models.user import User, Role, Permission
import os

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

with app.app_context():
    # 创建角色
    Role.insert_roles()
    print("角色已创建")
    
    # 创建管理员用户
    admin_email = 'admin@example.com'
    admin = User.query.filter_by(email=admin_email).first()
    
    if admin is None:
        admin = User(
            email=admin_email,
            username='admin',
            password='admin123',
            name='管理员'
        )
        db.session.add(admin)
        db.session.commit()
        print(f"管理员用户已创建: {admin_email}, 密码: admin123")
    else:
        print(f"管理员用户已存在: {admin_email}")
    
    # 创建测试用户
    test_email = 'test@example.com'
    test_user = User.query.filter_by(email=test_email).first()
    
    if test_user is None:
        test_user = User(
            email=test_email,
            username='test',
            password='test123',
            name='测试用户'
        )
        db.session.add(test_user)
        db.session.commit()
        print(f"测试用户已创建: {test_email}, 密码: test123")
    else:
        print(f"测试用户已存在: {test_email}")
    
    # 创建一些测试成果
    from app.models.achievement import Achievement
    from datetime import datetime, timedelta
    
    if Achievement.query.count() == 0:
        achievements = [
            {
                'title': '基于深度学习的图像识别算法研究',
                'description': '本研究提出了一种基于深度学习的图像识别算法，在CIFAR-10数据集上取得了98.2%的准确率。',
                'achievement_type': '论文',
                'authors': '张三, 李四, 王五',
                'publish_date': datetime.now() - timedelta(days=30),
                'user_id': admin.id
            },
            {
                'title': '一种新型传感器设计方法',
                'description': '本发明提出了一种新型传感器设计方法，可以提高传感器的灵敏度和稳定性。',
                'achievement_type': '专利',
                'authors': '李四, 王五',
                'publish_date': datetime.now() - timedelta(days=60),
                'user_id': admin.id
            },
            {
                'title': '智能交通系统关键技术研究',
                'description': '本项目研究了智能交通系统的关键技术，包括车辆检测、轨迹预测和交通流量分析等。',
                'achievement_type': '项目',
                'authors': '张三, 赵六',
                'publish_date': datetime.now() - timedelta(days=90),
                'user_id': test_user.id
            }
        ]
        
        for achievement_data in achievements:
            achievement = Achievement(**achievement_data)
            db.session.add(achievement)
        
        db.session.commit()
        print(f"已创建 {len(achievements)} 个测试成果")
    else:
        print(f"已存在 {Achievement.query.count()} 个成果记录")
    
    print("数据库初始化完成!") 