from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import requests as http_requests
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime, timedelta
import os
import jwt
import bcrypt
import random

# ── Load environment variables ──
load_dotenv()

# ── Initialize Flask ──
app = Flask(__name__)
CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173", "https://smartintern-ai.vercel.app"])


# ── Connect to MongoDB ──
client = MongoClient(os.getenv('MONGO_URI'))
db = client['smartintern']

# ── Collections ──
users = db['users']
internships = db['internships']
otp_store = db['otp_store']

# ── Uploads folder ──
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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

# STEP 1: Validate form + send OTP
@app.route('/api/send-otp', methods=['POST'])
def send_otp():
    import re
    data = request.json
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not name or not email or not password:
        return jsonify({'error': 'All fields are required'}), 400

    email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    if not re.match(email_regex, email):
        return jsonify({'error': 'Please enter a valid email address'}), 400

    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    if users.find_one({'email': email}):
        return jsonify({'error': 'Email already registered'}), 400

    otp = str(random.randint(100000, 999999))

    otp_store.delete_many({'email': email})
    otp_store.insert_one({
        'email': email,
        'otp': otp,
        'name': name,
        'password': password,
        'expires_at': datetime.utcnow() + timedelta(minutes=10)
    })

    try:
        response = http_requests.post(
            'https://api.brevo.com/v3/smtp/email',
            headers={
                'api-key': os.getenv('BREVO_API_KEY'),
                'Content-Type': 'application/json'
            },
            json={
                'sender': {'name': 'SmartIntern AI', 'email': os.getenv('MAIL_USERNAME')},
                'to': [{'email': email, 'name': name}],
                'subject': 'Your SmartIntern AI Verification Code',
                'htmlContent': f"""
                <div style="font-family: Arial, sans-serif; max-width: 480px; margin: auto; padding: 32px; border: 1px solid #e5e7eb; border-radius: 12px;">
                  <h2 style="color: #6366f1;">SmartIntern<span style="color:#111">AI</span> 🎓</h2>
                  <p>Hi <strong>{name}</strong>,</p>
                  <p>Use the code below to verify your email address:</p>
                  <div style="font-size: 36px; font-weight: bold; letter-spacing: 8px; color: #6366f1; text-align: center; margin: 24px 0; padding: 16px; background: #eef2ff; border-radius: 8px;">
                    {otp}
                  </div>
                  <p style="color: #6b7280; font-size: 14px;">This code expires in <strong>10 minutes</strong>. If you didn't request this, ignore this email.</p>
                </div>
                """
            }
        )
        if response.status_code not in (200, 201):
            return jsonify({'error': f'Email error: {response.text}'}), 500
    except Exception as e:
         return jsonify({'error': 'Failed to send email. Please try again.'}), 500

    return jsonify({'message': 'OTP sent to your email'}), 200


# STEP 2: Verify OTP + create account
@app.route('/api/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    email = data.get('email', '').strip().lower()
    otp = data.get('otp', '').strip()

    if not email or not otp:
        return jsonify({'error': 'Email and OTP are required'}), 400

    record = otp_store.find_one({'email': email})

    if not record:
        return jsonify({'error': 'OTP not found. Please register again.'}), 400

    if datetime.utcnow() > record['expires_at']:
        otp_store.delete_many({'email': email})
        return jsonify({'error': 'OTP has expired. Please register again.'}), 400

    if record['otp'] != otp:
        return jsonify({'error': 'Invalid OTP. Please try again.'}), 400

    if users.find_one({'email': email}):
        return jsonify({'error': 'Email already registered'}), 400

    hashed = bcrypt.hashpw(record['password'].encode('utf-8'), bcrypt.gensalt())

    user = {
        'name': record['name'],
        'email': email,
        'password': hashed,
        'college': '',
        'degree': '',
        'year': '',
        'phone': '',
        'bio': '',
        'skills': [],
        'resume': None,
        'resume_filename': None,
        'email_verified': True,
        'created_at': datetime.utcnow()
    }
    result = users.insert_one(user)
    otp_store.delete_many({'email': email})

    token = generate_token(result.inserted_id)
    return jsonify({
        'message': 'Account created successfully',
        'token': token,
        'user': {
            'id': str(result.inserted_id),
            'name': record['name'],
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

    user = users.find_one({'email': email})
    if not user:
        return jsonify({'error': 'Invalid email or password'}), 401

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
# RESUME ROUTES
# ────────────────────────────────

@app.route('/api/resume/upload', methods=['POST'])
def upload_resume():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    user_id = verify_token(token)
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    if 'resume' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['resume']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not file.filename.endswith('.pdf'):
        return jsonify({'error': 'Only PDF files are allowed'}), 400

    try:
        import tempfile, base64
        from resume_parser import extract_text_from_pdf
        from bson import ObjectId

        # Save temp file for parsing
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            tmp_path = tmp.name
            file.save(tmp_path)

        try:
            text = extract_text_from_pdf(tmp_path)
            # Read raw bytes and encode as base64 for MongoDB storage
            with open(tmp_path, 'rb') as f:
                pdf_base64 = base64.b64encode(f.read()).decode('utf-8')
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

        users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {
                'resume_text': text,
                'resume_pdf': pdf_base64,       # stored in MongoDB
                'resume_filename': file.filename,
                'resume_uploaded': True,
                'resume_updated_at': datetime.utcnow()
            }}
        )

        return jsonify({
            'message': 'Resume uploaded and parsed successfully',
            'text_length': len(text),
            'preview': text[:200]
        }), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Failed to parse resume'}), 500


@app.route('/api/resume/file', methods=['GET'])
def get_resume_file():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    user_id = verify_token(token)
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    import base64
    from bson import ObjectId
    from flask import Response

    user = users.find_one({'_id': ObjectId(user_id)})
    if not user or not user.get('resume_pdf'):
        return jsonify({'error': 'No resume found'}), 404

    pdf_bytes = base64.b64decode(user['resume_pdf'])
    return Response(
        pdf_bytes,
        mimetype='application/pdf',
        headers={'Content-Disposition': 'inline; filename=resume.pdf'}
    )


# ────────────────────────────────
# AI MATCHING ROUTES
# ────────────────────────────────

@app.route('/api/matches', methods=['GET'])
def get_matches():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    user_id = verify_token(token)
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    from bson import ObjectId
    from skill_matcher import match_resume_to_internships

    user = users.find_one({'_id': ObjectId(user_id)})
    if not user:
        return jsonify({'error': 'User not found'}), 404

    resume_text = user.get('resume_text', '')
    if not resume_text:
        return jsonify({'error': 'No resume uploaded yet'}), 400

    all_internships = list(internships.find())
    for i in all_internships:
        i['_id'] = str(i['_id'])

    matched = match_resume_to_internships(resume_text, all_internships)
    filtered = [m for m in matched if m['match_score'] >= 60]
    return jsonify(filtered[:10]), 200

# ────────────────────────────────
# RUN APP
# ────────────────────────────────
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
