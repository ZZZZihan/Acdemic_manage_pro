#!/usr/bin/env python3
"""
优化启动脚本
保留向量模型功能，但减少日志输出和提高启动速度
适用于需要完整功能的开发环境
"""

import os
import dotenv

# 设置优化环境变量（保留向量模型）
os.environ['DISABLE_VECTOR_MODEL'] = 'false'  # 保留向量模型
os.environ['ENABLE_VECTOR_CACHE'] = 'true'    # 启用缓存
os.environ['VERBOSE_STARTUP'] = 'false'       # 减少日志
os.environ['VECTOR_BATCH_SIZE'] = '16'        # 减小批次大小
os.environ['TOKENIZERS_PARALLELISM'] = 'false'  # 避免警告

# 加载其他环境变量
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    print("🔧 优化启动模式 - 正在加载环境变量...")
    dotenv.load_dotenv(dotenv_path)
    print(f"DEEPSEEK_API_KEY已设置: {bool(os.environ.get('DEEPSEEK_API_KEY'))}")
    print(f"OPENAI_API_KEY已设置: {bool(os.environ.get('OPENAI_API_KEY'))}")
    print("⚡ 启动优化已启用：缓存+减少日志+小批次处理")
    print("✅ 向量模型保持启用，搜索质量最佳")
else:
    print("未找到.env文件，请创建.env文件并设置API密钥")

from app import create_app
from flask_migrate import Migrate
from app.models import db

# 初始化启动优化器
from app.utils.startup_optimizer import startup_optimizer
startup_optimizer.print_startup_info()

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
migrate = Migrate(app, db)

@app.shell_context_processor
def make_shell_context():
    return dict(db=db)

if __name__ == '__main__':
    print("🎯 应用已启动，访问 http://localhost:5003")
    print("💡 提示：首次启动可能需要下载模型，后续启动会更快")
    app.run(host='0.0.0.0', port=5003, debug=True) 