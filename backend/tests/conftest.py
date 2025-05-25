import pytest
import tempfile
import os
from backend.app import app as flask_app # Renamed to avoid conflict
from backend.database import init_db as init_db_function, db_session # Renamed to avoid conflict

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # Create a new temporary database file for each test
    db_fd, db_path = tempfile.mkstemp()

    # Update Flask app config for testing
    flask_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}", # Use the temp database
        "DATABASE": db_path, # For compatibility if some parts use app.config['DATABASE'] directly
        "SECRET_KEY": "test_secret_key" # Consistent secret key for tests
    })

    # Initialize the database for the app context
    with flask_app.app_context():
        init_db_function()

    yield flask_app

    # Clean up: close and remove the temporary database file
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()

@pytest.fixture
def init_db(app):
    """
    Fixture to initialize the database. 
    This is useful if you want to ensure a clean db state for a module or specific tests,
    although the main `app` fixture already initializes it for each test.
    This can be called explicitly if a test somehow corrupts the db and needs a reset mid-test,
    or if tests are structured to run against a shared, pre-populated db for a module.
    """
    with app.app_context():
        init_db_function()
        # You might also populate some initial common data here if needed for many tests
    yield 
    # Teardown can be added here if needed, but `app` fixture handles temp db cleanup.

@pytest.fixture
def auth_client(client, app):
    """A test client that is pre-authenticated as a regular user."""
    # Helper function to register and login a user
    def _login(username="testuser", password="password", role="staff"):
        # Register user
        client.post('/auth/register', json={
            'username': username,
            'password': password,
            # 'role': role # Assuming role is not set at registration by default or handled differently
        })
        # Login user
        response = client.post('/auth/login', json={
            'username': username,
            'password': password
        })
        if response.status_code != 200:
            raise RuntimeError(f"Failed to login user {username}. Response: {response.get_data(as_text=True)}")
        
        # Set role if the User model and registration/login process supports it directly
        # For this example, we'll assume role is handled by admin or post-registration
        # If role needs to be set for testing, it might require direct DB manipulation here
        # or an admin endpoint to set roles.
        # For simplicity, let's assume we might need to create an admin user separately.
        if role == "admin" and username == "adminuser": # Special case for admin user
            # This is a simplified way; a real app might need an admin user creation script
            # or an existing admin user in the test DB setup.
            from backend.models import User
            from backend.database import db_session
            with app.app_context():
                admin_user = User.query.filter_by(username=username).first()
                if admin_user:
                    admin_user.role = "admin"
                    db_session.commit()
                else: # If registration didn't create it (e.g. if it was pre-existing)
                    # This part is tricky as registration should create it.
                    # If tests need an admin, ensure one is created with admin role.
                    pass


        return client
    
    # Provide a default logged-in client
    # To use this, a test would typically call _login with desired params or use a default user
    # For now, returning the _login function itself for flexibility in tests
    return _login
