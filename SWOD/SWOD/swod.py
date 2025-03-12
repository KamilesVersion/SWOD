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
    

# -------------------------------------------------------------- klausymo baze
    
class ListeningHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) 
    artist_name = db.Column(db.String(255), nullable=False)
    track_name = db.Column(db.String(255), nullable=False)
    album_name = db.Column(db.String(255), nullable=False)
    duration_ms = db.Column(db.Integer, nullable=False)
    played_at = db.Column(db.DateTime, nullable=False)
    genre = db.Column(db.String(255), nullable=True)

    user = db.relationship('User', backref=db.backref('listening_history', lazy=True))



migrate = Migrate(app, db)

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
            not re.search(r'[!@#$%^&*(),. ":{}|<>]', pwd) or 
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

    sp = get_spotify_client()  # Naudojame get_spotify_client funkcij
    if not sp:
        return redirect(url_for("connect_spotify", next=url_for("recent")))

    # Fetch last 20 played tracks
    recent_tracks = sp.current_user_recently_played(limit=50)

    lithuania_tz = pytz.timezone('Europe/Vilnius')
    tracks = []

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
        artist_id = track['artists'][0]['id']  # Taking the first artist's ID
        artist_info = sp.artist(artist_id)  # Get artist info
        artist_genres = artist_info.get('genres', [])
        genre = artist_genres[0] if artist_genres else None  # Take the first genre if exists

        # Check for duplicates (by played_at and user_id)
        existing_track = ListeningHistory.query.filter_by(
            played_at=played_at_utc,
            user_id=current_user.id
        ).first()

        # If track does not exist, insert it into database
        if not existing_track:
            new_history = ListeningHistory(
                user_id=current_user.id,
                artist_name=", ".join(artist['name'] for artist in track['artists']),
                track_name=track['name'],
                album_name=track['album']['name'],
                duration_ms=track['duration_ms'],
                played_at=played_at_utc,  # Save in UTC format
                genre=genre  # Add genre
            )
            db.session.add(new_history)
            db.session.commit()

        # For display purposes
        tracks.append({
            'name': track['name'],
            'artist': ", ".join(artist['name'] for artist in track['artists']),
            'album': track['album']['name'],
            'album_cover': track['album']['images'][0]['url'] if track['album']['images'] else None,
            'played_at': played_at_lt.strftime("%Y-%m-%d %H:%M:%S"),  # Format as Lithuanian time
            'genre': genre  # Include genre in display data
        })

    return render_template('recent.html', tracks=tracks)



# -------------------------------------------------------------- SENA
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

#     # Fetch last 20 played tracks
#     #sp = spotipy.Spotify(auth=token_info["access_token"])
#     #recent_tracks = sp.current_user_recently_played(limit=20)

#     sp = get_spotify_client()  # Naudojame get_spotify_client funkcij 
#     if sp:
#         recent_tracks = sp.current_user_recently_played(limit=20)
#     else:
#         return redirect(url_for("connect_spotify", next=url_for("recent")))  # Jei n ra galiojan io tokeno

#     # Define Lithuanian time zone
#     lithuania_tz = pytz.timezone('Europe/Vilnius')

#     # Extract necessary track details
#     tracks = []
#     for item in recent_tracks['items']:
#         track = item['track']
        
#         # Convert played_at to Lithuanian time zone
#         # played_at_utc = datetime.strptime(item['played_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
#         # played_at_utc = played_at_utc.replace(tzinfo=pytz.utc)
#         # played_at_lt = played_at_utc.astimezone(lithuania_tz)

# # Convert played_at to Lithuanian time zone
#         try:
#             played_at_utc = datetime.strptime(item['played_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
#         except ValueError:
#             played_at_utc = datetime.strptime(item['played_at'], "%Y-%m-%dT%H:%M:%SZ")
#         played_at_utc = played_at_utc.replace(tzinfo=pytz.utc)
#         played_at_lt = played_at_utc.astimezone(lithuania_tz)


