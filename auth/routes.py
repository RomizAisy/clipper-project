from flask import Blueprint, render_template, redirect, session, flash, current_app, url_for, request
from werkzeug.security import generate_password_hash

from models import User, Admin
from extensions import db, mail
from .forms import LoginForm, RegisterForm, AdminLoginForm

from functools import wraps
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Message

auth_bp = Blueprint("auth", __name__)

#Email Verification
def generate_token(email):
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return s.dumps(email, salt="email-verify")

def verify_token(token, expiration=3600):
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return s.loads(token, salt="email-verify", max_age=expiration)

def send_verification_email(user):
    token = generate_token(user.email)

    link = url_for(
        "auth.verify_email",
        token=token,
        _external=True
    )

    msg = Message(
        "Verify your account",
        recipients=[user.email]
    )

    msg.body = f"Click to verify your account: {link}"

    mail.send(msg)

@auth_bp.route("/verify/<token>")
def verify_email(token):
    try:
        email = verify_token(token)
    except:
        return "Invalid or expired token", 400

    user = User.query.filter_by(email=email).first_or_404()

    user.is_verified = True
    db.session.commit()

    return render_template("verify_email.html")

#LOGIN REGISTER LOGOUT

@auth_bp.route('/login', methods=["POST", "GET"])
def login():
    
    if "user_id" in session:
        return redirect('/')
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(
            username = form.username.data,
        ).first() 

        if not user:
            flash("Invalid username or password", "error")
            return render_template("login.html", form=form)

        if not user.is_verified:
            flash("Please verify your email first", "warning")
            return render_template("login.html", form=form)

        if user and user.check_password(form.password.data):
            session.permanent = True
            session["user_id"]  = user.id
            session["username"]  = user.username
            return redirect("/")
        else:
            flash("invalid username or password", "error")
    
    return render_template("login.html", form = form)

@auth_bp.route('/register', methods=["POST", "GET"])
def register():

    form = RegisterForm()
    
    print("METHOD:", request.method)
    if form.validate_on_submit():
        print("VALIDATED")
        if User.query.filter_by(username=form.username.data).first():
            flash("Username already taken", "error")
            return render_template("register.html", form=form)

        if User.query.filter_by(email=form.email.data).first():
            flash("Email already registered", "error")
            return render_template("register.html", form=form)

        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data),
            tokens=0
        )
        db.session.add(user)
        db.session.commit()
        send_verification_email(user)
        flash("Registration successful! Please verify your email.", "success")
        
        return redirect('/login')

    return render_template('register.html', form=form)

@auth_bp.route('/logout')
def logout():
    session.pop("user_id", None)
    session.pop("tokens", None)
    return redirect('/')


#ADMIN MASIH PROGRESS


@auth_bp.route('/admin', methods=["POST", "GET"])
def admin():
    form = AdminLoginForm()
    if form.validate_on_submit():
        
        admin_user = Admin.query.filter_by(
            username = form.username.data
        ).first()

        if admin_user and admin_user.check_password(form.password.data):
            session["admin"] = admin_user.username
            return redirect('/dashboard')
        else:
            flash("invalid username or password", "error")

    return render_template("adminLoginPage.html", form = form)

@auth_bp.route('/adminLogout')
def admin_logout():
    session.pop("admin", None)
    return redirect("/admin")

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "admin" not in session:
            return redirect("/admin")
        return f(*args, **kwargs)
    return decorated_function
  


#=======================================
# ADMIN MASIH PROGRESS
#======================================


@auth_bp.route('/dashboard', methods=["POST", "GET"])
@admin_required
def dashboard():
    if "admin" not in session:
        return redirect('/admin')

    admin = Admin.query.filter_by(
        username=session["admin"]
    ).first()

    return render_template("dashboard.html", admin=admin)

    