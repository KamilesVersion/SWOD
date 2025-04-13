from ast import List
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
from dotenv import load_dotenv
import pytz
from datetime import datetime, timedelta
from flask_migrate import Migrate
from collections import Counter, defaultdict
from models import db, User, ListeningHistory
from sqlalchemy.sql import func, desc
from spotify import SpotifyService


load_dotenv() # Load environment variables from .env file

app = Flask(__name__)

bcrypt = Bcrypt(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'thisisasecretkey'

spotify = SpotifyService();

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


# --------------------- UPDATING LISTENING HISTORY IN DATABASE ---------------------
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
            

# ---------------------------------- HOME PAGE ----------------------------------
@app.route('/')
def home():
    return render_template('home.html')

    
# ---------------------------------- LOGIN PAGE ----------------------------------
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



# ---------------------------------- REGISTER PAGE ----------------------------------
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


# ---------------------------------- MENU PAGE ----------------------------------
@app.route('/menu')
@login_required
def menu():
    token_info = session.get("token_info", None)
    if not token_info:
        return redirect(url_for("connect_spotify", next=url_for("menu")))

    sp_oauth = spotify.create_spotify_oauth()
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
        session["token_info"] = token_info

    sp = spotify.get_spotify_client()
    if not sp:
        return redirect(url_for("connect_spotify", next=url_for("menu")))

    update_listening_history(sp, current_user.id)  # Call common function

    return render_template('menuPage.html')


# ---------------------------------- ALL SPOTIFY PAGES ----------------------------------
@app.route('/connect_spotify')
def connect_spotify():
    session["next_url"] = request.args.get("next", url_for("menu"))
    sp_oauth = spotify.create_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    
    # Store the time when the user connected Spotify
    if current_user.is_authenticated:
        current_user.spotify_connected_at = datetime.utcnow().replace(tzinfo=pytz.utc)
        db.session.commit()
    
    return redirect(auth_url)

@app.route('/spotify_callback')
def spotify_callback():
    sp_oauth = spotify.create_spotify_oauth()
    
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


# ---------------------------------- MOST RECENT TRACKS ----------------------------------
@app.route('/recent')
@login_required
def recent():
    token_info = session.get("token_info", None)
    if not token_info:
        return redirect(url_for("connect_spotify", next=url_for("recent")))

    # Refresh token if expired
    sp_oauth = spotify.create_spotify_oauth()
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
        session["token_info"] = token_info  # Save the new token

    # Fetch last 20 played tracks
    #sp = spotipy.Spotify(auth=token_info["access_token"])
    #recent_tracks = sp.current_user_recently_played(limit=20)

    sp = spotify.get_spotify_client()  # Naudojame get_spotify_client funkcij 
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


# ---------------------------------- ALL PROFILE PAGES ----------------------------------
# @app.route('/profile1')
# @login_required
# def profile1():
#     if not current_user.is_authenticated:
#         return redirect(url_for('login'))
     
#     token_info = session.get("token_info", None)
#     if not token_info:
#         return redirect(url_for("connect_spotify", next=url_for("profile1")))
#     # Refresh token if expired
#     sp_oauth = spotify.create_spotify_oauth()
#     if sp_oauth.is_token_expired(token_info):
#         token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
#         session["token_info"] = token_info # Save the new token

#     # Use the access token to fetch user details
#     # sp = spotipy.Spotify(auth=token_info["access_token"])
#     # user_info = sp.current_user()

#     sp = spotify.get_spotify_client()  # Naudojame get_spotify_client funkcij 
#     if sp:
#         user_info = sp.current_user()
#     else:
#         return redirect(url_for("connect_spotify", next=url_for("profile1")))  # Jei n ra galiojan io tokeno

@app.route('/profile1')
@login_required
def profile():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    token_info = session.get("token_info", None)
    if not token_info:
        return redirect(url_for("connect_spotify", next=url_for("profile")))

    sp_oauth = spotify.create_spotify_oauth()
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
        session["token_info"] = token_info

    sp = spotify.get_spotify_client()
    spotify_logged_in = False
    profile_pic = None
    user = None

    if sp:
        user_info = sp.current_user()
        spotify_logged_in = True
        user = user_info.get("display_name")
        images = user_info.get("images")
        if images:
            profile_pic = images[0].get("url")

    # return render_template(
    #     "profile.html",
    #     username=current_user.username,
    #     spotify_logged_in=spotify_logged_in,
    #     user=user,
    #     profile_pic=profile_pic
    # )
   
    return render_template('profile1.html', 
                           user=user_info["display_name"], # spotify name
                           profile_pic=user_info["images"][0]["url"] if user_info["images"] else None,
                           username=current_user.username,
                           spotify_logged_in=True) 

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
    user_id = current_user.id
    
    # First, delete associated listening history records
    ListeningHistory.query.filter_by(user_id=user_id).delete()
    
    # Then delete the user
    db.session.delete(current_user)
    
    # Commit all changes at once
    db.session.commit()
    
    logout_user()
    session.clear()  # Clear any remaining session data
    return redirect(url_for('home'))


# ---------------------------------- ALL RECAPS ----------------------------------
@app.route('/recap')
@login_required
def recap():
    return render_template('recap_page.html')

# LAST WEEK RECAP
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
    time_of_day_counter = defaultdict(int)
    # Day periods
    time_periods = {
        "Early Morning": (4, 7), # 04:00–07:59
        "Morning": (8, 11),
        "Afternoon": (12, 15),
        "Evening": (16, 19),
        "Night": (20, 23),
        "Late Night": (0, 3)
    }
    
    sp = spotify.get_spotify_client()
    if not sp:
        return redirect(url_for("connect_spotify", next=url_for("last_week_recap")))    
    
    for track in last_week_tracks:
        # split artists by comma
        artists = [artist.strip() for artist in track.artist_name.split(',')]
        for artist in artists:
            artist_counter[artist] += 1
        song_counter[track.track_name, track.artist_name] += 1
        album_counter[track.album_name] += 1
        total_minutes += track.duration_ms


        key = (track.track_name, track.artist_name)
        song_durations[key] = song_durations.get(key, 0) + track.duration_ms
        album_durations[track.album_name] = album_durations.get(track.album_name, 0) + track.duration_ms
    
        # covert time
        played_time_lt = to_lithuanian_time(track.played_at)
        hour = played_time_lt.hour
        for label, (start_hour, end_hour) in time_periods.items():
            if start_hour <= hour <= end_hour:
                time_of_day_counter[label] += 1 
                break

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

    most_active_time, time_play_count = max(time_of_day_counter.items(), key=lambda x: x[1]) if time_of_day_counter else ("No data", 0)
    # for chart
    # Define your desired logical order
    ordered_labels = ["Early Morning", "Morning", "Afternoon", "Evening", "Night", "Late Night"]

    # Use the ordered labels to create labels and counts
    time_labels = []
    time_counts = []

    for label in ordered_labels:
        if label in time_of_day_counter:
            time_labels.append(label)
            time_counts.append(time_of_day_counter[label])
    
    return render_template(
        'last_week.html',
        top_artists=top_artists,
        top_songs=top_songs,
        most_played_album=most_played_album,
        total_minutes=total_minutes,
        most_active_time=most_active_time,
        time_play_count=time_play_count,
        time_labels=time_labels,
        time_counts=time_counts
    )

# UTC time to LT 
def to_lithuanian_time(dt):
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    return dt.astimezone(pytz.timezone("Europe/Vilnius"))    
# YESTERDAY RECAP
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

    # if not yesterday_tracks:
    #     return render_template('yesterday_recap.html', message="No listening data found for yesterday")
    
    if not yesterday_tracks:
        return render_template(
            'yesterday_recap.html',
               message="No listening data found for yesterday",
            top_artist={"name": "No data", "plays": 0, "image": None},
            top_song={"name": "No data", "artist": "Unknown", "plays": 0, "cover": None},
            total_minutes=0,
            song_durations={},
            most_active_time="No data",
            time_play_count=0,
            time_labels=[],
            time_counts=[]
    )


    # Count occurrences of songs and artists
    song_counter = Counter()
    artist_counter = Counter()
    song_durations = {}  # Store accumulated time per song
    total_minutes = 0

    # Day periods
    time_periods = {
        "Early Morning": (4, 7), # 04:00–07:59
        "Morning": (8, 11),
        "Afternoon": (12, 15),
        "Evening": (16, 19),
        "Night": (20, 23),
        "Late Night": (0, 3)
    }

    time_of_day_counter = defaultdict(int)

    for track in yesterday_tracks:
        key = (track.track_name, track.artist_name)
        song_counter[key] += 1
        # split artists by comma
        artists = [artist.strip() for artist in track.artist_name.split(',')]
        for artist in artists:
            artist_counter[artist] += 1

        # Calculate total time for each song
        if key in song_durations:
            song_durations[key] += track.duration_ms
        else:
            song_durations[key] = track.duration_ms

        total_minutes += track.duration_ms
        
        # covert UTC to LT
        played_time_lt = to_lithuanian_time(track.played_at)
        hour = played_time_lt.hour
        for label, (start_hour, end_hour) in time_periods.items():
            if start_hour <= hour <= end_hour:
                time_of_day_counter[label] += 1 
                break

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
        
    # Most active time of the day
    most_active_time, time_play_count = max(time_of_day_counter.items(), key=lambda x: x[1]) if time_of_day_counter else ("No data", 0)

    # Convert time_of_day_counter to list for chart
    # Define your desired logical order
    ordered_labels = ["Early Morning", "Morning", "Afternoon", "Evening", "Night", "Late Night"]

    # Use the ordered labels to create labels and counts
    time_labels = []
    time_counts = []

    for label in ordered_labels:
        if label in time_of_day_counter:
            time_labels.append(label)
            time_counts.append(time_of_day_counter[label])

    return render_template('yesterday_recap.html',
                           top_artist={"name": top_artist, "plays": top_artist_count, "image": artist_image},
                           top_song={"name": top_song, "artist": top_song_artist, "plays": top_song_count, "cover": song_cover},
                           total_minutes=total_minutes,
                           song_durations=song_durations,
                           most_active_time=most_active_time,
                           time_play_count=time_play_count,
                           time_labels=time_labels,
                           time_counts=time_counts 
   )

# TODAY RECAP
@app.route('/todays_recap')
@login_required
def today_recap():
    lt_timezone = pytz.timezone('Europe/Vilnius')
    now_lt = datetime.now(lt_timezone)
    today_start_lt = datetime.combine(now_lt.date(), datetime.min.time())
    today_start_utc = today_start_lt.astimezone(pytz.utc)

    today_tracks = ListeningHistory.query.filter(
        ListeningHistory.user_id == current_user.id,
        ListeningHistory.played_at >= today_start_utc,
        ListeningHistory.played_at <= now_lt.astimezone(pytz.utc)
    ).all()

    if not today_tracks:
        return render_template(
            'todays_recap.html',
            message="No listening data found for today",
            top_artist={"name": "No data", "plays": 0, "image": None},
            top_song={"name": "No data", "artist": "Unknown", "plays": 0, "cover": None},
            total_minutes=0,
            song_durations={}
        )

    # Count occurrences of songs and artists
    song_counter = Counter()
    artist_counter = Counter()
    song_durations = {}  # Store accumulated time per song
    total_minutes = 0

    for track in today_tracks:
        key = (track.track_name, track.artist_name)
        song_counter[key] += 1
        # split artists by comma
        artists = [artist.strip() for artist in track.artist_name.split(',')]
        for artist in artists:
            artist_counter[artist] += 1

        # Calculate total time for each song
        if key in song_durations:
            song_durations[key] += track.duration_ms
        else:
            song_durations[key] = track.duration_ms

        total_minutes += track.duration_ms

    # Safely get the top artist
    top_artist_data = artist_counter.most_common(1)
    if top_artist_data:
        top_artist, top_artist_count = top_artist_data[0]
    else:
        top_artist, top_artist_count = "No data", 0

    # Safely get the top song
    top_song_data = song_counter.most_common(1)
    if top_song_data:
        (top_song, top_song_artist), top_song_count = top_song_data[0]
    else:
        top_song, top_song_artist, top_song_count = "No data", "Unknown", 0

    # Convert total milliseconds to minutes
    total_minutes = round(total_minutes / (1000 * 60))

    # Convert song durations to minutes
    song_durations = {k: round(v / (1000 * 60)) for k, v in song_durations.items()}

    # Use stored Spotify credentials
    sp = spotipy.Spotify(auth=current_user.spotify_access_token)

    # Fetch artist image
    artist_image = None
    if top_artist != "No data":
        try:
            artist_search = sp.search(q=f"artist:{top_artist}", type="artist", limit=1)['artists']['items']
            artist_image = artist_search[0]['images'][0]['url'] if artist_search and artist_search[0]['images'] else None
        except:
            artist_image = None

    # Fetch song cover image
    song_cover = None
    if top_song != "No data":
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


# ---------------------------------- STATISTICS IN MENU PAGE ----------------------------------
#MOST LISTENED SONG
@app.route("/most_listened_song_json")
def most_listened_song_json():
    try:
        sp = spotify.get_spotify_client()

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

#FAVE ARTIST
@app.route("/most_listened_artist_json")
def most_listened_artist_json():
    try:
        sp = spotify.get_spotify_client()
        
         # First, get aggregated results from the database
        artist_counts = db.session.query(
            ListeningHistory.artist_name,
            db.func.count().label('play_count')
        ).filter(
            ListeningHistory.user_id == current_user.id
        ).group_by(
            ListeningHistory.artist_name
        ).all()
        
        # Process artists with commas
        artist_counter = Counter()
        artists_with_commas = ["Tyler, The Creator", "Earth, Wind & Fire"]
        
        for artist_name, count in artist_counts:
            # Check if this is a multi-artist entry or contains special artists
            needs_splitting = "," in artist_name and not any(special in artist_name for special in artists_with_commas)
            
            if needs_splitting:
                # Split and count individually
                for split_artist in artist_name.split(","):
                    split_artist = split_artist.strip()
                    if split_artist:
                        artist_counter[split_artist] += count
            else:
                # Keep as is
                artist_counter[artist_name] += count

        # Get the most listened artist
        if not artist_counter:
            return jsonify({"artist": None, "artist_image": None})
            
        artist_name, _ = artist_counter.most_common(1)[0]

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

#MOST LISTENED ALBUM
@app.route("/most_listened_album_json")
def most_listened_album_json():
    try:
        sp = spotify.get_spotify_client()

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

#MOST LISTENED GENRE
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
    

# ---------------------------------- TOP ALBUMS ----------------------------------
@app.route("/top_10_listened_albums")
def top_10_most_listened_albums_json():
    try:
        sp = spotify.get_spotify_client()

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

# ---------------------------------- TOP ARTISTS ----------------------------------
@app.route("/top_10_listened_artists")
@login_required  # <-- kad prie sito kelio galetu eiti tik prisijunge vartotojai
def top_10_listened_artists():
    try:
        sp = spotify.get_spotify_client()

        # First, get aggregated results from the database
        # This will handle most cases efficiently
        artist_counts = db.session.query(
            ListeningHistory.artist_name,
            db.func.count().label('play_count')
        ).filter(
            ListeningHistory.user_id == current_user.id
        ).group_by(
            ListeningHistory.artist_name
        ).all()

         # Process artists with commas
        artist_counter = Counter()
        artists_with_commas = ["Tyler, The Creator", "Earth, Wind & Fire"]
        
        for artist_name, count in artist_counts:
            # Check if this is a multi-artist entry or contains special artists
            needs_splitting = "," in artist_name and not any(special in artist_name for special in artists_with_commas)
            
            if needs_splitting:
                # Split and count individually
                for split_artist in artist_name.split(","):
                    split_artist = split_artist.strip()
                    if split_artist:
                        artist_counter[split_artist] += count
            else:
                # Keep as is
                artist_counter[artist_name] += count
                
        # Get top 10 artists
        top_artists = artist_counter.most_common(10)
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


# ---------------------------------- TOP TRACKS ----------------------------------
@app.route("/top_50_songs")
@login_required
def top_50_songs():
    try:
        
        top_songs = (
            db.session.query(
                ListeningHistory.track_name,
                ListeningHistory.artist_name,
                ListeningHistory.album_name,
                func.count(ListeningHistory.track_name).label("play_count")
            )
            .filter_by(user_id=current_user.id)
            .group_by(ListeningHistory.track_name, ListeningHistory.artist_name, ListeningHistory.album_name)
            .order_by(func.count(ListeningHistory.track_name).desc())
            .limit(50)
            .all()
        )
            
        album_covers = {}

        sp = spotify.get_spotify_client()
        if sp:
            unique_albums = {(song.album_name, song.artist_name) for song in top_songs}
            for album_name, artist_name in unique_albums:
                cover_url = None
                try:
                    first_artist = artist_name.split(",")[0].strip()
                    album_search = sp.search(q=f"album:{album_name} artist:{first_artist}", type="album", limit=1)
                    if album_search['albums']['items']:
                        cover_url = album_search['albums']['items'][0]['images'][0]['url']
                        
                    if not cover_url:
                        track_search = sp.search(q=f"track:{album_name} artist:{first_artist}", type="track", limit=1)
                        if track_search['tracks']['items']:
                            cover_url = track_search['tracks']['items'][0]['album']['images'][0]['url']
                except:
                    cover_url = None
             
                album_covers[(album_name, artist_name)] = cover_url
                
        
        formatted_songs = [
            {
                "song": song.track_name,
                "artist": song.artist_name,
                "album": song.album_name,
                "plays": song.play_count,
                "cover": album_covers.get((song.album_name, song.artist_name))
            }
            for song in top_songs
        ]        

            
        return render_template("top_50_songs.html", top_songs=formatted_songs)
    except Exception as e:
        return render_template("top_50_songs.html", error=f"Error fetching top songs: {str(e)}")
        

# ---------------------------------- ALL LISTENED GENRES ----------------------------------
@app.route('/genres')
@login_required
def genres():
    user_id = current_user.id

    # Query all genres the user has listened to, ordered by frequency
    genre_counts = (
        db.session.query(ListeningHistory.genre, db.func.count().label('count'))
        .filter(
            ListeningHistory.user_id == user_id,
            ListeningHistory.genre.isnot(None),
            ListeningHistory.genre != ''
        )
        .group_by(ListeningHistory.genre)
        .order_by(db.func.count().desc())
        .all()
    )

    # Create a list of dictionaries: [{'genre': 'Pop', 'count': 42}, ...]
    genre_list = [{'genre': genre, 'count': count} for genre, count in genre_counts]

    return render_template('genres.html', genre_list=genre_list)


# ---------------------------------- ARTISTS BY GENRE ----------------------------------
@app.route('/genre/<genre>')
@login_required
def genre_artists(genre):
    user_id = current_user.id

    # Get all artist_name values for the user and genre
    artists_raw = (
        db.session.query(ListeningHistory.artist_name)
        .filter(
            ListeningHistory.user_id == user_id,
            ListeningHistory.genre == genre
        )
        .all()
    )

    # Flatten, split by ", ", and remove duplicates using a set
    artist_set = set()
    for entry in artists_raw:
        for artist in entry[0].split(", "):
            artist_set.add(artist.strip())

    # Convert back to sorted list for display
    artist_list = sorted(artist_set)

    return render_template('genre_artists.html', genre=genre, artists=artist_list)


# ---------------------------------- CUSTOM DATE RANGE STATS ----------------------------------
@app.route('/select_interval')
@login_required
def select_interval():
    """Render the interval selection page with calendar widgets"""
    return render_template('select_interval.html')

@app.route("/review_statistics", methods=["POST"])
@login_required
def review_statistics():
    try:
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        
        # Validate dates were provided
        if not start_date or not end_date:
            flash('Please select both start and end dates', 'error')
            return redirect(url_for('select_interval'))

        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d') + timedelta(days=1)

        
        # Get top 5 songs
        top_songs = (
            db.session.query(
                ListeningHistory.track_name,
                ListeningHistory.artist_name,
                ListeningHistory.album_name,
                func.count(ListeningHistory.track_name).label("play_count")
            )
            .filter(
                ListeningHistory.user_id == current_user.id,
                ListeningHistory.played_at >= start_date,
                ListeningHistory.played_at <= end_date
            )
            .group_by(ListeningHistory.track_name, ListeningHistory.artist_name, ListeningHistory.album_name)
            .order_by(func.count(ListeningHistory.track_name).desc())
            .limit(5)
            .all()
        )
        
        # Get top 3 artists
        top_artists = (
            db.session.query(
                ListeningHistory.artist_name,
                func.count(ListeningHistory.artist_name).label("play_count")
            )
            .filter(
                ListeningHistory.user_id == current_user.id,
                ListeningHistory.played_at >= start_date,
                ListeningHistory.played_at <= end_date
            )
            .group_by(ListeningHistory.artist_name)
            .order_by(func.count(ListeningHistory.artist_name).desc())
            .limit(3)
            .all()
        )
        
        # Get top album
        top_album = (
            db.session.query(
                ListeningHistory.album_name,
                ListeningHistory.artist_name,
                func.count(ListeningHistory.album_name).label("play_count")
            )
            .filter(
                ListeningHistory.user_id == current_user.id,
                ListeningHistory.played_at >= start_date,
                ListeningHistory.played_at <= end_date
            )
            .group_by(ListeningHistory.album_name, ListeningHistory.artist_name)
            .order_by(func.count(ListeningHistory.album_name).desc())
            .first()
        )
        
        # Get Spotify client
        sp = spotify.get_spotify_client()
        album_covers = {}
        artist_images = {}
        
        if sp:
            # Get album covers for songs and top album
            unique_albums = {(song.album_name, song.artist_name) for song in top_songs}
            if top_album:
                unique_albums.add((top_album.album_name, top_album.artist_name))
                
            for album_name, artist_name in unique_albums:
                try:
                    first_artist = artist_name.split(",")[0].strip()
                    album_search = sp.search(q=f"album:{album_name} artist:{first_artist}", type="album", limit=1)
                    if album_search['albums']['items']:
                        album_covers[(album_name, artist_name)] = album_search['albums']['items'][0]['images'][0]['url']
                    else:
                        track_search = sp.search(q=f"track:{album_name} artist:{first_artist}", type="track", limit=1)
                        if track_search['tracks']['items']:
                            album_covers[(album_name, artist_name)] = track_search['tracks']['items'][0]['album']['images'][0]['url']
                except Exception as e:
                    print(f"Error fetching album cover for {album_name}: {str(e)}")
                    album_covers[(album_name, artist_name)] = None
            
            # Get artist images
            unique_artists = {artist.artist_name for artist in top_artists}
            for artist_name in unique_artists:
                try:
                    artist_search = sp.search(q=f"artist:{artist_name}", type="artist", limit=1)
                    if artist_search['artists']['items']:
                        artist_images[artist_name] = artist_search['artists']['items'][0]['images'][0]['url'] if artist_search['artists']['items'][0]['images'] else None
                except Exception as e:
                    print(f"Error fetching artist image for {artist_name}: {str(e)}")
                    artist_images[artist_name] = None
        
        # Format songs with covers
        formatted_songs = [
            {
                "track_name": song.track_name,
                "artist_name": song.artist_name,
                "album_name": song.album_name,
                "play_count": song.play_count,
                "image_url": album_covers.get((song.album_name, song.artist_name)) or 
                            url_for('static', filename='images/default-song.jpg')
            }
            for song in top_songs
        ]
        
        # Format artists with images
        formatted_artists = [
            {
                "artist_name": artist.artist_name,
                "play_count": artist.play_count,
                "image_url": artist_images.get(artist.artist_name) or 
                            url_for('static', filename='images/default-artist.jpg')
            }
            for artist in top_artists
        ]
        
        # Format top album
        # Format top album
        formatted_album = None
        if top_album:
            formatted_album = {
                "album_name": top_album.album_name,
                "artist_name": top_album.artist_name,
                "play_count": top_album.play_count,
                "image_url": album_covers.get((top_album.album_name, top_album.artist_name)) or 
                         url_for('static', filename='images/default-album.jpg')
            }
        else:
            formatted_album = {
                'album_name': 'No albums played',
                'artist_name': '',
                'play_count': 0,
                'image_url': url_for('static', filename='images/default-album.jpg')
            }



        return render_template('review_statistics.html',
                            top_songs=formatted_songs,
                            top_artists=formatted_artists,
                            top_album=formatted_album,
                            start_date=start_date.date(),
                            end_date=(end_date - timedelta(days=1)).date())
        
    except Exception as e:
        flash('Error processing your request: ' + str(e), 'error')
        return redirect(url_for('select_interval'))
    

@app.route('/artist_top_tracks', methods=['GET'])
def artist_top_tracks():
    artist_name = request.args.get('artist_name', '').strip()
    top_tracks = []
    sp = spotify.get_spotify_client()

    if artist_name:
        # Uzklausa i duomenu baze norint gauti populiariausias dainas
        results = (
            db.session.query(
                ListeningHistory.track_name,
                db.func.count(ListeningHistory.track_name).label('listen_count'),
                ListeningHistory.artist_name  # Pridedame atlikejo pavadinima
            )
            .filter_by(user_id=current_user.id)
            .filter(ListeningHistory.artist_name.ilike(f'%{artist_name}%'))
            .group_by(ListeningHistory.track_name, ListeningHistory.artist_name)
            .order_by(desc('listen_count'))
            .limit(10)
            .all()
        )

        # Uzklausa Spotify API, kad gautume albumo virselius
        for track in results:
            track_name = track.track_name
            artist_name = track.artist_name
            
            # Ieskome dainos Spotify pagal atlikeja ir dainos pavadinima
            search_result = sp.search(q=f"track:{track_name} artist:{artist_name}", type='track', limit=1)
            
            # Tikriname, ar yra daina
            if search_result['tracks']['items']:
                album_cover_url = search_result['tracks']['items'][0]['album']['images'][0]['url']
            else:
                album_cover_url = None  # Jei nerandame virselio, paliekame None
            
            top_tracks.append({
                'track_name': track_name,
                'listen_count': track.listen_count,
                'album_cover_url': album_cover_url  # Pridedame albumo virselio nuoroda
            })

    return render_template('artist_top_tracks.html', top_tracks=top_tracks, artist_name=artist_name)



#----------------------------------TEST---------------------------------------------------

@app.route('/index')
def index():
    return render_template('index.html')




# ----------------------- IDK KAS CIA BET TURI LIKT GALE ---------------------------------
if(__name__) == '__main__':
    app.run('localhost', 4449, debug = True)

# Pull test