#         tracks.append({
#             'name': track['name'],
#             'artist': ", ".join(artist['name'] for artist in track['artists']),
#             'album': track['album']['name'],
#             'album_cover': track['album']['images'][0]['url'] if track['album']['images'] else None,
#             'played_at': played_at_lt.strftime("%Y-%m-%d %H:%M:%S")  # Format as Lithuanian time
#         })

#     return render_template('recent.html', tracks=tracks)



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

# PRAEJUSIOS SAVAITES RECAP------------------------------------------------------
@app.route('/last-week-recap')
@login_required
def last_week_recap():
    return render_template('last_week.html');

# PRAEJUSIOS DIENOS RECAP------------------------------------------------------
@app.route('/yesterday_recap')
@login_required
def yesterday_recap():
    return render_template('yesterday_recap.html');

#LABIAUSIAI KLAUSOMIAUSIA DAINA--------------------------------------------------

# # # @app.route("/most_listened_song")
# # # def most_listened_song():
# # #     token_info = session.get("token_info", None)

# # #     if not token_info:
# # #         return redirect(url_for("login"))
# # #     sp = get_spotify_client()  # Naudojame get_spotify_client funkcij 
# # #     if sp:
# # #         top_tracks = sp.current_user_top_tracks(limit=1, time_range="long_term")
# # #         if top_tracks["items"]:
# # #             song = top_tracks["items"][0]
# # #             return f"Your most listened song is: {song['name']} by {song['artists'][0]['name']}"
# # #         return "No listening data found!"
# # #     else:
# # #         return redirect(url_for("connect_spotify"))  # Jei n ra galiojan io tokeno

    # sp = spotipy.Spotify(auth=token_info["access_token"])
    
    # # Fetch user's top tracks (long-term, i.e., most listened songs)
    # top_tracks = sp.current_user_top_tracks(limit=1, time_range="long_term")

    # if top_tracks["items"]:
    #     song = top_tracks["items"][0]
    #     song_name = song["name"]
    #     artist_name = song["artists"][0]["name"]
    #     return f"Your most listened song is: {song_name} by {artist_name}"
    
    # return "No listening data found!"

    



# @app.route("/most_listened_song_json")
# def most_listened_song_json():
#     # Pirmiausia bandome gauti Spotify klient 
#     sp = get_spotify_client()  

#     if not sp:
#         return {"error": "User not authenticated"}, 401  # Jei n ra galiojan io tokeno

#     # Gauti top dainas (ilgalaik s)
#     top_tracks = sp.current_user_top_tracks(limit=1, time_range="long_term")

#     if top_tracks["items"]:
#         song = top_tracks["items"][0]
#         return {"song": song["name"], "artist": song["artists"][0]["name"]}

#     return {"song": None, "artist": None}

# # # # # # @app.route("/most_listened_song_json")
# # # # # # def most_listened_song_json():
# # # # # #     # Try to get the Spotify client
# # # # # #     sp = get_spotify_client()  

# # # # # #     if not sp:
# # # # # #         return {"error": "User not authenticated"}, 401  # If no valid token exists

# # # # # #     # Fetch top tracks (long-term)
# # # # # #     top_tracks = sp.current_user_top_tracks(limit=1, time_range="long_term")

# # # # # #     if top_tracks["items"]:
# # # # # #         song = top_tracks["items"][0]
# # # # # #         song_name = song["name"]
# # # # # #         artist_name = song["artists"][0]["name"]

# # # # # #         # Get album cover URL (assuming the first album in the list)
# # # # # #         album_cover_url = song["album"]["images"][0]["url"] if song["album"]["images"] else None

# # # # # #         # Return song details along with the album cover URL
# # # # # #         return {
# # # # # #             "song": song_name,
# # # # # #             "artist": artist_name,
# # # # # #             "album_cover": album_cover_url
# # # # # #         }

# # # # # #     # Return a default response if no data is found
# # # # # #     return {"song": None, "artist": None, "album_cover": None}

