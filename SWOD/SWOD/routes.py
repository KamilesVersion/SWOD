# from flask import Blueprint, render_template, redirect, url_for, request, flash
# from flask_login import login_user, login_required, logout_user, current_user
# from flask_bcrypt import Bcrypt
# from models import db, User
# from forms import RegisterForm, LoginForm

# # Create a Blueprint for routes
# routes = Blueprint('routes', __name__)  

# bcrypt = Bcrypt()  # Initialize Bcrypt for password hashing

# # --------------------------- HOME ROUTE ---------------------------
# @routes.route('/')
# def home():
#     return render_template('home.html')

# # --------------------------- LOGIN ROUTE ---------------------------
# @routes.route('/login', methods=['GET', 'POST'])
# def login():
#     form = LoginForm()
#     if form.validate_on_submit():
#         user = User.query.filter_by(username=form.username.data).first()
#         if user and bcrypt.check_password_hash(user.password, form.password.data):
#             login_user(user)
#             return redirect(url_for('routes.menu'))  # Fix: use 'routes.menu'
#         else:
#             flash("Invalid username or password", "danger")
#     return render_template('login.html', form=form)

# # --------------------------- REGISTER ROUTE ---------------------------
# @routes.route('/register', methods=['GET', 'POST'])
# def register():
#     form = RegisterForm()
#     if form.validate_on_submit():
#         hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
#         new_user = User(username=form.username.data, password=hashed_password)
#         db.session.add(new_user)
#         db.session.commit()
#         login_user(new_user)
#         return redirect(url_for('routes.connect_spotify'))  # Adjusted for Blueprint

#     return render_template('register.html', form=form)
