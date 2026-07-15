-- SQLite Schema for StudySpace Classroom Availability & Booking System

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('student', 'admin'))
);

-- Classrooms Table
CREATE TABLE IF NOT EXISTS classrooms (
    room_id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_number TEXT UNIQUE NOT NULL,
    building TEXT NOT NULL,
    floor INTEGER NOT NULL,
    capacity INTEGER NOT NULL,
    room_type TEXT NOT NULL, -- e.g. 'Lecture Hall', 'Seminar Room', 'Discussion Room', 'Lab'
    projector INTEGER NOT NULL DEFAULT 0, -- 0 for No, 1 for Yes
    whiteboard INTEGER NOT NULL DEFAULT 1, -- 0 for No, 1 for Yes
    ac INTEGER NOT NULL DEFAULT 0, -- 0 for No, 1 for Yes
    status TEXT NOT NULL DEFAULT 'Available' CHECK(status IN ('Available', 'Occupied', 'Maintenance'))
);

-- Timetable Table (Recurring class schedules)
CREATE TABLE IF NOT EXISTS timetable (
    timetable_id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL,
    day TEXT NOT NULL CHECK(day IN ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')),
    start_time TEXT NOT NULL, -- Format: HH:MM (24-hour style, e.g., '09:00')
    end_time TEXT NOT NULL,   -- Format: HH:MM (24-hour style, e.g., '10:00')
    subject TEXT NOT NULL,
    FOREIGN KEY(room_id) REFERENCES classrooms(room_id) ON DELETE CASCADE
);

-- Bookings Table (Student bookings)
CREATE TABLE IF NOT EXISTS bookings (
    booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    room_id INTEGER NOT NULL,
    booking_date TEXT NOT NULL, -- Format: YYYY-MM-DD
    start_time TEXT NOT NULL,   -- Format: HH:MM
    end_time TEXT NOT NULL,     -- Format: HH:MM
    purpose TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending', 'Approved', 'Rejected')),
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY(room_id) REFERENCES classrooms(room_id) ON DELETE CASCADE
);
