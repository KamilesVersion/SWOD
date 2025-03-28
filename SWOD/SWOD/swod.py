from turtle import listen
from forms import RegisterForm, LoginForm, UpdateAccountForm
from tkinter import N
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
from datetime import datetime, timedelta
from flask_migrate import Migrate
from collections import Counter
from models import db, User, ListeningHistory



load_dotenv() # Load environment variables from .env file

app = Flask(__name__)

bcrypt = Bcrypt(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'thisisasecretkey'

# db = SQLAlchemy(app)


# class User(db.Model, UserMixin):
#     id = db.Column(db.Integer, primary_key=True)
#     username = db.Column(db.String(20), nullable=False, unique=True)
#     password = db.Column(db.String(80), nullable=False)
    
#     # Spotify tokens
#     spotify_access_token = db.Column(db.String(255), nullable=True)
#     spotify_refresh_token = db.Column(db.String(255), nullable=True)
#     spotif_token_expiry = db.Column(db.DateTime, nullable=True)
    

# # -------------------------------------------------------------- klausymo baze
    
# class ListeningHistory(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) 
#     artist_name = db.Column(db.String(255), nullable=False)
#     track_name = db.Column(db.String(255), nullable=False)
#     album_name = db.Column(db.String(255), nullable=False)
#     duration_ms = db.Column(db.Integer, nullable=False)
#     played_at = db.Column(db.DateTime, nullable=False)
#     genre = db.Column(db.String(255), nullable=True)

#     user = db.relationship('User', backref=db.backref('listening_history', lazy=True))

db.init_app(app)


# migrate = Migrate(app, db)

with app.app_context():
    db.create_all()


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# class RegisterForm(FlaskForm):
#     username = StringField(validators=[
#         InputRequired(), Length(min=4, max=20)],
#         render_kw={"placeholder": "Username"})

#     password = PasswordField(validators=[
#         InputRequired(), Length(min=8, max=20)],
#         render_kw={"placeholder": "Password"})

#     submit = SubmitField('Register')

#     def validate_username(self, username):
#         existing_user = User.query.filter_by(username=username.data).first()
#         if existing_user:
#             raise ValidationError('That username already exists. Please choose a different one.')

#     def validate_password(self, password):
#         pwd = password.data
#         if (len(pwd) < 8 or 
#             not re.search(r'[A-Z]', pwd) or 
#             not re.search(r'[!@#$%^&*(),. ":{}|<>]', pwd) or 
#             not re.search(r'\d', pwd)):
#             raise ValidationError(
#                 'Password must be at least 8 characters long, contain at least one uppercase letter, one special symbol, and one number.')

# class LoginForm(FlaskForm):
#     username = StringField(validators=[
#                            InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

#     password = PasswordField(validators=[
#                              InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})

#     submit = SubmitField('Login')




def get_spotify_client():
    if current_user.is_authenticated and current_user.spotify_access_token:
        sp_oauth = create_spotify_oauth()
        
        # Tikrina, ar pasibaig  prieigos  etono galiojimo laikas
        if datetime.utcnow() > current_user.spotif_token_expiry:
            new_token_info = sp_oauth.refresh_access_token(current_user.spotify_refresh_token)
            current_user.spotify_access_token = new_token_info["access_token"]
            current_user.spotif_token_expiry = datetime.utcfromtimestamp(new_token_info["expires_at"])
            db.session.commit()  #  ra ome atnaujintus duomenis   duomen  baz 
        
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
@login_required
def menu():
    token_info = session.get("token_info", None)
    if not token_info:
        return redirect(url_for("connect_spotify", next=url_for("menu")))

    sp_oauth = create_spotify_oauth()
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
        session["token_info"] = token_info

    sp = get_spotify_client()
    if not sp:
        return redirect(url_for("connect_spotify", next=url_for("menu")))

    update_listening_history(sp, current_user.id)  # Call common function

    return render_template('menuPage.html')


# @app.route('/menu-page')
# def menuPage():
#     return render_template('menuPage.html')

# @app.route('/connect_spotify')
# def connect_spotify():
#     session["next_url"] = request.args.get("next", url_for("menu")) # Stores the target (where user wants to go) page URL
#     sp_oauth = create_spotify_oauth()
   
#     auth_url = sp_oauth.get_authorize_url()
#     return redirect(auth_url)

@app.route('/connect_spotify')
def connect_spotify():
    session["next_url"] = request.args.get("next", url_for("menu"))
    sp_oauth = create_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    
    # Store the time when the user connected Spotify
    if current_user.is_authenticated:
        current_user.spotify_connected_at = datetime.utcnow().replace(tzinfo=pytz.utc)
        db.session.commit()
    
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



# @app.route('/recent')
# @login_required
# def recent():
#     token_info = session.get("token_info", None)
#     if not token_info:
#         return redirect(url_for("connect_spotify", next=url_for("recent")))

#     # Refresh token if expired
#     sp_oauth = create_spotify_oauth()
#     if sp_oauth.is_token_expired(token_info):
#         token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
#         session["token_info"] = token_info  # Save the new token

#     sp = get_spotify_client()  # Naudojame get_spotify_client funkcij
#     if not sp:
#         return redirect(url_for("connect_spotify", next=url_for("recent")))

#     # Fetch last 20 played tracks
#     recent_tracks = sp.current_user_recently_played(limit=50)

#     lithuania_tz = pytz.timezone('Europe/Vilnius')
#     tracks = []

#     for item in recent_tracks['items']:
#         track = item['track']

#         # Convert played_at to datetime (timezone aware)
#         try:
#             played_at_utc = datetime.strptime(item['played_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
#         except ValueError:
#             played_at_utc = datetime.strptime(item['played_at'], "%Y-%m-%dT%H:%M:%SZ")

#         played_at_utc = played_at_utc.replace(tzinfo=pytz.utc)
#         played_at_lt = played_at_utc.astimezone(lithuania_tz)

#         # Get artist's genre
#         artist_id = track['artists'][0]['id']  # Taking the first artist's ID
#         artist_info = sp.artist(artist_id)  # Get artist info
#         artist_genres = artist_info.get('genres', [])
#         genre = artist_genres[0] if artist_genres else None  # Take the first genre if exists

#         # Check for duplicates (by played_at and user_id)
#         existing_track = ListeningHistory.query.filter_by(
#             played_at=played_at_utc,
#             user_id=current_user.id
#         ).first()

#         # If track does not exist, insert it into database
#         if not existing_track:
#             new_history = ListeningHistory(
#                 user_id=current_user.id,
#                 artist_name=", ".join(artist['name'] for artist in track['artists']),
#                 track_name=track['name'],
#                 album_name=track['album']['name'],
#                 duration_ms=track['duration_ms'],
#                 played_at=played_at_utc,  # Save in UTC format
#                 genre=genre  # Add genre
#             )
#             db.session.add(new_history)
#             db.session.commit()

#         # For display purposes
#         tracks.append({
#             'name': track['name'],
#             'artist': ", ".join(artist['name'] for artist in track['artists']),
#             'album': track['album']['name'],
#             'album_cover': track['album']['images'][0]['url'] if track['album']['images'] else None,
#             'played_at': played_at_lt.strftime("%Y-%m-%d %H:%M:%S"),  # Format as Lithuanian time
#             'genre': genre  # Include genre in display data
#         })

#     return render_template('recent.html', tracks=tracks)


def update_listening_history(sp, user_id):
    recent_tracks = sp.current_user_recently_played(limit=50)
    lithuania_tz = pytz.timezone('Europe/Vilnius')

    for item in recent_tracks['items']:
        track = item['track']

        # Convert played_at to datetime (timezone aware)
        try:
            played_at_utc = datetime.strptime(item['played_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            played_at_utc = datetime.strptime(item['played_at'], "%Y-%m-%dT%H:%M:%SZ")

        played_at_utc = played_at_utc.replace(tzinfo=pytz.utc)
        played_at_lt = played_at_utc.astimezone(lithuania_tz)

        # Get artist's genre
        artist_id = track['artists'][0]['id']
        artist_info = sp.artist(artist_id)
        artist_genres = artist_info.get('genres', [])
        genre = artist_genres[0] if artist_genres else None

        # Check for duplicates
        existing_track = ListeningHistory.query.filter_by(
            played_at=played_at_utc,
            user_id=user_id
        ).first()

        if not existing_track:
            new_history = ListeningHistory(
                user_id=user_id,
                artist_name=", ".join(artist['name'] for artist in track['artists']),
                track_name=track['name'],
                album_name=track['album']['name'],
                duration_ms=track['duration_ms'],
                played_at=played_at_utc,
                genre=genre
            )
            db.session.add(new_history)
            db.session.commit()


# -------------------------------------------------------------- SENA
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

    sp = get_spotify_client()  # Naudojame get_spotify_client funkcij 
    if sp:
        recent_tracks = sp.current_user_recently_played(limit=20)
    else:
        return redirect(url_for("connect_spotify", next=url_for("recent")))  # Jei n ra galiojan io tokeno

    # Define Lithuanian time zone
    lithuania_tz = pytz.timezone('Europe/Vilnius')

    # Extract necessary track details
    tracks = []
    for item in recent_tracks['items']:
        track = item['track']
        
        # Convert played_at to Lithuanian time zone
        # played_at_utc = datetime.strptime(item['played_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
        # played_at_utc = played_at_utc.replace(tzinfo=pytz.utc)
        # played_at_lt = played_at_utc.astimezone(lithuania_tz)

# Convert played_at to Lithuanian time zone
        try:
            played_at_utc = datetime.strptime(item['played_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            played_at_utc = datetime.strptime(item['played_at'], "%Y-%m-%dT%H:%M:%SZ")
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

    sp = get_spotify_client()  # Naudojame get_spotify_client funkcij 
    if sp:
        user_info = sp.current_user()
    else:
        return redirect(url_for("connect_spotify", next=url_for("profile")))  # Jei n ra galiojan io tokeno

    



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

# class UpdateAccountForm(FlaskForm):
#     new_username = StringField(
#         validators=[Optional(), Length(min=4, max=20)],
#         render_kw={"placeholder": "New Username"}
#     )

#     new_password = PasswordField(
#         validators=[Optional(), Length(min=8, max=20)],
#         render_kw={"placeholder": "New Password"}
#     )

#     submit = SubmitField('Update')

#     def validate_new_username(self, new_username):
#         if new_username.data and new_username.data != current_user.username:
#             existing_user = User.query.filter_by(username=new_username.data).first()
#             if existing_user:
#                 raise ValidationError('That username is already taken. Please choose another.')

#     def validate_new_password(self, new_password):
#         if new_password.data:  # Only validate if a new password is entered
#             pwd = new_password.data
#             if (len(pwd) < 8 or 
#                 not re.search(r'[A-Z]', pwd) or 
#                 not re.search(r'[!@#$%^&*(),.?":{}|<>]', pwd) or 
#                 not re.search(r'\d', pwd)):
#                 raise ValidationError(
#                     'Password must be at least 8 characters long, contain at least one uppercase letter, one special symbol, and one number.')

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
    session.clear()
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

# PRAEJUSIOS SAVAITES RECAP------------------------------------------------------
@app.route('/last-week-recap')
@login_required
def last_week_recap():
    seven_days_ago_utc = datetime.utcnow() - timedelta(days=7)
    
    last_week_tracks = ListeningHistory.query.filter(
        ListeningHistory.user_id == current_user.id,
        ListeningHistory.played_at >= seven_days_ago_utc
    ).all()
    
    if not last_week_tracks:
        return render_template('last_week.html', message="No listening data found for the last week")
    
    song_counter = Counter()
    artist_counter = Counter()
    album_counter = Counter()
    song_durations = {} 
    album_durations = {}  
    total_minutes = 0
    artist_images = {}
    song_details = {}
    
    sp = get_spotify_client()
    if not sp:
        return redirect(url_for("connect_spotify", next=url_for("last_week_recap")))
    
    for track in last_week_tracks:
        song_counter[track.track_name, track.artist_name] += 1
        artist_counter[track.artist_name] += 1
        album_counter[track.album_name] += 1
        total_minutes += track.duration_ms


        key = (track.track_name, track.artist_name)
        song_durations[key] = song_durations.get(key, 0) + track.duration_ms
        album_durations[track.album_name] = album_durations.get(track.album_name, 0) + track.duration_ms
    

    song_durations = {key: round(value / (1000 * 60)) for key, value in song_durations.items()}
    album_durations = {key: round(value / (1000 * 60)) for key, value in album_durations.items()}
    total_minutes = round(total_minutes / (1000 * 60))
    

    top_artists = artist_counter.most_common(5)
    top_songs = song_counter.most_common(10)
    most_played_album_name, most_played_album_count = album_counter.most_common(1)[0] if album_counter else ("No data", 0)
    

    for artist, _ in top_artists:
        try:
            artist_search = sp.search(q=f"artist:{artist}", type="artist", limit=1)['artists']['items']
            artist_images[artist] = artist_search[0]['images'][0]['url'] if artist_search[0]['images'] else None
        except:
            artist_images[artist] = None
    
    for (song, artist), _ in top_songs:
        try: 
            song_search = sp.search(q=f"track:{song} artist:{artist}", type="track", limit=1)['tracks']['items']
            if song_search:
                song_details[(song, artist)] = {
                    "cover": song_search[0]["album"]["images"][0]["url"] if song_search[0]["album"]["images"] else None
                }
            else:
                song_details[(song, artist)] = {"cover": None}
        except:
            song_details[(song, artist)] = {"cover": None}
    

    album_details = {"artist": "Unknown", "cover": None}
    if most_played_album_name != "No data":
        try:
            album_search = sp.search(q=f"album:{most_played_album_name}", type="album", limit=1)['albums']['items']
            if album_search:
                album_info = album_search[0]
                album_details = {
                    "artist": album_info["artists"][0]["name"],
                    "cover": album_info["images"][0]["url"] if album_info["images"] else None
                }
        except:
            album_details = {"artist": "Unknown", "cover": None}
    

    top_artists = [(artist, count, artist_images.get(artist)) for artist, count in top_artists]
    top_songs = [
        (song, artist, count, song_details.get((song, artist), {}).get("cover"), song_durations.get((song, artist), 0))
        for (song, artist), count in top_songs
    ]
    
    most_played_album = {
        "name": most_played_album_name,
        "plays": most_played_album_count,
        "artist": album_details.get("artist", "Unknown"),
        "cover": album_details.get("cover", None),
        "total_minutes": album_durations.get(most_played_album_name, 0),
    }
    
    return render_template(
        'last_week.html',
        top_artists=top_artists,
        top_songs=top_songs,
        most_played_album=most_played_album,
        total_minutes=total_minutes
    )

# PRAEJUSIOS DIENOS RECAP------------------------------------------------------

@app.route('/yesterday_recap')
@login_required
def yesterday_recap():
    # Get the current time in UTC and convert it to Lithuanian time
    lithuanian_tz = pytz.timezone('Europe/Vilnius')
    today_utc = datetime.utcnow().replace(tzinfo=pytz.utc)  # Current time in UTC
    today_lithuanian = today_utc.astimezone(lithuanian_tz).date()  # Convert to Lithuanian time zone

    yesterday_start = datetime.combine(today_lithuanian - timedelta(days=1), datetime.min.time())  # 00:00 LT
    yesterday_end = datetime.combine(today_lithuanian - timedelta(days=1), datetime.max.time())  # 23:59:59 LT

    # Query tracks played yesterday
    yesterday_tracks = ListeningHistory.query.filter(
        ListeningHistory.user_id == current_user.id,
        ListeningHistory.played_at >= yesterday_start,
        ListeningHistory.played_at <= yesterday_end
    ).all()

    if not yesterday_tracks:
        return render_template('yesterday_recap.html', message="No listening data found for yesterday")

    # Count occurrences of songs and artists
    song_counter = Counter()
    artist_counter = Counter()
    song_durations = {}  # Store accumulated time per song
    total_minutes = 0

    for track in yesterday_tracks:
        key = (track.track_name, track.artist_name)
        song_counter[key] += 1
        artist_counter[track.artist_name] += 1

        # Calculate total time for each song
        if key in song_durations:
            song_durations[key] += track.duration_ms
        else:
            song_durations[key] = track.duration_ms

        total_minutes += track.duration_ms

    # Get top artist and top song
    top_artist, top_artist_count = artist_counter.most_common(1)[0] if artist_counter else ("No data", 0)
    (top_song, top_song_artist), top_song_count = song_counter.most_common(1)[0] if song_counter else (("No data", "Unknown"), 0)

    # Convert total milliseconds to minutes
    total_minutes = round(total_minutes / (1000 * 60))

    # Convert song durations to minutes
    song_durations = {k: round(v / (1000 * 60)) for k, v in song_durations.items()}

    # Use stored Spotify credentials
    sp = spotipy.Spotify(auth=current_user.spotify_access_token)

    # Fetch artist image
    try:
        artist_search = sp.search(q=f"artist:{top_artist}", type="artist", limit=1)['artists']['items']
        artist_image = artist_search[0]['images'][0]['url'] if artist_search and artist_search[0]['images'] else None
    except:
        artist_image = None

    # Fetch song cover image
    try:
        song_search = sp.search(q=f"track:{top_song} artist:{top_song_artist}", type="track", limit=1)['tracks']['items']
        song_cover = song_search[0]["album"]["images"][0]["url"] if song_search and song_search[0]["album"]["images"] else None
    except:
        song_cover = None

    return render_template('yesterday_recap.html',
                           top_artist={"name": top_artist, "plays": top_artist_count, "image": artist_image},
                           top_song={"name": top_song, "artist": top_song_artist, "plays": top_song_count, "cover": song_cover},
                           total_minutes=total_minutes,
                           song_durations=song_durations)


# @app.route('/yesterday_recap')
# @login_required
# def yesterday_recap():
#     # Get the current time in UTC and calculate yesterday's date range
#     today_utc = datetime.utcnow().date()
#     yesterday_start = datetime.combine(today_utc - timedelta(days=1), datetime.min.time())  # 00:00 UTC
#     yesterday_end = datetime.combine(today_utc - timedelta(days=1), datetime.max.time())  # 23:59:59 UTC

#     # Query tracks played yesterday
#     yesterday_tracks = ListeningHistory.query.filter(
#         ListeningHistory.user_id == current_user.id,
#         ListeningHistory.played_at >= yesterday_start,
#         ListeningHistory.played_at <= yesterday_end
#     ).all()

#     if not yesterday_tracks:
#         return render_template('yesterday_recap.html', message="No listening data found for yesterday")

#     # Count occurrences of songs and artists
#     song_counter = Counter()
#     artist_counter = Counter()
#     song_durations = {}  # Store accumulated time per song
#     total_minutes = 0

#     for track in yesterday_tracks:
#         key = (track.track_name, track.artist_name)
#         song_counter[key] += 1
#         artist_counter[track.artist_name] += 1

#         # Calculate total time for each song
#         if key in song_durations:
#             song_durations[key] += track.duration_ms
#         else:
#             song_durations[key] = track.duration_ms

#         total_minutes += track.duration_ms

#     # Get top artist and top song
#     top_artist, top_artist_count = artist_counter.most_common(1)[0] if artist_counter else ("No data", 0)
#     (top_song, top_song_artist), top_song_count = song_counter.most_common(1)[0] if song_counter else (("No data", "Unknown"), 0)

#     # Convert total milliseconds to minutes
#     total_minutes = round(total_minutes / (1000 * 60))

#     # Convert song durations to minutes
#     song_durations = {k: round(v / (1000 * 60)) for k, v in song_durations.items()}

#     # Use stored Spotify credentials
#     sp = spotipy.Spotify(auth=current_user.spotify_access_token)

#     # Fetch artist image
#     try:
#         artist_search = sp.search(q=f"artist:{top_artist}", type="artist", limit=1)['artists']['items']
#         artist_image = artist_search[0]['images'][0]['url'] if artist_search and artist_search[0]['images'] else None
#     except:
#         artist_image = None

#     # Fetch song cover image
#     try:
#         song_search = sp.search(q=f"track:{top_song} artist:{top_song_artist}", type="track", limit=1)['tracks']['items']
#         song_cover = song_search[0]["album"]["images"][0]["url"] if song_search and song_search[0]["album"]["images"] else None
#     except:
#         song_cover = None

#     return render_template('yesterday_recap.html',
#                            top_artist={"name": top_artist, "plays": top_artist_count, "image": artist_image},
#                            top_song={"name": top_song, "artist": top_song_artist, "plays": top_song_count, "cover": song_cover},
#                            total_minutes=total_minutes,
#                            song_durations=song_durations)

# TODAY'S RECAP ------------------------------------------------------

@app.route('/todays_recap')
@login_required
def today_recap():
    # Define Lithuanian timezone
    lt_timezone = pytz.timezone('Europe/Vilnius')

    # Get current time in Lithuania
    now_lt = datetime.now(lt_timezone)
    today_start_lt = datetime.combine(now_lt.date(), datetime.min.time())  # 00:00 Lithuanian time
    today_start_utc = today_start_lt.astimezone(pytz.utc)  # Convert to UTC

    # Query tracks played today in Lithuanian time
    today_tracks = ListeningHistory.query.filter(
        ListeningHistory.user_id == current_user.id,
        ListeningHistory.played_at >= today_start_utc,
        ListeningHistory.played_at <= now_lt.astimezone(pytz.utc)  # Convert now_lt to UTC
    ).all()

# @app.route('/todays_recap')
# @login_required
# def today_recap():
#     # Get the current date and time in UTC
#     now_utc = datetime.utcnow()
#     today_start = datetime.combine(now_utc.date(), datetime.min.time())  # 00:00 UTC
#     today_end = now_utc  # Current time UTC

#     # Query tracks played today
#     today_tracks = ListeningHistory.query.filter(
#         ListeningHistory.user_id == current_user.id,
#         ListeningHistory.played_at >= today_start,
#         ListeningHistory.played_at <= today_end
#     ).all()

    if not today_tracks:
        return render_template('todays_recap.html', message="No listening data found for today")

    # Count occurrences of songs and artists
    song_counter = Counter()
    artist_counter = Counter()
    song_durations = {}  # Store accumulated time per song
    total_minutes = 0

    for track in today_tracks:
        key = (track.track_name, track.artist_name)
        song_counter[key] += 1
        artist_counter[track.artist_name] += 1

        # Calculate total time for each song
        if key in song_durations:
            song_durations[key] += track.duration_ms
        else:
            song_durations[key] = track.duration_ms

        total_minutes += track.duration_ms

    # Get top artist and top song
    top_artist, top_artist_count = artist_counter.most_common(1)[0] if artist_counter else ("No data", 0)
    (top_song, top_song_artist), top_song_count = song_counter.most_common(1)[0] if song_counter else (("No data", "Unknown"), 0)

    # Convert total milliseconds to minutes
    total_minutes = round(total_minutes / (1000 * 60))

    # Convert song durations to minutes
    song_durations = {k: round(v / (1000 * 60)) for k, v in song_durations.items()}

    # Use stored Spotify credentials
    sp = spotipy.Spotify(auth=current_user.spotify_access_token)

    # Fetch artist image
    try:
        artist_search = sp.search(q=f"artist:{top_artist}", type="artist", limit=1)['artists']['items']
        artist_image = artist_search[0]['images'][0]['url'] if artist_search and artist_search[0]['images'] else None
    except:
        artist_image = None

    # Fetch song cover image
    try:
        song_search = sp.search(q=f"track:{top_song} artist:{top_song_artist}", type="track", limit=1)['tracks']['items']
        song_cover = song_search[0]["album"]["images"][0]["url"] if song_search and song_search[0]["album"]["images"] else None
    except:
        song_cover = None

    return render_template('todays_recap.html',
                           top_artist={"name": top_artist, "plays": top_artist_count, "image": artist_image},
                           top_song={"name": top_song, "artist": top_song_artist, "plays": top_song_count, "cover": song_cover},
                           total_minutes=total_minutes,
                           song_durations=song_durations)


#LABIAUSIAI KLAUSOMIAUSIA DAINA--------------------------------------------------



# @app.route("/most_listened_song_json")
# def most_listened_song_json():
#     most_listened_song = db.session.query(
#         ListeningHistory.artist_name, ListeningHistory.track_name
#     ).group_by(
#         ListeningHistory.artist_name, ListeningHistory.track_name
#     ).order_by(db.func.count().desc()).limit(1).first()
    

#     if most_listened_song:
#         artist_name, track_name = most_listened_song
#         response = {
#             "song": track_name,
#             "artist": artist_name,
#         }
#     else:
#         response = {"song": None, "artist": None}
    
#     return jsonify(response)

# @app.route("/most_listened_song_json")
# def most_listened_song_json():
#     try:
#         sp = get_spotify_client()
#         most_listened_song = db.session.query(
#             ListeningHistory.artist_name, ListeningHistory.track_name
#         ).group_by(
#             ListeningHistory.artist_name, ListeningHistory.track_name
#         ).order_by(db.func.count().desc()).limit(1).first()

#         if not most_listened_song:
#             return jsonify({"song": None, "artist": None, "album_cover": None})

#         artist_name, track_name = most_listened_song

#         # Search for the track on Spotify
#         search_results = sp.search(q=f"track:{track_name} artist:{artist_name}", type="track", limit=1)
#         if search_results['tracks']['items']:
#             track_info = search_results['tracks']['items'][0]
#             album_cover = track_info['album']['images'][0]['url'] if track_info['album']['images'] else None
#         else:
#             album_cover = None

#         return jsonify({
#             "song": track_name,
#             "artist": artist_name,
#             "album_cover": album_cover
#         })

#     except Exception as e:
#         return jsonify({"error": f"Error fetching data: {str(e)}"}), 500
@app.route("/most_listened_song_json")
def most_listened_song_json():
    try:
        sp = get_spotify_client()

        # Query the most listened song for the logged-in user
        most_listened_song = db.session.query(
            ListeningHistory.artist_name, ListeningHistory.track_name
        ).filter_by(
            user_id=current_user.id  # Get the current logged-in user's ID
        ).group_by(
            ListeningHistory.artist_name, ListeningHistory.track_name
        ).order_by(db.func.count().desc()).limit(1).first()

        if not most_listened_song:
            return jsonify({"song": None, "artist": None, "album_cover": None})

        artist_name, track_name = most_listened_song

        # Search for the track on Spotify
        search_results = sp.search(q=f"track:{track_name} artist:{artist_name}", type="track", limit=1)

        if search_results['tracks']['items']:
            track_info = search_results['tracks']['items'][0]
            album_cover = track_info['album']['images'][0]['url'] if track_info.get('album', {}).get('images') else None
        else:
            album_cover = None

        return jsonify({
            "song": track_name,
            "artist": artist_name,
            "album_cover": album_cover
        })

    except Exception as e:
        return jsonify({"error": f"Error fetching data: {str(e)}"}), 500



#-------------------------------------------------------------------------------
#FAVE AUTLIKEJAS
@app.route("/most_listened_artist_json")
def most_listened_artist_json():
    try:
        sp = get_spotify_client()
        
        # Query most listened artist for the logged-in user
        artist_name = db.session.query(
            ListeningHistory.artist_name
        ).filter_by(
            user_id=current_user.id
        ).group_by(
            ListeningHistory.artist_name
        ).order_by(
            db.func.count().desc()
        ).limit(1).scalar()

        if not artist_name:
            return jsonify({"artist": None, "artist_image": None})

        # Search for artist on Spotify
        search_results = sp.search(q=f"artist:{artist_name}", type="artist", limit=1)
        if search_results['artists']['items']:
            artist_info = search_results['artists']['items'][0]
            artist_image = artist_info['images'][0]['url'] if artist_info['images'] else None
        else:
            artist_image = None

        return jsonify({"artist": artist_name, "artist_image": artist_image})

    except Exception as e:
        return jsonify({"error": f"Error fetching data: {str(e)}"}), 500


@app.route("/most_listened_album_json")
def most_listened_album_json():
    try:
        sp = get_spotify_client()

        # Query the most listened album for the logged-in user
        most_listened_album = db.session.query(
            ListeningHistory.artist_name, ListeningHistory.album_name
        ).filter_by(
            user_id=current_user.id
        ).group_by(
            ListeningHistory.artist_name, ListeningHistory.album_name
        ).order_by(db.func.count().desc()).limit(1).first()

        if not most_listened_album:
            return jsonify({"album": None, "artist": None, "album_cover": None})

        artist_name, album_name = most_listened_album

        # Search for the album on Spotify
        search_results = sp.search(q=f"{album_name} {artist_name}", type="album", limit=1)

        if search_results['albums']['items']:
            album_info = search_results['albums']['items'][0]
            album_cover = album_info['images'][0]['url'] if album_info.get('images') else None
        else:
            album_cover = None

        return jsonify({
            "album": album_name,
            "artist": artist_name,
            "album_cover": album_cover
        })

    except Exception as e:
        return jsonify({"error": f"Error fetching data: {str(e)}"}), 500

@app.route("/top_10_listened_albums")
def top_10_most_listened_albums_json():
    try:
        sp = get_spotify_client()

        # Query the top 10 most listened albums for the logged-in user
        top_10_albums = db.session.query(
            ListeningHistory.artist_name,
            ListeningHistory.album_name,
            db.func.count().label('play_count')  # Counting the number of times the album was played
        ).filter_by(
            user_id=current_user.id
        ).group_by(
            ListeningHistory.artist_name,
            ListeningHistory.album_name
        ).order_by(db.func.count().desc()).limit(10).all()

        if not top_10_albums:
            return jsonify({"albums": []})

        albums_data = []

        # For each album, search for it on Spotify and get the album cover
        for artist_name, album_name, play_count in top_10_albums:
            search_results = sp.search(q=f"{album_name} {artist_name}", type="album", limit=1)

            if search_results['albums']['items']:
                album_info = search_results['albums']['items'][0]
                album_cover = album_info['images'][0]['url'] if album_info.get('images') else None
            else:
                album_cover = None

            albums_data.append({
                "album": album_name,
                "artist": artist_name,
                "album_cover": album_cover,
                "play_count": play_count  # Adding the play count to the response
            })

        return render_template("top_albums.html", albums=albums_data)

    except Exception as e:
        return jsonify({"error": f"Error fetching data: {str(e)}"}), 500



# @app.route("/most_listened_artist_json")
# def most_listened_artist_json():
#     try:
#         sp = get_spotify_client()
#         artist_name = db.session.query(
#             ListeningHistory.artist_name
#         ).group_by(
#             ListeningHistory.artist_name
#         ).order_by(
#             db.func.count().desc()
#         ).limit(1).scalar()

#         if not artist_name:
#             return jsonify({"artist": None, "artist_image": None})

#         # Search for artist on Spotify
#         search_results = sp.search(q=f"artist:{artist_name}", type="artist", limit=1)
#         if search_results['artists']['items']:
#             artist_info = search_results['artists']['items'][0]
#             artist_image = artist_info['images'][0]['url'] if artist_info['images'] else None
#         else:
#             artist_image = None

#         return jsonify({"artist": artist_name, "artist_image": artist_image})

#     except Exception as e:
#         return jsonify({"error": f"Error fetching data: {str(e)}"}), 500

# @app.route("/most_listened_album_json")
# def most_listened_album_json():
#     try:
#         sp = get_spotify_client()

#         # Query the most listened album
#         most_listened_album = db.session.query(
#             ListeningHistory.artist_name, ListeningHistory.album_name
#         ).group_by(
#             ListeningHistory.artist_name, ListeningHistory.album_name
#         ).order_by(db.func.count().desc()).limit(1).first()

#         if not most_listened_album:
#             return jsonify({"album": None, "artist": None, "album_cover": None})

#         artist_name, album_name = most_listened_album

#         # Search for the album on Spotify
#         search_results = sp.search(q=f"{album_name} {artist_name}", type="album", limit=1)

#         if search_results['albums']['items']:
#             album_info = search_results['albums']['items'][0]
#             album_cover = album_info['images'][0]['url'] if album_info.get('images') else None
#         else:
#             album_cover = None

#         return jsonify({
#             "album": album_name,
#             "artist": artist_name,
#             "album_cover": album_cover
#         })

#     except Exception as e:
#         return jsonify({"error": f"Error fetching data: {str(e)}"}), 500


#==========================================================
# @app.route("/most_listened_artist_json")
# def most_listened_artist_json():
#     most_listened_artist = db.session.query(
#         ListeningHistory.artist_name
#     ).group_by(
#         ListeningHistory.artist_name
#     ).order_by(db.func.count().desc()).limit(1).first()
    
#     if most_listened_artist:
#         artist_name = most_listened_artist[0]  # Extract the artist name from the tuple
#         response = {
#             "artist": artist_name,
#         }
#     else:
#         response = {"artist": None}
    
#     return jsonify(response)
#==========================================================



# @login_required
# def most_listened_genre_json():
#     # Suraskime klausomiausi
#     user_id = current_user.id
#     genre_count = db.session.query(ListeningHistory.genre, db.func.count().label('count')) \
#         .filter_by(user_id=user_id) \
#         .group_by(ListeningHistory.genre) \
#         .order_by(db.func.count().desc()) \
#         .first()

#     # Jeigu n ra  anr , gr  iname "No data"
#     if genre_count:
#         genre = genre_count[0]
#         return jsonify({'genre': genre})
#     else:
#         return jsonify({'genre': 'No data available'})

@app.route('/most_listened_genre_json')
@login_required
def most_listened_genre_json():
    user_id = current_user.id

    # Query the most frequently listened genres, ignoring NULL values
    genre_counts = (
        db.session.query(ListeningHistory.genre, db.func.count().label('count'))
        .filter(
            ListeningHistory.user_id == user_id,
            ListeningHistory.genre.isnot(None),  # Ignore NULL genres
            ListeningHistory.genre != ''         # Ignore empty string genres
        )
        .group_by(ListeningHistory.genre)
        .order_by(db.func.count().desc())
        .limit(1)  # Get top one genre
        .all()
    )

    # Check if there is at least one genre
    if genre_counts:
        genre = genre_counts[0][0]  # Take the top genre
        return jsonify({'genre': genre})

    # If no genres found
    return jsonify({'genre': 'No data available, listen to more music!'})




@app.route("/top_10_listened_artists")
@login_required  # <-- kad prie sito kelio galetu eiti tik prisijunge vartotojai
def top_10_listened_artists():
    try:
        sp = get_spotify_client()

        # Imame tik dabartinio vartotojo klausymosi istorija
        top_artists = db.session.query(
            ListeningHistory.artist_name,
            db.func.count().label('play_count')
        ).filter(
            ListeningHistory.user_id == current_user.id
        ).group_by(
            ListeningHistory.artist_name
        ).order_by(
            db.func.count().desc()
        ).limit(10).all()

        artist_data = []
        
        for artist_name, play_count in top_artists:
            search_results = sp.search(q=f"artist:{artist_name}", type="artist", limit=1)
            if search_results['artists']['items']:
                artist_info = search_results['artists']['items'][0]
                artist_image = artist_info['images'][0]['url'] if artist_info.get('images') else None
            else:
                artist_image = None

            artist_data.append({
                "artist": artist_name,
                "play_count": play_count,
                "artist_image": artist_image
            })

        return render_template('top_artists.html', artists=artist_data)

    except Exception as e:
        return jsonify({"error": f"Error fetching data: {str(e)}"}), 500


# MOST LISTENED SONGS -----------------------------------------------------------
@app.route("/top_50_songs")
@login_required
def top_50_songs():
    try:
        song_counter = Counter()
        album_covers = {}
        # current user
        user_tracks = ListeningHistory.query.filter_by(user_id=current_user.id).all()
        
        for track in user_tracks:
            song_counter[(track.track_name, track.artist_name, track.album_name)] += 1
            if track.album_name not in album_covers:
                album_covers[track.album_name] = None # placeholder for cover
        
        top_songs = song_counter.most_common(50)
        
        sp=get_spotify_client()
        if sp:
            for album_name in album_covers.keys():
                try:
                    search_results = sp.search(q=f"album:{album_name}", type="album", limit=1)
                    if search_results['albums']['items']:
                        album_covers[album_name] = search_results['albums']['items'][0]['images'][0]['url']
                except:
                    album_covers[album_name] = None
            
                #return redirect(url_for("connect_spotify", next=url_for("top_50_songs")))
        
        
        formatted_songs = []
        for(track_name, artist_name, album_name), play_count in top_songs:
            formatted_songs.append({
                "song": track_name,
                "artist": artist_name,
                "album": album_name,
                "plays": play_count
            })
            
        return render_template("top_50_songs.html", top_songs=formatted_songs)
    except Exception as e:
        return render_template("top_50_songs.html", error=f"Error fetching top songs: {str(e)}")
        
        

#-------------------------------------------------------------------------------

if(__name__) == '__main__':
    app.run('localhost', 4449, debug = True)


# Pull test