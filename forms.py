from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, validators


class LoginForm(FlaskForm):
    username = StringField('Username')
    password = PasswordField('Password')
    submit = SubmitField('Login')


class SignUpForm(FlaskForm):
    first_name = StringField('First Name', [validators.Length(min=1, max=20)])
    email = StringField('Email', [validators.Length(min=1, max=40)])
    username = StringField('Username', [validators.Length(min=1, max=20)])
    password = PasswordField('Password', [validators.Length(min=1, max=40)])
    sign_up = SubmitField('Sign Up')

class ReviewForm(FlaskForm):
    rating = IntegerField('Rating', [validators.NumberRange(0,5)])
    url = StringField('URL', [validators.Length(min=1, max=256)])
    review = SubmitField('Review')