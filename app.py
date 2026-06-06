from flask import Flask, render_template, request, redirect, session, url_for, flash
from pymongo import MongoClient
from bson import ObjectId
import bcrypt
from urllib.parse import urlparse
from werkzeug.security import generate_password_hash, check_password_hash
from bson.binary import Binary
import pymongo
import qrcode
import io
from flask import send_file
import os
# ==========================================
# 1. APPLICATION & DATABASE INITIALIZATION
# ==========================================

app = Flask(__name__)
app.secret_key = "safety_portal_secret"

# CHANGE HERE: Yahan hum environment variable ka use karenge
mongo_uri = os.environ.get("MONGO_URI")

# Agar Vercel par hoga toh Atlas se connect hoga, varna Localhost se
client = MongoClient(mongo_uri if mongo_uri else "mongodb://localhost:27017/")

# Database ka naam Atlas mein wahi hona chahiye jo yahan likha hai
db = client["safety_video_db"]

# Collections
users = db["users"]
categories = db["categories"]
videos = db["videos"]

@app.route("/users")
def manage_users():
    # Security Check: Khali admin hi access kar sakta hai
    if "username" not in session or str(session.get("role")).strip().lower() != "admin":
        flash("⚠️ Access Denied! Sirf Admin is page ko dekh sakta hai.", "error")
        return redirect("/")
        
    # Database se saare users ki list fetch karna
    all_users = list(users_collection.find())
    return render_template("users.html", users=all_users)


@app.route("/add_user", methods=["POST"])
def add_user():
    # Security Check: Khali admin hi user add kar sakta hai
    if "username" not in session or str(session.get("role")).strip().lower() != "admin":
        return redirect("/")

    username = request.form.get("username").strip()
    email = request.form.get("email").strip()
    password = request.form.get("password")
    role = request.form.get("role")

    # Validation: Check agar user pehle se exist toh nahi karta
    existing_user = users_collection.find_one({"$or": [{"username": username}, {"email": email}]})
    
    if existing_user:
        flash("⚠️ Username ya Email pehle se register hai!", "error")
    else:
        # Secure Password Hashing (Naye users ke liye ab scrypt hash use hoga standard)
        hashed_password = generate_password_hash(password)
        
        # New User Document Ingestion
        new_user = {
            "username": username,
            "email": email,
            "password": hashed_password,
            "role": role
        }
        users_collection.insert_one(new_user)
        flash("✅ Naya user successfully system me add ho gaya!", "success")
        
    return redirect(url_for("manage_users"))


@app.route("/delete_user/<user_id>")
def delete_user(user_id):
    # Security Check: Khali admin hi delete kar sakta hai
    if "username" not in session or str(session.get("role")).strip().lower() != "admin":
        return redirect("/")

    # User ID ke base par account permanent delete karna
    users_collection.delete_one({"_id": ObjectId(user_id)})
    flash("🗑️ User account successfully delete kar diya gaya.", "success")
    return redirect(url_for("manage_users"))


# =========================================
# 2. AUTHENTICATION ROUTES (Login & Logout)
# ==========================================

# --- LOGIN ROUTE ---
# Ye route login page dikhane aur form submit hone par user verify karne ke liye hai
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Form se username aur password data lena
        username = request.form["username"].strip()
        password = request.form["password"]

        # Database me username check karna
        user = users_collection.find_one({"username": username})

        if user:
            db_password = user["password"]
            password_matched = False

            # --- DUAL PASSWORD HASH CHECKING LOGIC ---
            # 1. Check agar database ka password 'bytes' ya MongoDB 'Binary' (Bcrypt) format me hai
            if isinstance(db_password, (bytes, Binary)):
                try:
                    # Agar purana format Binary hai toh pehle use byte string me convert karke check karenge
                    binary_password_bytes = bytes(db_password)
                    if bcrypt.checkpw(password.encode("utf-8"), binary_password_bytes):
                        password_matched = True
                except Exception:
                    pass

            # 2. Fallback check: Agar string format me store hai (Aapka naya scrypt standard)
            if not password_matched and isinstance(db_password, str):
                try:
                    if check_password_hash(db_password, password):
                        password_matched = True
                except Exception:
                    pass

            # Agar donon me se kisi bhi format se password match ho gaya
            if password_matched:
                # Session me user ki details save karna (Login state maintain karne ke liye)
                session["username"] = user["username"]
                session["role"] = user["role"]

                # 🌟 ROLE KE HISAB SE DASHBOARD LANDING LOGIC (Case Insensitive Match) 🌟
                user_role = str(user.get("role", "Viewer")).strip().lower()
                if user_role == "admin":
                    return redirect("/dashboard")
                else:
                    return redirect("/user_dashboard")

        # Agar login fail hua toh message return karna
        return "Invalid Username or Password"

    # GET request par login.html page dikhana
    return render_template("login.html")


