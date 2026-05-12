from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = "safetyportal123"

# ==========================================
# SQLITE DATABASE CONNECTION
# ==========================================

def get_db_connection():

    conn = sqlite3.connect('safety_portal.db')

    conn.row_factory = sqlite3.Row

    return conn

# ==========================================
# COMMON QUERY FUNCTION
# ==========================================

def execute_query(query, values=(), fetchone=False, fetchall=False):

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute(query, values)

    data = None

    if fetchone:
        data = cursor.fetchone()

    if fetchall:
        data = cursor.fetchall()

    conn.commit()

    conn.close()

    return data

# ==========================================
# HOME PAGE
# ==========================================

@app.route('/')
def home():

    return render_template('login.html')

# ==========================================
# LOGIN
# ==========================================

@app.route('/login', methods=['POST'])
def login():

    username = request.form['username']
    password = request.form['password']

    query = """
    SELECT * FROM employees
    WHERE username=? AND password=?
    """

    user = execute_query(
        query,
        (username, password),
        fetchone=True
    )

    if user:

        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        session['name'] = user['name']

        # ADMIN LOGIN

        if user['role'] == 'admin':

            return redirect(url_for('admin_dashboard'))

        # USER LOGIN

        else:

            return redirect(url_for('user_dashboard'))

    return "Invalid Username or Password"

# ==========================================
# USER DASHBOARD
# ==========================================

@app.route('/user_dashboard')
def user_dashboard():

    if 'user_id' not in session:

        return redirect(url_for('home'))

    query = """
    SELECT * FROM safety_videos
    ORDER BY id DESC
    """

    videos = execute_query(
        query,
        fetchall=True
    )

    return render_template(
        'user_dashboard.html',
        videos=videos,
        username=session['name']
    )

# ==========================================
# ADMIN DASHBOARD
# ==========================================

@app.route('/admin_dashboard')
def admin_dashboard():

    if 'user_id' not in session:

        return redirect(url_for('home'))

    if session['role'] != 'admin':

        return "Access Denied"

    total_employee = execute_query(
        "SELECT COUNT(*) AS total FROM employees",
        fetchone=True
    )['total']

    active_employee = execute_query(
        "SELECT COUNT(*) AS total FROM employees WHERE role='user'",
        fetchone=True
    )['total']

    total_admin = execute_query(
        "SELECT COUNT(*) AS total FROM employees WHERE role='admin'",
        fetchone=True
    )['total']

    total_videos = execute_query(
        "SELECT COUNT(*) AS total FROM safety_videos",
        fetchone=True
    )['total']

    return render_template(
        'admin_dashboard.html',
        total_employee=total_employee,
        active_employee=active_employee,
        total_admin=total_admin,
        total_videos=total_videos
    )

# ==========================================
# EMPLOYEE MANAGEMENT
# ==========================================

@app.route('/empmgt')
def empmgt():

    if 'user_id' not in session:

        return redirect(url_for('home'))

    if session['role'] != 'admin':

        return "Access Denied"

    employees = execute_query(
        """
        SELECT * FROM employees
        ORDER BY id DESC
        """,
        fetchall=True
    )

    # LAST EMP CODE

    last_emp = execute_query(
        """
        SELECT emp_code
        FROM employees
        ORDER BY id DESC
        LIMIT 1
        """,
        fetchone=True
    )

    next_emp_code = "EMP001"

    if last_emp:

        code = last_emp['emp_code']

        try:

            number = int(
                code.replace("EMP", "")
            )

            next_emp_code = f"EMP{number+1:03d}"

        except:

            pass

    return render_template(
        'employee_mgnt.html',
        employees=employees,
        next_emp_code=next_emp_code
    )

# ==========================================
# ADD EMPLOYEE
# ==========================================

