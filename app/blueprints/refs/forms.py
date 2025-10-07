from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp
from ...models import CodeType

class RefCodeForm(FlaskForm):
    code = StringField(
        "Код (ровно 5 цифр)",
        validators=[
            DataRequired(),
            Length(min=5, max=5, message="Ровно 5 символов"),
            Regexp(r"^\d{5}$", message="Допускаются только цифры"),
        ],
        render_kw={"placeholder": "например, 12045", "inputmode": "numeric", "maxlength": 5},
    )
    name = StringField("Наименование", validators=[DataRequired(), Length(max=128)])
    type_id = SelectField("Тип кода", coerce=int, validators=[DataRequired()])
    status = SelectField(
        "Статус",
        choices=[("active", "Активен"), ("inactive", "Не активен")],
        default="active",
        validators=[DataRequired()],
    )
    submit = SubmitField("Сохранить")

    def set_type_choices(self):
        self.type_id.choices = [(t.id, t.name) for t in CodeType.query.order_by(CodeType.name.asc()).all()]


class QuickTypeForm(FlaskForm):
    name = StringField("Новый тип", validators=[DataRequired(), Length(max=64)])
    submit = SubmitField("Добавить")