# --- LOGOUT ROUTE ---
# User ka session clear karke bahar nikalne (logout) ke liye
@app.route("/logout")
def logout():
    # Session ke sare data ko delete/clear karna
    session.clear()
    # Logout ke baad wapas login page par bhejna
    return redirect("/")


# ==========================================
# 3. ADMIN & USER DASHBOARDS
# ==========================================

# --- ADMIN DASHBOARD ROUTE ---
# Admin ka main panel jahan total counts (Categories, Videos, Users) dikhenge
@app.route("/dashboard")
def dashboard():
    # Security Check: Agar user logged in nahi hai ya admin nahi hai toh bahar pheko
    if "username" not in session or str(session.get("role")).strip().lower() != "admin":
        return redirect("/")

    # Database se alag-alag collections ka total count nikalna
    total_categories = categories.count_documents({})
    total_videos = videos.count_documents({})
    total_users = users_collection.count_documents({})

    # Counts ko dashboard.html template par pass karna
    return render_template(
        "dashboard.html",
        total_categories=total_categories,
        total_videos=total_videos,
        total_users=total_users
    )


# --- USER DASHBOARD ROUTE ---
# Normal users, students ya admin bhi is page ko video dekhne ke liye use kar sakte hain
@app.route("/user_dashboard")
def user_dashboard():
    # Security Check: Koi bhi logged in user ise dekh sakta hai
    if "username" not in session:
        return redirect("/")
        
    category_data = []
    # Database se saari categories fetch karna
    all_categories = categories.find()

    for category in all_categories:
        # Har category ke matching videos ko database se find karna
        category_videos = videos.find({"category_id": str(category["_id"])})
        
        # Category ka title (field map handles both title and category parameters) aur uske videos ki sublist map karna
        category_data.append({
            "title": category.get("title", category.get("category", "Unnamed Category")),
            "videos": list(category_videos)
        })
        
    # data lekar dashboard file render karna
    return render_template("user_dashboard.html", category_data=category_data)


# ==========================================
# 4. CATEGORY MANAGEMENT (CRUD) - ADMIN ONLY
# ==========================================

# --- ADD CATEGORY ---
@app.route("/add_category", methods=["GET", "POST"])
def add_category():
    # Security Check: Only Admin
    if "username" not in session or str(session.get("role")).strip().lower() != "admin":
        return redirect("/")

    if request.method == "POST":
        # Form se category ka title lena
        title = request.form["title"]

        # Database ke categories collection me insert karna
        categories.insert_one({
            "title": title
        })

        # Category add hone ke baad category list page par redirect karna
        return redirect("/categories")

    # GET request par add_category.html page dikhana
    return render_template("add_category.html")


# --- EDIT CATEGORY ---
@app.route("/edit_category/<id>", methods=["GET", "POST"])
def edit_category(id):
    # Security Check: Only Admin
    if "username" not in session or str(session.get("role")).strip().lower() != "admin":
        return redirect("/")

    # MongoDB ki ObjectId use karke specific category dhundhna
    category = categories.find_one({
        "_id": ObjectId(id)
    })

    if request.method == "POST":
        # Form se naya title lekar database me update karna
        categories.update_one(
            {"_id": ObjectId(id)},
            {
                "$set": {
                    "title": request.form["title"]
                }
            }
        )
        # Update hone ke baad list page par bhejna
        return redirect("/categories")

    # GET request par data ke sath edit page kholna
    return render_template(
        "edit_category.html",
        category=category
    )


# --- CATEGORY LIST ---
@app.route("/categories")
def category_list():
    # Security Check: Only Admin
    if "username" not in session or str(session.get("role")).strip().lower() != "admin":
        return redirect("/")

    # Database se sari categories nikalna
    all_categories = categories.find()

    return render_template(
        "category_list.html",
        categories=all_categories
    )    


# --- DELETE CATEGORY ---
@app.route("/delete_category/<id>")
def delete_category(id):
    # Security Check: Only Admin
    if "username" not in session or str(session.get("role")).strip().lower() != "admin":
        return redirect("/")

    # Cascade Delete: Pehle is category se jude sabhi videos delete karein
    videos.delete_many({
        "category_id": id
    })

    # Phir main category ko delete karein
    categories.delete_one({
        "_id": ObjectId(id)
    })

    return redirect("/categories")


# ==========================================
# 5. VIDEO MANAGEMENT (CRUD) - ADMIN ONLY
# ==========================================

