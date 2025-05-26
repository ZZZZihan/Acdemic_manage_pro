#!/usr/bin/env python3
"""
快速启动脚本
禁用向量模型以大幅提高启动速度
适用于开发和测试环境
"""

import os
import dotenv

# 设置快速启动环境变量
os.environ['DISABLE_VECTOR_MODEL'] = 'true'
os.environ['VERBOSE_STARTUP'] = 'false'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

# 加载其他环境变量
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    print("🚀 快速启动模式 - 正在加载环境变量...")
    dotenv.load_dotenv(dotenv_path)
    print(f"DEEPSEEK_API_KEY已设置: {bool(os.environ.get('DEEPSEEK_API_KEY'))}")
    print(f"OPENAI_API_KEY已设置: {bool(os.environ.get('OPENAI_API_KEY'))}")
    print("⚡ 向量模型已禁用，启动速度将大幅提升")
    print("💡 注意：搜索功能将使用关键词匹配，质量可能降低")
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
    app.run(host='0.0.0.0', port=5003, debug=True) 