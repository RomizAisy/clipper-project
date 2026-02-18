from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField, URLField, SelectField
from wtforms.validators import InputRequired, URL, Optional


class ClipperFileForm(FlaskForm):
    file = FileField("File" , validators=[Optional()])
    video_url  = URLField(
        "Video URL",
        validators=[Optional(), URL()],
        render_kw={"placeholder": "Paste YouTube / TikTok link"}
    )
    subtitleStyle = SelectField(u'Subtitle Style', 
                                choices=[('default_movie', 'Default Movie'),
                                         ('default_portrait', 'Default Portrait'),
                                         ('pop', 'Pop'),
                                         ('tiktok', 'Tiktok'),
                                         ('boxed','Boxed')], 
                                         default= 'default_portrait'
    )
    aspectRatio = SelectField(u'Aspect Ratio', 
                                choices=[('portrait', 'Portrait'),
                                         ('landscape', 'Landscape'),
                                         ('original', 'Original')], 
                                         default= 'original'
    )
    submit = SubmitField("Process")