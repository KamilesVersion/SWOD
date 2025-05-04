# import spotipy
# from spotipy.oauth2 import SpotifyOAuth
# import os
# from datetime import datetime
# from models import db
# from flask import current_app, session, url_for
# from flask_login import current_user

# class SpotifyService:
#     def __init__(self):
#         self.sp_oauth = None # Delay initialization until we have an app context
        
#     def create_spotify_oauth(self):
#         with current_app.app_context(): # Ensures we are inside the app context
#             return SpotifyOAuth(
#                 client_id=os.getenv("SPOTIFY_CLIENT_ID"),
#                 client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
#                 redirect_uri=url_for("spotify_callback", _external=True),
#                 scope="user-top-read user-read-recently-played playlist-modify-private",
#                 show_dialog=True
#             )
    
#     def get_spotify_client(self):
#         if current_user.is_authenticated and current_user.spotify_access_token:
#             if self.sp_oauth is None:
#                 self.sp_oauth = self.create_spotify_oauth()
        
#             # Tikrina, ar pasibaig  prieigos  etono galiojimo laikas
#             if datetime.utcnow() > current_user.spotif_token_expiry:
#                 new_token_info = self.sp_oauth.refresh_access_token(current_user.spotify_refresh_token)
#                 current_user.spotify_access_token = new_token_info["access_token"]
#                 current_user.spotif_token_expiry = datetime.utcfromtimestamp(new_token_info["expires_at"])
#                 db.session.commit()  #  ra ome atnaujintus duomenis   duomen  baz 
        
#             return spotipy.Spotify(auth=current_user.spotify_access_token)
#         return None
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from datetime import datetime
from models import db
from flask import current_app, session, url_for
from flask_login import current_user

class SpotifyService:
    def __init__(self):
        self.sp_oauth = None # Delay initialization until we have an app context

    def create_spotify_oauth(self):
        with current_app.app_context(): # Ensures we are inside the app context
            return SpotifyOAuth(
                client_id="70b586f5779b40c1854ac700da6567ab",
                client_secret="b0d6ca74bb024a38aa3780c5ed71f5dd",
                #client_id=os.getenv("SPOTIFY_CLIENT_ID"),
                #client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
                redirect_uri="https://lauzav.pythonanywhere.com/spotify_callback",
                scope="user-top-read user-read-recently-played playlist-modify-private",
                show_dialog=True
            )

    def get_spotify_client(self):
        if current_user.is_authenticated and current_user.spotify_access_token:
            if self.sp_oauth is None:
                self.sp_oauth = self.create_spotify_oauth()

            # Tikrina, ar pasibaig  prieigos  etono galiojimo laikas
            if datetime.utcnow() > current_user.spotif_token_expiry:
                new_token_info = self.sp_oauth.refresh_access_token(current_user.spotify_refresh_token)
                current_user.spotify_access_token = new_token_info["access_token"]
                current_user.spotif_token_expiry = datetime.utcfromtimestamp(new_token_info["expires_at"])
                db.session.commit()  #  ra ome atnaujintus duomenis   duomen  baz

            return spotipy.Spotify(auth=current_user.spotify_access_token)
        return None