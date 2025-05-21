from flask import Blueprint

api = Blueprint('api', __name__)

from app.api.v1 import auth, achievements, errors, files, tech_summaries, projects, users, meetings
from app.api.v1.rag import rag_bp
from app.api.v1.ollama import ollama_bp

# 注册子蓝图
api.register_blueprint(rag_bp, url_prefix='/rag')
api.register_blueprint(ollama_bp, url_prefix='/ollama')