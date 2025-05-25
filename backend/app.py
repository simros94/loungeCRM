from flask import Flask
import click
from flask.cli import with_appcontext
from flask_login import LoginManager
from backend.database import init_db, db_session
from backend import models # Import models to ensure they are registered
from backend.models import User # Ensure User is imported for the user_loader

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Change this in production!

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login' # Assuming 'auth' is the name of the auth Blueprint and 'login' is the login route

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Ensure the database session is closed after each request or context
@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()

# Define a CLI command to initialize the database
@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')

app.cli.add_command(init_db_command)

# Import and register blueprints
from backend.routes.auth import auth_bp
from backend.routes.checkin import checkin_bp
from backend.routes.dashboard import dashboard_bp
from backend.routes.passengers import passengers_bp
from backend.routes.reports import reports_bp
from backend.routes.reservations import reservations_bp
from backend.routes.settings import settings_bp

app.register_blueprint(auth_bp)
app.register_blueprint(checkin_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(passengers_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(reservations_bp)
app.register_blueprint(settings_bp)

@app.route('/')
def home():
    return "Hello, World!" # This could later serve the main frontend app

if __name__ == '__main__':
    app.run(debug=True)
