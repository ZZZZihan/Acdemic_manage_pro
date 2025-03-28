from flask import Blueprint

api = Blueprint('api', __name__)

from app.api.v1 import auth, achievements, errors, files, tech_summaries, ollama, rag