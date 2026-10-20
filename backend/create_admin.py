"""Use the authenticated-role administration CLI instead of default passwords."""
from app import create_app
from flask.cli import ScriptInfo
import os

if __name__ == '__main__':
    app = create_app(os.getenv('FLASK_CONFIG', 'development'))
    with app.app_context():
        app.cli.main(args=['create-admin', *__import__('sys').argv[1:]], prog_name='create_admin.py', obj=ScriptInfo(create_app=lambda: app))
