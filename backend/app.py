from flask import Flask, render_template, request, jsonify, url_for, session,redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from pdfminer.high_level import extract_text
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from PIL import Image
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecretkey"

# RESUME UPLOAD
UPLOAD_FOLDER = "static/resumes"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# PROFILE PICTURE UPLOAD
PROFILE_FOLDER = "static/profile_pics"
app.config["PROFILE_FOLDER"] = PROFILE_FOLDER
os.makedirs(PROFILE_FOLDER, exist_ok=True)

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

    profile_pic = db.Column(db.String(200), default="default.png")

    phone = db.Column(db.String(20))
    location = db.Column(db.String(100))
    dob = db.Column(db.Date)

    headline = db.Column(db.String(150))
    skills = db.Column(db.Text)
    education = db.Column(db.Text)
    experience = db.Column(db.Text)

    resume = db.Column(db.String(255))
    resume_text = db.Column(db.Text)

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
    resume = db.Column(db.String(255))
    status = db.Column(db.String(50), default="Pending")
    similarity_score = db.Column(db.Float, default=0.0)
    skill_score = db.Column(db.Float, default=0.0)
    experience_score = db.Column(db.Float, default=0.0)
    final_score = db.Column(db.Float, default=0.0)
    match_label = db.Column(db.String(50))
    
    interview_status = db.Column(db.String(20),default="Not Scheduled")
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

    created_at = db.Column(db.DateTime,default=datetime.utcnow)

# AI HELPERS
def extract_pdf_text(filepath):
    try:
        return extract_text(filepath)
    except:
        return ""


import re

COMMON_SKILLS = {
    "python", "java", "c", "c++", "javascript", "html", "css",
    "sql", "mysql", "flask", "django", "react", "node",
    "machine learning", "tensorflow", "pandas",
    "numpy", "git", "linux", "aws"
}


def extract_skills(text):
    text = text.lower()
    skills = set()

    for skill in COMMON_SKILLS:
        if skill in text:
            skills.add(skill)

    return skills


def skill_match_score(resume_text, job_text):
    resume_skills = extract_skills(resume_text)
    job_skills = extract_skills(job_text)

    if len(job_skills) == 0:
        return 0

    matched = resume_skills.intersection(job_skills)

    return round((len(matched) / len(job_skills)) * 100, 2)


def experience_score(resume_text):
    resume_text = resume_text.lower()

    match = re.search(r'(\d+)\+?\s*(year|years)', resume_text)

    if not match:
        return 0

    years = int(match.group(1))

    if years >= 10:
        return 100

    return years * 10

def calculate_similarity(resume_text, job_text):

    if not resume_text or not job_text:
        return {
            "similarity": 0,
            "skill_score": 0,
            "experience_score": 0,
            "final_score": 0
        }

    resume_text = resume_text.lower()
    job_text = job_text.lower()

    docs = [resume_text, job_text]

    tfidf = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1,2),
        max_features=5000
    )

    matrix = tfidf.fit_transform(docs)
    similarity = cosine_similarity(matrix[0:1], matrix[1:2])[0][0] * 100
    skill_score = skill_match_score(resume_text, job_text)
    experience = experience_score(resume_text)

    final_score = (
        similarity * 0.60 +
        skill_score * 0.25 +
        experience * 0.15
    )

    return {
        "similarity": round(similarity,2),
        "skill_score": round(skill_score,2),
        "experience_score": round(experience,2),
        "final_score": round(final_score,2)
    }

# CREATE DB
with app.app_context():
    db.create_all()
