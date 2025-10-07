from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length


class LoginForm(FlaskForm):
    username = StringField("Логин", validators=[DataRequired(), Length(min=2, max=64)])
    password = PasswordField("Пароль", validators=[DataRequired(), Length(min=3, max=128)])
    submit = SubmitField("Войти")
