from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from backend.models import User
from backend.database import db_session
from werkzeug.security import generate_password_hash

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'Username already exists'}), 400

    new_user = User(username=username)
    new_user.set_password(password) # Hash password
    db_session.add(new_user)
    db_session.commit()

    return jsonify({'message': 'User created successfully'}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        login_user(user)
        return jsonify({'message': 'Logged in successfully', 'user': {'username': user.username, 'role': user.role}}), 200
    
    return jsonify({'message': 'Invalid username or password'}), 401

@auth_bp.route('/logout', methods=['POST']) # Changed to POST as per best practices
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logged out successfully'}), 200

@auth_bp.route('/status', methods=['GET'])
@login_required
def status():
    if current_user.is_authenticated:
        return jsonify({'user': {'username': current_user.username, 'role': current_user.role}}), 200
    else:
        # This case might not be reachable if @login_required redirects unauthenticated users
        return jsonify({'message': 'No user is currently logged in'}), 401
