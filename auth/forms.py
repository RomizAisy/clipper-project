from flask_wtf import FlaskForm 
from wtforms import StringField, PasswordField,EmailField, validators
from wtforms.validators import DataRequired


#USER LOGIN FORM
class LoginForm(FlaskForm):
    username = StringField('Username:',  [validators.Length(min=4, max=25)])
    password = PasswordField ('password', [validators.InputRequired()])

#USER REGISTER FORM
class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

#ADMINs REGISTER FORM
class AdminLoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
