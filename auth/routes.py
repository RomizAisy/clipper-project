from flask import Blueprint, render_template, redirect, session, flash
from werkzeug.security import generate_password_hash

from models import User, Admin
from extensions import db
from .forms import LoginForm, RegisterForm, AdminLoginForm

from functools import wraps

auth_bp = Blueprint("auth", __name__)

@auth_bp.route('/login', methods=["POST", "GET"])
def login():

    if "user_id" in session:
        return redirect('/')
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(
            username = form.username.data,
        ).first() 

        if user and user.check_password(form.password.data):
            session.permanent = True
            session["user_id"]  = user.id
            session["username"]  = user.username
            return redirect("/")
        else:
            flash("invalid username or password", "error")
    
    return render_template("login.html", form = form)

@auth_bp.route('/register', methods = ["POST", "GET"])
def register():

    form = RegisterForm()

    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data),
            tokens = 0
        )
        db.session.add(user)
        db.session.commit()
        return redirect('/login')

    return render_template('register.html', form=form)

@auth_bp.route('/logout')
def logout():
    session.pop("user_id", None)
    session.pop("tokens", None)
    return redirect('/')


#ADMIN


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
# ADMIN
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

    