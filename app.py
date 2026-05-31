from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime, timedelta
import os
import jwt
import bcrypt

# ── Load environment variables ──
load_dotenv()

# ── Initialize Flask ──
app = Flask(__name__)
CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173"])

# ── Connect to MongoDB ──
client = MongoClient(os.getenv('MONGO_URI'))
db = client['smartintern']

# ── Collections ──
users = db['users']
internships = db['internships']

# ── Helper: Generate JWT Token ──
def generate_token(user_id):
    payload = {
        'user_id': str(user_id),
        'exp': datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, os.getenv('JWT_SECRET'), algorithm='HS256')

# ── Helper: Verify JWT Token ──
def verify_token(token):
    try:
        payload = jwt.decode(token, os.getenv('JWT_SECRET'), algorithms=['HS256'])
        return payload['user_id']
    except:
        return None

# ────────────────────────────────
# AUTH ROUTES
# ────────────────────────────────

# Register
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not name or not email or not password:
        return jsonify({'error': 'All fields are required'}), 400

    # Check if user already exists
    if users.find_one({'email': email}):
        return jsonify({'error': 'Email already registered'}), 400

    # Hash password
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # Save user
    user = {
        'name': name,
        'email': email,
        'password': hashed,
        'college': '',
        'degree': '',
        'year': '',
        'phone': '',
        'bio': '',
        'skills': [],
        'resume': None,
        'created_at': datetime.utcnow()
    }
    result = users.insert_one(user)
    token = generate_token(result.inserted_id)

    return jsonify({
        'message': 'Account created successfully',
        'token': token,
        'user': {
            'id': str(result.inserted_id),
            'name': name,
            'email': email
        }
    }), 201

# Login
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'All fields are required'}), 400

    # Find user
    user = users.find_one({'email': email})
    if not user:
        return jsonify({'error': 'Invalid email or password'}), 401

    # Check password
    if not bcrypt.checkpw(password.encode('utf-8'), user['password']):
        return jsonify({'error': 'Invalid email or password'}), 401

    token = generate_token(user['_id'])

    return jsonify({
        'message': 'Login successful',
        'token': token,
        'user': {
            'id': str(user['_id']),
            'name': user['name'],
            'email': user['email']
        }
    }), 200

# ────────────────────────────────
# INTERNSHIP ROUTES
# ────────────────────────────────

# Get all internships
@app.route('/api/internships', methods=['GET'])
def get_internships():
    query = request.args.get('q', '')
    location = request.args.get('location', '')

    filter = {}
    if query:
        filter['$or'] = [
            {'title': {'$regex': query, '$options': 'i'}},
            {'company': {'$regex': query, '$options': 'i'}},
            {'skills_required': {'$regex': query, '$options': 'i'}}
        ]
    if location:
        filter['location'] = {'$regex': location, '$options': 'i'}

    results = list(internships.find(filter))
    for r in results:
        r['_id'] = str(r['_id'])

    return jsonify(results), 200

# ────────────────────────────────
# USER ROUTES
# ────────────────────────────────

# Get user profile
@app.route('/api/profile', methods=['GET'])
def get_profile():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    user_id = verify_token(token)
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    from bson import ObjectId
    user = users.find_one({'_id': ObjectId(user_id)})
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user['_id'] = str(user['_id'])
    user.pop('password', None)

    return jsonify(user), 200

# Update user profile
@app.route('/api/profile', methods=['PUT'])
def update_profile():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    user_id = verify_token(token)
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    from bson import ObjectId
    data = request.json
    data.pop('password', None)
    data.pop('_id', None)

    users.update_one(
        {'_id': ObjectId(user_id)},
        {'$set': data}
    )

    return jsonify({'message': 'Profile updated successfully'}), 200

# ────────────────────────────────
# RUN APP
# ────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True, port=5000)