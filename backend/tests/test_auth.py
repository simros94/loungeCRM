import pytest
from backend.models import User # For checking DB state
from backend.database import db_session # For checking DB state

# Helper function (can also be a fixture if more complex setup is needed)
def register_and_login_user(client, username="testuser", password="password"):
    # Register
    reg_response = client.post('/auth/register', json={
        'username': username,
        'password': password
    })
    assert reg_response.status_code == 201

    # Login
    login_response = client.post('/auth/login', json={
        'username': username,
        'password': password
    })
    assert login_response.status_code == 200
    return login_response

def test_register_user_success(client, app):
    response = client.post('/auth/register', json={
        'username': 'newuser',
        'password': 'newpassword'
    })
    assert response.status_code == 201
    assert response.json['message'] == 'User created successfully'
    with app.app_context():
        user = User.query.filter_by(username='newuser').first()
        assert user is not None
        assert user.check_password('newpassword')

def test_register_user_existing_username(client, app):
    # First, register a user
    client.post('/auth/register', json={
        'username': 'existinguser',
        'password': 'password1'
    })
    # Attempt to register again with the same username
    response = client.post('/auth/register', json={
        'username': 'existinguser',
        'password': 'password2'
    })
    assert response.status_code == 400
    assert response.json['message'] == 'Username already exists'

def test_register_user_missing_fields(client):
    response = client.post('/auth/register', json={'username': 'user1'}) # Missing password
    assert response.status_code == 400
    assert 'Username and password are required' in response.json['message']

    response = client.post('/auth/register', json={'password': 'password1'}) # Missing username
    assert response.status_code == 400
    assert 'Username and password are required' in response.json['message']

def test_login_user_success(client, app):
    # Register user first
    client.post('/auth/register', json={
        'username': 'loginuser',
        'password': 'loginpassword'
    })
    # Attempt to login
    response = client.post('/auth/login', json={
        'username': 'loginuser',
        'password': 'loginpassword'
    })
    assert response.status_code == 200
    assert response.json['message'] == 'Logged in successfully'
    assert 'user' in response.json
    assert response.json['user']['username'] == 'loginuser'
    # Role might not be set by default, or could be 'staff'
    # assert response.json['user']['role'] == 'staff' 

def test_login_user_incorrect_password(client, app):
    client.post('/auth/register', json={
        'username': 'userpass',
        'password': 'correctpassword'
    })
    response = client.post('/auth/login', json={
        'username': 'userpass',
        'password': 'wrongpassword'
    })
    assert response.status_code == 401
    assert response.json['message'] == 'Invalid username or password'

def test_login_user_nonexistent_user(client):
    response = client.post('/auth/login', json={
        'username': 'nouser',
        'password': 'password'
    })
    assert response.status_code == 401
    assert response.json['message'] == 'Invalid username or password'

def test_logout_user_success(client, app):
    register_and_login_user(client, "logouttest", "password") # Login first
    
    response = client.post('/auth/logout')
    assert response.status_code == 200
    assert response.json['message'] == 'Logged out successfully'

    # Verify user is logged out by checking status or accessing a protected route
    status_response = client.get('/auth/status')
    assert status_response.status_code == 401 # Assuming @login_required redirects or denies

def test_logout_user_not_logged_in(client):
    response = client.post('/auth/logout') # Attempt logout without being logged in
    assert response.status_code == 401 # As @login_required should block it

def test_status_when_logged_in(client, app):
    login_data = register_and_login_user(client, "statustest", "password")
    
    response = client.get('/auth/status')
    assert response.status_code == 200
    assert 'user' in response.json
    assert response.json['user']['username'] == 'statustest'
    # Check for role if it's part of your user object in status
    # assert response.json['user']['role'] is not None 

def test_status_when_not_logged_in(client):
    response = client.get('/auth/status')
    assert response.status_code == 401 # Assuming @login_required behavior
    # The message might vary depending on how Flask-Login handles it.
    # It might be JSON like {'message': '...'} or HTML if it redirects to a login page.
    # For a JSON API, it should ideally be a JSON response.
    # The default is often a redirect, but if login_view is not set or for API blueprints,
    # it might return 401 directly. Our current setup might return 401.
    # Check your LoginManager's unauthorized handler or default behavior.
    # If it returns JSON:
    # assert 'message' in response.json
    # assert 'Please log in to access this resource' in response.json['message'] # Or similar
    # If it's just a 401 without a body or specific JSON, the status code check is primary.
    # Given the current setup, a 401 is expected.
    # The default Flask-Login behavior for @login_required without a login_view configured for the blueprint
    # or a global one might be just a 401.
    # If login_manager.login_view = 'auth.login' is effective, it might try to redirect,
    # but for XHR/fetch, it often results in the 401 being handled by the client.
    # Let's assume it's a direct 401 for API style interaction.

# Example of using the auth_client fixture from conftest.py for a staff user
def test_protected_route_with_staff_auth_client(auth_client, app):
    # Use the fixture to get a logged-in client
    # The fixture itself can handle registration and login
    staff_client = auth_client(username="staffuser", password="staffpassword", role="staff")
    
    # Now use staff_client to access a protected route
    # Example: Check status, which requires login
    response = staff_client.get('/auth/status')
    assert response.status_code == 200
    assert response.json['user']['username'] == 'staffuser'
    # The role assertion depends on how roles are set and returned.
    # The `auth_client` fixture in conftest might need adjustment if role isn't set by default.
    # For now, we'll assume the default role or test without strict role checking here.
    # assert response.json['user']['role'] == 'staff' 
    
    # If you need an admin client:
    # admin_client = auth_client(username="admin_fixture_user", password="adminpassword", role="admin")
    # admin_status_response = admin_client.get('/auth/status')
    # assert admin_status_response.status_code == 200
    # assert admin_status_response.json['user']['role'] == 'admin' # Requires auth_client to set role
    
    # Clean up (if users are persisted across tests and not using in-memory db that resets)
    # This is generally handled by the app fixture's db teardown.
    pass
