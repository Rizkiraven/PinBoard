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
    if categories_collection.count_documents({}) == 0:
        # Data contoh untuk koleksi kategori
        categories = [
            {"name": "Nature"},
            {"name": "Lifestyle"},
            {"name": "Sea"},
            {"name": "Food"},
            {"name": "Travel"},
            {"name": "Technology"},
            {"name": "Fashion"},
            {"name": "Art"},
            {"name": "Sports"},
            {"name": "Music"},
            {"name": "Education"},
            {"name": "Health"},
            {"name": "Fitness"},
            {"name": "Animals"},
            {"name": "History"},
            {"name": "Business"},
            {"name": "Gaming"},
            {"name": "Photography"},
            {"name": "DIY"},
            {"name": "Gardening"},
            {"name": "Hobbies"},
            {"name": "Events"}
        ]
        categories_collection.insert_many(categories)  # Menyisipkan semua kategori
        print("Database initialized with categories.")

# Panggil fungsi inisialisasi
initialize_database()

# Fungsi untuk membuat pengguna baru
def create_user(username, email, password, nickname) :
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    user = {
        "username": username,
        "email": email,
        "password": hashed_password,
        "nickname": nickname,
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
    
    # Tambahkan informasi likes untuk setiap post
    for post in posts:
        post["_id"] = str(post["_id"])
        # Ambil semua likes untuk post ini
        post_likes = list(likes_collection.find({"post_id": post["_id"]}).sort("created_at", DESCENDING))
        post["likes_count"] = len(post_likes)
        
        # Cek like dari user current
        user_like = next((like for like in post_likes if like["user_id"] == session["username"]), None)
        post["is_liked"] = user_like is not None
        if user_like:
            post["liked_at"] = user_like["created_at"].strftime("%Y-%m-%d %H:%M:%S")
        
        # Ambil 3 user terakhir yang like
        post["recent_likes"] = [{"user_id": like["user_id"], 
                               "liked_at": like["created_at"].strftime("%Y-%m-%d %H:%M:%S")} 
                              for like in post_likes[:3]]
        
        # Ambil comments
        post["comments"] = list(comments_collection.find({"post_id": post["_id"]}).limit(3))
    
    return render_template("home.html", 
                         username=session["username"],
                         posts=posts,
                         categories=categories)

@app.route("/post/<post_id>/likes")
def post_likes(post_id):
    if "username" not in session:
        return redirect(url_for("login"))
        
    likes = list(likes_collection.find({"post_id": post_id}).sort("created_at", DESCENDING))
    likes_with_time = [{
        "user_id": like["user_id"],
        "liked_at": like["created_at"].strftime("%Y-%m-%d %H:%M:%S")
    } for like in likes]
    
    return jsonify(likes_with_time)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        # Periksa apakah username sudah ada
        if users_collection.find_one({"username": username}):
            flash("Username already exists!", "error")
            return redirect(url_for("register"))

        # Set nickname dari username
        nickname = username
        
        # Set waktu pendaftaran
        created_at = datetime.now()

        # Fungsi create_user diubah agar menerima nickname dan created_at
        create_user(username, email, password, nickname)
        
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
                'bio': request.form['bio'],
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
    
    user_id = session["username"]
    current_time = datetime.now()
    
    # Cek apakah post exists
    post = posts_collection.find_one({"_id": ObjectId(post_id)})
    if not post:
        return jsonify({"error": "Post not found"}), 404

    # Cek apakah user sudah like post ini
    existing_like = likes_collection.find_one({
        "user_id": user_id,
        "post_id": post_id
    })
    
    response = {}
    
    if existing_like:
        # Unlike: Hapus like jika sudah ada
        likes_collection.delete_one({"_id": existing_like["_id"]})
        response["action"] = "unliked"
        response["likes_count"] = likes_collection.count_documents({"post_id": post_id})
    else:
        # Like: Tambah like baru dengan timestamp
        like = {
            "user_id": user_id,
            "post_id": post_id,
            "created_at": current_time
        }
        likes_collection.insert_one(like)
        response["action"] = "liked"
        response["likes_count"] = likes_collection.count_documents({"post_id": post_id})
        response["liked_at"] = current_time.strftime("%Y-%m-%d %H:%M:%S")
    
    return jsonify(response)

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
