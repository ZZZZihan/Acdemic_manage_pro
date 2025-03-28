from app import create_app
from app.models.achievement import Achievement
import os

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

with app.app_context():
    # 查询所有项目类型的成果
    achievements = Achievement.query.filter_by(achievement_type='项目').all()
    
    print(f'共找到 {len(achievements)} 个项目类型的成果记录:')
    for i, a in enumerate(achievements):
        print(f'{i+1}. {a.title}')
        print(f'   描述: {a.description[:50]}...')
        print(f'   作者: {a.authors}')
        print(f'   链接: {a.url}')
        print(f'   图片: {a.file_path}')
        print('-' * 50) 