@app.route('/add_employee', methods=['POST'])
def add_employee():

    if session['role'] != 'admin':

        return "Access Denied"

    emp_code = request.form['emp_code']
    name = request.form['name']
    department = request.form['department']
    designation = request.form['designation']

    dob = request.form['dob']
    doj = request.form['doj']

    category = request.form['category']

    mobile = request.form['mobile']

    email = request.form['email']

    username = request.form['username']
    password = request.form['password']

    role = request.form['role']

    query = """
    INSERT INTO employees
    (
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

    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """

    values = (
        emp_code,
        name,
        department,
        designation,
        dob,
        doj,
        category,
        mobile,
        email,
        username,
        password,
        role
    )

    execute_query(query, values)

    return redirect(url_for('empmgt'))

# ==========================================
# UPDATE EMPLOYEE
# ==========================================

@app.route('/update_employee', methods=['POST'])
def update_employee():

    if session['role'] != 'admin':

        return "Access Denied"

    id = request.form['id']

    emp_code = request.form['emp_code']
    name = request.form['name']
    department = request.form['department']
    designation = request.form['designation']

    dob = request.form['dob']
    doj = request.form['doj']

    category = request.form['category']

    mobile = request.form['mobile']

    email = request.form['email']

    username = request.form['username']
    password = request.form['password']

    role = request.form['role']

    query = """
    UPDATE employees
    SET

        emp_code=?,
        name=?,
        department=?,
        designation=?,
        date_of_birth=?,
        date_of_joining=?,
        category=?,
        mobile=?,
        email=?,
        username=?,
        password=?,
        role=?

    WHERE id=?
    """

    values = (
        emp_code,
        name,
        department,
        designation,
        dob,
        doj,
        category,
        mobile,
        email,
        username,
        password,
        role,
        id
    )

    execute_query(query, values)

    return redirect(url_for('empmgt'))

# ==========================================
# DELETE EMPLOYEE
# ==========================================

@app.route('/delete_employee/<int:id>')
def delete_employee(id):

    query = """
    DELETE FROM employees
    WHERE id=?
    """

    execute_query(query, (id,))

    return redirect(url_for('empmgt'))

# ==========================================
# VIDEO MANAGEMENT PAGE
# ==========================================

@app.route('/videomgt')
def videomgt():

    if 'user_id' not in session:

        return redirect(url_for('home'))

    if session['role'] != 'admin':

        return "Access Denied"

    videos = execute_query(
        """
        SELECT * FROM safety_videos
        ORDER BY id DESC
        """,
        fetchall=True
    )

    return render_template(
        'videomgt.html',
        videos=videos
    )

# ==========================================
# ADD VIDEO
# ==========================================

@app.route('/add_video', methods=['POST'])
def add_video():

    if session['role'] != 'admin':

        return "Access Denied"

    title = request.form['title']
    youtube_link = request.form['youtube_link']
    category = request.form['category']

    # ======================================
    # CONVERT NORMAL URL TO EMBED
    # ======================================

    video_id = ""

    if "youtu.be/" in youtube_link:

        video_id = youtube_link.split(
            "youtu.be/"
        )[1].split("?")[0]

    elif "watch?v=" in youtube_link:

        video_id = youtube_link.split(
            "watch?v="
        )[1].split("&")[0]

    elif "embed/" in youtube_link:

        video_id = youtube_link.split(
            "embed/"
        )[1].split("?")[0]

    embed_link = f"https://www.youtube.com/embed/{video_id}"

    query = """
    INSERT INTO safety_videos
    (
        title,
        youtube_link,
        category
    )

    VALUES (?,?,?)
    """

    execute_query(
        query,
        (
            title,
            embed_link,
            category
        )
    )

    return redirect(url_for('videomgt'))

# ==========================================
# DELETE VIDEO
# ==========================================

@app.route('/delete_video/<int:id>')
def delete_video(id):

    query = """
    DELETE FROM safety_videos
    WHERE id=?
    """

    execute_query(query, (id,))

    return redirect(url_for('videomgt'))

# ==========================================
# LOGOUT
# ==========================================

@app.route('/logout')
def logout():

    session.clear()

    return redirect(url_for('home'))

# ==========================================
# RUN APP
# ==========================================

if __name__ == '__main__':

    app.run(host='0.0.0.0', port=5000)