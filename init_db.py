import sqlite3
import os
from werkzeug.security import generate_password_hash

def init_db():
    db_path = 'database.db'
    schema_path = 'schema.sql'
    
    print("Initializing database...")
    
    # Connect and run schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
    
    cursor.executescript(schema_sql)
    
    # Check if we already have users. If not, seed data.
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        print("Seeding database with default values...")
        
        # Seed users
        admin_pass = generate_password_hash("admin123")
        student_pass = generate_password_hash("student123")
        
        users_data = [
            ("Admin User", "admin@studyspace.com", admin_pass, "admin"),
            ("Student User", "student@studyspace.com", student_pass, "student"),
            ("Rahul Sharma", "rahul@studyspace.com", student_pass, "student"),
            ("Priya Patel", "priya@studyspace.com", student_pass, "student")
        ]
        cursor.executemany(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            users_data
        )
        
        # Seed classrooms
        # Columns: room_number, building, floor, capacity, room_type, projector, whiteboard, ac, status
        classrooms_data = [
            ("101", "Ramanujan Block", 1, 60, "Lecture Hall", 1, 1, 1, "Available"),
            ("102", "Ramanujan Block", 1, 40, "Seminar Room", 1, 1, 0, "Available"),
            ("201", "Aryabhata Block", 2, 30, "Discussion Room", 0, 1, 1, "Available"),
            ("202", "Aryabhata Block", 2, 120, "Auditorium", 1, 1, 1, "Available"),
            ("301", "Kalam Labs Block", 3, 50, "Computer Lab", 1, 1, 1, "Available"),
            ("302", "Kalam Labs Block", 3, 45, "Electronics Lab", 1, 1, 0, "Maintenance")
        ]
        cursor.executemany(
            "INSERT INTO classrooms (room_number, building, floor, capacity, room_type, projector, whiteboard, ac, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            classrooms_data
        )
        
        # Seed timetable
        # Let's get the room ids first
        cursor.execute("SELECT room_id, room_number FROM classrooms")
        rooms = {row[1]: row[0] for row in cursor.fetchall()}
        
        # Columns: room_id, day, start_time, end_time, subject
        timetable_data = [
            (rooms["101"], "Monday", "09:00", "10:30", "Data Structures & Algorithms"),
            (rooms["101"], "Monday", "11:00", "12:30", "Database Management Systems"),
            (rooms["101"], "Wednesday", "09:00", "10:30", "Data Structures & Algorithms"),
            (rooms["102"], "Tuesday", "10:00", "11:30", "Software Engineering"),
            (rooms["201"], "Thursday", "14:00", "16:00", "Placement Prep Seminar"),
            (rooms["301"], "Wednesday", "13:30", "15:30", "Computer Networks Lab")
        ]
        cursor.executemany(
            "INSERT INTO timetable (room_id, day, start_time, end_time, subject) VALUES (?, ?, ?, ?, ?)",
            timetable_data
        )
        
        # Seed sample bookings
        # Let's get student user id
        cursor.execute("SELECT user_id FROM users WHERE email='student@studyspace.com'")
        student_id = cursor.fetchone()[0]
        
        cursor.execute("SELECT user_id FROM users WHERE email='rahul@studyspace.com'")
        rahul_id = cursor.fetchone()[0]
        
        # Columns: user_id, room_id, booking_date, start_time, end_time, purpose, status
        # We can seed some upcoming bookings
        from datetime import datetime, timedelta
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        day_after = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        
        bookings_data = [
            (student_id, rooms["201"], tomorrow, "10:00", "12:00", "Group Study for Exams", "Approved"),
            (rahul_id, rooms["102"], tomorrow, "14:00", "15:30", "Coding Club Prep", "Pending"),
            (student_id, rooms["101"], day_after, "15:00", "16:30", "Project Discussion", "Approved")
        ]
        cursor.executemany(
            "INSERT INTO bookings (user_id, room_id, booking_date, start_time, end_time, purpose, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            bookings_data
        )
        
        print("Database seeded successfully.")
    else:
        print("Database already has data. Skipping seed.")
        
    conn.commit()
    conn.close()
    print("Database initialization complete.")

if __name__ == "__main__":
    init_db()
