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
    all_users = list(users.find())
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
    existing_user = users.find_one({"$or": [{"username": username}, {"email": email}]})
    
    if existing_user:
        flash("⚠️ Username ya Email pehle se register hai!", "error")
    else:
        # Secure Password Hashing
        hashed_password = generate_password_hash(password)
        
        # New User Document Ingestion
        new_user = {
            "username": username,
            "email": email,
            "password": hashed_password,
            "role": role
        }
        users.insert_one(new_user)
        flash("✅ Naya user successfully system me add ho gaya!", "success")
        
    return redirect(url_for("manage_users"))


@app.route("/delete_user/<user_id>")
def delete_user(user_id):
    # Security Check: Khali admin hi delete kar sakta hai
    if "username" not in session or str(session.get("role")).strip().lower() != "admin":
        return redirect("/")

    # User ID ke base par account permanent delete karna
    users.delete_one({"_id": ObjectId(user_id)})
    flash("🗑️ User account successfully delete kar diya gaya.", "success")
    return redirect(url_for("manage_users"))


# =========================================
# 2. AUTHENTICATION ROUTES (Login & Logout)
# =========================================

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        user = users.find_one({"username": username})

        if user:
            db_password = user["password"]
            password_matched = False

            # --- DUAL PASSWORD HASH CHECKING LOGIC ---
            if isinstance(db_password, (bytes, Binary)):
                try:
                    binary_password_bytes = bytes(db_password)
                    if bcrypt.checkpw(password.encode("utf-8"), binary_password_bytes):
                        password_matched = True
                except Exception:
                    pass

            if not password_matched and isinstance(db_password, str):
                try:
                    if check_password_hash(db_password, password):
                        password_matched = True
                except Exception:
                    pass

            if password_matched:
                session["username"] = user["username"]
                session["role"] = user["role"]

                user_role = str(user.get("role", "Viewer")).strip().lower()
                if user_role == "admin":
                    return redirect("/dashboard")
                else:
                    return redirect("/user_dashboard")

        return "Invalid Username or Password"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ==========================================
# 3. ADMIN & USER DASHBOARDS
# ==========================================

@app.route("/dashboard")
def dashboard():
    if "username" not in session or str(session.get("role")).strip().lower() != "admin":
        return redirect("/")

    total_categories = categories.count_documents({})
    total_videos = videos.count_documents({})
    total_users = users.count_documents({})

    return render_template(
        "dashboard.html",
        total_categories=total_categories,
        total_videos=total_videos,
        total_users=total_users
    )


@app.route("/user_dashboard")
def user_dashboard():
    if "username" not in session:
        return redirect("/")
        
    category_data = []
    all_categories = categories.find()

    for category in all_categories:
        category_videos = videos.find({"category_id": str(category["_id"])})
        category_data.append({
            "title": category.get("title", category.get("category", "Unnamed Category")),
            "videos": list(category_videos)
        })
        
    return render_template("user_dashboard.html", category_data=category_data)


# ==========================================
# 4. CATEGORY MANAGEMENT (CRUD) - ADMIN ONLY
# ==========================================

@app.route("/add_category", methods=["GET", "POST"])
def add_category():
    if "username" not in session or str(session.get("role")).strip().lower() != "admin":
        return redirect("/")

    if request.method == "POST":
        title = request.form["title"]
        categories.insert_one({"title": title})
        return redirect("/categories")

    return render_template("add_category.html")


@app.route("/edit_category/<id>", methods=["GET", "POST"])
def edit_category(id):
    if "username" not in session or str(session.get("role")).strip().lower() != "admin":
        return redirect("/")

    category = categories.find_one({"_id": ObjectId(id)})

    if request.method == "POST":
        categories.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"title": request.form["title"]}}
        )
        return redirect("/categories")

    return render_template("edit_category.html", category=category)


@app.route("/categories")
def category_list():
    if "username" not in session or str(session.get("role")).strip().lower() != "admin":
        return redirect("/")

    all_categories = categories.find()
    return render_template("category_list.html", categories=all_categories)    


@app.route("/delete_category/<id>")
def delete_category(id):
    if "username" not in session or str(session.get("role")).strip().lower() != "admin":
        return redirect("/")

    videos.delete_many({"category_id": id})
    categories.delete_one({"_id": ObjectId(id)})
    return redirect("/categories")


# ==========================================
# 5. VIDEO MANAGEMENT (CRUD) - ADMIN ONLY
# ==========================================

@app.route("/add_video", methods=["GET", "POST"])
def add_video():
    if "username" not in session or str(session.get("role")).strip().lower() != "admin":
        return redirect("/")

    if request.method == "POST":
        category_id = request.form["category_id"]
        title = request.form["title"]
        youtube_url = request.form["youtube_url"]

        if "youtu.be/" in youtube_url:
            youtube_id = youtube_url.split("youtu.be/")[1].split("?")[0]
        elif "watch?v=" in youtube_url:
            youtube_id = youtube_url.split("watch?v=")[1].split("&")[0]
        else:
            youtube_id = youtube_url

        videos.insert_one({
            "category_id": category_id,
            "title": title,
            "youtube_id": youtube_id
        })
        return redirect("/videos")

    all_categories = categories.find()
    return render_template("add_video.html", categories=all_categories)


@app.route("/videos")
def video_list():
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
    return render_template("video_management.html", videos=all_videos, categories=all_categories)


@app.route("/delete_video/<id>")
def delete_video(id):
    if "username" not in session or str(session.get("role")).strip().lower() != "admin":
        return redirect("/")
    videos.delete_one({"_id": ObjectId(id)})
    return redirect("/videos")


# ==========================================
# 6. PUBLIC PORTAL & PLAYBACK ROUTES
# ==========================================

@app.route("/home")
def home():
    category_data = []
    all_categories = categories.find()
    for category in all_categories:
        category_videos = videos.find({"category_id": str(category["_id"])})
        category_data.append({
            "title": category.get("title", category.get("category", "Unnamed Category")),
            "videos": list(category_videos)
        })
    return render_template("home.html", category_data=category_data)  


@app.route("/watch/<id>")
def watch_video(id):
    if "username" not in session:
        return redirect("/")
    video = videos.find_one({"_id": ObjectId(id)})
    return render_template("watch_video.html", video=video)            


@app.route("/get_qr")
def get_qr():
    public_url = request.url_root + "public_dashboard"
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(public_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')


@app.route("/public_dashboard")
def public_dashboard():
    category_data = []
    all_categories = categories.find()
    for category in all_categories:
        cat_id_str = str(category["_id"])
        category_videos = list(videos.find({"category_id": cat_id_str}))
        resolved_title = category.get("title", category.get("category", "Unnamed Category"))
        category_data.append({"title": resolved_title, "videos": category_videos})
    return render_template("public_dashboard.html", category_data=category_data)


# ==========================================
# 7. SERVER RUNNER
# ==========================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4950, debug=True)
else:
    application = app