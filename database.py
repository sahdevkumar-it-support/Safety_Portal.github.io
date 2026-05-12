import sqlite3

# ==========================================
# DATABASE CONNECTION
# ==========================================

conn = sqlite3.connect('safety_portal.db')

cursor = conn.cursor()

# ==========================================
# EMPLOYEES TABLE
# ==========================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS employees (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    emp_code TEXT UNIQUE,

    name TEXT,

    department TEXT,

    designation TEXT,

    date_of_birth TEXT,

    date_of_joining TEXT,

    category TEXT,

    mobile TEXT,

    email TEXT,

    username TEXT UNIQUE,

    password TEXT,

    role TEXT
)
""")

# ==========================================
# SAFETY VIDEOS TABLE
# ==========================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS safety_videos (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    title TEXT,

    youtube_link TEXT,

    category TEXT
)
""")

# ==========================================
# DEFAULT ADMIN USER
# ==========================================

cursor.execute("""
INSERT OR IGNORE INTO employees (

    emp_code,
    name,
    department,
    designation,
    date_of_birth,
    date_of_joining,
    category,
    mobile,
    email,
    username,
    password,
    role

)

VALUES (

    'EMP001',
    'MAIN ADMIN',
    'IT',
    'SYSTEM ADMIN',
    '1995-01-01',
    '2025-01-01',
    'GENERAL',
    '9999999999',
    'admin@utkal.com',
    'admin',
    'admin123',
    'admin'
)
""")

# ==========================================
# SAVE DATABASE
# ==========================================

conn.commit()

conn.close()

print("DATABASE CREATED SUCCESSFULLY")