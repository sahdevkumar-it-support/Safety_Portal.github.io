import sqlite3

conn = sqlite3.connect("safety_portal.db")

cursor = conn.cursor()

# ================= IME =================

cursor.execute("""

ALTER TABLE employees
ADD COLUMN ime_date TEXT

""")

cursor.execute("""

ALTER TABLE employees
ADD COLUMN ime_valid_upto TEXT

""")

cursor.execute("""

ALTER TABLE employees
ADD COLUMN ime_status TEXT

""")

# ================= VTC =================

cursor.execute("""

ALTER TABLE employees
ADD COLUMN vtc_start_date TEXT

""")

cursor.execute("""

ALTER TABLE employees
ADD COLUMN vtc_end_date TEXT

""")

cursor.execute("""

ALTER TABLE employees
ADD COLUMN vtc_certificate_no TEXT

""")

cursor.execute("""

ALTER TABLE employees
ADD COLUMN vtc_grade TEXT

""")

cursor.execute("""

ALTER TABLE employees
ADD COLUMN vtc_training_type TEXT

""")

cursor.execute("""

ALTER TABLE employees
ADD COLUMN vtc_valid_upto TEXT

""")

conn.commit()

conn.close()

print("DATABASE UPDATED SUCCESSFULLY")