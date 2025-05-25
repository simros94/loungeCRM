from flask import Blueprint, request, jsonify
from flask_login import login_required
from backend.models import Reservation
from backend.database import db_session
from datetime import datetime, date, time # Ensure time is imported

reservations_bp = Blueprint('reservations', __name__, url_prefix='/reservations')

@reservations_bp.route('', methods=['POST']) # Changed to empty string to match /reservations
@login_required
def create_reservation():
    data = request.get_json()
    passenger_name = data.get('passenger_name')
    flight_number = data.get('flight_number')
    reservation_date_str = data.get('reservation_date')
    reservation_time_str = data.get('reservation_time')
    number_of_guests = data.get('number_of_guests', 1) # Default to 1 guest

    if not all([passenger_name, flight_number, reservation_date_str, reservation_time_str]):
        return jsonify({'message': 'Missing required fields (passenger_name, flight_number, reservation_date, reservation_time)'}), 400

    try:
        reservation_date = date.fromisoformat(reservation_date_str)
        # Correctly parse time string that might include HH:MM or HH:MM:SS
        hour, minute = map(int, reservation_time_str.split(':')[:2]) # Take only HH:MM part
        reservation_time = time(hour, minute)
    except ValueError:
        return jsonify({'message': 'Invalid date or time format. Use YYYY-MM-DD for date and HH:MM for time.'}), 400

    new_reservation = Reservation(
        passenger_name=passenger_name,
        flight_number=flight_number,
        reservation_date=reservation_date,
        reservation_time=reservation_time,
        number_of_guests=number_of_guests,
        status='confirmed'
    )
    db_session.add(new_reservation)
    try:
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        return jsonify({'message': 'Failed to create reservation', 'error': str(e)}), 500

    return jsonify({
        'message': 'Reservation created successfully',
        'reservation': {
            'id': new_reservation.id,
            'passenger_name': new_reservation.passenger_name,
            'flight_number': new_reservation.flight_number,
            'reservation_date': new_reservation.reservation_date.isoformat(),
            'reservation_time': new_reservation.reservation_time.isoformat(),
            'number_of_guests': new_reservation.number_of_guests,
            'status': new_reservation.status
        }
    }), 201

@reservations_bp.route('', methods=['GET']) # Changed to empty string to match /reservations
@login_required
def get_reservations():
    status_filter = request.args.get('status_filter') # e.g., 'upcoming', 'past', 'cancelled'
    
    query = Reservation.query
    today = date.today()

    if status_filter == 'upcoming':
        query = query.filter(
            Reservation.reservation_date >= today,
            Reservation.status == 'confirmed'
        )
    elif status_filter == 'past':
        query = query.filter(
            Reservation.reservation_date < today,
            # Or include 'completed' and 'confirmed' from past dates
            # (Reservation.status == 'completed') | ((Reservation.status == 'confirmed') & (Reservation.reservation_date < today))
        )
    elif status_filter == 'cancelled':
        query = query.filter(Reservation.status == 'cancelled')
    # No filter or unknown filter returns all reservations
    
    reservations_data = query.order_by(Reservation.reservation_date.desc(), Reservation.reservation_time.desc()).all()

    result = [
        {
            'id': r.id,
            'passenger_name': r.passenger_name,
            'flight_number': r.flight_number,
            'reservation_date': r.reservation_date.isoformat(),
            'reservation_time': r.reservation_time.isoformat(),
            'number_of_guests': r.number_of_guests,
            'status': r.status
        } for r in reservations_data
    ]
    return jsonify(result), 200

@reservations_bp.route('/<int:reservation_id>/status', methods=['PUT'])
@login_required
def update_reservation_status(reservation_id):
    data = request.get_json()
    new_status = data.get('new_status')

    if not new_status:
        return jsonify({'message': 'New status is required'}), 400
    
    # Validate new_status if necessary (e.g., against a list of allowed statuses)
    allowed_statuses = ['confirmed', 'cancelled', 'completed']
    if new_status not in allowed_statuses:
        return jsonify({'message': f'Invalid status. Allowed statuses are: {", ".join(allowed_statuses)}'}), 400

    reservation = Reservation.query.get(reservation_id)
    if not reservation:
        return jsonify({'message': 'Reservation not found'}), 404

    reservation.status = new_status
    try:
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        return jsonify({'message': 'Failed to update reservation status', 'error': str(e)}), 500

    return jsonify({
        'message': 'Reservation status updated successfully',
        'reservation': {
            'id': reservation.id,
            'status': reservation.status
        }
    }), 200
