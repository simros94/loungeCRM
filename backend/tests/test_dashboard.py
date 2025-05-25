import pytest
from datetime import datetime, timedelta

# Helper to register and login a staff user
def login_staff_user(client, username="staff_dashboard", password="password"):
    reg_response = client.post('/auth/register', json={'username': username, 'password': password})
    assert reg_response.status_code in [201, 400] # Allow if user already exists
    login_response = client.post('/auth/login', json={'username': username, 'password': password})
    assert login_response.status_code == 200
    return login_response

def test_get_dashboard_stats_unauthenticated(client):
    response = client.get('/dashboard/stats')
    assert response.status_code == 401 # Requires login

def test_get_recent_entries_unauthenticated(client):
    response = client.get('/dashboard/recent-entries')
    assert response.status_code == 401 # Requires login

def test_get_dashboard_stats_empty(client, app, init_db): # init_db to ensure clean slate
    login_staff_user(client)
    response = client.get('/dashboard/stats')
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['current_occupancy'] == 0
    assert json_data['total_entries_today'] == 0
    assert json_data['average_stay_duration_minutes'] == 0

def test_get_recent_entries_empty(client, app, init_db):
    login_staff_user(client)
    response = client.get('/dashboard/recent-entries')
    assert response.status_code == 200
    json_data = response.get_json()
    assert isinstance(json_data, list)
    assert len(json_data) == 0

def test_get_dashboard_stats_with_data(client, app, init_db):
    login_staff_user(client, "staff_dash_data", "password")

    # Add some entries
    # Active entry from today
    client.post('/checkin', json={
        'passenger_name': 'Active Today', 
        'flight_number': 'AT1', 
        'entry_time': datetime.utcnow().isoformat()
    })
    # Active entry from yesterday (should not count as today's entry, but will be in occupancy)
    client.post('/checkin', json={
        'passenger_name': 'Active Yesterday', 
        'flight_number': 'AY1', 
        'entry_time': (datetime.utcnow() - timedelta(days=1)).isoformat()
    })
    # Exited entry from today
    entry_response = client.post('/checkin', json={
        'passenger_name': 'Exited Today', 
        'flight_number': 'ET1', 
        'entry_time': (datetime.utcnow() - timedelta(hours=2)).isoformat()
    })
    entry_id = entry_response.get_json()['lounge_entry']['id']
    client.post(f'/passengers/{entry_id}/exit', json={
        'exit_time': (datetime.utcnow() - timedelta(hours=1)).isoformat()
    })


    response = client.get('/dashboard/stats')
    assert response.status_code == 200
    json_data = response.get_json()
    
    assert json_data['current_occupancy'] == 2 # Active Today, Active Yesterday
    assert json_data['total_entries_today'] == 2 # Active Today, Exited Today
    
    # Average stay duration: Exited Today stayed for 1 hour (60 minutes)
    # Only one completed entry today, so avg should be 60.
    assert 'average_stay_duration_minutes' in json_data
    # Allow for small floating point inaccuracies if any, or if more complex calculations happen
    assert abs(json_data['average_stay_duration_minutes'] - 60.0) < 0.1 


def test_get_recent_entries_with_data(client, app, init_db):
    login_staff_user(client, "staff_recent_data", "password")

    # Add a few entries
    entry1_time = (datetime.utcnow() - timedelta(minutes=30)).isoformat()
    entry2_time = (datetime.utcnow() - timedelta(minutes=15)).isoformat()
    entry3_time = datetime.utcnow().isoformat() # Most recent

    client.post('/checkin', json={'passenger_name': 'Recent1', 'flight_number': 'R1', 'entry_time': entry1_time})
    client.post('/checkin', json={'passenger_name': 'Recent2', 'flight_number': 'R2', 'entry_time': entry2_time})
    client.post('/checkin', json={'passenger_name': 'Recent3', 'flight_number': 'R3', 'entry_time': entry3_time})

    response = client.get('/dashboard/recent-entries')
    assert response.status_code == 200
    json_data = response.get_json()
    
    assert isinstance(json_data, list)
    assert len(json_data) == 3
    
    # Entries should be ordered by entry_time desc
    assert json_data[0]['passenger_name'] == 'Recent3'
    assert json_data[1]['passenger_name'] == 'Recent2'
    assert json_data[2]['passenger_name'] == 'Recent1'
    
    assert json_data[0]['flight_number'] == 'R3'
    assert json_data[0]['status'] == 'active'
    # Verify entry_time format and value (optional, but good for sanity check)
    # parsed_entry_time = datetime.fromisoformat(json_data[0]['entry_time'].replace('Z', '+00:00')) # Handle Z for UTC
    # assert parsed_entry_time.minute == datetime.fromisoformat(entry3_time).minute # Rough check

    # Check that it limits to 10 entries if more are present
    for i in range(12): # Add 12 more entries
         client.post('/checkin', json={'passenger_name': f'Extra{i}', 'flight_number': f'EX{i}'})
    
    response_limited = client.get('/dashboard/recent-entries')
    assert response_limited.status_code == 200
    json_data_limited = response_limited.get_json()
    assert len(json_data_limited) == 10 # Default limit in endpoint is 10
    assert json_data_limited[0]['passenger_name'].startswith('Extra') # Newest should be 'Extra11' or similar
    assert json_data_limited[9]['passenger_name'] == 'Recent3' # Oldest of the 10 most recent shown
                                                            # (assuming Extra entries are newest)
                                                            # Actually, the order depends on the exact times.
                                                            # The important part is len == 10.
                                                            # And the first one is the most recent 'Extra'
    # The first one should be 'Extra11' if times are sequential
    assert json_data_limited[0]['passenger_name'] == 'Extra11'
    # The last one of the 10 would be 'Extra2'
    assert json_data_limited[9]['passenger_name'] == 'Extra2'
