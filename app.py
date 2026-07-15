import sqlite3
import os
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'studyspace_secure_key_2026'
DATABASE = 'database.db'

# ==========================================================================
# Database Connection Helpers
# ==========================================================================
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row  # Access columns by name
    return db

@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    cur.close()

# ==========================================================================
# Authentication Helpers
# ==========================================================================
def login_required(role=None):
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                flash('Access denied. Insufficient permissions.', 'error')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ==========================================================================
# Root Route Redirector
# ==========================================================================
@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# ==========================================================================
# User Registration and Session Routes
# ==========================================================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password')
        role = request.form.get('role')
        
        if not name or not email or not password or not role:
            flash('All registration fields are required.', 'error')
            return render_template('register.html', active_page='register')
            
        hashed_password = generate_password_hash(password)
        
        try:
            execute_db(
                "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                (name, email, hashed_password, role)
            )
            flash('Registration successful! Please login below.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('An account with this email already exists.', 'error')
            
    return render_template('register.html', active_page='register')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password')
        
        user = query_db("SELECT * FROM users WHERE email = ?", (email,), one=True)
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['user_id']
            session['name'] = user['name']
            session['role'] = user['role']
            flash(f'Welcome back, {user["name"]}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password. Please try again.', 'error')
            
    return render_template('login.html', active_page='login')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

# ==========================================================================
# Student Dashboard
# ==========================================================================
@app.route('/dashboard')
@login_required(role='student')
def dashboard():
    user_id = session['user_id']
    
    # 1. Total bookings count
    total_bookings = query_db(
        "SELECT COUNT(*) FROM bookings WHERE user_id = ?", 
        (user_id,), one=True
    )[0]
    
    # 2. Upcoming bookings count (approved or pending from today onwards)
    today_str = date.today().strftime("%Y-%m-%d")
    upcoming_bookings = query_db(
        "SELECT COUNT(*) FROM bookings WHERE user_id = ? AND booking_date >= ? AND status IN ('Approved', 'Pending')",
        (user_id, today_str), one=True
    )[0]
    
    # 3. Available classrooms count (rooms currently set as 'Available')
    available_classrooms = query_db(
        "SELECT COUNT(*) FROM classrooms WHERE status = 'Available'", one=True
    )[0]
    
    stats = {
        'total_bookings': total_bookings,
        'upcoming_bookings': upcoming_bookings,
        'available_classrooms': available_classrooms
    }
    
    # 4. Upcoming booking list
    upcoming_list = query_db(
        """SELECT b.*, c.room_number, c.building 
           FROM bookings b 
           JOIN classrooms c ON b.room_id = c.room_id 
           WHERE b.user_id = ? AND b.booking_date >= ? AND b.status IN ('Approved', 'Pending')
           ORDER BY b.booking_date ASC, b.start_time ASC""",
        (user_id, today_str)
    )
    
    # 5. Recent Activity logs
    recent_activity = query_db(
        """SELECT b.*, c.room_number 
           FROM bookings b 
           JOIN classrooms c ON b.room_id = c.room_id 
           WHERE b.user_id = ? 
           ORDER BY b.booking_id DESC LIMIT 5""",
        (user_id,)
    )
    
    return render_template(
        'dashboard.html', 
        stats=stats, 
        upcoming_list=upcoming_list, 
        recent_activity=recent_activity,
        active_page='dashboard'
    )

# ==========================================================================
# Classroom Search & Filter
# ==========================================================================
@app.route('/classrooms')
@login_required()
def classrooms():
    # Fetch filter criteria from GET params
    room_number = request.args.get('room_number', '').strip()
    building = request.args.get('building', '')
    room_type = request.args.get('room_type', '')
    min_capacity = request.args.get('min_capacity', '')
    projector = request.args.get('projector')
    ac = request.args.get('ac')
    status = request.args.get('status')
    
    # Build dynamic search query
    query = "SELECT * FROM classrooms WHERE 1=1"
    params = []
    
    if room_number:
        query += " AND room_number LIKE ?"
        params.append(f"%{room_number}%")
    if building:
        query += " AND building = ?"
        params.append(building)
    if room_type:
        query += " AND room_type = ?"
        params.append(room_type)
    if min_capacity:
        query += " AND capacity >= ?"
        params.append(int(min_capacity))
    if projector:
        query += " AND projector = 1"
    if ac:
        query += " AND ac = 1"
    if status:
        query += " AND status = ?"
        params.append(status)
        
    query += " ORDER BY room_number ASC"
    rooms = query_db(query, params)
    
    # Fetch distinct categories for dynamic filter menus
    buildings = [r['building'] for r in query_db("SELECT DISTINCT building FROM classrooms ORDER BY building")]
    room_types = [r['room_type'] for r in query_db("SELECT DISTINCT room_type FROM classrooms ORDER BY room_type")]
    
    filters = {
        'room_number': room_number,
        'building': building,
        'room_type': room_type,
        'min_capacity': min_capacity,
        'projector': projector,
        'ac': ac,
        'status': status
    }
    
    return render_template(
        'classrooms.html',
        classrooms=rooms,
        buildings=buildings,
        room_types=room_types,
        filters=filters,
        active_page='classrooms'
    )

# ==========================================================================
# Classroom Booking System & Overlap Checking Logic
# ==========================================================================
@app.route('/book/<int:room_id>', methods=['GET', 'POST'])
@login_required(role='student')
def book(room_id):
    classroom = query_db("SELECT * FROM classrooms WHERE room_id = ?", (room_id,), one=True)
    if not classroom:
        flash('The requested classroom does not exist.', 'error')
        return redirect(url_for('classrooms'))
        
    # Get today's details for availability calculations
    today = date.today()
    today_str = today.strftime("%Y-%m-%d")
    day_of_week = today.strftime("%A")
    now_time_str = datetime.now().strftime("%H:%M")
    
    if request.method == 'POST':
        booking_date = request.form.get('booking_date')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        purpose = request.form.get('purpose', '').strip()
        
        form_data = {
            'booking_date': booking_date,
            'start_time': start_time,
            'end_time': end_time,
            'purpose': purpose
        }
        
        # Validation checks
        # 1. Start time must be before end time
        if start_time >= end_time:
            error_msg = "Invalid range: End time must be chronologically after the start time."
            return render_template('booking.html', classroom=classroom, booking_error=error_msg, form_data=form_data)
            
        # 2. Date/time must not be in the past
        if booking_date < today_str:
            error_msg = "Invalid date: You cannot request bookings for dates in the past."
            return render_template('booking.html', classroom=classroom, booking_error=error_msg, form_data=form_data)
        elif booking_date == today_str and start_time < now_time_str:
            error_msg = f"Invalid time: The selected slot starts in the past (Current time is {now_time_str})."
            return render_template('booking.html', classroom=classroom, booking_error=error_msg, form_data=form_data)
            
        # 3. Check for timetable overlaps
        booking_datetime = datetime.strptime(booking_date, "%Y-%m-%d")
        booking_day = booking_datetime.strftime("%A")
        
        timetable_overlap = query_db(
            """SELECT * FROM timetable 
               WHERE room_id = ? AND day = ? AND start_time < ? AND end_time > ?""",
            (room_id, booking_day, end_time, start_time), one=True
        )
        
        # 4. Check for approved student booking overlaps
        booking_overlap = query_db(
            """SELECT * FROM bookings 
               WHERE room_id = ? AND booking_date = ? AND status = 'Approved' AND start_time < ? AND end_time > ?""",
            (room_id, booking_date, end_time, start_time), one=True
        )
        
        if timetable_overlap or booking_overlap:
            # Overlap exists! Prevent booking and query alternatives.
            # Alternatives are rooms of the same type OR building that do not overlap during this specific time slot
            alternatives = query_db(
                """SELECT * FROM classrooms 
                   WHERE room_id != ? 
                     AND status = 'Available'
                     AND (building = ? OR room_type = ?)""",
                (room_id, classroom['building'], classroom['room_type'])
            )
            
            free_alternatives = []
            for alt in alternatives:
                # Timetable check for alternative room
                alt_t_check = query_db(
                    "SELECT COUNT(*) FROM timetable WHERE room_id = ? AND day = ? AND start_time < ? AND end_time > ?",
                    (alt['room_id'], booking_day, end_time, start_time), one=True
                )[0]
                
                # Booking check for alternative room
                alt_b_check = query_db(
                    "SELECT COUNT(*) FROM bookings WHERE room_id = ? AND booking_date = ? AND status = 'Approved' AND start_time < ? AND end_time > ?",
                    (alt['room_id'], booking_date, end_time, start_time), one=True
                )[0]
                
                if alt_t_check == 0 and alt_b_check == 0:
                    free_alternatives.append(alt)
                    if len(free_alternatives) >= 3:
                        break
                        
            error_msg = f"Double Booking Conflict! This classroom is already scheduled for another event or class during {start_time} - {end_time}."
            return render_template(
                'booking.html', 
                classroom=classroom, 
                booking_error=error_msg, 
                form_data=form_data, 
                alternatives=free_alternatives
            )
            
        # No conflict! Proceed to request booking
        execute_db(
            """INSERT INTO bookings (user_id, room_id, booking_date, start_time, end_time, purpose, status) 
               VALUES (?, ?, ?, ?, ?, ?, 'Pending')""",
            (session['user_id'], room_id, booking_date, start_time, end_time, purpose)
        )
        flash('Booking request submitted successfully! Awaiting administrator approval.', 'success')
        return redirect(url_for('history'))
        
    # GET Request: Determine dynamic "Available Until" and display details
    # Gather today's timetable classes
    today_timetable = query_db(
        "SELECT * FROM timetable WHERE room_id = ? AND day = ? ORDER BY start_time ASC",
        (room_id, day_of_week)
    )
    
    # Gather today's approved bookings
    today_bookings = query_db(
        "SELECT * FROM bookings WHERE room_id = ? AND booking_date = ? AND status = 'Approved' ORDER BY start_time ASC",
        (room_id, today_str)
    )
    
    # Combine busy slots to calculate "Available Until"
    busy_slots = []
    for slot in today_timetable:
        busy_slots.append({'start': slot['start_time'], 'end': slot['end_time']})
    for slot in today_bookings:
        busy_slots.append({'start': slot['start_time'], 'end': slot['end_time']})
        
    busy_slots = sorted(busy_slots, key=lambda x: x['start'])
    
    # Calculate available until
    available_until = "the end of the day"
    for slot in busy_slots:
        if slot['start'] > now_time_str:
            available_until = slot['start']
            break
            
    # Pre-fill suggestions if date/times are passed as URL queries
    url_date = request.args.get('date')
    url_start = request.args.get('start')
    url_end = request.args.get('end')
    
    form_data = {
        'booking_date': url_date or today_str,
        'start_time': url_start or '',
        'end_time': url_end or '',
        'purpose': ''
    }
    
    return render_template(
        'booking.html', 
        classroom=classroom, 
        today_timetable=today_timetable, 
        available_until=available_until,
        form_data=form_data
    )

# ==========================================================================
# Live Availability REST API (Helper for interactive frontend checking)
# ==========================================================================
@app.route('/api/check-availability')
def api_check_availability():
    room_id = request.args.get('room_id')
    booking_date = request.args.get('date')
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    
    if not room_id or not booking_date or not start_time or not end_time:
        return jsonify({'error': 'Missing parameters'}), 400
        
    booking_datetime = datetime.strptime(booking_date, "%Y-%m-%d")
    booking_day = booking_datetime.strftime("%A")
    
    # 1. Timetable overlap
    t_overlap = query_db(
        "SELECT COUNT(*) FROM timetable WHERE room_id = ? AND day = ? AND start_time < ? AND end_time > ?",
        (room_id, booking_day, end_time, start_time), one=True
    )[0]
    
    # 2. Approved bookings overlap
    b_overlap = query_db(
        "SELECT COUNT(*) FROM bookings WHERE room_id = ? AND booking_date = ? AND status = 'Approved' AND start_time < ? AND end_time > ?",
        (room_id, booking_date, end_time, start_time), one=True
    )[0]
    
    available = (t_overlap == 0 and b_overlap == 0)
    
    suggestion = None
    if not available:
        # Find one alternative
        alt = query_db(
            """SELECT room_id, room_number, building FROM classrooms 
               WHERE room_id != ? AND status = 'Available' LIMIT 1""",
            (room_id,), one=True
        )
        if alt:
            suggestion = {
                'room_id': alt['room_id'],
                'room_number': alt['room_number'],
                'building': alt['building']
            }
            
    return jsonify({
        'available': available,
        'suggestion': suggestion
    })

# ==========================================================================
# Booking History and Cancellation
# ==========================================================================
@app.route('/history')
@login_required(role='student')
def history():
    user_id = session['user_id']
    
    bookings_list = query_db(
        """SELECT b.*, c.room_number, c.building, c.floor 
           FROM bookings b 
           JOIN classrooms c ON b.room_id = c.room_id 
           WHERE b.user_id = ? 
           ORDER BY b.booking_date DESC, b.start_time DESC""",
        (user_id,)
    )
    
    return render_template('history.html', bookings=bookings_list, active_page='history')

@app.route('/bookings/cancel/<int:booking_id>')
@login_required()
def cancel_booking(booking_id):
    # Fetch booking
    booking = query_db("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,), one=True)
    if not booking:
        flash('Booking not found.', 'error')
        return redirect(url_for('index'))
        
    # Check permissions (only creator or administrator can cancel)
    if session.get('role') != 'admin' and booking['user_id'] != session.get('user_id'):
        flash('Unauthorized cancellation request.', 'error')
        return redirect(url_for('index'))
        
    # Cancel / delete booking
    execute_db("DELETE FROM bookings WHERE booking_id = ?", (booking_id,))
    flash('Booking cancelled successfully.', 'success')
    
    # Check redirect path
    redirect_target = request.args.get('redirect', 'history')
    if redirect_target == 'dashboard':
        return redirect(url_for('dashboard'))
    elif redirect_target == 'admin_dashboard':
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('history'))

# ==========================================================================
# Profile Settings Edit
# ==========================================================================
@app.route('/profile', methods=['GET', 'POST'])
@login_required()
def profile():
    user_id = session['user_id']
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password')
        
        if not name or not email:
            flash('Name and Email are required.', 'error')
            return redirect(url_for('profile'))
            
        try:
            # Check duplicate email
            duplicate = query_db("SELECT * FROM users WHERE email = ? AND user_id != ?", (email, user_id), one=True)
            if duplicate:
                flash('This email address is already in use by another user.', 'error')
                return redirect(url_for('profile'))
                
            # Update user info
            if password:
                hashed_pass = generate_password_hash(password)
                execute_db(
                    "UPDATE users SET name = ?, email = ?, password = ? WHERE user_id = ?",
                    (name, email, hashed_pass, user_id)
                )
            else:
                execute_db(
                    "UPDATE users SET name = ?, email = ? WHERE user_id = ?",
                    (name, email, user_id)
                )
                
            session['name'] = name
            flash('Profile updated successfully!', 'success')
        except Exception as e:
            flash('An error occurred while updating profile.', 'error')
            
        return redirect(url_for('profile'))
        
    user_info = query_db("SELECT * FROM users WHERE user_id = ?", (user_id,), one=True)
    return render_template('profile.html', user=user_info, active_page='profile')

# ==========================================================================
# Admin Control Panel Dashboard
# ==========================================================================
@app.route('/admin_dashboard', methods=['GET'])
@login_required(role='admin')
def admin_dashboard():
    # Gather statistics
    total_classrooms = query_db("SELECT COUNT(*) FROM classrooms", one=True)[0]
    total_students = query_db("SELECT COUNT(*) FROM users WHERE role='student'", one=True)[0]
    total_bookings = query_db("SELECT COUNT(*) FROM bookings", one=True)[0]
    available_rooms = query_db("SELECT COUNT(*) FROM classrooms WHERE status='Available'", one=True)[0]
    occupied_rooms = query_db("SELECT COUNT(*) FROM classrooms WHERE status != 'Available'", one=True)[0]
    
    stats = {
        'total_classrooms': total_classrooms,
        'total_students': total_students,
        'total_bookings': total_bookings,
        'available_rooms': available_rooms,
        'occupied_rooms': occupied_rooms
    }
    
    # Retrieve lists for lists
    all_classrooms = query_db("SELECT * FROM classrooms ORDER BY room_number ASC")
    
    all_timetables = query_db(
        """SELECT t.*, c.room_number, c.building 
           FROM timetable t 
           JOIN classrooms c ON t.room_id = c.room_id 
           ORDER BY c.room_number ASC, t.day ASC, t.start_time ASC"""
    )
    
    all_bookings = query_db(
        """SELECT b.*, u.name AS user_name, u.email AS user_email, c.room_number, c.building 
           FROM bookings b 
           JOIN users u ON b.user_id = u.user_id 
           JOIN classrooms c ON b.room_id = c.room_id 
           ORDER BY b.booking_date DESC, b.start_time DESC"""
    )
    
    all_students = query_db(
        """SELECT u.*, COUNT(b.booking_id) AS total_bookings 
           FROM users u 
           LEFT JOIN bookings b ON u.user_id = b.user_id 
           WHERE u.role = 'student' 
           GROUP BY u.user_id 
           ORDER BY u.name ASC"""
    )
    
    # Handle edit classroom trigger parameter
    edit_classroom = None
    edit_room_id = request.args.get('edit_room_id')
    if edit_room_id:
        edit_classroom = query_db("SELECT * FROM classrooms WHERE room_id = ?", (edit_room_id,), one=True)
        
    active_tab = request.args.get('active_tab', 'overview')
    
    return render_template(
        'admin_dashboard.html',
        stats=stats,
        classrooms=all_classrooms,
        timetables=all_timetables,
        bookings=all_bookings,
        students=all_students,
        edit_classroom=edit_classroom,
        active_tab=active_tab,
        active_page='admin_dashboard'
    )

# ==========================================================================
# Admin CRUD Action Endpoints
# ==========================================================================
@app.route('/admin/classroom/add', methods=['POST'])
@login_required(role='admin')
def add_classroom():
    room_number = request.form.get('room_number', '').strip()
    building = request.form.get('building', '').strip()
    floor = request.form.get('floor')
    capacity = request.form.get('capacity')
    room_type = request.form.get('room_type')
    
    projector = 1 if request.form.get('projector') else 0
    whiteboard = 1 if request.form.get('whiteboard') else 0
    ac = 1 if request.form.get('ac') else 0
    
    if not room_number or not building or not floor or not capacity or not room_type:
        flash('All classroom fields are required.', 'error')
        return redirect(url_for('admin_dashboard', active_tab='classrooms'))
        
    try:
        execute_db(
            """INSERT INTO classrooms (room_number, building, floor, capacity, room_type, projector, whiteboard, ac, status) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Available')""",
            (room_number, building, int(floor), int(capacity), room_type, projector, whiteboard, ac)
        )
        flash(f'Classroom Room {room_number} added successfully.', 'success')
    except sqlite3.IntegrityError:
        flash(f'Classroom Room {room_number} already exists.', 'error')
        
    return redirect(url_for('admin_dashboard', active_tab='classrooms'))

@app.route('/admin/classroom/edit/<int:room_id>', methods=['POST'])
@login_required(role='admin')
def edit_classroom(room_id):
    room_number = request.form.get('room_number', '').strip()
    building = request.form.get('building', '').strip()
    floor = request.form.get('floor')
    capacity = request.form.get('capacity')
    room_type = request.form.get('room_type')
    status = request.form.get('status')
    
    projector = 1 if request.form.get('projector') else 0
    whiteboard = 1 if request.form.get('whiteboard') else 0
    ac = 1 if request.form.get('ac') else 0
    
    try:
        execute_db(
            """UPDATE classrooms 
               SET room_number = ?, building = ?, floor = ?, capacity = ?, room_type = ?, projector = ?, whiteboard = ?, ac = ?, status = ? 
               WHERE room_id = ?""",
            (room_number, building, int(floor), int(capacity), room_type, projector, whiteboard, ac, status, room_id)
        )
        flash(f'Classroom Room {room_number} updated successfully.', 'success')
    except sqlite3.IntegrityError:
        flash('Another classroom with this room number already exists.', 'error')
        
    return redirect(url_for('admin_dashboard', active_tab='classrooms'))

@app.route('/admin/classroom/delete/<int:room_id>')
@login_required(role='admin')
def delete_classroom(room_id):
    execute_db("DELETE FROM classrooms WHERE room_id = ?", (room_id,))
    flash('Classroom deleted successfully.', 'success')
    return redirect(url_for('admin_dashboard', active_tab='classrooms'))

@app.route('/admin/timetable/add', methods=['POST'])
@login_required(role='admin')
def add_timetable():
    room_id = request.form.get('room_id')
    day = request.form.get('day')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    subject = request.form.get('subject', '').strip()
    
    if not room_id or not day or not start_time or not end_time or not subject:
        flash('All timetable schedule fields are required.', 'error')
        return redirect(url_for('admin_dashboard', active_tab='timetable'))
        
    if start_time >= end_time:
        flash('Timetable start time must be before end time.', 'error')
        return redirect(url_for('admin_dashboard', active_tab='timetable'))
        
    execute_db(
        "INSERT INTO timetable (room_id, day, start_time, end_time, subject) VALUES (?, ?, ?, ?, ?)",
        (int(room_id), day, start_time, end_time, subject)
    )
    flash('Timetable slot added successfully.', 'success')
    return redirect(url_for('admin_dashboard', active_tab='timetable'))

@app.route('/admin/timetable/delete/<int:timetable_id>')
@login_required(role='admin')
def delete_timetable(timetable_id):
    execute_db("DELETE FROM timetable WHERE timetable_id = ?", (timetable_id,))
    flash('Timetable entry deleted successfully.', 'success')
    return redirect(url_for('admin_dashboard', active_tab='timetable'))

@app.route('/admin/booking/<int:booking_id>/<action>')
@login_required(role='admin')
def handle_booking(booking_id, action):
    if action not in ('approve', 'reject'):
        flash('Invalid action requested.', 'error')
        return redirect(url_for('admin_dashboard', active_tab='overview'))
        
    status = 'Approved' if action == 'approve' else 'Rejected'
    execute_db("UPDATE bookings SET status = ? WHERE booking_id = ?", (status, booking_id))
    flash(f'Booking request #{booking_id} has been {status.lower()}.', 'success')
    return redirect(url_for('admin_dashboard', active_tab='overview'))

# ==========================================================================
# Run local development server
# ==========================================================================
if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
