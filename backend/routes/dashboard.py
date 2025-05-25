from flask import Blueprint, jsonify
from flask_login import login_required
from backend.models import LoungeEntry, Passenger
from backend.database import db_session
from sqlalchemy import func
from datetime import datetime, date, timedelta

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/stats', methods=['GET'])
@login_required
def get_dashboard_stats():
    current_occupancy = LoungeEntry.query.filter_by(status='active').count()
    
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())
    
    total_entries_today = LoungeEntry.query.filter(
        LoungeEntry.entry_time >= today_start,
        LoungeEntry.entry_time <= today_end
    ).count()

    # Average stay duration (simplified: for entries that ended today)
    completed_entries_today = LoungeEntry.query.filter(
        LoungeEntry.status == 'exited',
        LoungeEntry.exit_time >= today_start,
        LoungeEntry.exit_time <= today_end,
        LoungeEntry.entry_time.isnot(None), # Ensure entry_time is not null
        LoungeEntry.exit_time.isnot(None) # Ensure exit_time is not null
    ).all()

    total_duration_seconds = 0
    count_for_avg = 0
    if completed_entries_today:
        for entry in completed_entries_today:
            if entry.entry_time and entry.exit_time: # Redundant check, but safe
                duration = entry.exit_time - entry.entry_time
                total_duration_seconds += duration.total_seconds()
                count_for_avg +=1
    
    average_stay_duration_minutes = (total_duration_seconds / count_for_avg) / 60 if count_for_avg > 0 else 0

    return jsonify({
        'current_occupancy': current_occupancy,
        'total_entries_today': total_entries_today,
        'average_stay_duration_minutes': round(average_stay_duration_minutes, 2)
    }), 200

@dashboard_bp.route('/recent-entries', methods=['GET'])
@login_required
def get_recent_entries():
    # Fetch last 10 entries, joining with Passenger to get names
    recent_entries_data = db_session.query(
        LoungeEntry.id,
        Passenger.name.label('passenger_name'),
        Passenger.flight_number,
        LoungeEntry.entry_time,
        LoungeEntry.status
    ).join(Passenger, LoungeEntry.passenger_id == Passenger.id)\
    .order_by(LoungeEntry.entry_time.desc())\
    .limit(10)\
    .all()

    recent_entries_list = [
        {
            'id': entry.id,
            'passenger_name': entry.passenger_name,
            'flight_number': entry.flight_number,
            'entry_time': entry.entry_time.isoformat() if entry.entry_time else None,
            'status': entry.status
        } for entry in recent_entries_data
    ]

    return jsonify(recent_entries_list), 200
