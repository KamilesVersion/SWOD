# -*- coding: utf-8 -*-


from flask import Flask, render_template, url_for, redirect, session, request, flash, jsonify
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
import pytz
from datetime import datetime
from flask_migrate import Migrate

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
    
    # Spotify tokens
    spotify_access_token = db.Column(db.String(255), nullable=True)
    spotify_refresh_token = db.Column(db.String(255), nullable=True)
    spotif_token_expiry = db.Column(db.DateTime, nullable=True)


migrate = Migrate(app, db)

# with app.app_context():
#     db.create_all()





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




def get_spotify_client():
    if current_user.is_authenticated and current_user.spotify_access_token:
        sp_oauth = create_spotify_oauth()
        
        # Tikrina, ar pasibaig� prieigos �etono galiojimo laikas
        if datetime.utcnow() > current_user.spotif_token_expiry:
            new_token_info = sp_oauth.refresh_access_token(current_user.spotify_refresh_token)
            current_user.spotify_access_token = new_token_info["access_token"]
            current_user.spotif_token_expiry = datetime.utcfromtimestamp(new_token_info["expires_at"])
            db.session.commit()  # �ra�ome atnaujintus duomenis � duomen� baz�
        
        return spotipy.Spotify(auth=current_user.spotify_access_token)
    return None


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

# @app.route('/spotify_callback')
# def spotify_callback():
#     sp_oauth = create_spotify_oauth()
    
#     code = request.args.get("code")
    
#     if not code:
#         return "Error: No code received from Spotify.", 400

#     token_info = sp_oauth.get_access_token(code)
    
#     if not token_info:
#         return "Error: Could not get access token form Spotify.", 500
    
#     if current_user.is_authenticated:
#             current_user.spotify_access_token = token_info["access_token"]
#             current_user.spotify_refresh_token = token_info["refresh_token"]
#             current_user.spotif_token_expiry = datetime.utcfromtimestamp(token_info["expires_at"])
            
    
#     session["token_info"] = token_info
#     # gets url where user wanted to go or chooses menu for fallback
#     next_url = session.pop("next_url", url_for("menu"))
#     return redirect(next_url)

@app.route('/spotify_callback')
def spotify_callback():
    sp_oauth = create_spotify_oauth()
    
    code = request.args.get("code")
    
    if not code:
        return "Error: No code received from Spotify.", 400

    try:
        token_info = sp_oauth.get_access_token(code)
    except Exception as e:
        return f"Error: {str(e)}", 500

    if not token_info:
        return "Error: Could not get access token from Spotify.", 500

    if current_user.is_authenticated:
        current_user.spotify_access_token = token_info["access_token"]
        current_user.spotify_refresh_token = token_info["refresh_token"]
        current_user.spotif_token_expiry = datetime.utcfromtimestamp(token_info["expires_at"])
        db.session.commit()

    session["token_info"] = token_info

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
    #sp = spotipy.Spotify(auth=token_info["access_token"])
    #recent_tracks = sp.current_user_recently_played(limit=20)

    sp = get_spotify_client()  # Naudojame get_spotify_client funkcij�
    if sp:
        recent_tracks = sp.current_user_recently_played(limit=20)
    else:
        return redirect(url_for("connect_spotify", next=url_for("recent")))  # Jei n�ra galiojan�io tokeno

    # Define Lithuanian time zone
    lithuania_tz = pytz.timezone('Europe/Vilnius')

    # Extract necessary track details
    tracks = []
    for item in recent_tracks['items']:
        track = item['track']
        
        # Convert played_at to Lithuanian time zone
        played_at_utc = datetime.strptime(item['played_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
        played_at_utc = played_at_utc.replace(tzinfo=pytz.utc)
        played_at_lt = played_at_utc.astimezone(lithuania_tz)

        tracks.append({
            'name': track['name'],
            'artist': ", ".join(artist['name'] for artist in track['artists']),
            'album': track['album']['name'],
            'album_cover': track['album']['images'][0]['url'] if track['album']['images'] else None,
            'played_at': played_at_lt.strftime("%Y-%m-%d %H:%M:%S")  # Format as Lithuanian time
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
    # sp = spotipy.Spotify(auth=token_info["access_token"])
    # user_info = sp.current_user()

    sp = get_spotify_client()  # Naudojame get_spotify_client funkcij�
    if sp:
        user_info = sp.current_user()
    else:
        return redirect(url_for("connect_spotify", next=url_for("profile")))  # Jei n�ra galiojan�io tokeno

    



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

@app.route('/recap')
@login_required
def recap():
    return render_template('recap_page.html')

#LABIAUSIAI KLAUSOMIAUSIA DAINA--------------------------------------------------

@app.route("/most_listened_song")
def most_listened_song():
    token_info = session.get("token_info", None)

    if not token_info:
        return redirect(url_for("login"))

    # sp = spotipy.Spotify(auth=token_info["access_token"])
    
    # # Fetch user's top tracks (long-term, i.e., most listened songs)
    # top_tracks = sp.current_user_top_tracks(limit=1, time_range="long_term")

    # if top_tracks["items"]:
    #     song = top_tracks["items"][0]
    #     song_name = song["name"]
    #     artist_name = song["artists"][0]["name"]
    #     return f"Your most listened song is: {song_name} by {artist_name}"
    
    # return "No listening data found!"

    sp = get_spotify_client()  # Naudojame get_spotify_client funkcij�
    if sp:
        top_tracks = sp.current_user_top_tracks(limit=1, time_range="long_term")
        if top_tracks["items"]:
            song = top_tracks["items"][0]
            return f"Your most listened song is: {song['name']} by {song['artists'][0]['name']}"
        return "No listening data found!"
    else:
        return redirect(url_for("connect_spotify"))  # Jei n�ra galiojan�io tokeno


@app.route("/most_listened_song_json")
def most_listened_song_json():
    # Pirmiausia bandome gauti Spotify klient�
    sp = get_spotify_client()  

    if not sp:
        return {"error": "User not authenticated"}, 401  # Jei n�ra galiojan�io tokeno

    # Gauti top dainas (ilgalaik�s)
    top_tracks = sp.current_user_top_tracks(limit=1, time_range="long_term")

    if top_tracks["items"]:
        song = top_tracks["items"][0]
        return {"song": song["name"], "artist": song["artists"][0]["name"]}

    return {"song": None, "artist": None}


#-------------------------------------------------------------------------------

if(__name__) == '__main__':
    app.run('localhost', 4449, debug = True)


# Pull test