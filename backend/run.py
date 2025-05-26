import os
import dotenv
from app import create_app
from flask_migrate import Migrate
from app.models import db

# 加载环境变量
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    print("正在从.env文件加载环境变量...")
    dotenv.load_dotenv(dotenv_path)
    print(f"DEEPSEEK_API_KEY已设置: {bool(os.environ.get('DEEPSEEK_API_KEY'))}")
    print(f"OPENAI_API_KEY已设置: {bool(os.environ.get('OPENAI_API_KEY'))}")
else:
    print("未找到.env文件，请创建.env文件并设置API密钥")

# 初始化启动优化器
from app.utils.startup_optimizer import startup_optimizer
startup_optimizer.print_startup_info()

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
migrate = Migrate(app, db)

@app.shell_context_processor
def make_shell_context():
    return dict(db=db)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003) 