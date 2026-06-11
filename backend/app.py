from flask import Flask, render_template, request, jsonify, url_for, session,redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

# DATABASE
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///recruitment.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# =========================
# USER TABLE
# =========================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# =========================
# RECRUITER TABLE
# =========================
class Recruiter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'))

    status = db.Column(db.String(50), default="Pending")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
# =========================
# JOB TABLE
# =========================
class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    recruiter_id = db.Column(
        db.Integer,
        db.ForeignKey('recruiter.id')
    )

    title = db.Column(db.String(200))
    company = db.Column(db.String(200))
    location = db.Column(db.String(200))
    salary = db.Column(db.String(100))
    description = db.Column(db.Text)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

# CREATE DB
with app.app_context():
    db.create_all()

# =========================
# HOME
# =========================
@app.route('/')
def home():
    return render_template('login.html')

# =========================
# SIGNUP
# =========================
@app.route('/signup')
def signup():
    return render_template('signup.html')

# =========================
# REGISTER
# =========================
@app.route('/register', methods=['POST'])
def register():

    data = request.get_json()

    fullname = data.get("fullname")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role")

    if role == "user":

        if User.query.filter_by(email=email).first():
            return jsonify({"success": False, "message": "User already exists"})

        db.session.add(User(fullname=fullname, email=email, password=password))
        db.session.commit()

        return jsonify({"success": True, "message": "User registered"})

    elif role == "recruiter":

        if Recruiter.query.filter_by(email=email).first():
            return jsonify({"success": False, "message": "Recruiter already exists"})

        db.session.add(Recruiter(fullname=fullname, email=email, password=password))
        db.session.commit()

        return jsonify({"success": True, "message": "Recruiter registered"})

    return jsonify({"success": False, "message": "Invalid role"})

# =========================
# LOGIN
# =========================
@app.route('/login', methods=['POST'])
def login():

    data = request.get_json()

    email = data.get("email")
    password = data.get("password")
    role = data.get("role")


    # ADMIN
    if email == "mangila.adhikari111@gmail.com" and password == "1234":
        session["role"] = "admin"
        return jsonify({"success": True, "redirect": url_for("admin")})

    # USER
    if role == "user":
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            session["role"] = "user"
            session["user_id"] = user.id
            session["user_name"] = user.fullname
            return jsonify({"success": True, "redirect": url_for("user")})

    # RECRUITER
    if role == "recruiter":
        recruiter = Recruiter.query.filter_by(email=email, password=password).first()
        if recruiter:
            session["role"] = "recruiter"
            session["recruiter_id"] = recruiter.id
            session["recruiter_name"] = recruiter.fullname
            return jsonify({"success": True, "redirect": url_for("recruiter")})

    return jsonify({"success": False, "message": "Invalid credentials"})

@app.route("/create-job", methods=["POST"])
def create_job():

    recruiter_id = session.get("recruiter_id")

    job = Job(
        recruiter_id=recruiter_id,
        title=request.form["title"],
        company=request.form["company"],
        location=request.form["location"],
        salary=request.form["salary"],
        description=request.form["description"]
    )

    db.session.add(job)
    db.session.commit()

    return redirect("/post-jobs")

@app.route("/post-jobs")
def post_jobs():

    recruiter_id = session.get("recruiter_id")

    jobs = Job.query.filter_by(recruiter_id=recruiter_id).all()

    return render_template("recruiter/post_jobs.html", jobs=jobs)

@app.route("/candidates")
def candidates():

    users = User.query.all()

    return render_template("recruiter/candidates.html", users=users)

@app.route("/applications")
def applications():

    recruiter_id = session.get("recruiter_id")

    data = db.session.query(Application, User, Job).join(
        User, Application.user_id == User.id
    ).join(
        Job, Application.job_id == Job.id
    ).filter(
        Job.recruiter_id == recruiter_id
    ).all()

    return render_template("recruiter/applications.html", data=data)

@app.route("/recruiter-profile")
def recruiter_profile():

    if "recruiter_id" not in session:
        return redirect("/")
    recruiter_id = session.get("recruiter_id")
    recruiter = Recruiter.query.get(recruiter_id)

    return render_template("recruiter/recruiter_profile.html",recruiter=recruiter)

@app.route("/jobs")
def jobs():

    jobs = Job.query.all()

    return render_template("users/jobs.html", jobs=jobs)

# ADMIN PAGE
# =========================
@app.route('/admin')
def admin():
    return render_template("admin/admin.html")

@app.route('/user')
def user():
    return render_template("users/user.html")
@app.route("/user-profile")
def user_profile():

    if "user_id" not in session:
        return redirect("/")

    user_id = session.get("user_id")

    user = User.query.get(user_id)

    return render_template(
        "users/user_profile.html",
        user=user)


@app.route('/recruiter')
def recruiter():

    if "recruiter_id" not in session:
        return redirect("/")

    recruiter_id = session.get("recruiter_id")

    total_jobs = Job.query.filter_by(
        recruiter_id=recruiter_id
    ).count()

    total_applications = db.session.query(Application).join(
        Job,
        Application.job_id == Job.id
    ).filter(
        Job.recruiter_id == recruiter_id
    ).count()

    return render_template(
        "recruiter/recruiter.html",
        total_jobs=total_jobs,
        total_applications=total_applications
    )

@app.route("/userbutton")
def userbutton():
    return render_template("admin/userbutton.html")

# =========================
# RECENT USERS (USER + RECRUITER)
# =========================
@app.route("/api/recent-users")
def recent_users():

    users = User.query.all()
    recruiters = Recruiter.query.all()

    combined = []

    for u in users:
        combined.append({
            "name": u.fullname,
            "email": u.email,
            "type": "User",
            "created_at": u.created_at
        })

    for r in recruiters:
        combined.append({
            "name": r.fullname,
            "email": r.email,
            "type": "Recruiter",
            "created_at": r.created_at
        })

    combined.sort(key=lambda x: x["created_at"], reverse=True)

    return jsonify(combined[:10])

@app.route("/my-applications")
def my_applications():

    user_id = session.get("user_id")

    data = db.session.query(Application, Job).join(
        Job, Application.job_id == Job.id
    ).filter(
        Application.user_id == user_id
    ).all()

    return render_template("users/my_applications.html", data=data)

@app.route("/api/user-stats")
def user_stats():

    user_id = session.get("user_id")

    total = Application.query.filter_by(user_id=user_id).count()

    interviews = Application.query.filter_by(
        user_id=user_id,
        status="Shortlisted"
    ).count()

    return jsonify({
        "jobs_applied": total,
        "interviews": interviews,
        "profile_completion": 70,
        "ai_score": 65
    })

@app.route("/api/applications")
def api_applications():

    user_id = session.get("user_id")

    data = db.session.query(Application, Job).join(
        Job, Application.job_id == Job.id
    ).filter(
        Application.user_id == user_id
    ).all()

    result = []

    for app_obj, job in data:
        result.append({
            "company": job.company,
            "role": job.title,
            "status": app_obj.status
        })

    return jsonify(result)

@app.route("/apply/<int:job_id>", methods=["POST"])
def apply_job(job_id):

    user_id = session.get("user_id")

    # prevent duplicate application
    existing = Application.query.filter_by(
        user_id=user_id,
        job_id=job_id
    ).first()

    if existing:
        return redirect("/jobs")

    app_obj = Application(
        user_id=user_id,
        job_id=job_id,
        status="Pending"
    )

    db.session.add(app_obj)
    db.session.commit()

    return redirect("/my-applications")
# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True)