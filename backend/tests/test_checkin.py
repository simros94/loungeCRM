import pytest
from backend.models import Passenger, LoungeEntry
from backend.database import db_session # For checking DB state
from datetime import datetime

# Helper to register and login a staff user (most CRM actions would be by staff)
def login_staff_user(client, username="staff_checkin", password="password"):
    # Register
    reg_response = client.post('/auth/register', json={
        'username': username,
        'password': password
        # Assuming default role is staff, or role is not strictly checked for checkin
    })
    # Allow 400 if user already exists from a previous test run (if db is not perfectly clean)
    # A better approach is to ensure clean DB or use unique usernames per test function.
    assert reg_response.status_code in [201, 400] 


    # Login
    login_response = client.post('/auth/login', json={
        'username': username,
        'password': password
    })
    assert login_response.status_code == 200
    return login_response

def test_check_in_passenger_success(client, app):
    login_staff_user(client) # Ensure user is logged in

    passenger_name = "Test Passenger"
    flight_number = "TP123"
    entry_time_iso = datetime.utcnow().isoformat()

    response = client.post('/checkin', json={
        'passenger_name': passenger_name,
        'flight_number': flight_number,
        'entry_time': entry_time_iso
    })

    assert response.status_code == 201
    json_data = response.get_json()
    assert json_data['message'] == 'Passenger checked in successfully'
    assert 'lounge_entry' in json_data
    assert json_data['lounge_entry']['passenger_name'] == passenger_name
    assert json_data['lounge_entry']['flight_number'] == flight_number
    assert json_data['lounge_entry']['status'] == 'active'
    
    # Verify in database
    with app.app_context():
        entry = LoungeEntry.query.get(json_data['lounge_entry']['id'])
        assert entry is not None
        assert entry.passenger.name == passenger_name
        assert entry.passenger.flight_number == flight_number
        assert entry.status == 'active'

def test_check_in_passenger_existing_passenger(client, app):
    login_staff_user(client, "staff_checkin_exist", "password")

    # First check-in
    client.post('/checkin', json={
        'passenger_name': 'Existing Name',
        'flight_number': 'EX789'
    })

    # Second check-in for the same passenger (should create a new entry)
    response = client.post('/checkin', json={
        'passenger_name': 'Existing Name',
        'flight_number': 'EX789' 
        # Optionally a different entry time
    })
    assert response.status_code == 201
    json_data = response.get_json()
    assert json_data['message'] == 'Passenger checked in successfully'

    with app.app_context():
        passenger = Passenger.query.filter_by(name='Existing Name', flight_number='EX789').first()
        assert passenger is not None
        # Ensure there are two entries for this passenger
        assert len(passenger.lounge_entries) >= 2 # Could be more if tests run multiple times without full clean

def test_check_in_passenger_missing_fields(client, app):
    login_staff_user(client, "staff_checkin_missing", "password")

    # Missing flight_number
    response = client.post('/checkin', json={'passenger_name': 'Test Name'})
    assert response.status_code == 400
    assert 'Passenger name and flight number are required' in response.get_json()['message']

    # Missing passenger_name
    response = client.post('/checkin', json={'flight_number': 'FL100'})
    assert response.status_code == 400
    assert 'Passenger name and flight number are required' in response.get_json()['message']

def test_check_in_passenger_invalid_entry_time_format(client, app):
    login_staff_user(client, "staff_checkin_invalid_time", "password")
    
    response = client.post('/checkin', json={
        'passenger_name': 'Time Test',
        'flight_number': 'TT001',
        'entry_time': 'not-a-valid-date'
    })
    assert response.status_code == 400
    assert 'Invalid entry_time format' in response.get_json()['message']

def test_check_in_passenger_not_logged_in(client, app):
    response = client.post('/checkin', json={
        'passenger_name': 'No Auth Passenger',
        'flight_number': 'NA123'
    })
    assert response.status_code == 401 # Expect redirect or 401 if not logged in
    # The exact response might depend on Flask-Login's unauthorized handler.
    # For API, it should be 401.
    # assert 'message' in response.get_json() # Or check for redirect location
    # assert 'Login required' in response.get_json()['message'] # Example, if it returns JSON
    # For now, status code 401 is the primary check.

# Test case for when entry_time is not provided (backend should default it)
def test_check_in_passenger_no_entry_time(client, app):
    login_staff_user(client, "staff_checkin_no_time", "password")

    passenger_name = "Default Time Passenger"
    flight_number = "DT789"

    response = client.post('/checkin', json={
        'passenger_name': passenger_name,
        'flight_number': flight_number
        # entry_time is omitted
    })

    assert response.status_code == 201
    json_data = response.get_json()
    assert json_data['message'] == 'Passenger checked in successfully'
    assert 'lounge_entry' in json_data
    assert json_data['lounge_entry']['passenger_name'] == passenger_name
    assert json_data['lounge_entry']['flight_number'] == flight_number
    assert json_data['lounge_entry']['status'] == 'active'
    assert json_data['lounge_entry']['entry_time'] is not None # Backend should have set this

    with app.app_context():
        entry = LoungeEntry.query.get(json_data['lounge_entry']['id'])
        assert entry is not None
        assert entry.entry_time is not None # Verify in DB as well
        # Check if entry_time is recent (e.g., within last few seconds)
        # This can be tricky due to timing, but a basic check is that it exists.
        # time_difference = datetime.utcnow() - entry.entry_time
        # assert time_difference.total_seconds() < 5 # Example: within 5 seconds
    
    # Test that passenger is created if new
    with app.app_context():
        passenger = Passenger.query.filter_by(name=passenger_name, flight_number=flight_number).first()
        assert passenger is not None
        assert passenger.name == passenger_name
        assert passenger.flight_number == flight_number
        assert len(passenger.lounge_entries) == 1 # First entry for this passenger
        assert passenger.lounge_entries[0].id == json_data['lounge_entry']['id']
