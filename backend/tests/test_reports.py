import pytest
from datetime import datetime, date, timedelta

# Helper to register and login a staff user
def login_staff_user(client, username="staff_reports", password="password"):
    reg_response = client.post('/auth/register', json={'username': username, 'password': password})
    assert reg_response.status_code in [201, 400]
    login_response = client.post('/auth/login', json={'username': username, 'password': password})
    assert login_response.status_code == 200
    return login_response

def setup_lounge_entries_for_reports(client):
    # Today's entries
    client.post('/checkin', json={'passenger_name': 'Today Entry 1', 'flight_number': 'RPT01', 'entry_time': datetime.utcnow().isoformat()})
    client.post('/checkin', json={'passenger_name': 'Today Entry 2', 'flight_number': 'RPT02', 'entry_time': (datetime.utcnow() - timedelta(hours=1)).isoformat()})

    # Yesterday's entries
    client.post('/checkin', json={'passenger_name': 'Yesterday Entry 1', 'flight_number': 'RPY01', 'entry_time': (datetime.utcnow() - timedelta(days=1, hours=2)).isoformat()})
    
    # 5 days ago entries
    client.post('/checkin', json={'passenger_name': '5 Days Ago Entry', 'flight_number': 'RPF01', 'entry_time': (datetime.utcnow() - timedelta(days=5)).isoformat()})
    
    # 10 days ago entries
    client.post('/checkin', json={'passenger_name': '10 Days Ago Entry', 'flight_number': 'RPTEN01', 'entry_time': (datetime.utcnow() - timedelta(days=10)).isoformat()})


def test_get_lounge_usage_report_unauthenticated(client):
    response = client.get('/reports/lounge-usage')
    assert response.status_code == 401

def test_get_lounge_usage_report_default_last_7_days(client, app, init_db):
    login_staff_user(client)
    setup_lounge_entries_for_reports(client)

    response = client.get('/reports/lounge-usage') # Default is last_7_days
    assert response.status_code == 200
    json_data = response.get_json()
    
    assert json_data['report_name'] == 'Lounge Usage Over Time'
    # Expected entries: Today (2), Yesterday (1), 5 Days Ago (1) = 4 entries in data list over 7 days
    # The data array will have 7 items, one for each day in the range.
    assert len(json_data['data']) == 7 
    
    total_entries_in_report = sum(item['total_entries'] for item in json_data['data'])
    assert total_entries_in_report == 4

    # Check today's count specifically (last item in the list for default range ending today)
    today_str = date.today().isoformat()
    today_data = next((item for item in json_data['data'] if item['date'] == today_str), None)
    assert today_data is not None
    assert today_data['total_entries'] == 2
    
    yesterday_str = (date.today() - timedelta(days=1)).isoformat()
    yesterday_data = next((item for item in json_data['data'] if item['date'] == yesterday_str), None)
    assert yesterday_data is not None
    assert yesterday_data['total_entries'] == 1

    five_days_ago_str = (date.today() - timedelta(days=5)).isoformat()
    five_days_ago_data = next((item for item in json_data['data'] if item['date'] == five_days_ago_str), None)
    assert five_days_ago_data is not None
    assert five_days_ago_data['total_entries'] == 1
    
    # 10 days ago entry should not be in last_7_days report
    ten_days_ago_str = (date.today() - timedelta(days=10)).isoformat()
    ten_days_ago_data = next((item for item in json_data['data'] if item['date'] == ten_days_ago_str), None)
    assert ten_days_ago_data is None


def test_get_lounge_usage_report_last_30_days(client, app, init_db):
    login_staff_user(client, "staff_reports_30d", "password")
    setup_lounge_entries_for_reports(client)

    response = client.get('/reports/lounge-usage?date_range=last_30_days')
    assert response.status_code == 200
    json_data = response.get_json()
    assert len(json_data['data']) == 30
    # Expected: Today (2), Yesterday (1), 5 Days Ago (1), 10 Days Ago (1) = 5 entries
    total_entries_in_report = sum(item['total_entries'] for item in json_data['data'])
    assert total_entries_in_report == 5

def test_get_lounge_usage_report_custom_date_range(client, app, init_db):
    login_staff_user(client, "staff_reports_custom", "password")
    setup_lounge_entries_for_reports(client)

    start_date_str = (date.today() - timedelta(days=6)).isoformat() # Covers 5 days ago and yesterday
    end_date_str = (date.today() - timedelta(days=1)).isoformat() # Covers yesterday, but not today

    response = client.get(f'/reports/lounge-usage?start_date={start_date_str}&end_date={end_date_str}')
    assert response.status_code == 200
    json_data = response.get_json()
    
    # Range from 6 days ago to 1 day ago is 6 days inclusive.
    assert len(json_data['data']) == 6 
    # Expected: Yesterday (1), 5 Days Ago (1) = 2 entries
    total_entries_in_report = sum(item['total_entries'] for item in json_data['data'])
    assert total_entries_in_report == 2

    # Check that today's entries are NOT included
    today_str = date.today().isoformat()
    assert not any(item['date'] == today_str and item['total_entries'] > 0 for item in json_data['data'])
    
    # Check that 10 days ago entries are NOT included
    ten_days_ago_str = (date.today() - timedelta(days=10)).isoformat()
    assert not any(item['date'] == ten_days_ago_str and item['total_entries'] > 0 for item in json_data['data'])


def test_get_lounge_usage_report_invalid_date_format(client, app, init_db):
    login_staff_user(client)
    response = client.get('/reports/lounge-usage?start_date=invalid-date&end_date=invalid-date-too')
    assert response.status_code == 400
    assert 'Invalid start_date format' in response.get_json()['message'] # Or similar depending on which it checks first

    response_end_date = client.get(f'/reports/lounge-usage?start_date={(date.today()-timedelta(days=1)).isoformat()}&end_date=invalid-date-too')
    assert response_end_date.status_code == 400
    assert 'Invalid end_date format' in response_end_date.get_json()['message']


def test_get_lounge_usage_report_no_data_in_range(client, app, init_db):
    login_staff_user(client)
    # No entries set up for this test specifically.
    
    start_date_str = (date.today() - timedelta(days=50)).isoformat()
    end_date_str = (date.today() - timedelta(days=40)).isoformat()
    
    response = client.get(f'/reports/lounge-usage?start_date={start_date_str}&end_date={end_date_str}')
    assert response.status_code == 200
    json_data = response.get_json()
    # Data array will have items for each day in the range, but all total_entries will be 0.
    assert len(json_data['data']) == 11 # 50 days ago to 40 days ago inclusive
    total_entries_in_report = sum(item['total_entries'] for item in json_data['data'])
    assert total_entries_in_report == 0
