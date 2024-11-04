from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from pymongo import MongoClient, DESCENDING
from bson import ObjectId
from datetime import datetime
import bcrypt

app = Flask(__name__)
app.secret_key = "secret_key"  # Kunci rahasia untuk session

# Koneksi ke MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["pinterest_clone"]

# Koleksi untuk pengguna, postingan, dan kategori
users_collection = db["users"]
posts_collection = db["posts"]
categories_collection = db["categories"]
login_logs_collection = db["login_logs"]
likes_collection = db["likes"]
comments_collection = db["comments"]
follows_collection = db["follows"]
profile_collection = db["profile"]

# Fungsi untuk inisialisasi database
def initialize_database():
    if users_collection.count_documents({}) == 0:
        # Data contoh
        user_example = {
            "username": "user123",
            "email": "user@example.com",
            "password": bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt()),
            "joined_at": datetime.now()
        }
        users_collection.insert_one(user_example)
        print("Database initialized with example data.")

# Panggil fungsi inisialisasi
initialize_database()

# Fungsi untuk membuat pengguna baru
def create_user(username, email, password):
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    user = {
        "username": username,
        "email": email,
        "password": hashed_password,
        "joined_at": datetime.now(),  # Simpan waktu registrasi
        "profile_pic": None,  # Default profile picture: None (belum diunggah)
        "bio": "",  # Default bio: kosong
        "followers_count": 0,  # Default followers count: 0
        "following_count": 0   # Default following count: 0
    }
    users_collection.insert_one(user)

# Fungsi untuk memverifikasi pengguna
def verify_user(username, password):
    user = users_collection.find_one({"username": username})
    if user and bcrypt.checkpw(password.encode('utf-8'), user["password"]):
        return user
    return None

def log_login_activity(username, successful):
    login_log = {
        "username": username,
        "login_time": datetime.now(),
        "ip_address": request.remote_addr,  # Mendapatkan alamat IP dari request
        "device": "desktop",  
        "location": None,  # Lokasi pengguna (opsional)
        "successful": successful,
        "login_method": "password"
    }
    login_logs_collection.insert_one(login_log)

# Route Home
@app.route("/")
def home():
    if "username" not in session:
        return redirect(url_for("login"))
    
    page = int(request.args.get("page", 1))
    per_page = 20
    skip = (page - 1) * per_page
    
    posts = list(posts_collection.find().sort("created_at", DESCENDING).skip(skip).limit(per_page))
    categories = list(categories_collection.find())
    
    for post in posts:
        post["likes_count"] = likes_collection.count_documents({"post_id": str(post["_id"])})
        post["comments"] = list(comments_collection.find({"post_id": str(post["_id"])}).limit(3))
        post["is_liked"] = likes_collection.find_one({
            "user_id": session["username"],
            "post_id": str(post["_id"])
        }) is not None
    
    return render_template("home.html", 
                         username=session["username"],
                         posts=posts,
                         categories=categories)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        if users_collection.find_one({"username": username}):
            flash("Username already exists!", "error")
            return redirect(url_for("register"))

        create_user(username, email, password)
        flash("Registration successful! Please login.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = users_collection.find_one({'username': session['username']})
    profile_data = profile_collection.find_one({'username': session['username']})
    
    if request.method == 'POST':
        # Mengunggah foto profil
        profile_pic = request.files['profile_pic']
        if profile_pic:
            profile_data = {
                'username': session['username'],
                'profile_pic': profile_pic.read()  # Menyimpan foto profil sebagai binary data
            }
            profile_collection.replace_one({'username': session['username']}, profile_data, upsert=True)
    
    return render_template('Profile.html', user=user, profile=profile_data)

@app.route("/create-post", methods=["GET", "POST"])
def create_post():
    if "username" not in session:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        post = {
            "user_id": session["username"],
            "title": request.form["title"],
            "description": request.form["description"],
            "image_url": request.form["image_url"],
            "category_id": request.form["category"],
            "tags": request.form.getlist("tags"),
            "created_at": datetime.now().strftime("%Y-%m-%d")
        }
        posts_collection.insert_one(post)
        flash("Post created successfully!", "success")
        return redirect(url_for("home"))
    
    categories = list(categories_collection.find())
    return render_template("create_post.html", categories=categories)

@app.route("/search")
def search():
    query = request.args.get("q", "")
    category = request.args.get("category", "")
    
    search_filters = {}
    if query:
        search_filters["$or"] = [
            {"title": {"$regex": query, "$options": "i"}},
            {"description": {"$regex": query, "$options": "i"}},
            {"tags": {"$regex": query, "$options": "i"}}
        ]
    if category:
        search_filters["category_id"] = category
        
    posts = list(posts_collection.find(search_filters).sort("created_at", DESCENDING))
    return jsonify({"posts": posts})

@app.route("/like/<post_id>", methods=["POST"])
def like_post(post_id):
    if "username" not in session:
        return jsonify({"error": "Please login first"}), 401
    
    like = {
        "user_id": session["username"],
        "post_id": post_id,
        "created_at": datetime.now()
    }
    
    existing_like = likes_collection.find_one({
        "user_id": session["username"],
        "post_id": post_id
    })
    
    if existing_like:
        likes_collection.delete_one({"_id": existing_like["_id"]})
        return jsonify({"liked": False})
    
    likes_collection.insert_one(like)
    return jsonify({"liked": True})

@app.route("/comment/<post_id>", methods=["POST"])
def add_comment(post_id):
    if "username" not in session:
        return jsonify({"error": "Please login first"}), 401
    
    comment = {
        "user_id": session["username"],
        "post_id": post_id,
        "content": request.json["content"],
        "created_at": datetime.now()
    }
    
    comments_collection.insert_one(comment)
    return jsonify({"success": True})

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = verify_user(username, password)
        if user:
            session["username"] = user["username"]
            log_login_activity(username, successful=True)
            flash("Login successful!", "success")
            return redirect(url_for("home"))
        else:
            log_login_activity(username, successful=False)
            flash("Invalid username or password!", "error")
            return redirect(url_for("login"))
    return render_template("login.html")

# Route Logout
@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
