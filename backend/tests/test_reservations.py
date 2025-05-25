import pytest
from backend.models import Reservation
from backend.database import db_session
from datetime import datetime, date, time, timedelta

# Helper to register and login a staff user
def login_staff_user(client, username="staff_reservations", password="password"):
    reg_response = client.post('/auth/register', json={'username': username, 'password': password})
    assert reg_response.status_code in [201, 400]
    login_response = client.post('/auth/login', json={'username': username, 'password': password})
    assert login_response.status_code == 200
    return login_response

def test_create_reservation_unauthenticated(client):
    response = client.post('/reservations', json={}) # Empty payload, will fail validation but auth first
    assert response.status_code == 401

def test_create_reservation_success(client, app, init_db):
    login_staff_user(client)
    
    reservation_data = {
        'passenger_name': 'Reserve User',
        'flight_number': 'RU001',
        'reservation_date': (date.today() + timedelta(days=5)).isoformat(),
        'reservation_time': '14:30', # HH:MM format
        'number_of_guests': 2
    }
    response = client.post('/reservations', json=reservation_data)
    
    assert response.status_code == 201
    json_data = response.get_json()
    assert json_data['message'] == 'Reservation created successfully'
    assert 'reservation' in json_data
    res_details = json_data['reservation']
    assert res_details['passenger_name'] == reservation_data['passenger_name']
    assert res_details['flight_number'] == reservation_data['flight_number']
    assert res_details['reservation_date'] == reservation_data['reservation_date']
    assert res_details['reservation_time'] == '14:30:00' # Backend stores with seconds
    assert res_details['number_of_guests'] == reservation_data['number_of_guests']
    assert res_details['status'] == 'confirmed'

    with app.app_context():
        db_reservation = Reservation.query.get(res_details['id'])
        assert db_reservation is not None
        assert db_reservation.passenger_name == reservation_data['passenger_name']

def test_create_reservation_missing_fields(client, app, init_db):
    login_staff_user(client)
    
    response = client.post('/reservations', json={
        'passenger_name': 'Missing Fields User'
        # Other fields missing
    })
    assert response.status_code == 400
    assert 'Missing required fields' in response.get_json()['message']

def test_create_reservation_invalid_date_time_format(client, app, init_db):
    login_staff_user(client)
    
    invalid_date_data = {
        'passenger_name': 'Invalid Date User',
        'flight_number': 'IDU001',
        'reservation_date': 'not-a-date',
        'reservation_time': '10:00'
    }
    response = client.post('/reservations', json=invalid_date_data)
    assert response.status_code == 400
    assert 'Invalid date or time format' in response.get_json()['message']

    invalid_time_data = {
        'passenger_name': 'Invalid Time User',
        'flight_number': 'ITU001',
        'reservation_date': date.today().isoformat(),
        'reservation_time': 'not-a-time'
    }
    response = client.post('/reservations', json=invalid_time_data)
    assert response.status_code == 400
    assert 'Invalid date or time format' in response.get_json()['message']


def test_get_reservations_unauthenticated(client):
    response = client.get('/reservations')
    assert response.status_code == 401

def test_get_reservations_empty(client, app, init_db):
    login_staff_user(client)
    response = client.get('/reservations')
    assert response.status_code == 200
    json_data = response.get_json()
    assert isinstance(json_data, list)
    assert len(json_data) == 0

def setup_reservations_data(client):
    # Upcoming
    client.post('/reservations', json={
        'passenger_name': 'Upcoming Res', 'flight_number': 'UP01', 
        'reservation_date': (date.today() + timedelta(days=3)).isoformat(), 'reservation_time': '10:00'
    })
    # Past (completed)
    past_res = client.post('/reservations', json={
        'passenger_name': 'Past Res', 'flight_number': 'PA01', 
        'reservation_date': (date.today() - timedelta(days=3)).isoformat(), 'reservation_time': '11:00'
    })
    past_res_id = past_res.get_json()['reservation']['id']
    client.put(f'/reservations/{past_res_id}/status', json={'new_status': 'completed'})
    
    # Cancelled
    cancelled_res = client.post('/reservations', json={
        'passenger_name': 'Cancelled Res', 'flight_number': 'CA01', 
        'reservation_date': (date.today() + timedelta(days=1)).isoformat(), 'reservation_time': '12:00'
    })
    cancelled_res_id = cancelled_res.get_json()['reservation']['id']
    client.put(f'/reservations/{cancelled_res_id}/status', json={'new_status': 'cancelled'})


