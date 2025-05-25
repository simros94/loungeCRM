import pytest
from backend.models import User, LoungeSetting
from backend.database import db_session

# Helper to register and login a user with a specific role
def login_user_with_role(client, app, username, password, role):
    # Registration (ensure user exists for login)
    reg_response = client.post('/auth/register', json={'username': username, 'password': password})
    # User might already exist if tests are run multiple times or fixtures set them up
    assert reg_response.status_code in [201, 400] 

    # Manually set role after registration (if not handled by registration endpoint)
    # This is crucial for admin tests.
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user: # Should not happen if registration was 201
             pytest.fail(f"User {username} not found after registration attempt.")
        user.role = role
        db_session.commit()

    # Login
    login_response = client.post('/auth/login', json={'username': username, 'password': password})
    assert login_response.status_code == 200
    return login_response


@pytest.fixture
def admin_client(client, app):
    login_user_with_role(client, app, "admin_settings", "adminpass", "admin")
    return client

@pytest.fixture
def staff_client(client, app):
    login_user_with_role(client, app, "staff_settings", "staffpass", "staff")
    return client

# --- Lounge Settings Tests ---
def test_get_lounge_settings_unauthenticated(client):
    response = client.get('/settings/lounge')
    assert response.status_code == 401

def test_get_lounge_settings_as_staff(staff_client, app):
    # Create a default setting first if none exists, or ensure one is there.
    with app.app_context():
        if not LoungeSetting.query.first():
            db_session.add(LoungeSetting(lounge_name="Default Lounge From Test"))
            db_session.commit()

    response = staff_client.get('/settings/lounge')
    assert response.status_code == 200
    json_data = response.get_json()
    assert 'lounge_name' in json_data # Check for expected fields

def test_get_lounge_settings_as_admin(admin_client, app):
    with app.app_context():
        if not LoungeSetting.query.first():
            db_session.add(LoungeSetting(lounge_name="Admin Test Lounge"))
            db_session.commit()
    response = admin_client.get('/settings/lounge')
    assert response.status_code == 200
    json_data = response.get_json()
    assert 'lounge_name' in json_data

def test_update_lounge_settings_as_staff(staff_client):
    response = staff_client.post('/settings/lounge', json={'lounge_name': 'Staff Update Attempt'})
    assert response.status_code == 403 # Staff should not be able to update

def test_update_lounge_settings_as_admin_success(admin_client, app):
    new_settings = {
        'lounge_name': 'Updated Prima Vista',
        'lounge_address': '123 Test Avenue',
        'lounge_capacity': 150,
        'entry_tracking_method': 'qr_scan'
    }
    response = admin_client.post('/settings/lounge', json=new_settings)
    assert response.status_code == 200
    assert response.get_json()['message'] == 'Lounge settings updated successfully'

    with app.app_context():
        settings = LoungeSetting.query.first()
        assert settings is not None
        assert settings.lounge_name == new_settings['lounge_name']
        assert settings.lounge_address == new_settings['lounge_address']
        assert settings.lounge_capacity == new_settings['lounge_capacity']
        assert settings.entry_tracking_method == new_settings['entry_tracking_method']

def test_update_lounge_settings_partial_update(admin_client, app):
    # First, ensure some settings exist
    admin_client.post('/settings/lounge', json={'lounge_name': 'Initial Name', 'lounge_capacity': 100})
    
    # Partial update
    response = admin_client.post('/settings/lounge', json={'lounge_name': 'New Partial Name'})
    assert response.status_code == 200
    
    with app.app_context():
        settings = LoungeSetting.query.first()
        assert settings.lounge_name == 'New Partial Name'
        assert settings.lounge_capacity == 100 # Should remain unchanged

# --- User Accounts Tests ---
def test_get_users_as_staff(staff_client):
    response = staff_client.get('/settings/users')
    assert response.status_code == 403 # Staff should not list users

