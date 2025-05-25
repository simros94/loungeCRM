from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user # current_user for role checks
from backend.models import LoungeSetting, User
from backend.database import db_session
from werkzeug.security import generate_password_hash

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

# Decorator for admin-only routes (example)
def admin_required(fn):
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.role == 'admin': # Assuming User model has a 'role' attribute
            return jsonify({'message': 'Admin access required'}), 403
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__ # Preserve original function name for Flask
    return wrapper

@settings_bp.route('/lounge', methods=['GET'])
@login_required # All settings routes should require login
def get_lounge_settings():
    settings = LoungeSetting.query.first()
    if not settings:
        # Return default settings if none are in the DB
        return jsonify({
            'lounge_name': 'Prima Vista Lounge',
            'lounge_address': '',
            'lounge_capacity': 0,
            'entry_tracking_method': 'manual'
        }), 200
    return jsonify({
        'id': settings.id,
        'lounge_name': settings.lounge_name,
        'lounge_address': settings.lounge_address,
        'lounge_capacity': settings.lounge_capacity,
        'entry_tracking_method': settings.entry_tracking_method
    }), 200

@settings_bp.route('/lounge', methods=['POST'])
@admin_required # Modifying settings should be admin-only
def update_lounge_settings():
    data = request.get_json()
    settings = LoungeSetting.query.first()
    if not settings:
        settings = LoungeSetting() # Create new if none exist
        db_session.add(settings)

    settings.lounge_name = data.get('lounge_name', settings.lounge_name)
    settings.lounge_address = data.get('lounge_address', settings.lounge_address)
    settings.lounge_capacity = data.get('lounge_capacity', settings.lounge_capacity)
    settings.entry_tracking_method = data.get('entry_tracking_method', settings.entry_tracking_method)
    
    try:
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        return jsonify({'message': 'Failed to update lounge settings', 'error': str(e)}), 500
    return jsonify({'message': 'Lounge settings updated successfully'}), 200

@settings_bp.route('/users', methods=['GET'])
@admin_required # Viewing all users should be admin-only
def get_users():
    users = User.query.all()
    users_data = [{
        'id': user.id, 
        'username': user.username, 
        'role': user.role
        # Add 'is_active' if implemented in User model
        # 'is_active': user.is_active 
    } for user in users]
    return jsonify(users_data), 200

@settings_bp.route('/users', methods=['POST'])
@admin_required # Creating users should be admin-only
def create_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'staff') # Default role to 'staff'

    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'Username already exists'}), 400

    new_user = User(username=username, role=role)
    new_user.set_password(password) # Hashes the password
    # If User model has 'is_active', set it here: new_user.is_active = True
    
    db_session.add(new_user)
    try:
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        return jsonify({'message': 'Failed to create user', 'error': str(e)}), 500
        
    return jsonify({
        'message': 'User created successfully',
        'user': {'id': new_user.id, 'username': new_user.username, 'role': new_user.role}
    }), 201

@settings_bp.route('/users/<int:user_id>', methods=['PUT'])
@admin_required # Updating users should be admin-only
def update_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404

    data = request.get_json()
    user.username = data.get('username', user.username)
    user.role = data.get('role', user.role)
    # Handle 'is_active' status if implemented
    # if 'is_active' in data: user.is_active = data.get('is_active')

    if 'password' in data and data['password']: # Check for non-empty password
        user.set_password(data['password'])
    
    try:
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        return jsonify({'message': 'Failed to update user', 'error': str(e)}), 500

    return jsonify({
        'message': 'User updated successfully',
        'user': {'id': user.id, 'username': user.username, 'role': user.role}
    }), 200