#------------------------------------------------------------------------------
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg"}
def allowed_image(filename):
    return ("." in filename
        and filename.rsplit(".",1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS)
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

        hashed_password = generate_password_hash(password)

        db.session.add(User(fullname=fullname,email=email,password=hashed_password))
        db.session.commit()

        return jsonify({"success": True, "message": "User registered"})

    elif role == "recruiter":

        if Recruiter.query.filter_by(email=email).first():
            return jsonify({"success": False, "message": "Recruiter already exists"})

        hashed_password = generate_password_hash(password)

        db.session.add(Recruiter(fullname=fullname,email=email,password=hashed_password ))
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
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session["role"] = "user"
            session["user_id"] = user.id
            session["user_name"] = user.fullname
            return jsonify({ "success": True, "redirect": url_for("user") })

    # RECRUITER
    if role == "recruiter":
        recruiter = Recruiter.query.filter_by(email=email).first()

        if recruiter and check_password_hash(recruiter.password, password):
            session["role"] = "recruiter"
            session["recruiter_id"] = recruiter.id
            session["recruiter_name"] = recruiter.fullname
            return jsonify({"success": True,"redirect": url_for("recruiter") })
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
    data = db.session.query(Application, User, Job).join(User, Application.user_id == User.id).join(Job, Application.job_id == Job.id).filter(Job.recruiter_id == recruiter_id).order_by(Application.final_score.desc())

    return render_template("recruiter/applications.html", data=data)

@app.route("/schedule-interview/<int:app_id>", methods=["POST"])
def schedule_interview(app_id):
    application = Application.query.get_or_404(app_id)
    if application.interview_status != "Scheduled":
        application.interview_status = "Scheduled"
        db.session.commit()

    return redirect("/shortlisted")

@app.route("/interviews")
def interviews():

    recruiter_id = session.get("recruiter_id")

    data = db.session.query(Application,
        User,Job).join(
        User, Application.user_id == User.id).join(
        Job, Application.job_id == Job.id).filter(
        Job.recruiter_id == recruiter_id,
        Application.interview_status == "Scheduled").all()

    return render_template(
        "recruiter/interviews.html",data=data)

@app.route("/recruiter-profile")
def recruiter_profile():

    if "recruiter_id" not in session:
        return redirect("/")
    recruiter_id = session.get("recruiter_id")
    recruiter = Recruiter.query.get(recruiter_id)

    return render_template("recruiter/recruiter_profile.html",recruiter=recruiter)


@app.route("/recruiter/<int:recruiter_id>")
def recruiter_details(recruiter_id):

    recruiter = Recruiter.query.get_or_404(recruiter_id)

    return render_template(
        "recruiter/recruiter_profile.html",
        recruiter=recruiter
    )


@app.route("/jobs")
def jobs():
    jobs = Job.query.all()
    applied_jobs = []
    if "user_id" in session:
        user_id = session["user_id"]

        applied_jobs = [app.job_id
            for app in Application.query.filter_by(user_id=user_id).all()]

    return render_template("users/jobs.html",jobs=jobs,
        applied_jobs=applied_jobs)

# ADMIN PAGE
# =========================
@app.route('/admin')
def admin():
    total_users = User.query.count()
    total_recruiters = Recruiter.query.count()
    total_jobs = Job.query.count()

    return render_template("admin/admin.html",
        total_users=total_users,
        total_recruiters=total_recruiters,
        total_jobs=total_jobs)

@app.route("/recruiters")
def recruiters():
    recruiters = Recruiter.query.all()

    return render_template("admin/recruiters.html",recruiters=recruiters)

@app.route("/admin-jobs")
def admin_jobs():
    jobs = db.session.query(Job,Recruiter).join(Recruiter, Job.recruiter_id == Recruiter.id).all()
    return render_template( "admin/jobs.html",jobs=jobs)

@app.route("/users")
def users():
    users = User.query.all()
    return render_template( "admin/users.html", users=users)

@app.route("/api/recent-users")
def recent_users():
    users = User.query.all()
    recruiters = Recruiter.query.all()
    combined = []
    for u in users:
        combined.append({"name": u.fullname,"email": u.email,"type": "User","created_at": u.created_at})

    for r in recruiters:
        combined.append({
            "name": r.fullname,
            "email": r.email,
            "type": "Recruiter",
            "created_at": r.created_at})

    combined.sort(key=lambda x: x["created_at"], reverse=True)
    return jsonify(combined[:10])   # latest 10
#==========================================================
@app.route('/user')
def user():
    return render_template("users/user.html")
@app.route("/profile")
def profile():

    if "user_id" not in session:
        return redirect("/")

    user = User.query.get(session["user_id"])

    total_applications = Application.query.filter_by(user_id=user.id).count()
    shortlisted = Application.query.filter_by(user_id=user.id,status="Shortlisted").count()
    pending = Application.query.filter_by(user_id=user.id,status="Pending").count()
    rejected = Application.query.filter_by(user_id=user.id,status="Rejected").count()

    return render_template("users/profile.html",user=user,total_applications=total_applications,
        shortlisted=shortlisted,pending=pending,rejected=rejected)


@app.route("/user/<int:user_id>")
def admin_user_profile(user_id):

    user = User.query.get_or_404(user_id)

    return render_template(
        "recruiter/candidate_profile.html",
        user=user
    )

@app.route("/edit-profile", methods=["GET","POST"])
def edit_profile():
    if "user_id" not in session:
        return redirect("/")

    user = User.query.get(session["user_id"])
    if request.method == "POST":

        user.fullname = request.form["fullname"]
        user.phone = request.form["phone"]
        user.location = request.form["location"]
        user.headline = request.form["headline"]
        user.skills = request.form["skills"]
        user.education = request.form["education"]
        user.experience = request.form["experience"]
        dob = request.form.get("dob")

        if dob:
            user.dob = datetime.strptime(dob,"%Y-%m-%d").date()

        picture = request.files.get("profile_pic")

        if picture and picture.filename != "":
            if allowed_image(picture.filename):

                filename = secure_filename(picture.filename)
                filename = f"user_{user.id}_{filename}"

                filepath = os.path.join(app.config["PROFILE_FOLDER"], filename)
                picture.save(filepath)

                user.profile_pic = filename

            else:
                return render_template("users/edit_profile.html", user=user, error="Only PNG, JPG and JPEG images are allowed.")

        db.session.commit()
        return redirect("/profile")
    return render_template("users/edit_profile.html", user=user)

@app.route("/my-interviews")
def my_interviews():
    if "user_id" not in session:
        return redirect("/")

    user_id = session["user_id"]

    interviews = db.session.query(Application,Job,Recruiter).join(
        Job, Application.job_id == Job.id
    ).join(Recruiter, Job.recruiter_id == Recruiter.id).filter(
        Application.user_id == user_id,Application.interview_status == "Scheduled").all()

    return render_template("users/my_interviews.html",interviews=interviews)

@app.route("/resume", methods=["GET", "POST"])
def resume():

    if "user_id" not in session:
        return redirect("/")
    user = User.query.get(session["user_id"])

    if request.method == "POST":
        file = request.files.get("resume")

        if file and file.filename != "":
            if not file.filename.lower().endswith(".pdf"):
                return "Only PDF resumes are allowed."

            filename = secure_filename(file.filename)
            filename = f"{user.id}_{filename}"

            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            user.resume = filename
            user.resume_text = extract_pdf_text(filepath)

            db.session.commit()

        return redirect("/resume")

    # THIS IS MISSING
    return render_template( "users/resume.html",user=user)

@app.route("/api/profile-completion")
def profile_completion():

    if "user_id" not in session:
        return jsonify({"completion": 0})

    user = User.query.get(session["user_id"])

    fields = [
        user.phone,
        user.location,
        user.dob,
        user.headline,
        user.skills,
        user.education,
        user.experience,
        user.resume,
        user.profile_pic
    ]

    filled = sum(1 for field in fields if field)

    percent = round((filled / len(fields)) * 100)

    return jsonify({"completion": percent})

@app.route("/api/user-stats")
def user_stats():

    user_id = session.get("user_id")

    if not user_id:
        return jsonify({"error": "User not logged in"}), 401

    user = User.query.get(user_id)

    total = Application.query.filter_by(user_id=user_id).count()

    interviews = Application.query.filter_by(
        user_id=user_id,
        interview_status="Scheduled"
    ).count()

    fields = [
        user.phone,
        user.location,
        user.dob,
        user.headline,
        user.skills,
        user.education,
        user.experience,
        user.resume,
        user.profile_pic if user.profile_pic != "default.png" else None
    ]

    filled = sum(1 for field in fields if field)
    completion = round((filled / len(fields)) * 100)

    return jsonify({
        "jobs_applied": total,
        "interviews": interviews,
        "profile_completion": completion,
        "ai_score": 65
    })

#=======================================================================
@app.route('/recruiter')
def recruiter():
    if "recruiter_id" not in session:
        return redirect("/")

    recruiter_id = session.get("recruiter_id")
    total_jobs = Job.query.filter_by(recruiter_id=recruiter_id).count()

    total_applications = db.session.query(Application).join(Job,
        Application.job_id == Job.id).filter(
        Job.recruiter_id == recruiter_id).count()

    shortlisted_count = db.session.query(Application).join(Job,
        Application.job_id == Job.id
    ).filter(Job.recruiter_id == recruiter_id,
        Application.status == "Shortlisted").count()
    
    interview_count = db.session.query(Application).join(
    Job,Application.job_id == Job.id).filter(
    Job.recruiter_id == recruiter_id,
    Application.interview_status == "Scheduled").count()

    return render_template( "recruiter/recruiter.html",
    total_jobs=total_jobs, total_applications=total_applications,
    shortlisted_count=shortlisted_count,
    interview_count=interview_count )


@app.route("/posted-jobs")
def posted_jobs():
    recruiter_id = session.get("recruiter_id")
    jobs = Job.query.filter_by(recruiter_id=recruiter_id).all()

    return render_template("recruiter/posted_jobs.html", jobs=jobs)

@app.route("/edit-job/<int:job_id>", methods=["GET", "POST"])
def edit_job(job_id):

    job = Job.query.get_or_404(job_id)

    if request.method == "POST":

        job.title = request.form["title"]
        job.company = request.form["company"]
        job.location = request.form["location"]
        job.salary = request.form["salary"]
        job.description = request.form["description"]

        db.session.commit()

        return redirect("/posted-jobs")

    return render_template(
        "recruiter/edit_job.html",
        job=job
    )

@app.route("/delete-job/<int:job_id>", methods=["POST"])
def delete_job(job_id):

    job = Job.query.get_or_404(job_id)

    db.session.delete(job)
    db.session.commit()

    return redirect("/posted-jobs")

@app.route("/candidate/<int:user_id>")
def candidate_profile(user_id):
    user = User.query.get_or_404(user_id)

    return render_template( "recruiter/candidate_profile.html",user=user)

@app.route("/my-applications")
def my_applications():

    user_id = session.get("user_id")

    data = db.session.query(Application, Job).join(
        Job, Application.job_id == Job.id).filter(
        Application.user_id == user_id).all()

    return render_template("users/my_applications.html", data=data)

@app.route("/shortlisted")
def shortlisted():

    recruiter_id = session.get("recruiter_id")

    data = db.session.query(Application, User, Job).join(
        User, Application.user_id == User.id).join( Job, Application.job_id == Job.id).filter(
        Job.recruiter_id == recruiter_id,
        Application.status == "Shortlisted").all()

    return render_template( "recruiter/shortlisted.html",data=data )


@app.route("/api/applications")
def api_applications():

    user_id = session.get("user_id")

    data = db.session.query(Application, Job).join(
        Job, Application.job_id == Job.id).filter(
        Application.user_id == user_id).all()

    result = []
    for app_obj, job in data:
        result.append({"company": job.company,
            "role": job.title,
            "status": app_obj.status})

    return jsonify(result)


@app.route("/update-application/<int:app_id>", methods=["POST"])
def update_application(app_id):

    app_obj = Application.query.get(app_id)
    app_obj.status = request.form["status"]

    db.session.commit()
    return redirect("/applications")

def get_recommendation(score):
    if score >= 90:
        return "⭐ Excellent Match"
    elif score >= 75:
        return "✅ Good Match"
    elif score >= 60:
        return "⚠ Fair Match"
    else:
        return "❌ Low Match"


@app.route("/apply/<int:job_id>", methods=["POST"])
def apply_job(job_id):

    user_id = session.get("user_id")
    user = User.query.get(user_id)

    if not user:
        return redirect("/login")

    existing = Application.query.filter_by(
        user_id=user_id,
        job_id=job_id
    ).first()

    if existing:
        return redirect("/jobs")

    job = Job.query.get(job_id)

    # AI MATCHING
    job_text = job.title + " " + job.description
    resume_text = user.resume_text or ""

    scores = calculate_similarity(resume_text, job_text)

    similarity = scores["similarity"]
    skill_score = scores["skill_score"]
    experience = scores["experience_score"]
    final_score = scores["final_score"]

    label = get_recommendation(final_score)

    app_obj = Application(
        user_id=user_id,
        job_id=job_id,
        resume=user.resume,
        status="Pending",

        similarity_score=similarity,
        skill_score=skill_score,
        experience_score=experience,
        final_score=final_score,

        match_label=label
    )

    db.session.add(app_obj)
    db.session.commit()

    return redirect("/my-applications")


@app.route("/recalculate-scores")
def recalculate_scores():

    applications = Application.query.all()

    for app_obj in applications:

        user = User.query.get(app_obj.user_id)
        job = Job.query.get(app_obj.job_id)

        if not user or not job:
            continue

        resume_text = user.resume_text or ""
        job_text = job.title + " " + job.description

        scores = calculate_similarity(resume_text, job_text)

        app_obj.similarity_score = scores["similarity"]
        app_obj.skill_score = scores["skill_score"]
        app_obj.experience_score = scores["experience_score"]
        app_obj.final_score = scores["final_score"]
        app_obj.match_label = get_recommendation(scores["final_score"])

    db.session.commit()

    return jsonify({"message": "All scores recalculated successfully"})

@app.route("/delete-user/<int:user_id>", methods=["POST"])
def delete_user(user_id):

    user = User.query.get_or_404(user_id)

    # Delete applications submitted by this user
    Application.query.filter_by(user_id=user.id).delete()

    db.session.delete(user)
    db.session.commit()

    return redirect(url_for("users"))

@app.route("/delete-recruiter/<int:recruiter_id>", methods=["POST"])
def delete_recruiter(recruiter_id):

    recruiter = Recruiter.query.get_or_404(recruiter_id)

    jobs = Job.query.filter_by(recruiter_id=recruiter.id).all()

    for job in jobs:
        Application.query.filter_by(job_id=job.id).delete()
        db.session.delete(job)

    db.session.delete(recruiter)
    db.session.commit()

    return redirect(url_for("recruiters"))
#==============================================================
@app.route("/logout")
def logout():
    session.clear()      # Clears all session data
    return redirect("/") # Redirects to the login page

# RUN
if __name__ == "__main__":
    app.run(debug=True)