def test_get_reservations_with_data_no_filter(client, app, init_db):
    login_staff_user(client, "staff_get_res_all", "password")
    setup_reservations_data(client)
    
    response = client.get('/reservations') # No filter means all
    assert response.status_code == 200
    json_data = response.get_json()
    assert len(json_data) == 3 # All three reservations

def test_get_reservations_filter_upcoming(client, app, init_db):
    login_staff_user(client, "staff_get_res_up", "password")
    setup_reservations_data(client) # Re-setup for this specific test context if needed

    response = client.get('/reservations?status_filter=upcoming')
    assert response.status_code == 200
    json_data = response.get_json()
    assert len(json_data) == 1
    assert json_data[0]['passenger_name'] == 'Upcoming Res'
    assert json_data[0]['status'] == 'confirmed' # Upcoming confirmed reservations

def test_get_reservations_filter_past(client, app, init_db):
    login_staff_user(client, "staff_get_res_past", "password")
    setup_reservations_data(client)

    response = client.get('/reservations?status_filter=past')
    assert response.status_code == 200
    json_data = response.get_json()
    # This filter is for dates < today. The "Past Res" was completed.
    # Depending on endpoint logic for "past", it might include "confirmed" ones from past too.
    # Current backend logic for 'past' is just `Reservation.reservation_date < today`.
    assert len(json_data) == 1
    assert json_data[0]['passenger_name'] == 'Past Res' 
    # Status could be 'completed' or 'confirmed' if it just passed without completion.
    # assert json_data[0]['status'] == 'completed' # if only completed are shown, or both

def test_get_reservations_filter_cancelled(client, app, init_db):
    login_staff_user(client, "staff_get_res_cancel", "password")
    setup_reservations_data(client)

    response = client.get('/reservations?status_filter=cancelled')
    assert response.status_code == 200
    json_data = response.get_json()
    assert len(json_data) == 1
    assert json_data[0]['passenger_name'] == 'Cancelled Res'
    assert json_data[0]['status'] == 'cancelled'

def test_update_reservation_status_unauthenticated(client):
    response = client.put('/reservations/1/status', json={}) # Dummy ID
    assert response.status_code == 401

def test_update_reservation_status_success(client, app, init_db):
    login_staff_user(client)
    
    # Create a reservation
    res_data = {
        'passenger_name': 'Status Update User', 'flight_number': 'SUU01',
        'reservation_date': (date.today() + timedelta(days=2)).isoformat(), 'reservation_time': '15:00'
    }
    create_res = client.post('/reservations', json=res_data)
    reservation_id = create_res.get_json()['reservation']['id']

    # Update status to 'cancelled'
    update_response = client.put(f'/reservations/{reservation_id}/status', json={'new_status': 'cancelled'})
    assert update_response.status_code == 200
    json_data = update_response.get_json()
    assert json_data['message'] == 'Reservation status updated successfully'
    assert json_data['reservation']['id'] == reservation_id
    assert json_data['reservation']['status'] == 'cancelled'

    with app.app_context():
        db_res = Reservation.query.get(reservation_id)
        assert db_res.status == 'cancelled'

def test_update_reservation_status_not_found(client, app, init_db):
    login_staff_user(client)
    non_existent_id = 9999
    response = client.put(f'/reservations/{non_existent_id}/status', json={'new_status': 'confirmed'})
    assert response.status_code == 404
    assert 'Reservation not found' in response.get_json()['message']

def test_update_reservation_status_missing_status(client, app, init_db):
    login_staff_user(client)
    # Create a reservation first
    res = client.post('/reservations', json={
        'passenger_name': 'Test Res', 'flight_number': 'TR01', 
        'reservation_date': date.today().isoformat(), 'reservation_time': '10:00'
    })
    res_id = res.get_json()['reservation']['id']
    
    response = client.put(f'/reservations/{res_id}/status', json={}) # Missing new_status
    assert response.status_code == 400
    assert 'New status is required' in response.get_json()['message']

def test_update_reservation_status_invalid_status(client, app, init_db):
    login_staff_user(client)
    # Create a reservation first
    res = client.post('/reservations', json={
        'passenger_name': 'Test Res Invalid', 'flight_number': 'TRI01', 
        'reservation_date': date.today().isoformat(), 'reservation_time': '11:00'
    })
    res_id = res.get_json()['reservation']['id']

    response = client.put(f'/reservations/{res_id}/status', json={'new_status': 'invalid_status_value'})
    assert response.status_code == 400
    assert 'Invalid status' in response.get_json()['message']
