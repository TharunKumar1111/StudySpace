# StudySpace – Smart Classroom Availability & Booking System

> **Tagline:** Find. Book. Study.  
> A clean, production-ready, interview-friendly web application for college campuses to manage classroom bookings, prevent double-bookings, and track real-time study slot availability.

---

## 🌟 Overview & Architecture

**StudySpace** is built using a simple yet robust tech stack suited for rapid local testing and simple deployment:
- **Backend:** Python + Flask (minimalist, fast route definition, modular MVC structure).
- **Database:** SQLite (lightweight, file-based, serverless, native to Python).
- **Frontend:** Semantic HTML5 + Responsive CSS3 Variables + Vanilla JavaScript (zero external dependencies/frameworks to keep performance fast and codebase beginner-friendly).

---

## 🚀 Getting Started

### 1. Install Dependencies
Run the command below in the project root directory:
```bash
pip install -r requirements.txt
```

### 2. Initialize the SQLite Database
Set up the schema and insert mock data (student/admin test credentials, default classrooms, and default class schedules):
```bash
py init_db.py
```

### 3. Run the Application
Start the Flask local development server:
```bash
py app.py
```
Open your browser and navigate to `http://127.0.0.1:5000/`.

---

## 🔑 Test Credentials (Pre-seeded)

- **Student User Account:**
  - **Email:** `student@studyspace.com`
  - **Password:** `student123`
- **Admin User Account:**
  - **Email:** `admin@studyspace.com`
  - **Password:** `admin123`

---

## 📂 Project Structure

```
StudySpace/
├── app.py              # Main Flask server (Routing, logic, API, authorization checks)
├── init_db.py          # Database initialization and seeding script
├── schema.sql          # SQL file containing table designs
├── requirements.txt    # Application dependencies list
├── README.md           # Documentation guide
├── static/
│   ├── css/
│   │   └── style.css   # Main stylesheet (Flexbox/Grid, Color variables, Responsive styles)
│   └── js/
│       └── main.js     # JavaScript helpers (Date validation, live availability checking)
└── templates/          # Jinja2 HTML templates
    ├── base.html       # Shared header, navbar, alerts, footer layouts
    ├── login.html      # Sign in portal
    ├── register.html   # Student/Admin signup form
    ├── dashboard.html  # Student home panel
    ├── classrooms.html # Interactive classroom catalog (Search & filters)
    ├── booking.html    # Booking request with live checks & suggestions
    ├── history.html    # Student request lists and cancellation controls
    ├── profile.html    # Profile details edit settings
    └── admin_dashboard.html # Admin central command (CRUD, timelining, approvals)
```

---

## 💬 Interview & Placement FAQ Prep

### 1. Why was Flask chosen instead of Django?
Flask is a lightweight micro-framework. Unlike Django, which comes with a heavy builtin ORM, admin panel, and session management system out-of-the-box, Flask allows complete flexibility. It is ideal for freshers because it does not hide underlying operations (like manual SQLite queries and raw sessions), making it far easier to explain the complete request-response flow in interviews.

### 2. Why was SQLite selected?
SQLite is a serverless, zero-configuration SQL database engine. The entire database is stored as a single file (`database.db`) inside the workspace. It requires no installation of local database services (like MySQL or PostgreSQL), making it lightweight for development while still adhering to standard SQL and relational normalization principles.

### 3. How does the double-booking prevention logic work?
When a student requests a booking slot for a specific `booking_date` between `start_time` and `end_time` (e.g., Room 101, Monday 10:00 - 11:30):
1. **Recurring Timetable Check:** The system looks for recurring lectures scheduled in `timetable` for Room 101 on that day of the week that overlap:
   ```sql
   SELECT * FROM timetable WHERE room_id = ? AND day = ? AND start_time < ? AND end_time > ?
   ```
2. **Approved Bookings Check:** The system checks the `bookings` table for approved bookings on that date/time for Room 101:
   ```sql
   SELECT * FROM bookings WHERE room_id = ? AND booking_date = ? AND status = 'Approved' AND start_time < ? AND end_time > ?
   ```
If either query yields records, the booking is blocked, and the student is shown the double-booking warning.

### 4. How are alternative classrooms suggested?
If the chosen room is taken, the backend retrieves other rooms in the same building or of the same room type. For each candidate room, it performs the timetable and approved booking checks for the requested date and time slot. Only rooms that are completely free are presented to the user under the "Alternative Available Rooms" section.

### 5. How is "Available Until" calculated?
When a user views a classroom, the system fetches all of today's recurring timetable slots and approved bookings for that room, sorting them by start time. It loops through the list to find the first busy slot starting *after* the current time. If found, it displays that start time (e.g., "Available Until 14:00 today"). Otherwise, it shows "Available for the rest of the day."
