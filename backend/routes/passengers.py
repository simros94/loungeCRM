from flask import Blueprint, request, jsonify
from flask_login import login_required
from backend.models import Passenger, LoungeEntry
from backend.database import db_session
from sqlalchemy import or_
import datetime

passengers_bp = Blueprint('passengers', __name__, url_prefix='/passengers')

@passengers_bp.route('', methods=['GET']) # Changed to empty string to match /passengers
@login_required
def get_passengers():
    search_query = request.args.get('search_query')
    
    query = db_session.query(Passenger).join(LoungeEntry)

    if search_query:
        query = query.filter(
            or_(
                Passenger.name.ilike(f"%{search_query}%"),
                Passenger.flight_number.ilike(f"%{search_query}%")
            )
        )
    
    # To optimize, consider what fields are truly needed.
    # This currently fetches all passengers matching and then all their entries.
    passengers_data = query.order_by(Passenger.name).all()
    
    result = []
    for p in passengers_data:
        entries = []
        # N+1 query potential here. If performance is an issue, consider joinedload or subqueryload.
        for entry in p.lounge_entries:
            entries.append({
                'id': entry.id,
                'entry_time': entry.entry_time.isoformat() if entry.entry_time else None,
                'exit_time': entry.exit_time.isoformat() if entry.exit_time else None,
                'status': entry.status
            })
        result.append({
            'id': p.id,
            'name': p.name,
            'flight_number': p.flight_number,
            'lounge_entries': sorted(entries, key=lambda x: x['entry_time'] or '', reverse=True) # Sort entries, most recent first
        })
        
    return jsonify(result), 200

@passengers_bp.route('/<int:entry_id>/exit', methods=['POST'])
@login_required
def exit_passenger(entry_id):
    data = request.get_json()
    exit_time_str = data.get('exit_time')

    lounge_entry = LoungeEntry.query.get(entry_id)

    if not lounge_entry:
        return jsonify({'message': 'Lounge entry not found'}), 404

    if lounge_entry.status == 'exited':
        return jsonify({'message': 'Passenger already exited'}), 400
    
    try:
        exit_time = datetime.datetime.fromisoformat(exit_time_str) if exit_time_str else datetime.datetime.utcnow()
    except ValueError:
        return jsonify({'message': 'Invalid exit_time format. Use ISO format e.g. YYYY-MM-DDTHH:MM:SS'}), 400

    lounge_entry.exit_time = exit_time
    lounge_entry.status = 'exited'
    
    try:
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        return jsonify({'message': 'Failed to update lounge entry', 'error': str(e)}), 500

    return jsonify({
        'message': 'Passenger exited successfully',
        'lounge_entry': {
            'id': lounge_entry.id,
            'passenger_id': lounge_entry.passenger_id,
            'entry_time': lounge_entry.entry_time.isoformat() if lounge_entry.entry_time else None,
            'exit_time': lounge_entry.exit_time.isoformat() if lounge_entry.exit_time else None,
            'status': lounge_entry.status
        }
    }), 200
