import click
from flask.cli import with_appcontext
from app.models import db, User, Role


def register_auth_commands(app):
    @app.cli.command('init-auth')
    @with_appcontext
    def init_auth():
        """Create missing tables and seed roles without replacing business data."""
        db.create_all()
        Role.insert_roles()
        role = Role.query.filter_by(name='User').one()
        User.query.filter(User.role_id.is_(None)).update({'role_id': role.id})
        db.session.commit()
        click.echo('Auth schema and roles are ready; existing assigned roles were preserved.')

    @app.cli.command('create-admin')
    @click.option('--email', required=True)
    @click.option('--username', required=True)
    @click.password_option(confirmation_prompt=True)
    @with_appcontext
    def create_admin(email, username, password):
        """Explicit local bootstrap; public registration never creates an administrator."""
        email, username = email.strip(), username.strip()
        if '@' not in email or not username or len(email) > 64 or len(username) > 64 or not 6 <= len(password) <= 256:
            raise click.ClickException('Invalid email, username or password length.')
        if User.query.filter((User.email == email) | (User.username == username)).first():
            raise click.ClickException('Account exists; use set-role to change its role without changing its password.')
        role = Role.query.filter_by(name='Administrator').first()
        if role is None:
            raise click.ClickException('Run init-auth first.')
        db.session.add(User(email=email, username=username, password=password, role=role))
        db.session.commit()
        click.echo('Administrator created.')

    @app.cli.command('set-role')
    @click.argument('username')
    @click.argument('role_name', type=click.Choice(['User', 'Moderator', 'Administrator']))
    @with_appcontext
    def set_role(username, role_name):
        user = User.query.filter_by(username=username).first()
        role = Role.query.filter_by(name=role_name).first()
        if user is None or role is None:
            raise click.ClickException('User or role not found; run init-auth and verify the username.')
        if user.is_administrator() and role_name != 'Administrator':
            admins = User.query.join(Role).filter(Role.name == 'Administrator').count()
            if admins <= 1:
                raise click.ClickException('Cannot remove the last administrator.')
        user.role = role
        db.session.commit()
        click.echo('Role updated.')