# --- ADD VIDEO ---
@app.route("/add_video", methods=["GET", "POST"])
def add_video():
    # Security Check: Only Admin
    if "username" not in session or str(session.get("role")).strip().lower() != "admin":
        return redirect("/")

    if request.method == "POST":
        category_id = request.form["category_id"]
        title = request.form["title"]
        youtube_url = request.form["youtube_url"]

        # --- YouTube URL Parsing Logic ---
        if "youtu.be/" in youtube_url:
            youtube_id = youtube_url.split("youtu.be/")[1].split("?")[0]
        elif "watch?v=" in youtube_url:
            youtube_id = youtube_url.split("watch?v=")[1].split("&")[0]
        else:
            youtube_id = youtube_url

        # Video details database me save karna
        videos.insert_one({
            "category_id": category_id,
            "title": title,
            "youtube_id": youtube_id
        })

        return redirect("/videos")

    # Dropdown me dikhane ke liye sari categories fetch karna
    all_categories = categories.find()

    return render_template(
        "add_video.html",
        categories=all_categories
    )


# --- VIDEO LIST ---
@app.route("/videos")
def video_list():
    # Security Check: Only Admin
    if "username" not in session or str(session.get("role")).strip().lower() != "admin":
        return redirect("/")

    all_videos = []
    for video in videos.find():
        category = categories.find_one({"_id": ObjectId(video["category_id"])})
        if category:
            video["category_name"] = category.get("title", category.get("category", "Standard Category"))
        else:
            video["category_name"] = "Unknown Category"
        all_videos.append(video)

    all_categories = categories.find()
    return render_template(
        "video_management.html",
        videos=all_videos, 
        categories=all_categories
    )


# --- DELETE VIDEO ---
@app.route("/delete_video/<id>")
def delete_video(id):
    # Security Check: Only Admin
    if "username" not in session or str(session.get("role")).strip().lower() != "admin":
        return redirect("/")

    # ID ke base par video delete karna
    videos.delete_one({
        "_id": ObjectId(id)
    })

    return redirect("/videos")


# ==========================================
# 6. PUBLIC PORTAL & PLAYBACK ROUTES
# ==========================================

# --- HOME PAGE ---
@app.route("/home")
def home():
    category_data = []
    all_categories = categories.find()

    for category in all_categories:
        category_videos = videos.find({
            "category_id": str(category["_id"])
        })

        category_data.append({
            "title": category.get("title", category.get("category", "Unnamed Category")),
            "videos": list(category_videos)
        })

    return render_template(
        "home.html",
        category_data=category_data
    )  


# --- WATCH VIDEO PAGE ---
# Dono Normal viewer aur admin is route se video load kar ke dekh sakte hain
@app.route("/watch/<id>")
def watch_video(id):
    # Security Check: Kam se kam login hona mandatory hai
    if "username" not in session:
        return redirect("/")

    # Video ID ke data fetch karna (jisme youtube_id store hai)
    video = videos.find_one({
        "_id": ObjectId(id)
    })

    # Video object ko play page par bhej dena
    return render_template(
        "watch_video.html",
        video=video
    )            
        


@app.route("/get_qr")
def get_qr():
    # 1. Yahan apne hosting domain ya server ka link daalein jo QR scan karne par khulega
    # Agar local network par test kar rahe hain, toh localhost ki jagah system ki IP daalein (e.g., 192.168.1.50:5000)
    public_url = request.url_root + "public_dashboard"
    
    # 2. QR Code Generate karein
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(public_url)
    qr.make(fit=True)

    # 3. Image ko memory me save karke browser ko send karein
    img = qr.make_image(fill_color="black", back_color="white")
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    return send_file(img_io, mimetype='image/png')

# ==========================================
# 7. PUBLIC DASHBOARD - NO LOGIN REQUIRED
# ==========================================

@app.route("/public_dashboard")
def public_dashboard():
    # Yahan humne login session check ("if 'username' not in session:") ko poora hata diya hai
    category_data = []
    all_categories = categories.find()

    for category in all_categories:
        cat_id_str = str(category["_id"])
        category_videos = list(videos.find({"category_id": cat_id_str}))
        
        resolved_title = category.get("title", category.get("category", "Unnamed Category"))
        
        category_data.append({
            "title": resolved_title,
            "videos": category_videos
        })
        
    # Yeh public view ke liye alag template load karega
    return render_template("public_dashboard.html", category_data=category_data)



# ==========================================
# 7. SERVER RUNNER
# ==========================================

# ==========================================
# 7. SERVER RUNNER (Final Update for Cloud)
# ==========================================

if __name__ == "__main__":
    # Yeh sirf tab chalega jab aap apne PC par terminal mein 'python app.py' likhenge
    app.run(host="0.0.0.0", port=4950, debug=True)
else:
    # Yeh Vercel ya kisi bhi server ke liye zaruri hai
    application = app