@app.route("/most_listened_song_json")
def most_listened_song_json():
    most_listened_song = db.session.query(
        ListeningHistory.artist_name, ListeningHistory.track_name
    ).group_by(
        ListeningHistory.artist_name, ListeningHistory.track_name
    ).order_by(db.func.count().desc()).limit(1).first()
    

    if most_listened_song:
        artist_name, track_name = most_listened_song
        response = {
            "song": track_name,
            "artist": artist_name,
        }
    else:
        response = {"song": None, "artist": None}
    
    return jsonify(response)



#-------------------------------------------------------------------------------
#FAVE AUTLIKEJAS

@app.route("/most_listened_artist_json")
def most_listened_artist_json():
    most_listened_artist = db.session.query(
        ListeningHistory.artist_name
    ).group_by(
        ListeningHistory.artist_name
    ).order_by(db.func.count().desc()).limit(1).first()
    
    if most_listened_artist:
        artist_name = most_listened_artist[0]  # Extract the artist name from the tuple
        response = {
            "artist": artist_name,
        }
    else:
        response = {"artist": None}
    
    return jsonify(response)


# # # # @app.route("/most_listened_artist")
# # # # def most_listened_artist():
# # # #     token_info = session.get("token_info", None)

# # # #     if not token_info:
# # # #         return redirect(url_for("login"))

# # # #     sp = get_spotify_client()  # Use the get_spotify_client function
# # # #     if sp:
# # # #         top_artists = sp.current_user_top_artists(limit=1, time_range="long_term")
# # # #         if top_artists["items"]:
# # # #             artist = top_artists["items"][0]
# # # #             artist_name = artist["name"]
# # # #             return f"Your most listened artist is: {artist_name}"
# # # #         return "No listening data found!"
# # # #     else:
# # # #         return redirect(url_for("connect_spotify"))  # Redirect to the connect page if the user is not authenticated

# # # # @app.route("/most_listened_artist_json")
# # # # def most_listened_artist_json():
# # # #     # Try to get the Spotify client
# # # #     sp = get_spotify_client()

# # # #     if not sp:
# # # #         return jsonify({"error": "User not authenticated"}), 401  # If no valid token exists

# # # #     # Fetch top artists (long-term)
# # # #     top_artists = sp.current_user_top_artists(limit=1, time_range="long_term")

# # # #     if top_artists["items"]:
# # # #         artist = top_artists["items"][0]
# # # #         artist_name = artist["name"]

# # # #         # Get artist image URL (assuming the first image in the list)
# # # #         artist_image_url = artist["images"][0]["url"] if artist["images"] else None

# # # #         # Return artist details along with the image URL
# # # #         return jsonify({
# # # #             "artist": artist_name,
# # # #             "artist_image": artist_image_url
# # # #         })

# # # #     # Return a default response if no data is found
# # # #     return jsonify({"artist": None, "artist_image": None})




@app.route('/most_listened_genre_json')
@login_required
def most_listened_genre_json():
    user_id = current_user.id

    # Query the most frequently listened genres, ignoring NULL values
    genre_counts = (
        db.session.query(ListeningHistory.genre, db.func.count().label('count'))
        .filter(ListeningHistory.user_id == user_id, ListeningHistory.genre.isnot(None))  # Ignore NULL genres
        .group_by(ListeningHistory.genre)
        .order_by(db.func.count().desc())
        .limit(2)  # Get top two genres
        .all()
    )

    # Check if there are results
    if genre_counts:
        # If the first genre is somehow NULL, take the second one if available
        if genre_counts[0][0] is None and len(genre_counts) > 1:
            genre = genre_counts[1][0]  # Use second most listened genre
        else:
            genre = genre_counts[0][0]  # Use the most listened genre

        return jsonify({'genre': genre})

    return jsonify({'genre': 'No data available'})



#-------------------------------------------------------------------------------

if(__name__) == '__main__':
    app.run('localhost', 4449, debug = True)


# Pull test