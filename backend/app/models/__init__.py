from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# 导入模型类，使其对ORM可见
from app.models.user import User, Role, Permission
from app.models.achievement import Achievement
from app.models.tech_summary import TechSummary
from app.models.project import Project, ProjectMember
from app.models.meeting import Meeting, MeetingParticipant, MeetingFile 