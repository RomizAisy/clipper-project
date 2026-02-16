from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField, URLField, SelectField
from wtforms.validators import InputRequired, URL, Optional


class AspectFileForm(FlaskForm):
    file = FileField("File" , validators=[Optional()])
    video_url  = URLField(
        "Video URL",
        validators=[Optional(), URL()],
        render_kw={"placeholder": "Paste YouTube / TikTok link"}
    )
    aspectRatio = SelectField(u'Aspect Ratio', 
                                choices=[('portrait', 'Portrait'),
                                         ('landscape', 'Landscape'),
                                         ('original', 'Original')], 
                                         default= 'original'
    )
    submit = SubmitField("Convert Video")