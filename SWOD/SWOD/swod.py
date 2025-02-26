from flask import Flask, render_template, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_bcrypt import Bcrypt
import re
from wtforms import ValidationError
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

app = Flask(__name__)

bcrypt = Bcrypt(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'thisisasecretkey'

db = SQLAlchemy(app)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)


with app.app_context():
    db.create_all()


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class RegisterForm(FlaskForm):
    username = StringField(validators=[
        InputRequired(), Length(min=4, max=20)],
        render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[
        InputRequired(), Length(min=8, max=20)],
        render_kw={"placeholder": "Password"})

    submit = SubmitField('Register')

    def validate_username(self, username):
        existing_user = User.query.filter_by(username=username.data).first()
        if existing_user:
            raise ValidationError('That username already exists. Please choose a different one.')

    def validate_password(self, password):
        pwd = password.data
        if (len(pwd) < 8 or 
            not re.search(r'[A-Z]', pwd) or 
            not re.search(r'[!@#$%^&*(),.?":{}|<>]', pwd) or 
            not re.search(r'\d', pwd)):
            raise ValidationError(
                'Password must be at least 8 characters long, contain at least one uppercase letter, one special symbol, and one number.')

class LoginForm(FlaskForm):
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField('Login')

@app.route('/')
def home():
    return render_template('home.html')

    
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('menu'))
            else:
                form.password.errors.append("Netinkamas slaptazodis.")
        else:
            form.username.errors.append("Tokios paskyros su vartotojo vardu nera.")
    return render_template('login.html', form=form)




@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        new_user = User(username=form.username.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        # Log the user in after registration
        login_user(new_user)
        return redirect(url_for('connect_spotify'))

    return render_template('register.html', form=form)

@app.route('/menu')
def menu():
    return render_template('menuPage.html')

# @app.route('/menu-page')
# def menuPage():
#     return render_template('menuPage.html')

@app.route('/connect_spotify')
def connect_spotify():
    sp_oauth = create_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/recent')
def recent():
    return render_template('recent.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')

def create_spotify_oauth():
    return SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=url_for("menu", _external=True),
        scope="user-top-read user-read-recently-played")

# # EDIT PROFILE FEATURE START

# # Edit Profile Form
# class EditProfileForm(FlaskForm):
#     username = StringField(validators=[Length(min=4, max=20)], render_kw={"placeholder": "New Username"})
#     password = PasswordField(validators=[Length(min=8, max=20)], render_kw={"placeholder": "New Password"})
#     submit = SubmitField('Update Profile')

# @app.route('/edit-profile', methods=['GET', 'POST'])
# @login_required
# def edit_profile():
#     form = EditProfileForm()

#     if request.method == 'POST' and form.validate_on_submit():
#         if form.username.data:
#             existing_user = User.query.filter_by(username=form.username.data).first()
#             if existing_user and existing_user.id != current_user.id:
#                 flash('Username already taken. Choose another one.', 'danger')
#             else:
#                 current_user.username = form.username.data

#         if form.password.data:
#             hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
#             current_user.password = hashed_password

#         db.session.commit()
#         flash('Profile updated successfully!', 'success')
#         return redirect(url_for('edit_profile'))

#     return render_template('edit_profile.html', form=form)

# # EDIT PROFILE FEATURE END

if(__name__) == '__main__':
    app.run('localhost', 4449, debug = True)