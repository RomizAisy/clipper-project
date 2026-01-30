from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField, SelectField
from wtforms.validators import InputRequired


class AutosubFileForm(FlaskForm):
    subtitleStyle = SelectField(u'Subtitle Style', choices=[('default', 'Default'),('pop', 'Pop'),('tiktok', 'Tiktok'),('boxed','Boxed')], default= 'default'

    )
    file = FileField("File" , validators=[InputRequired()])
    submit = SubmitField("Upload File Auto Subtitle")