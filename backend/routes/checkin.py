from flask import Blueprint, request, jsonify
from flask_login import login_required
from backend.models import Passenger, LoungeEntry
from backend.database import db_session
import datetime

checkin_bp = Blueprint('checkin', __name__, url_prefix='/checkin')

@checkin_bp.route('', methods=['POST']) # Changed to empty string to match /checkin
@login_required
def check_in_passenger():
    data = request.get_json()
    passenger_name = data.get('passenger_name')
    flight_number = data.get('flight_number')
    # entry_time should ideally be UTC and set by the server, 
    # but allowing client to send for now if specific use case.
    # For robustness, consider validating or defaulting entry_time.
    entry_time_str = data.get('entry_time') 

    if not passenger_name or not flight_number:
        return jsonify({'message': 'Passenger name and flight number are required'}), 400

    try:
        entry_time = datetime.datetime.fromisoformat(entry_time_str) if entry_time_str else datetime.datetime.utcnow()
    except ValueError:
        return jsonify({'message': 'Invalid entry_time format. Use ISO format e.g. YYYY-MM-DDTHH:MM:SS'}), 400

    # Find or create passenger
    passenger = Passenger.query.filter_by(name=passenger_name, flight_number=flight_number).first()
    if not passenger:
        passenger = Passenger(name=passenger_name, flight_number=flight_number)
        db_session.add(passenger)
        # Committing here to get passenger.id for LoungeEntry, or can use flush
        # db_session.flush() 

    # Create LoungeEntry
    lounge_entry = LoungeEntry(
        # passenger_id=passenger.id, # This will be set by relationship if configured, or after commit
        passenger=passenger, # Assign the passenger object
        entry_time=entry_time,
        status='active'
    )
    db_session.add(lounge_entry)

    try:
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        return jsonify({'message': 'Failed to check-in passenger', 'error': str(e)}), 500

    return jsonify({
        'message': 'Passenger checked in successfully',
        'lounge_entry': {
            'id': lounge_entry.id,
            'passenger_name': passenger.name,
            'flight_number': passenger.flight_number,
            'entry_time': lounge_entry.entry_time.isoformat(),
            'status': lounge_entry.status
        }
    }), 201
