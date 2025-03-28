from PIL import Image, ImageDraw, ImageFont
import os
from app import create_app
import random

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

# 项目图片信息
project_images = [
    {'filename': 'medical_imaging.jpg', 'title': '医疗影像分析'},
    {'filename': 'smart_campus.png', 'title': '智慧校园管理'},
    {'filename': 'agriculture.jpg', 'title': '智能农业监测'},
    {'filename': 'blockchain.png', 'title': '区块链溯源'},
    {'filename': 'traffic.jpg', 'title': '智能交通管理'},
    {'filename': 'maintenance.png', 'title': '设备预测维护'},
    {'filename': 'chatbot.jpg', 'title': '智能客服系统'},
    {'filename': 'environment.png', 'title': '环境质量监测'},
    {'filename': 'education.jpg', 'title': '智能教学辅助'},
    {'filename': 'telemedicine.png', 'title': '远程医疗会诊'}
]

# 获取上传文件夹路径
upload_folder = os.path.join(app.root_path, 'static', 'uploads', 'projects')
if not os.path.exists(upload_folder):
    os.makedirs(upload_folder)
    print(f'创建目录: {upload_folder}')

# 创建每个图片
for img_data in project_images:
    filename = img_data['filename']
    title = img_data['title']
    file_path = os.path.join(upload_folder, filename)
    
    # 确定文件类型
    if filename.endswith('.jpg') or filename.endswith('.jpeg'):
        mode = 'RGB'
        extension = 'JPEG'
    elif filename.endswith('.png'):
        mode = 'RGBA'
        extension = 'PNG'
    else:
        mode = 'RGB'
        extension = 'JPEG'
    
    # 创建随机颜色的图片
    r = random.randint(0, 200)
    g = random.randint(0, 200)
    b = random.randint(0, 200)
    
    # 创建图片
    img = Image.new(mode, (800, 400), (r, g, b))
    draw = ImageDraw.Draw(img)
    
    # 添加文字
    try:
        # 尝试加载字体，如果失败则使用默认字体
        font = ImageFont.truetype('Arial', 40)
    except IOError:
        font = ImageFont.load_default()
        
    # 添加标题
    text_width = draw.textlength(title, font=font)
    text_position = ((800 - text_width) / 2, 150)
    draw.text(text_position, title, fill=(255, 255, 255), font=font)
    
    # 保存图片
    img.save(file_path, extension)
    print(f'已创建图片: {file_path}')

print('示例项目图片创建完成！')

# 调整数据库中的图片路径
with app.app_context():
    from app.models import db
    from app.models.achievement import Achievement
    
    achievements = Achievement.query.filter_by(achievement_type='项目').all()
    updated = 0
    
    for achievement in achievements:
        if achievement.file_path and achievement.file_path.startswith('/uploads/'):
            # 移除前导斜杠，使其与静态文件路径匹配
            achievement.file_path = achievement.file_path[1:]
            updated += 1
    
    if updated > 0:
        db.session.commit()
        print(f'已更新 {updated} 个项目记录的图片路径')
    else:
        print('没有项目记录需要更新图片路径') 