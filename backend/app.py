from flask import Flask, render_template, request, jsonify, url_for

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    # 🔥 ADMIN LOGIN (YOUR REQUIREMENT)
    if email == "mangila.adhikari111@gmail.com" and password == "1234":
        return jsonify({"redirect": url_for("admin")})

    # fallback (optional)
    return jsonify({"redirect": url_for("home")})


@app.route('/admin')
def admin():
    return render_template("admin.html")


@app.route('/user')
def user():
    return render_template("user.html")


@app.route('/recruiter')
def recruiter():
    return render_template("recruiter.html")


if __name__ == "__main__":
    app.run(debug=True)