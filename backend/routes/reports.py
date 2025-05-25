from flask import Blueprint, request, jsonify
from flask_login import login_required
from backend.models import LoungeEntry
from backend.database import db_session
from sqlalchemy import func, cast, Date as SQLDate # Avoid conflict with Python's Date
from datetime import datetime, timedelta, date

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/lounge-usage', methods=['GET'])
@login_required
def get_lounge_usage_report():
    date_range_param = request.args.get('date_range', 'last_7_days') # Default to last 7 days
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    end_date = datetime.utcnow().date() 
    if end_date_str:
        try:
            end_date = datetime.fromisoformat(end_date_str).date()
        except ValueError:
            return jsonify({'message': 'Invalid end_date format. Use YYYY-MM-DD.'}), 400
    
    # Ensure end_date includes the entire day by setting time to end of day for comparisons
    end_datetime_for_query = datetime.combine(end_date, datetime.max.time())


    if start_date_str:
        try:
            start_date = datetime.fromisoformat(start_date_str).date()
        except ValueError:
            return jsonify({'message': 'Invalid start_date format. Use YYYY-MM-DD.'}), 400
    elif date_range_param == 'last_7_days':
        start_date = end_date - timedelta(days=6) # 7 days including today
    elif date_range_param == 'last_30_days':
        start_date = end_date - timedelta(days=29) # 30 days including today
    elif date_range_param == 'specific_month': # Example, you might need year and month params
        # This would need year and month parameters. For simplicity, not fully implemented.
        # For now, specific_month will just default to last 30 days.
        # start_date = datetime(end_date.year, end_date.month, 1).date()
        return jsonify({'message': 'Specific month not fully implemented, use start/end dates or other ranges.'}), 400
    else: # Default to last 7 days if invalid range_param and no start_date
        start_date = end_date - timedelta(days=6)

    # Ensure start_date has time at the beginning of the day for comparisons
    start_datetime_for_query = datetime.combine(start_date, datetime.min.time())

    # Query to group entries by date and count them
    # Using cast to SQLDate to group by date part of datetime field
    usage_data = db_session.query(
            cast(LoungeEntry.entry_time, SQLDate).label('entry_date'),
            func.count(LoungeEntry.id).label('total_entries')
        ).filter(
            LoungeEntry.entry_time >= start_datetime_for_query,
            LoungeEntry.entry_time <= end_datetime_for_query
        ).group_by(
            cast(LoungeEntry.entry_time, SQLDate)
        ).order_by(
            cast(LoungeEntry.entry_time, SQLDate)
        ).all()

    # Format data for response
    report_data = [
        {
            'date': entry.entry_date.isoformat(), 
            'total_entries': entry.total_entries
        } for entry in usage_data
    ]
    
    # Fill in missing dates with 0 entries
    # This makes the chart on the frontend more consistent.
    # Create a dictionary from the report_data for quick lookups
    data_map = {item['date']: item['total_entries'] for item in report_data}
    
    # Iterate from start_date to end_date
    current_date = start_date
    final_report = []
    while current_date <= end_date:
        iso_date = current_date.isoformat()
        final_report.append({
            'date': iso_date,
            'total_entries': data_map.get(iso_date, 0) # Get count or 0 if not present
        })
        current_date += timedelta(days=1)

    return jsonify({
        'report_name': 'Lounge Usage Over Time',
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'data': final_report
    }), 200
