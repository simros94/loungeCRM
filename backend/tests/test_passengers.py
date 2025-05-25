import pytest
from backend.models import Passenger, LoungeEntry
from backend.database import db_session
from datetime import datetime, timedelta

# Helper to register and login a staff user
def login_staff_user(client, username="staff_passengers", password="password"):
    reg_response = client.post('/auth/register', json={'username': username, 'password': password})
    assert reg_response.status_code in [201, 400]
    login_response = client.post('/auth/login', json={'username': username, 'password': password})
    assert login_response.status_code == 200
    return login_response

def setup_passenger_data(client):
    # Passenger 1: John Doe, Flight JD123, 2 entries (1 active, 1 exited)
    client.post('/checkin', json={'passenger_name': 'John Doe', 'flight_number': 'JD123', 'entry_time': (datetime.utcnow() - timedelta(days=1)).isoformat()}) # Active
    entry_to_exit_res = client.post('/checkin', json={'passenger_name': 'John Doe', 'flight_number': 'JD123', 'entry_time': (datetime.utcnow() - timedelta(days=2, hours=2)).isoformat()})
    entry_id_to_exit = entry_to_exit_res.get_json()['lounge_entry']['id']
    client.post(f'/passengers/{entry_id_to_exit}/exit', json={'exit_time': (datetime.utcnow() - timedelta(days=2, hours=1)).isoformat()})

    # Passenger 2: Jane Smith, Flight JS456, 1 active entry
    client.post('/checkin', json={'passenger_name': 'Jane Smith', 'flight_number': 'JS456', 'entry_time': (datetime.utcnow() - timedelta(hours=5)).isoformat()})
    
    # Passenger 3: Alex Johnson, Flight AJ789, no lounge entries directly, but for reservation tests later
    # For this module, we only care about passengers with entries.
    # We can also create a passenger who made a reservation but never checked in.
    # For now, focusing on passengers with LoungeEntry records.

def test_get_passengers_unauthenticated(client):
    response = client.get('/passengers')
    assert response.status_code == 401

def test_get_passengers_no_query_empty_db(client, app, init_db):
    login_staff_user(client)
    response = client.get('/passengers')
    assert response.status_code == 200
    json_data = response.get_json()
    assert isinstance(json_data, list)
    assert len(json_data) == 0

def test_get_passengers_no_query_with_data(client, app, init_db):
    login_staff_user(client, "staff_pass_data", "password")
    setup_passenger_data(client)

    response = client.get('/passengers')
    assert response.status_code == 200
    json_data = response.get_json()
    assert isinstance(json_data, list)
    # Should return unique passengers based on their entries
    # John Doe (1 passenger record with 2 entries)
    # Jane Smith (1 passenger record with 1 entry)
    assert len(json_data) == 2 
    
    # Check structure (example for one passenger)
    # Note: The order might vary, so it's better to find the passenger by name
    john_doe_data = next((p for p in json_data if p['name'] == 'John Doe'), None)
    assert john_doe_data is not None
    assert john_doe_data['flight_number'] == 'JD123' # Assuming latest flight number is shown or consistent
    assert len(john_doe_data['lounge_entries']) == 2
    
    jane_smith_data = next((p for p in json_data if p['name'] == 'Jane Smith'), None)
    assert jane_smith_data is not None
    assert len(jane_smith_data['lounge_entries']) == 1


def test_get_passengers_with_search_query_name(client, app, init_db):
    login_staff_user(client, "staff_pass_search_name", "password")
    setup_passenger_data(client)

    response = client.get('/passengers?search_query=John')
    assert response.status_code == 200
    json_data = response.get_json()
    assert len(json_data) == 1
    assert json_data[0]['name'] == 'John Doe'

    response_no_match = client.get('/passengers?search_query=NonExistent')
    assert response_no_match.status_code == 200
    json_data_no_match = response_no_match.get_json()
    assert len(json_data_no_match) == 0

def test_get_passengers_with_search_query_flight(client, app, init_db):
    login_staff_user(client, "staff_pass_search_flight", "password")
    setup_passenger_data(client)

    response = client.get('/passengers?search_query=JS456')
    assert response.status_code == 200
    json_data = response.get_json()
    assert len(json_data) == 1
    assert json_data[0]['flight_number'] == 'JS456'
    assert json_data[0]['name'] == 'Jane Smith'


def test_exit_passenger_success(client, app, init_db):
    login_staff_user(client, "staff_pass_exit", "password")
    
    # Check-in a passenger to create an active entry
    entry_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()
    checkin_response = client.post('/checkin', json={
        'passenger_name': 'Exit Test User',
        'flight_number': 'ETU001',
        'entry_time': entry_time
    })
    assert checkin_response.status_code == 201
    entry_id = checkin_response.get_json()['lounge_entry']['id']

    # Now, exit this passenger
    exit_time = datetime.utcnow().isoformat()
    exit_response = client.post(f'/passengers/{entry_id}/exit', json={'exit_time': exit_time})
    assert exit_response.status_code == 200
    json_data = exit_response.get_json()
    assert json_data['message'] == 'Passenger exited successfully'
    assert json_data['lounge_entry']['id'] == entry_id
    assert json_data['lounge_entry']['status'] == 'exited'
    assert json_data['lounge_entry']['exit_time'] is not None

    # Verify in DB
    with app.app_context():
        entry = LoungeEntry.query.get(entry_id)
        assert entry is not None
        assert entry.status == 'exited'
        assert entry.exit_time is not None
        # Ensure exit_time is close to what was sent (may need dateutil.parser for precision)
        # parsed_exit_time_db = entry.exit_time
        # parsed_exit_time_sent = datetime.fromisoformat(exit_time.replace('Z', '+00:00'))
        # assert abs((parsed_exit_time_db - parsed_exit_time_sent).total_seconds()) < 1 

def test_exit_passenger_already_exited(client, app, init_db):
    login_staff_user(client, "staff_pass_already_exit", "password")
    entry_res = client.post('/checkin', json={'passenger_name': 'Already Exited', 'flight_number': 'AE01'})
    entry_id = entry_res.get_json()['lounge_entry']['id']
    client.post(f'/passengers/{entry_id}/exit', json={}) # First exit

    # Attempt to exit again
    exit_response = client.post(f'/passengers/{entry_id}/exit', json={})
    assert exit_response.status_code == 400
    assert 'Passenger already exited' in exit_response.get_json()['message']

def test_exit_passenger_not_found(client, app, init_db):
    login_staff_user(client, "staff_pass_exit_notfound", "password")
    non_existent_entry_id = 99999
    response = client.post(f'/passengers/{non_existent_entry_id}/exit', json={})
    assert response.status_code == 404
    assert 'Lounge entry not found' in response.get_json()['message']

def test_exit_passenger_invalid_exit_time_format(client, app, init_db):
    login_staff_user(client, "staff_pass_exit_invalid_time", "password")
    entry_res = client.post('/checkin', json={'passenger_name': 'Exit Invalid Time', 'flight_number': 'EIT01'})
    entry_id = entry_res.get_json()['lounge_entry']['id']

    response = client.post(f'/passengers/{entry_id}/exit', json={'exit_time': 'not-a-date'})
    assert response.status_code == 400
    assert 'Invalid exit_time format' in response.get_json()['message']

def test_exit_passenger_unauthenticated(client, app):
    # No login
    response = client.post('/passengers/1/exit', json={}) # Assuming entry ID 1 might exist or not
    assert response.status_code == 401 # Requires login
    # If it was a GET route, Flask-Login might redirect to login page (302)
    # but for POST, it often returns 401 directly.
    # Verify based on your Flask-Login unauthorized handler.
