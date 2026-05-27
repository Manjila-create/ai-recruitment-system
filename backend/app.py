from flask import Flask, render_template, request, jsonify, url_for, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.secret_key = "supersecretkey"

# DATABASE CONFIG
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///recruitment.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# USER TABLE

class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    fullname = db.Column(db.String(100), nullable=False)

    email = db.Column(db.String(100), unique=True, nullable=False)

    password = db.Column(db.String(100), nullable=False)



# RECRUITER TABLE

class Recruiter(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    fullname = db.Column(db.String(100), nullable=False)

    email = db.Column(db.String(100), unique=True, nullable=False)

    password = db.Column(db.String(100), nullable=False)

# CREATE DATABASE
with app.app_context():
    db.create_all()



# HOME PAGE

@app.route('/')
def home():
    return render_template('login.html')



# SIGNUP PAGE

@app.route('/signup')
def signup():
    return render_template('signup.html')



# REGISTER USER

@app.route('/register', methods=['POST'])
def register():

    data = request.get_json()

    fullname = data.get("fullname")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role")

   
    # USER REGISTRATION
 
    if role == "user":

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            return jsonify({
                "success": False,
                "message": "User already exists"
            })

        new_user = User(
            fullname=fullname,
            email=email,
            password=password
        )

        db.session.add(new_user)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "User registration successful"
        })


   
    # RECRUITER REGISTRATION
 
    elif role == "recruiter":

        existing_recruiter = Recruiter.query.filter_by(email=email).first()

        if existing_recruiter:
            return jsonify({
                "success": False,
                "message": "Recruiter already exists"
            })

        new_recruiter = Recruiter(
            fullname=fullname,
            email=email,
            password=password
        )

        db.session.add(new_recruiter)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Recruiter registration successful"
        })

    return jsonify({
        "success": False,
        "message": "Invalid role"
    })


# LOGIN

@app.route('/login', methods=['POST'])
def login():

    data = request.get_json()

    email = data.get("email")
    password = data.get("password")
    role = data.get("role")


    # ADMIN LOGIN
    
    if email == "mangila.adhikari111@gmail.com" and password == "1234":

        session["role"] = "admin"

        return jsonify({
            "success": True,
            "redirect": url_for("admin")
        })

   
    # USER LOGIN
   
    if role == "user":

        user = User.query.filter_by(
            email=email,
            password=password
        ).first()

        if user:

            session["role"] = "user"

            return jsonify({
                "success": True,
                "redirect": url_for("user")
            })

    
    # RECRUITER LOGIN
    
    elif role == "recruiter":

        recruiter = Recruiter.query.filter_by(
            email=email,
            password=password
        ).first()

        if recruiter:

            session["role"] = "recruiter"

            return jsonify({
                "success": True,
                "redirect": url_for("recruiter")
            })

    return jsonify({
        "success": False,
        "message": "Invalid credentials"
    })


# PAGES

@app.route('/admin')
def admin():
    return render_template("admin.html")


@app.route('/user')
def user():
    return render_template("user.html")


@app.route('/recruiter')
def recruiter():
    return render_template("recruiter.html")



# RUN APP

if __name__ == "__main__":
    app.run(debug=True)