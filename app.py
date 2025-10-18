from flask import Flask, request, jsonify, send_from_directory, redirect
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import json
import os
import uuid

app = Flask(__name__, static_folder='.')
CORS(app)

# MongoDB Configuration
client = MongoClient("mongodb+srv://nvk:618618to@cluster0.vfoknfd.mongodb.net/lms_db?retryWrites=true&w=majority&appName=Cluster0")
db = client['lms_db']
courses_collection = db['courses']
enrollments_collection = db['enrollments']
users_collection = db['users']

# Test MongoDB connection
try:
    client.admin.command('ping')
    print("✅ MongoDB connected successfully!")
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")

# Create uploads directory if it doesn't exist
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Custom JSON encoder to handle ObjectId
class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super(JSONEncoder, self).default(obj)

app.json_encoder = JSONEncoder

# DEBUG: Print current working directory and files
print(f"📁 Current working directory: {os.getcwd()}")
print("📄 Files in current directory:")
for file in os.listdir('.'):
    print(f"   - {file}")

# Serve uploaded files
@app.route('/uploads/<filename>')
def serve_file_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Student Routes
@app.route('/api/courses', methods=['GET'])
def get_courses():
    try:
        courses = list(courses_collection.find(
            {}, 
            {
                'title': 1, 
                'description': 1, 
                'teacher_name': 1, 
                'created_at': 1,
                '_id': 1
            }
        ).sort('created_at', -1))
        
        for course in courses:
            course['_id'] = str(course['_id'])
        return jsonify(courses)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/courses/<course_id>', methods=['GET'])
def get_course_details(course_id):
    try:
        course = courses_collection.find_one({'_id': ObjectId(course_id)})
        if course:
            course['_id'] = str(course['_id'])
            return jsonify(course)
        else:
            return jsonify({'error': 'Course not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/courses/enroll', methods=['POST'])
def enroll_course():
    try:
        data = request.json
        enrollment = {
            'student_id': data.get('student_id', 'default_student'),
            'course_id': data['course_id'],
            'course_title': data.get('course_title', ''),
            'enrolled_at': datetime.utcnow()
        }
        result = enrollments_collection.insert_one(enrollment)
        return jsonify({'message': 'Enrolled successfully', 'enrollment_id': str(result.inserted_id)}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Teacher Routes
@app.route('/api/courses/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        file.save(file_path)
        
        return jsonify({
            'message': 'File uploaded successfully',
            'filename': unique_filename,
            'original_name': file.filename,
            'file_url': f'/uploads/{unique_filename}'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/courses', methods=['POST'])
def create_course():
    try:
        data = request.json
        course = {
            'title': data['title'],
            'description': data['description'],
            'content': data.get('content', []),
            'created_at': datetime.utcnow(),
            'teacher_id': data.get('teacher_id', 'default_teacher'),
            'teacher_name': data.get('teacher_name', 'Teacher')
        }
        result = courses_collection.insert_one(course)
        
        course['_id'] = str(result.inserted_id)
        return jsonify({
            'message': 'Course created successfully',
            'course': course
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/courses/<course_id>', methods=['PUT'])
def update_course(course_id):
    try:
        data = request.json
        update_data = {
            'title': data.get('title'),
            'description': data.get('description'),
            'content': data.get('content'),
            'updated_at': datetime.utcnow()
        }
        
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        result = courses_collection.update_one(
            {'_id': ObjectId(course_id)},
            {'$set': update_data}
        )
        
        if result.modified_count > 0:
            return jsonify({'message': 'Course updated successfully'})
        else:
            return jsonify({'error': 'Course not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/courses/<course_id>', methods=['DELETE'])
def delete_course(course_id):
    try:
        course = courses_collection.find_one({'_id': ObjectId(course_id)})
        if course and 'content' in course:
            for file_data in course['content']:
                if 'filename' in file_data:
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_data['filename'])
                    if os.path.exists(file_path):
                        os.remove(file_path)
        
        result = courses_collection.delete_one({'_id': ObjectId(course_id)})
        if result.deleted_count > 0:
            enrollments_collection.delete_many({'course_id': course_id})
            return jsonify({'message': 'Course deleted successfully'})
        else:
            return jsonify({'error': 'Course not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/teacher/courses', methods=['GET'])
def get_teacher_courses():
    try:
        teacher_id = request.args.get('teacher_id', 'default_teacher')
        courses = list(courses_collection.find({'teacher_id': teacher_id}))
        for course in courses:
            course['_id'] = str(course['_id'])
        return jsonify(courses)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Main Application Routes - FIXED with DEBUG
@app.route('/')
def index():
    print("🔍 DEBUG: Serving index.html from root route")
    if os.path.exists('index.html'):
        print("✅ index.html exists, serving file")
        return send_from_directory('.', 'index.html')
    else:
        print("❌ index.html NOT FOUND!")
        return "index.html not found", 404

@app.route('/index.html')
def serve_index():
    print("🔍 DEBUG: Serving index.html from explicit route")
    return send_from_directory('.', 'index.html')

@app.route('/student-portal.html')
def student_portal():
    print("🔍 DEBUG: Serving student-portal.html")
    return send_from_directory('.', 'student-portal.html')

@app.route('/teacher-portal.html')
def teacher_portal():
    print("🔍 DEBUG: Serving teacher-portal.html")
    return send_from_directory('.', 'teacher-portal.html')

@app.route('/student')
def student_redirect():
    return redirect('/student-portal.html')

@app.route('/teacher')
def teacher_redirect():
    return redirect('/teacher-portal.html')

# Serve static files with better error handling
@app.route('/<path:filename>')
def serve_static(filename):
    print(f"🔍 DEBUG: Requested file: {filename}")
    
    # Check if file exists
    if os.path.exists(filename):
        print(f"✅ File {filename} exists, serving")
        return send_from_directory('.', filename)
    else:
        print(f"❌ File {filename} not found, serving index.html")
        # For any unknown route, serve index.html (SPA behavior)
        return send_from_directory('.', 'index.html')

# Health check
@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'message': 'LMS Server is running'})

if __name__ == '__main__':
    print("🚀 Starting CLEX LMS Server...")
    print("📚 Available Routes:")
    print("   - Main Page: http://localhost:5000")
    print("   - Student Portal: http://localhost:5000/student-portal.html")
    print("   - Teacher Portal: http://localhost:5000/teacher-portal.html")
    print("   - API Health: http://localhost:5000/health")
    app.run(debug=True, port=5000)