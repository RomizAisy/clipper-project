from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField, SelectField, URLField
from wtforms.validators import InputRequired, URL, Optional


class AutosubFileForm(FlaskForm):
    subtitleStyle = SelectField(u'Subtitle Style', 
                                choices=[('default_movie', 'Default Movie'),
                                         ('default_portrait', 'Default Portrait'),
                                         ('pop', 'Pop'),
                                         ('tiktok', 'Tiktok'),
                                         ('boxed','Boxed')], 
                                         default= 'default_portrait'

    )
    file = FileField("File" , validators=[Optional()])
    video_url  = URLField(
        "Video URL",
        validators=[Optional(), URL()],
        render_kw={"placeholder": "Paste YouTube / TikTok link"}
    )
    submit = SubmitField("Upload File Auto Subtitle")