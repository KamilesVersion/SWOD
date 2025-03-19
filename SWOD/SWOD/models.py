class models(object):
    """description of class"""
    
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime


db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)
    
    # Spotify tokens
    spotify_access_token = db.Column(db.String(255), nullable=True)
    spotify_refresh_token = db.Column(db.String(255), nullable=True)
    spotif_token_expiry = db.Column(db.DateTime, nullable=True)


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



