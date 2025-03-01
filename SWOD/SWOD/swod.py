from flask import Flask, render_template, url_for, redirect, session, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError, Optional
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
                form.password.errors.append("Invalid password.")
        else:
            form.username.errors.append("No account exists with this username.")
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
    session["next_url"] = request.args.get("next", url_for("menu")) # Stores the target (where user wants to go) page URL
    sp_oauth = create_spotify_oauth()
   
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/spotify_callback')
def spotify_callback():
    sp_oauth = create_spotify_oauth()
    
    code = request.args.get("code")
    
    if not code:
        return "Error: No code received from Spotify.", 400

    token_info = sp_oauth.get_access_token(code)
    
    if not token_info:
        return "Error: Could not get access token form Spotify.", 500
    
    session["token_info"] = token_info
    # gets url where user wanted to go or chooses menu for fallback
    next_url = session.pop("next_url", url_for("menu"))
    return redirect(next_url)

@app.route('/recent')
@login_required
def recent():
    token_info = session.get("token_info", None)
    if not token_info:
        return redirect(url_for("connect_spotify", next=url_for("recent")))

    # Refresh token if expired
    sp_oauth = create_spotify_oauth()
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
        session["token_info"] = token_info  # Save the new token

    # Fetch last 20 played tracks
    sp = spotipy.Spotify(auth=token_info["access_token"])
    recent_tracks = sp.current_user_recently_played(limit=20)

    # Extract necessary track details
    tracks = []
    for item in recent_tracks['items']:
        track = item['track']
        tracks.append({
            'name': track['name'],
            'artist': ", ".join(artist['name'] for artist in track['artists']),
            'album': track['album']['name'],
            'album_cover': track['album']['images'][0]['url'] if track['album']['images'] else None,
            'played_at': item['played_at']
        })

    return render_template('recent.html', tracks=tracks)


@app.route('/profile')
@login_required
def profile():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
     
    token_info = session.get("token_info", None)
    if not token_info:
        return redirect(url_for("connect_spotify", next=url_for("profile")))
    # Refresh token if expired
    sp_oauth = create_spotify_oauth()
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
        session["token_info"] = token_info # Save the new token

    # Use the access token to fetch user details
    sp = spotipy.Spotify(auth=token_info["access_token"])
    user_info = sp.current_user()
    return render_template('profile.html', 
                           user=user_info["display_name"], # spotify name
                           profile_pic=user_info["images"][0]["url"] if user_info["images"] else None,
                           username=current_user.username,
                           spotify_logged_in=True) 

def create_spotify_oauth():
    return SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=url_for("spotify_callback", _external=True),
        scope="user-top-read user-read-recently-played",
        show_dialog=True)

class UpdateAccountForm(FlaskForm):
    new_username = StringField(
        validators=[Optional(), Length(min=4, max=20)],
        render_kw={"placeholder": "New Username"}
    )

    new_password = PasswordField(
        validators=[Optional(), Length(min=8, max=20)],
        render_kw={"placeholder": "New Password"}
    )

    submit = SubmitField('Update')

    def validate_new_username(self, new_username):
        if new_username.data and new_username.data != current_user.username:
            existing_user = User.query.filter_by(username=new_username.data).first()
            if existing_user:
                raise ValidationError('That username is already taken. Please choose another.')

    def validate_new_password(self, new_password):
        if new_password.data:  # Only validate if a new password is entered
            pwd = new_password.data
            if (len(pwd) < 8 or 
                not re.search(r'[A-Z]', pwd) or 
                not re.search(r'[!@#$%^&*(),.?":{}|<>]', pwd) or 
                not re.search(r'\d', pwd)):
                raise ValidationError(
                    'Password must be at least 8 characters long, contain at least one uppercase letter, one special symbol, and one number.')

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = UpdateAccountForm()

    if form.validate_on_submit():
        # Update username only if it's provided
        if form.new_username.data:
            current_user.username = form.new_username.data

        # Update password only if it's provided
        if form.new_password.data:
            hashed_password = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')
            current_user.password = hashed_password

        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('login'))  # Redirect after successful update

    return render_template('edit_profile.html', form=form)

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/remove', methods=['GET', 'POST'])
@login_required
def remove():
    #deleting from database
    db.session.delete(current_user)
    db.session.commit()
    
    logout_user()
    session.clear() # Clear any remaining session data
    return redirect(url_for('home'))

if(__name__) == '__main__':
    app.run('localhost', 4449, debug = True)