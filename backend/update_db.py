from app import create_app
from app.models import db
import sqlite3
import os

app = create_app("default")

with app.app_context():
    print("开始更新数据库...")
    conn = sqlite3.connect("data-dev.sqlite")
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(tech_summaries)")
    columns = [column[1] for column in cursor.fetchall()]
    print("现有列:", columns)