def test_get_users_as_admin(admin_client, app):
    # Ensure admin_client itself is a user that would be listed
    response = admin_client.get('/settings/users')
    assert response.status_code == 200
    json_data = response.get_json()
    assert isinstance(json_data, list)
    # At least the admin user used for admin_client should be there
    assert any(u['username'] == 'admin_settings' for u in json_data) 

def test_create_user_as_staff(staff_client):
    response = staff_client.post('/settings/users', json={
        'username': 'staff_created_user', 'password': 'password', 'role': 'staff'
    })
    assert response.status_code == 403

def test_create_user_as_admin_success(admin_client, app):
    new_user_data = {'username': 'test_staff_by_admin', 'password': 'password123', 'role': 'staff'}
    response = admin_client.post('/settings/users', json=new_user_data)
    assert response.status_code == 201
    json_data = response.get_json()
    assert json_data['message'] == 'User created successfully'
    assert json_data['user']['username'] == new_user_data['username']
    assert json_data['user']['role'] == new_user_data['role']

    with app.app_context():
        user = User.query.filter_by(username=new_user_data['username']).first()
        assert user is not None
        assert user.role == new_user_data['role']

def test_create_user_as_admin_existing_username(admin_client):
    client.post('/auth/register', json={'username': 'existing_for_admin_test', 'password': 'pw'}) # Pre-register
    
    response = admin_client.post('/settings/users', json={
        'username': 'existing_for_admin_test', 'password': 'new_pw', 'role': 'staff'
    })
    assert response.status_code == 400
    assert 'Username already exists' in response.get_json()['message']

def test_create_user_as_admin_missing_fields(admin_client):
    response = admin_client.post('/settings/users', json={'username': 'missing_pass_role'})
    assert response.status_code == 400
    assert 'Username and password are required' in response.get_json()['message']


def test_update_user_as_staff(staff_client, app):
    # Need a user ID to attempt to update. Create one with admin first.
    admin_client_for_setup = app.test_client() # Fresh client to act as admin
    login_user_with_role(admin_client_for_setup, app, "admin_setup_for_staff", "apass", "admin")
    user_to_update_res = admin_client_for_setup.post('/settings/users', json={
        'username': 'user_for_staff_update_attempt', 'password': 'password', 'role': 'staff'
    })
    user_id = user_to_update_res.get_json()['user']['id']
    
    response = staff_client.put(f'/settings/users/{user_id}', json={'role': 'admin'})
    assert response.status_code == 403

def test_update_user_as_admin_success(admin_client, app):
    # Create a user to update
    create_user_res = admin_client.post('/settings/users', json={
        'username': 'user_to_be_updated', 'password': 'oldpassword', 'role': 'staff'
    })
    user_id = create_user_res.get_json()['user']['id']

    update_data = {'username': 'updated_username', 'role': 'admin', 'password': 'newpassword'}
    response = admin_client.put(f'/settings/users/{user_id}', json=update_data)
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['message'] == 'User updated successfully'
    assert json_data['user']['username'] == update_data['username']
    assert json_data['user']['role'] == update_data['role']

    with app.app_context():
        user = User.query.get(user_id)
        assert user.username == update_data['username']
        assert user.role == update_data['role']
        assert user.check_password(update_data['password'])

def test_update_user_as_admin_change_only_role(admin_client, app):
    user_res = admin_client.post('/settings/users', json={'username': 'role_change_user', 'password': 'password', 'role': 'staff'})
    user_id = user_res.get_json()['user']['id']

    response = admin_client.put(f'/settings/users/{user_id}', json={'role': 'admin'})
    assert response.status_code == 200
    with app.app_context():
        user = User.query.get(user_id)
        assert user.role == 'admin'
        assert user.check_password('password') # Password should be unchanged

def test_update_user_as_admin_not_found(admin_client):
    response = admin_client.put('/settings/users/99999', json={'role': 'staff'})
    assert response.status_code == 404
    assert 'User not found' in response.get_json()['message']
