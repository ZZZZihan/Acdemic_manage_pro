from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# 导入模型类，使其对ORM可见
from app.models.user import User
from app.models.achievement import Achievement
from app.models.tech_summary import TechSummary 