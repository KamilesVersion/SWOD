# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError, Optional
import re
from models import User

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

    # Remove current_user dependency from validators
    def validate_new_username(self, new_username):
        from flask_login import current_user
        if new_username.data and hasattr(current_user, 'username') and new_username.data != current_user.username:
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