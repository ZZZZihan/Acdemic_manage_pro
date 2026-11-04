"""Initialize schema and roles without creating accounts with public default passwords."""
import os
from app import create_app
from flask.cli import ScriptInfo

if __name__ == '__main__':
    app = create_app(os.getenv('FLASK_CONFIG', 'development'))
    with app.app_context():
        app.cli.main(args=['init-auth'], prog_name='init_db.py', obj=ScriptInfo(create_app=lambda: app))
