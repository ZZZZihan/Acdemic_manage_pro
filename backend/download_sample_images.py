import os
import requests
from app import create_app
from io import BytesIO
from PIL import Image

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

# 定义项目图片和对应的示例图片URL
project_images = [
    {'filename': 'medical_imaging.jpg', 'url': 'https://img.freepik.com/free-photo/doctor-examining-brain-scan_23-2149367436.jpg'},
    {'filename': 'smart_campus.png', 'url': 'https://img.freepik.com/free-vector/smart-city-technology-background_23-2148416888.jpg'},
    {'filename': 'agriculture.jpg', 'url': 'https://img.freepik.com/free-photo/smart-agriculture-iot-with-hand-planting-tree_53876-125943.jpg'},
    {'filename': 'blockchain.png', 'url': 'https://img.freepik.com/free-vector/gradient-cryptocurrency-concept_23-2149215743.jpg'},
    {'filename': 'traffic.jpg', 'url': 'https://img.freepik.com/free-photo/aerial-shot-busy-interchange-rush-hour_181624-16812.jpg'},
    {'filename': 'maintenance.png', 'url': 'https://img.freepik.com/free-photo/process-engine-maintenance-factory-close-up_1359-275.jpg'},
    {'filename': 'chatbot.jpg', 'url': 'https://img.freepik.com/free-vector/gradient-chat-bot-illustration_23-2149746409.jpg'},
    {'filename': 'environment.png', 'url': 'https://img.freepik.com/free-vector/environmental-protection-concept-illustration_114360-8469.jpg'},
    {'filename': 'education.jpg', 'url': 'https://img.freepik.com/free-photo/happy-students-with-laptop-books-university_176420-628.jpg'},
    {'filename': 'telemedicine.png', 'url': 'https://img.freepik.com/free-vector/telemedicine-abstract-concept-illustration_335657-3812.jpg'}
]

# 获取图片保存路径
upload_folder = os.path.join(app.root_path, 'static', 'uploads', 'projects')
if not os.path.exists(upload_folder):
    os.makedirs(upload_folder)
    print(f'创建目录: {upload_folder}')

# 下载和保存图片
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

successful = 0
failed = 0

for img_data in project_images:
    filename = img_data['filename']
    url = img_data['url']
    file_path = os.path.join(upload_folder, filename)
    
    try:
        # 下载图片
        print(f"正在下载: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 使用PIL处理图片
        img = Image.open(BytesIO(response.content))
        
        # 调整图片大小，保持宽高比例
        max_size = (800, 400)
        img.thumbnail(max_size, Image.LANCZOS)
        
        # 替代URL - 如果无法下载图片
        if img.width < 100 or img.height < 100:
            raise Exception("图片太小，可能是占位图")
        
        # 保存图片
        img.save(file_path)
        successful += 1
        print(f"图片已保存: {file_path}")
            
    except Exception as e:
        print(f"下载失败: {url}, 错误: {e}")
        failed += 1
        
        # 替代方案：生成一个有项目名称的颜色块
        try:
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
            
            # 从文件名提取项目类型
            project_type = filename.split('.')[0]
            title = ' '.join(word.capitalize() for word in project_type.split('_'))
            
            # 创建颜色块图片
            from PIL import Image, ImageDraw, ImageFont
            import random
            
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
            print(f"已创建替代图片: {file_path}")
        except Exception as e2:
            print(f"创建替代图片也失败: {e2}")

print(f"\n总结: 成功下载 {successful} 张图片, 失败 {failed} 张图片") 